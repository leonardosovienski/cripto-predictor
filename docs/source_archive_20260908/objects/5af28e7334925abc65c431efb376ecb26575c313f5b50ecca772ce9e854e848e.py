"""Publish the single fixed historical diagnostic and its offline reproduction."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parent
REPO = WORK / "cripto-v1.2"
OUT = WORK.parent / "outputs"
EVIDENCE = REPO / "docs/evidence/altcoin_retro_20260907"
RESULTS = WORK / "altcoin-retro-results"
BASE = "3eabcf4a6b5a68b0c7d39e1346599cea99fbe8a2"
FILES = ("results.json", "weekly_results.json", "decisions.json", "scores.json.gz")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def stage():
    replay = {}
    for name in FILES:
        first = sha(RESULTS / name)
        repeated = sha(WORK / "altcoin-retro-replay" / name)
        assert first == repeated, name
        replay[name] = first
    freeze = json.loads((EVIDENCE / "code_freeze.json").read_text())
    for relative, expected in freeze.items():
        assert sha(REPO / relative) == expected, relative
    protected = [
        "charters/scientific_state.json", "GarimpoInvestimentos/trials.json",
        "GarimpoInvestimentos/v3/costs.py", "CR_FREEZE_INDEX.md", "CR_RESEARCH_FREEZE.md",
        "scripts/observe_altcoin_forward.py", "scripts/prepare_altcoin_payoff.py",
        "scripts/research_altcoin_analogs.py", "scripts/collect_altcoin_analogs.py",
        "docs/evidence/altcoin_profit_20260907/freeze.json",
    ]
    protected_hashes = {}
    for relative in protected:
        assert not git("diff", BASE, "--", relative), relative
        protected_hashes[relative] = sha(REPO / relative)
    versions = {name: importlib.metadata.version(name) for name in (
        "numpy", "scikit-learn", "scipy", "httpx", "joblib", "threadpoolctl", "pytest"
    )}
    validation = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "versions": versions,
        "targeted_tests_passed": 53,
        "test_files": ["tests/test_altcoin_retro.py", "tests/test_altcoin_payoff.py",
                       "tests/test_altcoin_analogs.py", "tests/test_altcoin_forward.py"],
        "test_execution": "Executed before publication; independent auditor records no test claims.",
        "ruff": "PASS", "pyright": "PASS",
        "full_offline_replay": "BYTE_IDENTICAL", "replay_file_sha256": replay,
        "scoring_freeze_verified": True,
        "protected_files_unchanged_against": BASE, "protected_file_sha256": protected_hashes,
        "audit_script_sha256": sha(REPO / "scripts/audit_altcoin_retro.py"),
        "formal_attestation": False,
    }
    dump(EVIDENCE / "validation.json", validation)
    for name in (*FILES, "audit.json"):
        shutil.copyfile(RESULTS / name, EVIDENCE / name)
    shutil.copyfile(WORK / "altcoin-retro-data/acquisition.json", EVIDENCE / "acquisition.json")
    search_log = {
        "protocol_registration_commit": "3a89023",
        "initial_evaluator_freeze_commit": "3d887ae",
        "partial_day_loader_fix_before_scoring": "653f04f",
        "zero_volume_placeholder_fix_before_scoring": "903f280",
        "new_historical_performance_trials": 1,
        "model_parameter_searches": 0, "model_changes": 0,
        "first_two_attempts": "Failed while loading inputs, before scoring or results; fixes preserve invalid days as missing.",
        "post_result_work": "Independent arithmetic audit, deterministic replay, packaging; no retuning.",
        "decision": "NO_TRADING_EVIDENCE_RULE_ABSTAINS",
        "promoted": False, "active_automation_changed": False,
    }
    dump(EVIDENCE / "search_log.json", search_log)
    history = REPO / "docs/HYPOTHESES.md"
    title = "### 2026-09-07 — Fixed net-payoff retrospective diagnostic v5"
    assert title not in history.read_text(encoding="utf-8"), "already published"
    with history.open("a", encoding="utf-8") as stream:
        stream.write("\n\n" + title + "\n\n" + """User explicitly requests retrospective quality measurement. One adaptive historical performance trial was registered in 3a89023; evaluator and causal/accounting controls froze in 3d887ae. Loader-only amendments 653f04f and 903f280 occurred before any scoring/results, after input failures: 199 partial halt candles and one zero-volume stale-timestamp placeholder remain in raw data but are missing for complete-window eligibility. No model, training, costs or threshold was retuned.

