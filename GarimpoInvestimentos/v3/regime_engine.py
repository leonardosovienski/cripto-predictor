"""
Regime Engine — Hidden Markov Model para detecção de estado de mercado.

MODELO:
    GaussianHMM com 3 estados latentes (Bull / Bear / Sideways).
    Emissão: [log_return_8h, realized_vol_24h] — Gaussiana multivariada.
    Treinamento: Baum-Welch (offline, sobre série in-sample).
    Inferência: Forward Algorithm CAUSAL — sem lookahead bias.

ANTI-LOOKAHEAD (CRÍTICO):
    hmmlearn.predict_proba() usa forward-backward (Viterbi), que olha
    para o FUTURO da série. Isso é PROIBIDO em backtesting.
    Este módulo implementa o Forward Algorithm passo a passo:
        α_t(i) = B_i(x_t) × Σ_j [α_{t-1}(j) × A_{j,i}]
    que usa apenas x_{0:t} — causal por construção.

RÓTULOS DE ESTADO:
    Após treinamento, os estados são rotulados automaticamente pelo
    retorno médio do estado:
        bull     = estado com maior retorno médio
        sideways = estado intermediário
        bear     = estado com menor retorno médio

OUTPUT (RegimeOutput):
    hmm_state       int    — índice bruto do HMM (0/1/2)
    hmm_state_label str    — "bull" / "bear" / "sideways"
    hmm_posterior   list   — [P(s0|x), P(s1|x), P(s2|x)] — CAUSAL
    hmm_entropy     float  — entropia normalizada [0,1]; > 0.85 = incerto
    is_uncertain    bool   — True se entropia > ENTROPY_THRESHOLD
"""

import logging
import math
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)

N_STATES = 3
ENTROPY_THRESHOLD = 0.85  # H_norm > 0.85 → sistema em modo de observação
_LOG_N = math.log(N_STATES)

_COVARIANCE_TYPE = "full"  # tipo de covariância do GaussianHMM (usado no fit e no fingerprint)
_MAX_FIT_RETRIES = (
    5  # tentativas de random_state alternativa se o EM não convergir p/ covariância válida
)

# --- Provenância do modelo serializado (espelha o config_hash do wc-predictor) ---
# Um .pkl é um modelo treinado sob um CONTRATO: features de emissão, nº de estados,
# tipo de covariância. Se o contrato muda no código mas o .pkl em cache é velho, o
# load() serviria um HMM incoerente com o que o feature_builder calcula — bug
# silencioso e caro. O fingerprint carimba o contrato no save e o valida no load.
#
# MODEL_SCHEMA_VERSION é a alavanca MANUAL: incremente quando a SEMÂNTICA das
# features de emissão mudar (ex.: realized_vol passa de 24h p/ 12h) — é o que um
# hash de estrutura não pega sozinho.
MODEL_SCHEMA_VERSION = 1
_EMISSION_FEATURES = ("log_return_8h", "realized_vol_24h")  # ordem = colunas de X no fit

# H7 (macro/DXY, docs/HYPOTHESES.md): covariáveis extras OPCIONAIS na emissão do
# HMM. Nomeadas explicitamente (não uma lista genérica) para manter o contrato de
# fingerprint auditável — adicionar uma covariável nova exige decidir o nome aqui,
# não só passar mais uma coluna. Default (extra_features=()) preserva EXATAMENTE o
# comportamento de H1-H3: mesmas 2 features, mesmo fingerprint, mesmo .pkl válido.
_SUPPORTED_EXTRA_FEATURES = ("macro_event_dummy", "dxy_return_1d")


class StaleRegimeModelError(RuntimeError):
    """O .pkl carregado foi treinado sob um contrato de features/HMM incompatível
    com o código atual. Retreine o modelo em vez de servir previsões incoerentes."""


def _covariance_type_for(extra_features: tuple[str, ...]) -> str:
    """ "full" para H1-H3 (2 features, comportamento congelado, NUNCA muda).
    "diag" quando há extra_features (H7+): achado em produção (2026-09-04) —
    "full" com 4 dimensões e estados raros (às vezes <1% da amostra por fold IS
    de ~180d/~540 obs) converge, via EM, para covariância quase singular; TODOS
    os 15 folds do primeiro backtest H7 real dispararam 'Model is not
    converging', vários colapsaram para 1 estado efetivo. Não é falta de sorte
    de seed (o retry de seeds alternativas ajudou em 2/15 folds e mesmo assim
    um fold esgotou o orçamento) — é subamostragem estrutural de "full" nessa
    janela/dimensionalidade. "diag" estima variância por feature (sem
    covariância cruzada entre elas), removendo a superfície onde a matriz pode
    ficar não-positiva-definida. Decisão tomada ANTES de qualquer leitura OOS
    do H7 contar (nenhum fold produziu veredito válido até aqui) — é correção
    de infraestrutura, não reação a um resultado científico."""
    return "diag" if extra_features else _COVARIANCE_TYPE


