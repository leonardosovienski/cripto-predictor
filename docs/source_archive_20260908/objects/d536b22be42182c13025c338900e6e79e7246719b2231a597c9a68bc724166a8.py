import gzip
import hashlib
import json
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

WORK = Path(__file__).resolve().parent
ROOT = WORK / "cripto-research"
OUTPUTS = WORK.parent / "outputs"
DATA = WORK / "immediate-audit-data"
EXTRA = WORK / "immediate-intra-hour-check"
EVIDENCE = ROOT / "docs/evidence/immediate_audit_20260908"
sys.path.insert(0, str(ROOT))
from scripts.run_immediate_audit import verify


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


verify()
before = json.loads((EVIDENCE / "preservation_before.json").read_bytes())
assert all(sha(Path(name).read_bytes()) == digest for name, digest in before.items())
original = WORK.parent.parent / "files-mentioned-by-the-user-cripto/work/cripto-v1.2"
assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=original).strip()
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=original).decode().strip() == "fbf4c714a092668bc1b82942ebdececd396e3ab7"
r = json.loads((DATA / "results.json").read_bytes())
a = json.loads((DATA / "decimal-audit.json").read_bytes())
samples = json.loads((DATA / "live_samples.json").read_bytes())
extra = json.loads((EXTRA / "result.json").read_bytes())
assert a["status"] == "PASS" and extra["status"] == "NO_SETTLEMENTS_RETURNED"
for meta in json.loads((EXTRA / "sources.json").read_bytes()):
    assert sha(gzip.decompress((EXTRA / meta["raw_file"]).read_bytes())) == meta["sha256"]
cross = [s["snapshot"]["cross_source"] for s in samples if s["snapshot"]]
assert len(cross) == 11 and all(c["status"] == "CONSISTENT_WITHIN_50BPS" for c in cross)
validation = {
    "checked_utc": datetime.now(UTC).isoformat(), "technical_status":"PASS",
    "economic_conclusion":"Recent historical positive profit did not survive registered adverse costs",
    "historical":r["historical"], "live":r["live"], "accounting_audit":a,
    "cross_source":{"valid_pairs":len(cross), "maximum_absolute_bps":max(abs(c["difference_bps"]) for c in cross),
                    "binance_funding_authenticated_by_okx":False},
    "funding_within_live_window":{"public_events":0,"separate_public_query":True,"account_receipts_certified":False},
    "public_requests_main":r["public_requests"], "public_requests_additional_check":1,
    "full_pytest":{"passed":1167,"new_cases":8,"seconds":106.95,"exit_code":0},
    "relevant_tests_before_collection":57,"ruff":"PASS","pyright_errors":0,
    "original_runtime":{"status":"PASS","files_checked":3785},
    "old_deliveries_and_observer_files_unchanged":len(before),
    "original_repository_clean":True,"old_strategies_changed":False,"orders":0,
    "external_audit_completed":False,"future_profit_proven":False,
    "carry_84day_automation_activated":False,
    "sources":{
        "spot_api":"https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md",
        "futures_fee_example":"https://www.binance.com/en/support/faq/detail/360033544231",
        "private_commission_endpoint":"https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account#user-commission-rate",
        "okx_public_api":"https://app.okx.com/docs-v5/en/"
    }
}
write(EVIDENCE / "validation.json", validation)
write(EVIDENCE / "preservation_after.json", {"status":"PASS","verified_files":len(before),"before_record_sha256":sha((EVIDENCE/"preservation_before.json").read_bytes())})