Archive-catalog universe: 661 USDT symbol histories, 727,447 captured daily rows, 240 exact reused histories and zero acquisition errors. This avoids a present-day survivors-only filter but does not certify full historical investability or archive retention. The repaired, SHA-verified 5,204-observation 2021–2023 training set is unchanged. This history was previously consumed; the diagnostic is not an untouched test or Proof.

All 140 consecutive weekly slots from 2024-01-01 through 2026-08-31 were evaluated, with final exit 2026-09-06. Decisions were saved before attaching outcomes. There were 13,996 eligible feature observations and ZERO qualifying scores, ZERO selected holdings, ZERO active weeks and 140 cash weeks. Hypothetical 5,000 USDT remains 5,000 USDT: zero simulated profit under every predeclared cost scenario. No trades means win rate, mean gain/loss, profit factor and meaningful trading uncertainty are undefined. Zero endpoint drawdown is a consequence of zero exposure, not evidence of risk-free trading.

Of candidate scores, 12,730 failed the fixed positive-margin condition, 1,265 contained a censored neighbor and one had too few distinct training weeks. Although 1,448 neighbor means were positive before the heuristic uncertainty penalty, no final score was positive. This is not solely a minimum-universe failure. Decision: NO_TRADING_EVIDENCE_RULE_ABSTAINS; the current rule did not demonstrate the user's absolute-profit objective in the observed interval. No external investment comparison or parameter search was performed.

Fifty-three targeted tests, Ruff and Pyright passed. Independent calculations checked 1,133 raw response hashes, 32 feature vectors traced to 3,881 raw bars, 32 neighbor/score calculations, and 560 Decimal weekly portfolio factors. A complete offline rerun reproduced all four result/decision/score files byte for byte. With no selected holdings there were no executed-position returns to audit. Daily OHLC price proxies and assumed trading costs are not historical executable fills or investor net BRL results. Active automation/model, production, protected state/trials/costs and frozen research remain unchanged. Detailed evidence: docs/evidence/altcoin_retro_20260907/.
""")
    report = """# Teste histórico da regra atual de cripto

**Concluído em 07/09/2026: lucro simulado zero. A regra não abriu nenhuma operação nas 140 semanas avaliadas.**

| Medida | Resultado |
|---|---:|
| Período dos resultados | 01/01/2024 a 06/09/2026 |
| Semanas avaliadas | 140 |
| Símbolos no catálogo histórico pesquisado | 661 |
| Registros diários coletados ou reutilizados | 727.447 |
| Candidatos com dados e liquidez suficientes, somados por semana | 13.996 |
| Operações selecionadas | **0** |
| Semanas inteiramente em caixa simulado | **140** |
| Capital hipotético inicial | 5.000 USDT |
| Capital hipotético final | **5.000 USDT** |
| Lucro simulado | **0 USDT / 0%** |
| Taxa de acerto das operações | Indefinida: nenhuma operação |

Os 13.996 candidatos são ocorrências de símbolos em semanas diferentes, não 13.996 moedas distintas. O universo cobre pares históricos Binance spot/USDT, incluindo símbolos retirados de negociação; não cobre todas as corretoras. O caixa foi uma referência contábil sem rendimento em USDT, não dinheiro realmente depositado.

## O que isso revela sobre a qualidade