def _model_fingerprint(extra_features: tuple[str, ...] = ()) -> dict:
    """Contrato estrutural do modelo — o que torna um .pkl compatível (ou não).

    `extra_features` entra no fingerprint por nome: um modelo treinado com H7
    (macro/DXY) nunca é carregável como se fosse H1-H3 (e vice-versa) — o guard
    de StaleRegimeModelError em load() já existente protege isso sem código novo.
    `covariance_type` também entra — diverge entre H1-H3 ("full") e H7+ ("diag"),
    então esse fingerprint sozinho já barra qualquer mistura dos dois."""
    return {
        "schema_version": MODEL_SCHEMA_VERSION,
        "n_states": N_STATES,
        "covariance_type": _covariance_type_for(extra_features),
        "emission_features": list(_EMISSION_FEATURES) + list(extra_features),
    }


# Importação lazy de dependências pesadas para não quebrar testes leves
try:
    import numpy as np
    from hmmlearn import base as _hmmlearn_base
    from hmmlearn import hmm as _hmmlearn
    from hmmlearn import utils as _hmmlearn_utils
    from sklearn.preprocessing import StandardScaler

    def _hmmlearn_normalize(a, axis=None):
        a_sum = a.sum(axis)
        if axis and a.ndim > 1:
            a_sum[a_sum == 0] = 1
            shape = list(a.shape)
            shape[axis] = 1
            a_sum = np.reshape(a_sum, shape)
        a /= a_sum

    # Monkey-patch do hmmlearn: o `normalize` original levanta em linhas com
    # soma zero; a versão acima tolera (soma 0 → 1). Necessário para a
    # decodificação causal `_forward_causal` com emissões degeneradas.
    # FRÁGIL a upgrades: validado contra a versão pinada em uv.lock; se o
    # hmmlearn mudar a assinatura/semântica de `normalize`, este patch deve
    # ser revisto (há teste: tests/test_v3_hmm_no_lookahead.py).
    import hmmlearn as _hmmlearn_pkg

    _HMMLEARN_PATCHED_VERSION = _hmmlearn_pkg.__version__
    _hmmlearn_utils.normalize = _hmmlearn_normalize
    if hasattr(_hmmlearn_base, "normalize"):
        _hmmlearn_base.normalize = _hmmlearn_normalize

    _DEPS_OK = True
except ImportError as _e:
    _DEPS_OK = False
    _IMPORT_ERR = str(_e)


# ------------------------------------------------------------------ #
# Contrato de saída                                                   #
# ------------------------------------------------------------------ #


@dataclass
class RegimeOutput:
    hmm_state: int
    hmm_state_label: str  # "bull" / "bear" / "sideways"
    hmm_posterior: list[float]  # [P(state_i|x_{0:t})] — CAUSAL
    hmm_entropy: float  # entropia normalizada [0,1]
    is_uncertain: bool  # True se entropia > ENTROPY_THRESHOLD

    # Pesos sugeridos para os motores de sinal condicionados ao regime
    # (usados pelo signal_engine; pode ser sobrescrito pelo pipeline)
    signal_weights: dict[str, float] = field(default_factory=dict)


_REGIME_WEIGHTS = {
    "bull": {
        "funding_pressure": 0.55,  # longs overcrowded → pressão de short
        "oi_divergence": 0.30,
        "volatility_context": 0.15,
    },
    "bear": {
        "funding_pressure": 0.50,  # shorts overcrowded → pressão de long
        "oi_divergence": 0.35,
        "volatility_context": 0.15,
    },
    "sideways": {
        "funding_pressure": 0.40,
        "oi_divergence": 0.30,
        "volatility_context": 0.30,
    },
}


# ------------------------------------------------------------------ #
# Forward Algorithm causal (sem lookahead)                            #
# ------------------------------------------------------------------ #