report = """# Coleta e auditoria feitas agora — BTC, 08/09/2026

Foi possível coletar dados públicos e conferir as contas agora. O resultado recente **não sustentou lucro positivo sob os custos adversos registrados**. A diferença é entre executar uma auditoria hoje e já possuir 84 dias de observações futuras; a segunda coisa ainda não existe.

## Resultado dos 84 dias encerrados

Período: **16/06/2026, 00h UTC, a 08/09/2026, 00h UTC**. Referência de **5.000 USDT por cenário**, com até 1.250 USDT na perna spot. Uma posição hipotética de 0,018 BTC comprada no spot e vendida no perpétuo, quantidade fixa. Cada cenário é financiado separadamente.

| Cenário | Lucro/prejuízo modelado | Retorno sobre 5.000 USDT |
|---|---:|---:|
| Base | **+10,56 USDT** | +0,211% |
| Adverso | **−6,97 USDT** | −0,139% |
| Estresse | **−21,65 USDT** | −0,433% |

O funding líquido de sinais, antes de aplicar custos, somou 17,22 USDT. A mudança do diferencial entre os preços das pernas contribuiu −0,12 USDT. No cenário base, taxas e deslizamento assumidos consumiram 6,54 USDT. No adverso, consumiram 18,32 USDT, acrescidos de 5,75 USDT de custo fixo proporcional. No estresse, somente funding positivo foi reduzido à metade e foi descontado um choque inicial adicional de 0,5% do valor spot.

Foram verificadas **251 liquidações de funding** e **2.016 horas de mark price**. Os drawdowns calculados pelas marcas diárias de encerramento foram aproximadamente 0,124%, 0,339% e 0,470%, respectivamente. Houve 1, 1 e 4 semanas negativas entre as 12 semanas. O caixa separado permaneceu positivo no teste horário registrado com salto adicional de 30%; isso não certifica as regras reais de liquidação da corretora.

As entradas e saídas históricas usam aberturas de candles com custos assumidos. Não existem livros históricos de ofertas ou execuções reais certificados para esses pontos. A abertura do candle final foi isolada de sua máxima, mínima e fechamento. **83 dos 84 dias já estavam dentro do período anteriormente consultado**: baixar os dados novamente não os transforma em teste independente fora da amostra.

## O que foi observado ao vivo

Entre aproximadamente **03h40 e 03h45 de Brasília**, foram obtidos **11 pares válidos de livros Binance spot/perp**, espaçados por 30 segundos. A primeira e a última cotações foram fixadas pelo protocolo; não houve escolha posterior de uma entrada favorável. A duração entre elas foi de 300,12 segundos.

O preço spot BTC/USDT também foi consultado na **OKX** nos 11 momentos. A maior diferença absoluta entre os preços médios foi **0,873 ponto-base**, aproximadamente **0,00873%**. As amostras cumpriram as verificações de horário, validade dos livros e tolerância entre fontes. Isso confere a consistência dos preços; a OKX não autentica os eventos internos de funding da Binance e não certifica negócios simultâneos.

Para a posição hipotética de 0,015 BTC, as marcas de encerramento após cinco minutos foram:

| Cenário | Resultado modelado de entrada e saída |
|---|---:|
| Base | **−5,87 USDT** |
| Adverso | **−16,45 USDT** |
| Estresse | **−22,34 USDT** |

A variação do diferencial das pernas contribuiu apenas +0,0126 USDT. O cenário base descontou 5,8809 USDT de taxas/deslizamento de entrada e saída. Uma consulta pública adicional de funding estritamente entre as duas cotações não retornou pagamentos. Uma janela de cinco minutos serve para verificar custos e cotações; não substitui um teste de carry mantido por 84 dias. Nenhuma hora inteira ficou contida no intervalo; a margem horária dessa observação curta permanece não certificada.

O diagnóstico separado de comissão cobrada em BTC calculou compra bruta de 0,01502000 BTC, posição vendida de 0,015 BTC e residual de aproximadamente 0,39 USDT. É uma hipótese de tarifa/ativo da comissão, não uma informação da conta e não lucro criado.

## O que passou na auditoria

- **44 respostas públicas** da rodada principal, mais **uma consulta** adicional de funding, com dados brutos, URLs, horários e hashes preservados.
- Reconstrução histórica com **Decimal**, por implementação separada que não importa o normalizador ou o motor contábil principal.
- **334 comparações numéricas**, com maior diferença de aproximadamente **0,00000000000178 USDT**. Conferência de funding, custos, resultado, margem, curvas diárias e semanas.
- Conferência do diário encadeado: decisões anteriores às cotações, resultados ligados às respostas brutas e ausência de troca dos pontos de entrada/saída.
- **1.167 testes aprovados**, incluindo oito novos; Ruff passou e Pyright não encontrou erros. O runtime original passou na verificação de 3.785 arquivos.
- Código congelado antes da coleta. Relatórios antigos e os diários de carry prospectivo e altcoins foram preservados. Nenhuma ordem, conta autenticada ou movimentação de dinheiro.

As duas implementações foram feitas pelo mesmo assistente. A segunda corretora é uma segunda fonte para os preços, mas **não houve auditoria externa de autoria**.

## O que continua desconhecido

As taxas públicas servem como referência: a [documentação Binance de futuros](https://www.binance.com/en/support/faq/detail/360033544231) exemplifica a cobrança pelo valor da operação. A tarifa efetiva da conta é fornecida por um [endpoint autenticado](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account#user-commission-rate), que não foi acessado. Execuções reais, tributos, residência fiscal, conversão para reais e regras efetivas de margem não podem ser certificados por essa coleta pública.

O acompanhamento futuro de 84 dias não foi adiantado nem iniciado retroativamente. A automação nova continua não criada, pelo limite já registrado de uma automação por tarefa; esta coleta imediata não alterou a de altcoins.

**Conclusão:** a coleta e a auditoria disponíveis agora foram feitas. Os dados recentes mostram que o ganho é pequeno e desaparece com custos adversos; ainda não há evidência suficiente para classificar esta estratégia como fonte confiável de lucro líquido futuro.

## Arquivos reproduzíveis

`CRIPTO_AUDITORIA_AGORA.zip` contém código e congelamento, testes, protocolo, diário, respostas públicas, cálculos e auditoria. O `README.md` do pacote explica a reprodução offline. `CRIPTO_AUDITORIA_AGORA.json` registra as métricas e verificações; `CRIPTO_AUDITORIA_AGORA_SHA256.json` identifica a entrega.
"""
report_path = OUTPUTS / "CRIPTO_AUDITORIA_AGORA.md"
report_path.write_text(report, encoding="utf-8")
(EVIDENCE / "RESULTADOS.md").write_bytes(report_path.read_bytes())