**A configuração atual não demonstrou capacidade de gerar lucro nesse histórico.** Ela recusou todas as entradas. Isso mede a ausência de atividade e o resultado da carteira simulada, mas não permite calcular acerto, ganho médio ou qualidade de operações que nunca aconteceram.

Em 12.730 avaliações, a estimativa final não teve margem positiva. Outras 1.265 tinham um desfecho desconhecido entre os casos históricos semelhantes; uma tinha poucas semanas distintas de referência. Em 1.448 casos a média dos exemplos era positiva antes da penalidade de incerteza, mas nenhuma margem final passou do zero. A ausência de operações foi confirmada pelos cálculos independentes.

O próximo problema de pesquisa é definir uma regra que produza sinais economicamente úteis e testá-la de forma registrada. Reduzir o filtro até aparecer lucro neste mesmo histórico não demonstraria qualidade. Também não basta interpretar a espera por novas semanas como caminho garantido para lucro.

## Como foi medido

Foi usada a regra já existente, sem ajustes após os resultados: treinamento fixo de 2021–2023, 200 casos semelhantes, mesma penalidade de incerteza e até cinco posições de 20%. Cada segunda-feira usa somente os dados anteriores até o sábado; as decisões são gravadas antes de anexar os desfechos seguintes.

A simulação prevê entrada na abertura de segunda e saída no fechamento de domingo, com preços diários de referência. O cenário principal assume 0,10% de taxa e 0,10% de deslizamento em cada perna. Cenários de custo maiores e menores deram o mesmo zero, pois nenhuma compra foi selecionada. Não houve comparação com outros investimentos.

Como os anos avaliados já haviam sido consultados na pesquisa, este é um diagnóstico histórico adaptativo, não validação independente. Foram preservadas lacunas, dias parciais e desfechos desconhecidos; não se inventaram preços de saída. O catálogo histórico reduz o viés de olhar apenas moedas ainda ativas, mas sua cobertura e a negociabilidade em cada data não estão certificadas.

## Conferência e reprodução

Passaram 53 testes de software. A conferência por implementação independente verificou 1.133 respostas brutas, 32 conjuntos de indicadores, seus 200 vizinhos e notas, além das 560 contas semanais dos quatro cenários de custo. A repetição completa sem rede produziu decisões e resultados idênticos byte a byte.

O pacote de reprodução contém código, treinamento fixo, dados brutos e normalizados, protocolo, testes e resultados esperados. O lucro simulado de zero não representa lucro real realizado, resultado líquido em reais, ausência de risco nem comprovação de segurança. Nenhuma ordem foi enviada; o acompanhamento futuro e sua regra não foram alterados nesta rodada.
"""
    (OUT / "CRIPTO_TESTE_HISTORICO.md").write_text(report, encoding="utf-8")
    combined = {"results": json.loads((RESULTS / "results.json").read_text()),
                "audit": json.loads((RESULTS / "audit.json").read_text()),
                "validation": validation, "search_log": search_log}
    dump(OUT / "CRIPTO_TESTE_HISTORICO.json", combined)
    tracking = OUT / "ACOMPANHAMENTO_CRIPTO.md"
    previous = OUT / "ACOMPANHAMENTO_CRIPTO_V4_20260907.md"
    if not previous.exists():
        shutil.copyfile(tracking, previous)
    old = previous.read_text(encoding="utf-8")
    update = """# Cripto — resultado histórico atualizado em 07/09/2026

**Ainda não há lucro demonstrado.** O teste retrospectivo da regra atual terminou: nas 140 semanas de 01/01/2024 a 06/09/2026, foram zero operações. Uma carteira hipotética de 5.000 USDT terminou com 5.000 USDT, lucro simulado zero. A regra ficou em caixa o período inteiro; sua taxa de acerto em operações não pode ser estimada.

Foram avaliados 661 símbolos do catálogo histórico e 13.996 ocorrências elegíveis de candidatos por semana. Os resultados foram conferidos independentemente e reproduzidos sem rede. Esse histórico já havia sido consultado durante a pesquisa: é diagnóstico, não validação independente. Relatório completo: CRIPTO_TESTE_HISTORICO.md; dados e reprodução: CRIPTO_TESTE_HISTORICO_REPRODUCAO.zip.