def _emission_probs(x: "np.ndarray", means: "np.ndarray", covars: "np.ndarray") -> "np.ndarray":
    """
    P(x | state=i) para cada estado i — log-space para estabilidade numérica.
    Gaussiana multivariada implementada manualmente (sem scipy) para manter
    a dependência apenas em numpy.
    """
    n_states, n_features = means.shape
    log_probs = np.zeros(n_states)
    for i in range(n_states):
        diff = x - means[i]
        cov = covars[i]  # full covariance
        try:
            sign, log_det = np.linalg.slogdet(cov)
            if sign <= 0:
                log_probs[i] = -1e300
                continue
            inv_cov = np.linalg.inv(cov)
            mahal = float(diff @ inv_cov @ diff)
            log_probs[i] = -0.5 * (n_features * math.log(2 * math.pi) + log_det + mahal)
        except np.linalg.LinAlgError:
            log_probs[i] = -1e300
    # Normalizar para escala linear (soft-max estável)
    log_probs -= log_probs.max()
    probs = np.exp(log_probs)
    return probs


def _forward_causal(
    X_scaled: "np.ndarray",
    startprob: "np.ndarray",
    transmat: "np.ndarray",
    means: "np.ndarray",
    covars: "np.ndarray",
) -> "np.ndarray":
    """
    Forward Algorithm passo a passo — causal por construção.

    Retorna alpha de shape (T, K) onde alpha[t, i] = P(s_t=i | x_{0:t}).
    NÃO usa observações futuras — seguro para backtesting.

    Equação de recursão:
        α_0(i) = π_i × B_i(x_0)
        α_t(i) = B_i(x_t) × Σ_j [α_{t-1}(j) × A_{j,i}]
        normalizar α_t a cada passo (log-sum-exp evita underflow).
    """
    T, _ = X_scaled.shape
    K = len(startprob)
    alpha = np.zeros((T, K))

    # Inicialização
    B0 = _emission_probs(X_scaled[0], means, covars)
    alpha[0] = startprob * B0
    total = alpha[0].sum()
    alpha[0] = alpha[0] / total if total > 1e-300 else np.ones(K) / K

    # Recursão
    for t in range(1, T):
        Bt = _emission_probs(X_scaled[t], means, covars)
        predicted = transmat.T @ alpha[t - 1]  # shape (K,)
        alpha[t] = predicted * Bt
        total = alpha[t].sum()
        alpha[t] = alpha[t] / total if total > 1e-300 else np.ones(K) / K

    return alpha


# ------------------------------------------------------------------ #
# Motor principal                                                     #
# ------------------------------------------------------------------ #


