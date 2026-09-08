"""Laço LLM-propõe-hipótese (B9 em docs/HYPOTHESES.md) — o agente escolhe a
DIREÇÃO do raciocínio; o motor determinístico executa o protocolo.

Inverte o papel do LLM em relação a H4/H5/H6, onde ele ERA o preditor (o
`opportunity_score` era a previsão, e foi refutado). Aqui ele propõe hipóteses
falsificáveis, cada uma acompanhada de uma RECIPE no DSL point-in-time; a recipe
é validada contra a whitelist e avaliada por código determinístico, com as MESMAS
funções canônicas que o backtest oficial usa (`spearman_block_ci`,
`overlap_block_length`) — nunca uma reimplementação amaciada.

=== O QUE ESTE MÓDULO NUNCA FAZ, e por quê ===

1. NÃO escreve em `trials.json`. Registrar tentativa é ato humano e exige
   atestado de poder válido + `metric` declarado. Um laço que registra sozinho
   transformaria o denominador do DSR em algo que uma máquina infla à vontade.
2. NÃO emite veredito. Nenhuma saída daqui contém "validado", "GO" ou
   equivalente: veredito exige critério PRÉ-registrado, e um critério lido
   depois do resultado é exatamente o que o pré-registro existe para impedir.
3. NÃO descarta proposta em silêncio. Recipe inválida, duplicada ou malformada
   é REGISTRADA com o motivo. Guardar só as boas mentiria sobre quantas
   tentativas de fato aconteceram — e o denominador honesto é a única coisa que
   dá sentido ao DSR e ao PBO.
4. NÃO promove nada. Promover exige os quatro requisitos do B9.

=== O RISCO QUE ESTE DESENHO CRIA, declarado ===

Um LLM propõe hipóteses baratas e em volume. Gerar 500 fatores e escolher o
melhor É data snooping industrializado — mais rápido que um humano faria à mão,
não mais válido. As contramedidas embutidas: toda proposta entra no traço
append-only (o denominador conta as rejeitadas também) e o `analyzers/pbo.py`
mede, sobre o conjunto avaliado, com que frequência a melhor in-sample cai na
metade pior out-of-sample. PBO alto aqui significa: pare de propor, o processo
de seleção não distingue sinal de sorte.

Uso (offline, com propositor injetado nos testes):
    python -m GarimpoInvestimentos.analyzers.hypothesis_loop --dry-run
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.stats import spearman_block_ci

from GarimpoInvestimentos.analyzers.backtest import overlap_block_length
from GarimpoInvestimentos.analyzers.factor_dsl import _BUILDERS as _DSL_OPS
from GarimpoInvestimentos.analyzers.factor_dsl import (
    Factor,
    RecipeError,
    evaluate,
    from_recipe,
    warmup,
)

# Traço append-only das propostas. `.json` e NÃO `.jsonl` de propósito: o
# .gitignore do projeto captura `*.jsonl` (linha 20), e um traço científico
# invisível ao git seria o mesmo buraco que o h6_status.json veio tapar.
PROPOSALS_PATH = Path(__file__).resolve().parent.parent / "hypothesis_proposals.json"

ACCEPTED = "ACCEPTED_FOR_EVALUATION"
REJECTED_INVALID = "REJECTED_INVALID_RECIPE"
REJECTED_DUPLICATE = "REJECTED_DUPLICATE"
REJECTED_MALFORMED = "REJECTED_MALFORMED_OUTPUT"


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    proposed_at: str
    hypothesis: str
    recipe: dict
    horizon_days: int
    proposer: str
    status: str
    reason: str = ""


@dataclass(frozen=True)
class Evaluation:
    proposal_id: str
    n: int
    rho: float | None
    ic_lower: float | None
    ic_upper: float | None
    warmup_dropped: int
    nota: str = field(
        default=(
            "Estatistica descritiva. NAO e veredito: veredito exige criterio "
            "pre-registrado antes do resultado (docs/HYPOTHESES.md)."
        )
    )


def recipe_fingerprint(recipe: dict) -> str:
    """Identidade estável da recipe. Canonicalizada, então a mesma ideia escrita
    com espaçamento diferente não conta como proposta nova."""
    canonical = json.dumps(recipe, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def vocabulary_doc() -> str:
    """Descrição do vocabulário GERADA da whitelist real. Escrever à mão faria a
    documentação do prompt divergir do que o validador aceita — e o LLM passaria
    a receber instruções sobre operações que não existem."""
    return ", ".join(f"{op}({n} arg)" for op, (n, _) in sorted(_DSL_OPS.items()))


def build_prompt(*, features: Sequence[str], horizon_days: int, historico: str) -> str:
    return f"""Voce e um pesquisador quantitativo. Proponha hipoteses FALSIFICAVEIS
sobre retorno de criptoativos em {horizon_days} dias.

REGRAS INEGOCIAVEIS:
- Cada hipotese precisa de um MECANISMO CAUSAL em 1-2 frases. "O modelo detecta
  padroes" nao e mecanismo.
- Cada hipotese vira uma recipe no DSL abaixo. So estas operacoes existem:
  {vocabulary_doc()}
- Toda operacao le apenas o passado. Nao existe operacao que olhe para frente.
- Features disponiveis: {", ".join(sorted(features))}
- NAO reproponha as familias ja refutadas listadas abaixo, salvo com mecanismo
  causal DIFERENTE e explicitado.

HISTORICO DO QUE JA FOI TENTADO E REFUTADO:
{historico}

