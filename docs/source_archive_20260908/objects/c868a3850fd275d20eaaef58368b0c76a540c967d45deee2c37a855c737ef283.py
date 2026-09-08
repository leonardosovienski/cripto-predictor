import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

WORK = Path(__file__).resolve().parent
ROOT = WORK / "cripto-research"
OUTPUTS = WORK.parent / "outputs"
EVIDENCE = ROOT / "docs/evidence/corrections_20260908"
FORWARD = ROOT / "docs/evidence/carry_forward_20260908"
DATA = WORK / "carry-forward-data"
sys.path.insert(0, str(ROOT))
from scripts.carry_forward_math import opening
from scripts.observe_carry_forward import verify
from scripts.research_io import Ledger


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


protocol, freeze_hash = verify()
ledger = Ledger(DATA / "ledger.jsonl")
assert len(ledger.rows) == 1 and ledger.rows[0]["kind"] == "PREFLIGHT"
preflight = ledger.rows[0]["payload"]
snapshot = preflight["snapshot"]
position_diagnostic = opening(snapshot, protocol)
assert len(snapshot["sources"]) == 6 and all(s["status"] == 200 and s["complete_response"] for s in snapshot["sources"])
status = json.loads((DATA / "status.json").read_bytes())
assert status["phase"] == "WAITING" and status["entry_observed"] is False
assert status["ledger_head"] == ledger.rows[-1]["sha256"]
receipt = {
    "checked_utc": datetime.now(UTC).isoformat(), "code_commit_before_network": "3f4a1f1",
    "status": "PASS", "public_requests": len(snapshot["sources"]),
    "public_bytes": sum(len(__import__("gzip").decompress((DATA / s["raw_file"]).read_bytes())) for s in snapshot["sources"]),
    "maximum_request_seconds": max(s["monotonic_elapsed_ns"] / 1e9 for s in snapshot["sources"]),
    "clock_offsets_ms": snapshot["clock_offsets_ms"],
    "quote_utc": datetime.fromtimestamp(snapshot["quote_ns"] / 1e9, UTC).isoformat(),
    "actual_entry_recorded": False, "ledger_rows": 1, "ledger_head": status["ledger_head"],
    "pre_start_tick_ledger_unchanged": True, "code_freeze_sha256": freeze_hash,
    "three_cost_entry_calculation_diagnostic": position_diagnostic,
    "orders": 0, "real_profit": None, "prospective_outcome": None,
    "meaning": "Only a public preflight; no synthetic entry was written to the prospective journal."
}
write(FORWARD / "preflight_receipt.json", receipt)
validation = json.loads((EVIDENCE / "validation.json").read_bytes())
validation["preflight"] = receipt
validation["scheduling"] = json.loads((FORWARD / "scheduling.json").read_bytes())["status"]
write(EVIDENCE / "validation.json", validation)

