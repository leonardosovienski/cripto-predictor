"""Controle positivo do pipeline de validação (critério de saída do ciclo — auditoria).

Um pipeline que só emitiu NO-GO até hoje é infalsificável: "sabe rejeitar" ou "não tem
poder estatístico"? Este módulo responde injetando séries sintéticas de edge CONHECIDO
no _report real (Spearman + IC95% via block bootstrap pareado):

  - edge presente e calibrado → o pipeline DEVE emitir "validado" (IC não cruza 0)
  - ruído puro (edge zero)    → o pipeline DEVE emitir "RUÍDO" (IC cruza 0)

O teste nulo garante que o positivo não passa por complacência ("sim automático");
juntos são o teste de regressão do PODER do pedágio. Remover o edge do gerador faz o
teste positivo falhar (verificado na implementação). O ruído é AR(1) (dependência
serial) de propósito: é o regime para o qual o block bootstrap existe.

Mesma redoma do test_report_harness: chaves dummy, httpx stubbado, eventos em tmp.
"""
import random
import sys
import types


def _serie(n=80, edge=0.08, phi=0.5, seed=42):
    """Pares (score, retorno_d7) com edge conhecido e ruído AR(1).

    edge: pontos percentuais de retorno por ponto de score acima/abaixo de 50
    (0.08 → score 90 rende ~+3.2% + ruído; 0 → score e retorno independentes).
    phi: persistência do ruído (autocorrelação serial que o block bootstrap
    precisa absorver sem fabricar significância)."""
    rng = random.Random(seed)
    rows, eps = [], 0.0
    for _ in range(n):
        score = rng.uniform(0, 100)
        eps = phi * eps + rng.gauss(0, 2)
        rows.append({
            "score": score,
            "var_d1_pct": rng.gauss(0, 2),
            "var_d7_pct": edge * (score - 50) + eps,   # horizonte principal
            "var_d30_pct": rng.gauss(0, 5),
            "divergencia": 0,
        })
    return rows


def _roda_report(rows, tmp_path, monkeypatch):
    """Executa o _report real na redoma e devolve o evento toll_passed emitido."""
    monkeypatch.setenv("GEMINI_API_KEY", "GEMINIKEY-0123456789-abcdef")
    monkeypatch.setenv("SERP_API_KEY", "SERPKEY-0123456789-abcdef")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(events))
    monkeypatch.setitem(sys.modules, "httpx", types.ModuleType("httpx"))  # sem rede

    from GarimpoInvestimentos.analyzers import backtest
    from predictor_core import obs

    backtest._report(rows)
    tolls = [e for e in obs.read_events(events) if e["event"] == "toll_passed"]
    assert len(tolls) == 1, f"esperava 1 toll_passed, veio {len(tolls)}"
    return tolls[0]


def test_controle_positivo_edge_conhecido_vira_validado(tmp_path, monkeypatch):
    """Se o pipeline não detecta um edge FABRICADO para ser detectável, nenhum
    NO-GO dele é interpretável. Este é o controle positivo."""
    e = _roda_report(_serie(edge=0.08), tmp_path, monkeypatch)
    assert e["metadata"]["veredito"].startswith("validado"), (
        f"pipeline sem poder: edge sintético não detectado — {e['metrics']}")
    assert e["metrics"]["ic_lower"] > 0, e["metrics"]


def test_controle_nulo_ruido_puro_vira_ruido(tmp_path, monkeypatch):
    """Anti-complacência: o mesmo gerador com edge=0 (score e retorno independentes,
    ruído AR(1) idêntico) tem que sair RUÍDO — prova que o 'validado' do controle
    positivo não é um sim automático."""
    e = _roda_report(_serie(edge=0.0), tmp_path, monkeypatch)
    assert e["metadata"]["veredito"].startswith("RUÍDO"), (
        f"falso positivo: ruído puro validado — {e['metrics']}")
    assert e["metrics"]["ic_lower"] <= 0 <= e["metrics"]["ic_upper"], e["metrics"]


def test_edge_negativo_tambem_e_sinal(tmp_path, monkeypatch):
    """Documenta o comportamento do veredito: IC inteiro ABAIXO de zero também é
    'validado' (correlação negativa = sinal contrário, não ruído). Se um dia isso
    mudar, que seja decisão consciente — este teste força a conversa."""
    e = _roda_report(_serie(edge=-0.08), tmp_path, monkeypatch)
    assert e["metadata"]["veredito"].startswith("validado"), e["metrics"]
    assert e["metrics"]["ic_upper"] < 0, e["metrics"]
