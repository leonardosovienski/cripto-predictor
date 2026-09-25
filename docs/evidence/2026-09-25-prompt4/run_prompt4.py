"""Execução do Prompt 4 (na raiz do repositório, sem rede):

  <python do venv> run_prompt4.py <inventario.json> <ledger_execucoes.jsonl> <saida.json>

1. sela o holdout em `docs/research_ledger/holdouts.jsonl` (versionado; ID imutável: se já
   estiver selado, não sela de novo);
2. roda a reavaliação (`research.reevaluation.run_reevaluation`). O ledger de execuções recebido
   deve ser a continuação do ledger do Prompt 3c: o histórico é preservado, nunca apagado.
"""

import json
import sys
from pathlib import Path

from GarimpoInvestimentos.analyzers.trials import TRIALS_PATH
from GarimpoInvestimentos.research import holdout, reevaluation
from GarimpoInvestimentos.run_ledger import RunLedger

EVIDENCE = Path("docs/evidence/2026-09-25-prompt4")
HOLDOUT_LEDGER = Path("docs/research_ledger/holdouts.jsonl")
HOLDOUT_ID = "cripto-holdout-btcusdt-20260926-20270326"

inventory, runs, out = (Path(a) for a in sys.argv[1:4])
HOLDOUT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
holdouts = RunLedger(HOLDOUT_LEDGER)
if holdout.holdout_state(holdouts, HOLDOUT_ID) == "NOT_SEALED":
    holdout.seal_holdout(
        holdouts,
        holdout_id=HOLDOUT_ID,
        universe=(
            "todos os dados de mercado do BTCUSDT (spot e perpétuo UM; qualquer frequência; preço, "
            "volume, funding e OI) com timestamp no intervalo"
        ),
        interval_utc=("2026-09-26T00:00:00Z", "2027-03-26T00:00:00Z"),
        content_rule=(
            "no fechamento da janela: sha256 do JSON canônico (sort_keys) dos candles diários spot "
            "BTCUSDT da Binance no intervalo, [open_ms, close], coletados uma vez e gravados com "
            "register_content_hash ANTES de qualquer abertura"
        ),
        opening_conditions=[
            "janela encerrada e hash do conteúdo registrado no ledger antes da abertura",
            "hipótese pré-registrada no ledger com o template completo do Prompt 4, depois da "
            "vigência da política v1 e antes da abertura, apontando este holdout",
            "período de desenvolvimento da hipótese fora do intervalo (assert_outside_holdouts)",
            "avaliação de desenvolvimento registrada no ledger com decisão GO pela política vigente",
            "aprovação humana do dono para esta abertura (approved_by, approved_at_utc, evidência)",
            "uma única avaliação no holdout, sem nenhum ajuste depois da abertura",
        ],
    )
report = reevaluation.run_reevaluation(
    ledger_path=runs,
    out_path=out,
    paths={
        "scientific_state": Path("charters/scientific_state.json"),
        "trials": TRIALS_PATH,
        "h6_status": Path("GarimpoInvestimentos/h6_status.json"),
        "inventory": inventory,
        "fm_report": Path("docs/evidence/2026-09-24-prompt3c/report.json"),
        "fm_prereg": Path("docs/evidence/2026-09-24-prompt3c/preregistro.json"),
    },
    protocol=json.loads((EVIDENCE / "protocol.json").read_text(encoding="utf-8")),
)
print(
    json.dumps(
        {
            "run_id": report["run_id"],
            "holdout": holdout.holdout_state(holdouts, HOLDOUT_ID),
            "rows": {
                r["hypothesis"]: [r["status_new_protocol"], r["status_new"]] for r in report["rows"]
            },
            "n_trials": report["n_trials"]["all_families"],
        },
        ensure_ascii=False,
    )
)