freeze = json.loads((EVIDENCE / "freeze.json").read_bytes())
files = {name:(ROOT/name).read_bytes() for name in freeze["files"]}
for path in EVIDENCE.rglob("*"):
    if path.is_file():
        files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
files["README.md"] = (EVIDENCE / "REPRODUZIR.md").read_bytes()
files["CRIPTO_AUDITORIA_AGORA.md"] = report_path.read_bytes()
for folder, prefix in ((DATA,"data"),(EXTRA,"intra-hour-check")):
    for path in folder.rglob("*"):
        if path.is_file():
            files[prefix+"/"+path.relative_to(folder).as_posix()] = path.read_bytes()
files["FILES_SHA256.json"] = json.dumps({n:sha(raw) for n,raw in files.items()},indent=2).encode()
package = OUTPUTS / "CRIPTO_AUDITORIA_AGORA.zip"
with ZipFile(package,"x",compression=ZIP_DEFLATED,compresslevel=9) as archive:
    for name,raw in sorted(files.items()):
        archive.writestr(name,raw)
extract = WORK / "immediate-package-check"
extract.mkdir(exist_ok=False)
with ZipFile(package) as archive:
    for name in archive.namelist():
        assert (extract/name).resolve().is_relative_to(extract.resolve())
    archive.extractall(extract)
manifest = json.loads((extract/"FILES_SHA256.json").read_bytes())
assert all(sha((extract/n).read_bytes())==v for n,v in manifest.items())
tests = subprocess.run([sys.executable,"-m","pytest","-q","tests/test_immediate_audit.py","tests/test_research_corrections.py","tests/test_carry_forward.py","tests/test_carry_public.py"],cwd=extract,text=True,capture_output=True)
print(tests.stdout,flush=True)
assert tests.returncode==0,tests.stderr
offline = '''import json,socket
from pathlib import Path
from scripts.audit_immediate_decimal import audit
from scripts.run_immediate_audit import verify
def blocked(*args, **kwargs):
    raise AssertionError("Network forbidden in offline audit")
socket.socket.connect=blocked
verify()
r=audit(Path("data"),Path("docs/evidence/immediate_audit_20260908/protocol.json"))
old=json.loads(Path("data/decimal-audit.json").read_bytes())
assert r==old
print(json.dumps(r))
'''
run = subprocess.run([sys.executable,"-c",offline],cwd=extract,text=True,capture_output=True)
print(run.stdout,flush=True)
assert run.returncode==0,run.stderr
validation["extracted_package"] = {"files_verified":len(manifest),"tests_passed":57,"accounting_audit_identical":True,
    "network_blocked_during_audit":True,"package_sha256":sha(package.read_bytes()),"bytes":package.stat().st_size}
write(OUTPUTS/"CRIPTO_AUDITORIA_AGORA.json",validation)
names = ("CRIPTO_AUDITORIA_AGORA.md","CRIPTO_AUDITORIA_AGORA.json","CRIPTO_AUDITORIA_AGORA.zip")
write(OUTPUTS/"CRIPTO_AUDITORIA_AGORA_SHA256.json",{"outputs":{n:sha((OUTPUTS/n).read_bytes()) for n in names}})
write(EVIDENCE/"delivery_receipt.json",validation["extracted_package"])
assert all(sha(Path(name).read_bytes())==digest for name,digest in before.items())
print(json.dumps(validation["extracted_package"]))