class RegimeEngine:
    """
    HMM Gaussiano 3-estados para classificação de regime de mercado.

    Ciclo de vida:
        1. fit(log_returns, realized_vols)  — treina sobre série in-sample
        2. predict(log_returns, realized_vols) — infere regime (causal) para toda a série
        3. predict_last(log_returns, realized_vols) — infere apenas o último ponto
        4. save(path) / load(path)          — persistência do modelo treinado
    """

    def __init__(
        self,
        model_path: Path | None = None,
        extra_features: tuple[str, ...] = (),
    ) -> None:
        """`extra_features`: subconjunto de `_SUPPORTED_EXTRA_FEATURES`, na ordem em
        que serão concatenadas após [log_return_8h, realized_vol_24h]. Vazio (default)
        = comportamento idêntico a H1-H3. Usado por H7 (macro/DXY) — ver
        docs/HYPOTHESES.md."""
        unknown = set(extra_features) - set(_SUPPORTED_EXTRA_FEATURES)
        if unknown:
            raise ValueError(
                f"extra_features desconhecidas: {sorted(unknown)}. "
                f"Suportadas: {_SUPPORTED_EXTRA_FEATURES}"
            )
        self._extra_features = tuple(extra_features)
        self._model = None
        self._scaler: StandardScaler | None = None
        self._state_map: dict[int, str] = {}  # HMM state idx → label
        if model_path and model_path.exists():
            self.load(model_path)

    # ---------------------------------------------------------------- #
    # Treinamento                                                       #
    # ---------------------------------------------------------------- #

    def fit(
        self,
        log_returns: list[float],
        realized_vols: list[float],
        extra_covariates: list[list[float]] | None = None,
    ) -> None:
        """
        Treina o HMM via Baum-Welch sobre a série in-sample.
        Exige hmmlearn, numpy, scikit-learn.

        `extra_covariates`: colunas adicionais, na mesma ordem de `extra_features`
        passado ao construtor. Obrigatório (mesmo nº de colunas) se `extra_features`
        não é vazio; deve ser None/omitido se `extra_features` é vazio — o par
        (construtor, chamada) tem que concordar, senão é bug de wiring, não de dado.
        """
        if not _DEPS_OK:
            raise ImportError(
                f"Dependências ausentes para RegimeEngine: {_IMPORT_ERR}. "
                "Execute: pip install hmmlearn scikit-learn numpy"
            )
        if len(log_returns) != len(realized_vols):
            raise ValueError("log_returns e realized_vols devem ter o mesmo tamanho")
        if len(log_returns) < 30:
            raise ValueError(
                f"Série muito curta para treinar HMM: {len(log_returns)} obs. "
                "Mínimo recomendado: 100 (30 dias × 3 períodos/dia)."
            )
        columns = [log_returns, realized_vols]
        columns.extend(self._validate_extra_covariates(extra_covariates, len(log_returns)))

        X = np.column_stack(columns)
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        # covariance_type="full" com mais dimensões (extra_features) e estados raros
        # (ex.: "bull" com <5% da amostra) pode convergir, durante o EM, para uma
        # covariância quase singular — hmmlearn só usa min_covar para inicializar,
        # não para regularizar cada M-step de covariância "full". A trajetória do EM
        # é sensível ao random_state; retry com seeds alternativas (prática padrão
        # em EM/HMM sensível a inicialização) resolve sem mudar covariance_type nem
        # alterar o sinal. Achado em produção rodando H7 (2026-09-04): fold quebrou
        # com 'covars must be symmetric, positive-definite' na seed default.
        # random_state=42 continua a PRIMEIRA tentativa sempre — H1-H3 (sem
        # extra_features) nunca precisou de retry nos testes/produção, então o
        # comportamento default permanece byte-idêntico (mesma seed, mesma primeira
        # tentativa, sem esse laço alterar o resultado quando converge de primeira).
        last_err: ValueError | None = None
        model = None
        for attempt in range(_MAX_FIT_RETRIES):
            seed = 42 + attempt
            candidate = _hmmlearn.GaussianHMM(
                n_components=N_STATES,
                covariance_type=_COVARIANCE_TYPE,
                n_iter=300,
                tol=1e-5,
                random_state=seed,
                verbose=False,
            )
            try:
                candidate.fit(X_scaled)
            except ValueError as exc:
                last_err = exc
                logger.warning(
                    "RegimeEngine.fit: seed=%d nao convergiu para covariancia valida (%s); tentando seed=%d",
                    seed,
                    exc,
                    seed + 1,
                )
                continue
            model = candidate
            if seed != 42:
                logger.warning(
                    "RegimeEngine.fit: convergiu apenas com seed=%d (default 42 instavel para este dataset/features)",
                    seed,
                )
            break
        if model is None:
            raise RuntimeError(
                f"RegimeEngine.fit: HMM nao convergiu para covariancia valida em "
                f"{_MAX_FIT_RETRIES} tentativas de seed (42..{42 + _MAX_FIT_RETRIES - 1}). "
                f"Ultimo erro: {last_err}"
            ) from last_err
        self._model = model

        # Rotular estados pelo retorno médio (bull > sideways > bear)
        all_states = model.predict(X_scaled)
        mean_ret_by_state = {
            i: float(np.array(log_returns)[all_states == i].mean())
            for i in range(N_STATES)
            if (all_states == i).sum() > 0
        }
        sorted_states = sorted(mean_ret_by_state, key=mean_ret_by_state.__getitem__, reverse=True)
        label_order = ["bull", "sideways", "bear"]
        self._state_map = {s: label_order[rank] for rank, s in enumerate(sorted_states)}

        logger.info("RegimeEngine treinado com %d observações.", len(log_returns))
        logger.info("Mapa de estados: %s", self._state_map)
        for s, label in self._state_map.items():
            n_obs = (all_states == s).sum()
            pct = 100 * n_obs / len(all_states)
            logger.info(
                "  Estado %d (%s): %.1f%% das obs, retorno médio=%.6f",
                s,
                label,
                pct,
                mean_ret_by_state.get(s, 0.0),
            )

    # ---------------------------------------------------------------- #
    # Inferência — CAUSAL (sem lookahead)                              #
    # ---------------------------------------------------------------- #

    def _validate_extra_covariates(
        self, extra_covariates: list[list[float]] | None, n: int
    ) -> list[list[float]]:
        """Confere que `extra_covariates` bate exatamente com `self._extra_features`
        (contagem e tamanho de cada coluna). Levanta ValueError em qualquer
        descompasso — silenciosamente ignorar/preencher seria mascarar um erro de
        wiring como se fosse comportamento normal."""
        n_expected = len(self._extra_features)
        provided = extra_covariates or []
        if len(provided) != n_expected:
            raise ValueError(
                f"extra_covariates tem {len(provided)} coluna(s), esperado "
                f"{n_expected} (extra_features={self._extra_features})"
            )
        for name, col in zip(self._extra_features, provided, strict=True):
            if len(col) != n:
                raise ValueError(
                    f"extra_covariates[{name!r}] tem {len(col)} pontos, "
                    f"esperado {n} (mesmo tamanho de log_returns)"
                )
        return provided

    def predict_series(
        self,
        log_returns: list[float],
        realized_vols: list[float],
        extra_covariates: list[list[float]] | None = None,
    ) -> list[RegimeOutput]:
        """
        Infere o regime para cada ponto da série usando o Forward Algorithm.
        O output[t] usa apenas x_{0:t} — sem lookahead.
        Retorna lista de RegimeOutput alinhada com a série de entrada.

        `extra_covariates`: mesma regra de fit() — precisa bater com as
        `extra_features` declaradas no construtor.
        """
        if self._model is None or self._scaler is None:
            raise RuntimeError("RegimeEngine não foi treinado. Chame fit() primeiro.")

        columns = [log_returns, realized_vols]
        columns.extend(self._validate_extra_covariates(extra_covariates, len(log_returns)))
        X = np.column_stack(columns)
        # cast: o stub do sklearn infere um tipo de retorno espúrio p/ transform()
        X_scaled = cast("np.ndarray", self._scaler.transform(X))
        covars = self._model.covars_
        assert covars is not None

        alpha = _forward_causal(
            X_scaled,
            self._model.startprob_,
            self._model.transmat_,
            self._model.means_,
            covars,
        )

        results = []
        for t in range(len(alpha)):
            posterior = alpha[t].tolist()
            state = int(np.argmax(alpha[t]))
            label = self._state_map.get(state, "unknown")
            entropy = _entropy_norm(posterior)
            results.append(
                RegimeOutput(
                    hmm_state=state,
                    hmm_state_label=label,
                    hmm_posterior=[round(p, 6) for p in posterior],
                    hmm_entropy=round(entropy, 4),
                    is_uncertain=entropy > ENTROPY_THRESHOLD,
                    signal_weights=_REGIME_WEIGHTS.get(label, {}),
                )
            )
        return results

    def predict_last(
        self,
        log_returns: list[float],
        realized_vols: list[float],
    ) -> RegimeOutput | None:
        """
        Infere apenas o regime do último ponto — wrapper conveniente
        para uso em tempo real (alimentar a janela completa, receber apenas o último).
        """
        series = self.predict_series(log_returns, realized_vols)
        return series[-1] if series else None

    # ---------------------------------------------------------------- #
    # Persistência                                                      #
    # ---------------------------------------------------------------- #

    def save(self, path: Path) -> None:
        if self._model is None:
            raise RuntimeError("Nada para salvar — modelo não foi treinado.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "model": self._model,
                    "scaler": self._scaler,
                    "state_map": self._state_map,
                    "fingerprint": _model_fingerprint(self._extra_features),
                },
                f,
            )
        logger.info("RegimeEngine salvo em %s", path)

    def load(self, path: Path) -> None:
        """Carrega um modelo treinado, validando a provenância do contrato.

        - fingerprint ausente  → modelo legado (salvo antes do guard): avisa e segue
          (compatibilidade de migração; o próximo save carimba).
        - fingerprint diferente → StaleRegimeModelError: o contrato de features/HMM
          mudou, o modelo em cache é incoerente — retreine."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        saved_fp = data.get("fingerprint")
        current_fp = _model_fingerprint(self._extra_features)
        if saved_fp is None:
            logger.warning(
                "RegimeEngine: modelo legado em %s sem fingerprint de provenância — "
                "compatibilidade de features não verificável; recomendado retreinar.",
                path,
            )
        elif saved_fp != current_fp:
            raise StaleRegimeModelError(
                f"Modelo em {path} incompatível com o código atual.\n"
                f"  salvo: {saved_fp}\n  atual: {current_fp}\n"
                "Retreine: python -m GarimpoInvestimentos.v3.pipeline --symbol <SYM> "
                "--start-date <YYYY-MM-DD> --force-refresh"
            )
        self._model = data["model"]
        self._scaler = data["scaler"]
        self._state_map = data["state_map"]
        logger.info("RegimeEngine carregado de %s (estado_map=%s)", path, self._state_map)

    @property
    def is_trained(self) -> bool:
        return self._model is not None


# ------------------------------------------------------------------ #
# Utilitários                                                         #
# ------------------------------------------------------------------ #


def _entropy_norm(posterior: list[float]) -> float:
    """Entropia de Shannon normalizada: H/log(K) ∈ [0,1]."""
    h = -sum(p * math.log(max(p, 1e-12)) for p in posterior)
    return h / _LOG_N if _LOG_N > 0 else 0.0
