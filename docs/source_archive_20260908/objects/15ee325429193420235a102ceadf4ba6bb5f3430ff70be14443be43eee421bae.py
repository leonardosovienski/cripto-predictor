import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

work = Path(__file__).resolve().parent
repo = work / "cripto-v1.2"
old = repo / "docs/evidence/altcoin_profit_20260907"
new = repo / "docs/evidence/altcoin_reviewed_20260907"
new.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dump = lambda p, x: p.write_text(json.dumps(x, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
protocol = json.loads((old / "protocol.json").read_text(encoding="utf-8"))
protocol.update({
    "id": "discovery-altcoin-absolute-profit-20260907-v6-reviewed",
    "base_commit": "5d28a63c1b2a147d17054ace3914de698a7959a4",
    "authorization": "Final review and corrections explicitly requested by user after v5 historical diagnosis. No prospective decisions exist yet.",
    "amendment": "Operational review v6: crash-released OS lock, complete slot accounting, explicit failed-run status. Same training, scorer, universe, costs, schedule and public-only scope. Preserve v4 records under their original profile; use a new v6 data directory.",
    "registered_at": datetime.now(timezone.utc).isoformat(),
    "evidence": "Twelve prospective slots test recorder operation and generate new observations; not automatic proof of profit. Already-consumed v5 historical diagnostic has 140 cash weeks and no selected holdings.",
    "operational_review": {
        "parent_profile": "altcoin_profit_20260907",
        "parent_freeze_sha256": sha(old / "freeze.json"),
        "current_data_directory": "work/altcoin-reviewed-data",
        "locking": "Persistent observer.lock metadata file with OS advisory lock. Process death releases the lock; file existence alone is not a running process. Do not delete it while another process might run.",
        "accounting": "Each weekly selection uses a new fixed 5000 USDT sizing reference. Status sums completed-week hypothetical P&L and reports missing due slots separately; whole-pilot sum remains null until every slot is known. No compounded account equity or actual investor profit claim.",
        "retrospective_outcome": "0 selected holdings in 140 weeks, 0 simulated return; no trading evidence. Scorer remains unmodified.",
        "preserved_legacy": "Old v4 freezes remain immutable and run using their saved source revision/package, not this changed observer. Existing v4 ledger is retained separately.",
    },
})
dump(new / "protocol.json", protocol)
oldfreeze = json.loads((old / "freeze.json").read_text(encoding="utf-8"))
paths = [key for key in oldfreeze["repository_files"] if key != "docs/evidence/altcoin_profit_20260907/protocol.json"]
paths.append("docs/evidence/altcoin_reviewed_20260907/protocol.json")
dump(new / "freeze.json", {
    "known_at": datetime.now(timezone.utc).isoformat(),
    "repository_files": {name: sha(repo / name) for name in paths},
    "acquisition_sha256": oldfreeze["acquisition_sha256"],
    "training_sha256": oldfreeze["training_sha256"],
    "note": "Operational fixes only, before prospective decisions. v4 files and evidence unchanged. New profile reviewed_20260907; scores and marks retain their prior economic assumptions.",
})
text = (old / "RUNBOOK.md").read_text(encoding="utf-8")
text = text.replace("# Objetivo e acompanhamento v4", "# Objetivo e acompanhamento v6 após revisão")
text = text.replace("altcoin-profit-data", "altcoin-reviewed-data").replace("altcoin_profit_20260907", "altcoin_reviewed_20260907")
text += """

Revisão de 07/09: o teste histórico v5 terminou com 140 semanas em caixa e zero operações. A regra continua sem lucro demonstrado. O piloto mantém essa regra para observação, não para buscar parâmetros até aparecer lucro.

O arquivo observer.lock agora pode continuar existindo com o processo encerrado: a exclusão mútua depende do bloqueio do sistema operacional, liberado quando o processo termina. Não apagar o arquivo para tentar obter acesso paralelo.

Ler observation_quality em status.json: known_due_weeks, missing_due_weeks, cash_due_weeks e active_due_weeks. Nenhuma observação significa lucro desconhecido, não zero. Semanas faltantes nunca são apagadas do denominador. standardized_completed_week_profit_usdt soma apenas semanas conhecidas; standardized_pilot_profit_usdt só existe quando todas as 12 semanas têm resultado. São experimentos semanais com tamanho fixo de 5.000 USDT: não apresentar a soma como saldo de uma conta composta. realized_profit e investor_net_brl_profit continuam null.

Se last_run_error não for null ou o processo sair com erro, comunicar a falha conforme a preferência já registrada. Se pilot_finished for verdadeiro, divulgar também as semanas ausentes e o veredito de qualidade; concluir o calendário não significa validar lucro.

O estudo separado de carry tem cenários históricos positivos após custos assumidos. A antiga rejeição por comparação externa foi revista. Isso não muda o seletor spot nem autoriza futuros, margem ou capital.
"""
(new / "RUNBOOK.md").write_text(text, encoding="utf-8")
print(json.dumps({"profile": str(new), "freeze_sha256": sha(new / "freeze.json")}))