report = """# Correções da pesquisa de criptomoedas — 08/09/2026

Corrigi as falhas técnicas identificadas e retifiquei as conclusões. A suíte completa passou: **1.159 testes**, incluindo **49 novos casos**. Ruff passou e Pyright não encontrou erros. Isso valida o comportamento testado; não comprova lucro futuro nem ausência de todo defeito possível.

## O que ficou corrigido

- O planejador vigente é a versão 3. Rejeita livros cruzados/desordenados, valores não finitos, horários inválidos, JSON ambíguo e fontes inconsistentes. Falhas devolvem código de saída 1. As versões anteriores permanecem para reprodução histórica.
- A auditoria ganhou um leitor e normalizador separados, usando apenas a biblioteca padrão e sem importar o normalizador anterior. Conciliou **532 respostas públicas e 29 séries**. Continua sendo trabalho do mesmo assistente e da mesma fonte de dados; não é uma auditoria externa.
- O observador de carry BTC usa protocolo e código congelados, decisões persistidas antes das cotações, proteção contra processos simultâneos, diário encadeado, conferência dos dados brutos e estado gravado atomicamente. Uma entrada/saída interrompida não pode ser refeita com preço posterior. Dados ausentes permanecem desconhecidos.
- As contas do observador consideram profundidade dos livros, lotes atuais na entrada e saída, custos explícitos, funding com sinal e caixa de margem separado. Taxas reais da conta, execução simultânea, tributos e liquidação efetiva continuam não certificados.
- A referência vigente distingue retorno histórico acumulado, exposição residual, resultado prospectivo e lucro líquido real. Retira a interpretação de que os testes ou o tamanho dos números demonstraram uma estratégia rentável no futuro.

## Resultado econômico preservado

Nenhuma estratégia histórica foi ajustada para produzir um número melhor. Os **28 arquivos de resultados**, **26 arquivos de código/protocolo congelados** e os pacotes anteriores mantiveram seus hashes. Os **12 planos válidos salvos** mantiveram os campos econômicos. Repositório original, runtime e automação/diário de altcoins foram preservados; a conferência do runtime passou em 3.785 arquivos.

Com referência de 5.000 USDT por cenário, de 01/01/2024 a 07/09/2026:

| Modelo | Base | Adverso |
|---|---:|---:|
| Carry contínuo BTC (AR1) | +424,25 USDT | +341,13 USDT |
| BTC com vencimento (BR1) | +230,17 USDT | +110,07 USDT |

São lucros **modelados e acumulados em 980 dias**, não mensais. O BR1 não melhorou o AR1 e teve apenas cinco operações. Em 2026 até o corte, o AR1 BTC adverso contribuiu apenas 5,75 USDT. Resultados negativos, estratégias sem entradas e custos fixos hipotéticos continuam visíveis na documentação. A redução de aproximadamente 58 USDT de exposição residual em uma cotação não representa lucro criado pelo planejador.

## Acompanhamento preparado; agendamento pendente

O pré-teste passou com **seis requisições públicas**, sem conta autenticada ou ordem. O diário contém somente um registro de pré-teste; o estado é **WAITING**, sem posição prospectiva nem lucro registrado. Uma chamada normal antes do início preservou esse diário.

O protocolo prevê uma única posição hipotética de 84 dias, com coletas às **21h15 de Brasília**, primeira janela em **08/09/2026** e saída em **01/12/2026**. Uma rodada dessa duração não basta para confirmação estatística de lucro.

**A automação nova não foi criada.** O aplicativo recusou uma segunda automação nesta tarefa, que já possui o acompanhamento de altcoins. Solicitei autorização para criar uma tarefa separada, preservando a anterior. O prompt completo está preparado em `docs/evidence/carry_forward_20260908/scheduling.json` no pacote. Sem essa autorização, não há promessa de coleta automática. Não alterei a automação de altcoins nem criei um cron alternativo.

Quando autorizado e agendado, o computador e o aplicativo precisam estar em execução para o acesso aos arquivos locais. [Documentação oficial de tarefas agendadas](https://learn.chatgpt.com/pt-BR/docs/automations).

## Entrega e reprodução

`CRIPTO_CORRECOES_CODIGO_E_EVIDENCIAS.zip` contém o código vigente e suas dependências locais, os 49 testes novos, protocolo/congelamento, registro de falhas e correções, runbook, cotações salvas para reprodução e a fotografia do pré-teste. Não substitua o diário operacional pela cópia do pacote.

Os dados históricos completos continuam nos pacotes anteriores. `CRIPTO_CORRECOES_VERIFICACAO.json` registra os checks e o pré-teste. `CRIPTO_CORRECOES_SHA256.json` identifica os arquivos entregues. A referência consolidada está em `docs/CURRENT_RESEARCH_STATE_20260908.md` dentro do ZIP.

Os campos de lucro real e expectativa futura validada permanecem nulos. A parte que depende de observações futuras, dados reais de conta ou auditoria externa continua explicitamente pendente, em vez de receber uma marca artificial de “resolvido”.
"""
(OUTPUTS / "CRIPTO_CORRECOES.md").write_text(report, encoding="utf-8")