O acompanhamento futuro permanece agendado com a mesma regra. Ele poderá trazer observações novas, mas a configuração atual não demonstrou lucro no período histórico. Revisar a hipótese é uma etapa distinta de apenas esperar.

---

Registro anterior do acompanhamento, preservado abaixo:

"""
    tracking.write_text(update + old, encoding="utf-8")
    print(json.dumps({"offline_replay": "BYTE_IDENTICAL", "protected_files": len(protected),
                      "results": combined["results"]["overall"]["decision"]}))


def package():
    stage_dir = WORK / "altcoin-retro-package"
    stage_dir.mkdir(exist_ok=True)

    def copy(source, relative):
        target = stage_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    for name in ("__init__.py", "collect_altcoin_retro.py", "backtest_altcoin_payoff.py",
                 "audit_altcoin_retro.py", "prepare_altcoin_payoff.py",
                 "research_altcoin_analogs.py", "collect_altcoin_analogs.py",
                 "observe_altcoin_forward.py"):
        copy(REPO / "scripts" / name, Path("scripts") / name)
    for name in ("test_altcoin_retro.py", "test_altcoin_payoff.py", "test_altcoin_analogs.py", "test_altcoin_forward.py"):
        copy(REPO / "tests" / name, Path("tests") / name)
    for path in EVIDENCE.iterdir():
        if path.is_file():
            copy(path, path.relative_to(REPO))
    for relative in (
        "docs/evidence/altcoin_analogs_20260907/protocol.json",
        "docs/evidence/altcoin_payoff_20260907/protocol.json",
        "docs/evidence/altcoin_payoff_20260907/results.json",
        "docs/evidence/altcoin_payoff_20260907/identity_events.json",
        "docs/evidence/altcoin_forward_20260907/protocol.json",
        "docs/evidence/altcoin_profit_20260907/freeze.json",
        "docs/evidence/altcoin_profit_20260907/protocol.json",
    ):
        copy(REPO / relative, relative)
    for path in (WORK / "altcoin-retro-data").rglob("*"):
        if path.is_file():
            copy(path, Path("data") / path.relative_to(WORK / "altcoin-retro-data"))
    copy(WORK / "altcoin-data/acquisition.json", "provenance/base_acquisition.json")
    copy(WORK / "altcoin-payoff-results/samples_identity_corrected.json.gz", "training/samples_identity_corrected.json.gz")
    for name in (*FILES, "audit.json"):
        copy(RESULTS / name, Path("expected") / name)
    copy(EVIDENCE / "validation.json", "expected/validation.json")
    copy(OUT / "CRIPTO_TESTE_HISTORICO.md", "RELATORIO.md")
    copy(Path(__file__), "provenance/deliver_retro.py")
    versions = json.loads((EVIDENCE / "validation.json").read_text())["versions"]
    (stage_dir / "requirements.txt").write_text("\n".join(f"{n}=={v}" for n, v in versions.items()) + "\n", encoding="utf-8")
    (stage_dir / "README.md").write_text("""# Reprodução do diagnóstico histórico v5

Resultado esperado: 140 semanas, zero operações e lucro simulado zero. Leia RELATORIO.md.
Python usado: 3.13.14. Dependências exatas em requirements.txt. Os comandos de avaliação abaixo funcionam sem rede após instalar as dependências; execute a partir desta pasta.

```powershell
python -m pip install -r requirements.txt
python -m scripts.backtest_altcoin_payoff --data-dir data --training training/samples_identity_corrected.json.gz --output-dir reproduced
python -m scripts.audit_altcoin_retro --data-dir data --results-dir reproduced --training training/samples_identity_corrected.json.gz
python -m pytest -q tests
python verify_reproduction.py
```