Responda SOMENTE um array JSON valido, sem texto ao redor:
[
  {{"hypothesis": "mecanismo causal em 1-2 frases",
    "recipe": {{"op": "zscore", "args": [{{"op": "feature", "args": ["volume"]}}, 20]}}}}
]"""


def parse_proposals(
    texto: str,
    *,
    proposed_at: str,
    proposer: str,
    horizon_days: int,
    vistos: set[str] | None = None,
) -> list[Proposal]:
    """Converte a saida do LLM em propostas. NUNCA levanta por saida ruim do
    modelo: saida ruim vira proposta REGISTRADA com status de rejeicao, porque
    tentativa malformada tambem e tentativa e precisa entrar no denominador."""
    ja_vistos = set(vistos or ())
    limpo = texto.strip()
    if limpo.startswith("```"):
        limpo = limpo.split("```")[1] if "```" in limpo[3:] else limpo[3:]
        limpo = limpo.removeprefix("json").strip()
    try:
        bruto = json.loads(limpo)
    except (json.JSONDecodeError, ValueError) as exc:
        return [
            Proposal(
                proposal_id=hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16],
                proposed_at=proposed_at,
                hypothesis="",
                recipe={},
                horizon_days=horizon_days,
                proposer=proposer,
                status=REJECTED_MALFORMED,
                reason=f"saida nao e JSON valido: {exc}",
            )
        ]
    if not isinstance(bruto, list):
        bruto = [bruto]

    saida: list[Proposal] = []
    for item in bruto:
        hipotese = (item or {}).get("hypothesis", "") if isinstance(item, dict) else ""
        recipe = (item or {}).get("recipe", {}) if isinstance(item, dict) else {}
        fid = recipe_fingerprint(recipe)
        base = dict(
            proposal_id=fid,
            proposed_at=proposed_at,
            hypothesis=str(hipotese),
            recipe=recipe if isinstance(recipe, dict) else {},
            horizon_days=horizon_days,
            proposer=proposer,
        )
        if not isinstance(item, dict) or not isinstance(recipe, dict) or not recipe:
            saida.append(Proposal(**base, status=REJECTED_MALFORMED, reason="item sem recipe"))
            continue
        try:
            from_recipe(recipe)
        except RecipeError as exc:
            saida.append(Proposal(**base, status=REJECTED_INVALID, reason=str(exc)))
            continue
        if fid in ja_vistos:
            saida.append(
                Proposal(**base, status=REJECTED_DUPLICATE, reason="recipe ja proposta antes")
            )
            continue
        ja_vistos.add(fid)
        saida.append(Proposal(**base, status=ACCEPTED))
    return saida


def evaluate_proposal(
    proposal: Proposal, dados: dict[str, list[float | None]], retornos: Sequence[float | None]
) -> Evaluation:
    """Avaliacao determinista com as funcoes canonicas do backtest oficial.
    O warmup do fator e descartado: contar `None` de aquecimento como observacao
    inflaria o n."""
    fator: Factor = from_recipe(proposal.recipe)
    valores = evaluate(fator, dados)
    aquecimento = warmup(fator)
    pares = [
        (v, r)
        for v, r in zip(valores[aquecimento:], retornos[aquecimento:], strict=False)
        if v is not None and r is not None
    ]
    if len(pares) < 3:
        return Evaluation(proposal.proposal_id, len(pares), None, None, None, aquecimento)
    rho, lo, hi = spearman_block_ci(pares, block_length=overlap_block_length(proposal.horizon_days))
    return Evaluation(proposal.proposal_id, len(pares), rho, lo, hi, aquecimento)


def load_proposals(path: Path = PROPOSALS_PATH) -> list[dict]:
    if not path.exists():
        return []
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return dados if isinstance(dados, list) else []


def append_proposals(proposals: Sequence[Proposal], path: Path = PROPOSALS_PATH) -> int:
    """Append-only: le, concatena, reescreve. NUNCA remove nem reescreve linha
    existente — mesmo principio do predictions_archive (migracao 0016)."""
    atuais = load_proposals(path)
    atuais.extend(asdict(p) for p in proposals)
    path.write_text(json.dumps(atuais, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(proposals)


async def _default_proposer(prompt: str) -> str:
    """Adaptador real. Importado tarde para o modulo continuar carregavel (e
    testavel) sem SDK de LLM instalado."""
    from GarimpoInvestimentos.analyzers.ai_insights import _call_gemini

    return await _call_gemini(prompt)


async def run_round(
    *,
    features: Sequence[str],
    horizon_days: int,
    historico: str,
    proposer: Callable | None = None,
    proposer_name: str = "gemini",
    path: Path = PROPOSALS_PATH,
    now: datetime | None = None,
) -> list[Proposal]:
    """Uma rodada: monta prompt, coleta propostas, valida, registra TODAS."""
    prompt = build_prompt(features=features, horizon_days=horizon_days, historico=historico)
    chamar = proposer or _default_proposer
    texto = await chamar(prompt)
    vistos = {p.get("proposal_id") for p in load_proposals(path)}
    propostas = parse_proposals(
        texto,
        proposed_at=(now or datetime.now(UTC)).isoformat(),
        proposer=proposer_name,
        horizon_days=horizon_days,
        vistos={v for v in vistos if v},
    )
    append_proposals(propostas, path)
    return propostas


__all__ = [
    "ACCEPTED",
    "PROPOSALS_PATH",
    "REJECTED_DUPLICATE",
    "REJECTED_INVALID",
    "REJECTED_MALFORMED",
    "Evaluation",
    "Proposal",
    "append_proposals",
    "build_prompt",
    "evaluate_proposal",
    "load_proposals",
    "parse_proposals",
    "recipe_fingerprint",
    "run_round",
    "vocabulary_doc",
]
