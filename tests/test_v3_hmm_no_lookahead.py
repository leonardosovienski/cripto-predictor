"""Auditoria do Risco nº 1 (look-ahead no HMM) — prova de invariância ao truncamento.

Contrato anti-lookahead do regime_engine: o posterior em t depende APENAS de x_{0:t}.
Logo, ESTENDER a série com dados futuros não pode alterar nenhum ponto do passado —
é exatamente o que o teste de invariância exige, bit a bit.

Contraprova incluída: um decodificador SUAVIZADO (forward-backward, gamma) montado
aqui dentro do teste VIOLA a invariância — se um dia a decodificação causal for
trocada por suavização (o erro clássico com hmmlearn.predict_proba), o teste de
invariância acusa, e a contraprova documenta por quê.

Roda com numpy puro (engine stub com parâmetros fixos); o teste com modelo REAL
treinado (Baum-Welch) roda onde hmmlearn/sklearn existem (.venv_v3) e é skipped
nos ambientes leves — mesmo padrão do restante da suíte V3.
"""
import types

import pytest

np = pytest.importorskip("numpy")

from GarimpoInvestimentos.v3.regime_engine import (
    RegimeEngine,
    _emission_probs,
    _forward_causal,
)


class _IdScaler:
    def transform(self, X):
        return np.asarray(X, dtype=float)


def _engine_stub():
    """Engine com parâmetros HMM fixos e válidos — isola a DECODIFICAÇÃO
    (objeto da auditoria) do treinamento (coberto no teste com hmmlearn)."""
    transmat = np.array([[0.90, 0.05, 0.05],
                         [0.05, 0.90, 0.05],
                         [0.05, 0.05, 0.90]])
    means = np.array([[0.8, -0.2], [-0.8, 0.6], [0.0, 0.0]])
    covars = np.stack([np.eye(2) * s for s in (0.5, 0.7, 0.3)])
    eng = RegimeEngine()
    eng._scaler = _IdScaler()  # pyright: ignore[reportAttributeAccessIssue] — duck-typed test double
    eng._model = types.SimpleNamespace(
        startprob_=np.array([1 / 3] * 3),
        transmat_=transmat, means_=means, covars_=covars)
    eng._state_map = {0: "bull", 1: "bear", 2: "sideways"}
    return eng


def _serie(n=200, seed=42):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, 1.0, n).tolist()
    vols = np.abs(rng.normal(0.5, 0.3, n)).tolist()
    return rets, vols


def test_regime_em_t_invariante_a_dados_futuros():
    """O teste pedido pela auditoria: trunca em t, estende com futuro, e exige que
    NADA antes de t mude. Igualdade exata: a recursão alpha é determinística e
    depende só do prefixo."""
    eng = _engine_stub()
    rets, vols = _serie()
    full = eng.predict_series(rets, vols)
    for cut in (50, 120, 199):
        parcial = eng.predict_series(rets[:cut], vols[:cut])
        for t in range(cut):
            assert parcial[t].hmm_posterior == full[t].hmm_posterior, (
                f"LOOKAHEAD: posterior em t={t} mudou quando a série "
                f"foi estendida além de {cut}")
            assert parcial[t].hmm_state == full[t].hmm_state


def test_contraprova_suavizado_viola_a_invariancia():
    """Poder do teste: o decodificador forward-BACKWARD (suavizado) muda o passado
    quando o futuro chega. Se a decodificação causal regredir para suavização,
    o teste de invariância acima FALHA — como deve."""
    eng = _engine_stub()
    rets, vols = _serie(n=80)
    X = np.column_stack([rets, vols])
    m = eng._model
    assert m is not None
    startprob, transmat, means, covars = m.startprob_, m.transmat_, m.means_, m.covars_
    assert covars is not None

    def smoothed(xs):
        T = len(xs)
        alpha = _forward_causal(xs, startprob, transmat, means, covars)
        beta = np.ones((T, 3))
        for t in range(T - 2, -1, -1):
            bt1 = _emission_probs(xs[t + 1], means, covars)
            beta[t] = transmat @ (bt1 * beta[t + 1])
            beta[t] /= beta[t].sum()
        gamma = alpha * beta
        return gamma / gamma.sum(axis=1, keepdims=True)

    cut = 40
    diff = np.abs(smoothed(X)[:cut] - smoothed(X[:cut])).max()
    assert diff > 1e-6, (
        "o suavizado deveria depender do futuro — se não depende, o teste de "
        "invariância não teria poder para detectar a regressão")


def test_invariancia_com_modelo_real_treinado():
    """Mesma invariância com o ciclo COMPLETO (Baum-Welch + scaler congelado no
    fit), como o backtest_v3 usa: treina no IS, infere IS+OOS. Exige hmmlearn."""
    pytest.importorskip("hmmlearn")
    pytest.importorskip("sklearn")

    rng = np.random.default_rng(7)
    # série com regimes de verdade (blocos com médias distintas) p/ o fit convergir
    rets, vols = [], []
    for mu, sigma in ((0.4, 0.8), (-0.5, 1.2), (0.0, 0.4), (0.3, 0.9)):
        rets += rng.normal(mu, sigma, 75).tolist()
        vols += np.abs(rng.normal(sigma, 0.2, 75)).tolist()

    eng = RegimeEngine()
    eng.fit(rets[:150], vols[:150])          # treino SÓ no IS (como o backtest_v3)
    full = eng.predict_series(rets, vols)
    cut = 220
    parcial = eng.predict_series(rets[:cut], vols[:cut])
    for t in range(cut):
        assert parcial[t].hmm_posterior == full[t].hmm_posterior