verify_reproduction.py confere todos os arquivos distribuídos e compara decisões, notas e resultados com expected/. Não use python -O para o auditor: ele usa assertions para verificações. O auditor não executa pytest/Ruff/Pyright; esses controles constam separadamente em validation.json.

O pacote inclui respostas brutas, 661 históricos normalizados, catálogo de origem, treinamento fixo, código do coletor e código necessário à avaliação. A reprodução usa os dados preservados; não é necessário buscar preços novamente. A função de coleta pressupõe o acervo original, enquanto a avaliação e auditoria são autossuficientes neste pacote.

Há uma única tentativa registrada de performance histórica. As duas correções do carregador ocorreram antes de calcular notas: preservam como ausentes dias parciais e um placeholder de volume zero. O algoritmo e seus parâmetros não foram alterados após os resultados. Protocolos antigos incluídos são proveniência e dependências; não autorizam ações adicionais. O objetivo v5 não exige superar outro investimento.

O conjunto já havia sido consultado e a seleção de universo/objetivo é adaptativa. Não é teste intocado, simulação de fills executáveis nem prova de lucro. A ausência de operações não mede taxa de acerto ou risco de uma estratégia negociada. Não há contas, credenciais, ordens, capital ou execução agendada neste pacote.
""", encoding="utf-8")
    verify = '''import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "FILES_SHA256.json").read_text(encoding="utf-8"))
for name, expected in manifest.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("Packaged file hash mismatch: " + name)
names = ("results.json", "weekly_results.json", "decisions.json", "scores.json.gz", "audit.json")
for name in names:
    if (root / "reproduced" / name).read_bytes() != (root / "expected" / name).read_bytes():
        raise ValueError("Reproduction differs: " + name)
print(f"PASS: {len(manifest)} packaged files checked; {len(names)} reproduced files byte-identical.")
'''
    (stage_dir / "verify_reproduction.py").write_text(verify, encoding="utf-8")
    checksums = {p.relative_to(stage_dir).as_posix(): sha(p)
                 for p in sorted(stage_dir.rglob("*")) if p.is_file() and p.name != "FILES_SHA256.json"}
    dump(stage_dir / "FILES_SHA256.json", checksums)
    archive = OUT / "CRIPTO_TESTE_HISTORICO_REPRODUCAO.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(stage_dir.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(stage_dir).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name, expected in checksums.items():
            assert hashlib.sha256(z.read(name)).hexdigest() == expected, name
    print(json.dumps({"archive": str(archive), "size": archive.stat().st_size,
                      "sha256": sha(archive), "packaged_files": len(checksums) + 1}))


def manifest():
    patch = subprocess.check_output(["git", "diff", "--binary", BASE, "HEAD"], cwd=REPO)
    (OUT / "CRIPTO_TESTE_HISTORICO.patch").write_bytes(patch)
    files = ("CRIPTO_TESTE_HISTORICO.md", "CRIPTO_TESTE_HISTORICO.json",
             "CRIPTO_TESTE_HISTORICO.patch", "CRIPTO_TESTE_HISTORICO_REPRODUCAO.zip",
             "ACOMPANHAMENTO_CRIPTO.md", "ACOMPANHAMENTO_CRIPTO_V4_20260907.md")
    dump(OUT / "CRIPTO_TESTE_HISTORICO_MANIFESTO.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "base_commit": BASE,
        "head_commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
        "decision": "NO_TRADING_EVIDENCE_RULE_ABSTAINS", "new_historical_performance_trials": 1,
        "files": {name: {"sha256": sha(OUT / name), "bytes": (OUT / name).stat().st_size} for name in files},
        "offline_replay": "BYTE_IDENTICAL", "formal_attestation": False,
    })
    print(json.dumps({"head": git("rev-parse", "HEAD"), "files": len(files)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("stage", "package", "manifest"))
    args = parser.parse_args()
    {"stage": stage, "package": package, "manifest": manifest}[args.mode]()