freeze = json.loads((FORWARD / "code_freeze.json").read_bytes())
files = {name: (ROOT / name).read_bytes() for name in freeze["files"]}
files["scripts/__init__.py"] = (ROOT / "scripts/__init__.py").read_bytes()
for folder in (FORWARD, EVIDENCE):
    for path in folder.rglob("*"):
        if path.is_file():
            files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
files["docs/CURRENT_RESEARCH_STATE_20260908.md"] = (ROOT / "docs/CURRENT_RESEARCH_STATE_20260908.md").read_bytes()
files["README.md"] = (FORWARD / "RUNBOOK.md").read_bytes()
files["CRIPTO_CORRECOES.md"] = (OUTPUTS / "CRIPTO_CORRECOES.md").read_bytes()
for folder, prefix in ((WORK / "btc-execution-diagnostic-v1", "saved-quotes"), (DATA, "preflight-snapshot")):
    for path in folder.rglob("*"):
        if path.is_file() and path.name != "observer.lock":
            files[prefix + "/" + path.relative_to(folder).as_posix()] = path.read_bytes()
files["FILES_SHA256.json"] = json.dumps({n: sha(raw) for n, raw in files.items()}, indent=2).encode()
package = OUTPUTS / "CRIPTO_CORRECOES_CODIGO_E_EVIDENCIAS.zip"
assert not package.exists()
with ZipFile(package, "x", compression=ZIP_DEFLATED, compresslevel=9) as archive:
    for name, raw in sorted(files.items()):
        archive.writestr(name, raw)
extract = WORK / "corrections-package-check-02"
extract.mkdir(exist_ok=False)
with ZipFile(package) as archive:
    for name in archive.namelist():
        assert (extract / name).resolve().is_relative_to(extract.resolve())
    archive.extractall(extract)
manifest = json.loads((extract / "FILES_SHA256.json").read_bytes())
assert all(sha((extract / name).read_bytes()) == digest for name, digest in manifest.items())
tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_research_corrections.py", "tests/test_carry_forward.py", "tests/test_carry_public.py"], cwd=extract, text=True, capture_output=True)
print(tests.stdout, flush=True)
assert tests.returncode == 0, tests.stderr
offline = '''import json,socket
from pathlib import Path
from scripts.observe_carry_forward import verify
from scripts.plan_btc_hedge_v3 import replay
def blocked(*args, **kwargs):
    raise AssertionError("Network forbidden in offline reproduction")
socket.socket.connect=blocked
verify()
r=replay(Path("saved-quotes"), Path("replayed-v3.json"))
old=json.loads(Path("docs/evidence/corrections_20260908/net_hedge_plans_v3.json").read_bytes())
assert [p["plan"] for p in r["plans"]]==[p["plan"] for p in old["plans"]]
print("PASS: frozen package, 12 identical plans, network blocked")
'''
check = subprocess.run([sys.executable, "-c", offline], cwd=extract, text=True, capture_output=True)
print(check.stdout, flush=True)
assert check.returncode == 0, check.stderr
validation["package_validation"] = {"extracted_tests_passed": 49, "files_hashes_verified": len(manifest),
    "freeze_verified": True, "saved_quote_plans_equal": 12, "network_blocked_for_replay": True,
    "package_sha256": sha(package.read_bytes()), "package_bytes": package.stat().st_size}
write(OUTPUTS / "CRIPTO_CORRECOES_VERIFICACAO.json", validation)
names = ("CRIPTO_CORRECOES.md", "CRIPTO_CORRECOES_CODIGO_E_EVIDENCIAS.zip", "CRIPTO_CORRECOES_VERIFICACAO.json")
write(OUTPUTS / "CRIPTO_CORRECOES_SHA256.json", {"outputs": {n: sha((OUTPUTS / n).read_bytes()) for n in names}, "supplement_only": True})
write(EVIDENCE / "delivery_receipt.json", validation["package_validation"])
print(json.dumps(validation["package_validation"]))
