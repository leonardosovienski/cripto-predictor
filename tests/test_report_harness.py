"""Redoma sintética para o _report do backtest (Opção A): prova o comportamento de
runtime — emissão do evento `toll_passed` e a estratificação alinhadas vs divergentes —
SEM chamada real à OpenAI/Gemini/CoinGecko.

Como: chaves dummy (settings passa), `httpx` stubbado (o _report não faz rede, mas o
módulo importa httpx na carga), e PREDICTOR_EVENTS_PATH apontando p/ tmp.
"""
import random
import sys
import types


def _synthetic(n=60):
    """Histórico fabricado: alinhadas correlacionam score↔retorno; divergentes não."""
    rng = random.Random(42)
    rows = []
    for i in range(n):
        score = rng.uniform(0, 100)
        flagged = (i % 5 == 0)                       # ~20% divergentes
        v7 = rng.gauss(0, 3) if flagged else 0.08 * (score - 50) + rng.gauss(0, 2)
        rows.append({
            "score": score,
            "var_d1_pct": rng.gauss(0, 2),
            "var_d7_pct": v7,                        # horizonte principal (default 7)
            "var_d30_pct": rng.gauss(0, 5),
            "divergencia": 1 if flagged else 0,
            "news_provider": "cryptopanic" if i % 2 else "google_news_rss",
            "collection_policy": "policy-a" if i % 3 else "policy-b",
        })
    return rows


def test_report_emits_toll_passed_and_stratifies(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "GEMINIKEY-0123456789-abcdef")
    monkeypatch.setenv("SERP_API_KEY", "SERPKEY-0123456789-abcdef")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(events))
    monkeypatch.setitem(sys.modules, "httpx", types.ModuleType("httpx"))  # stub: sem rede

    from GarimpoInvestimentos.analyzers import backtest
    from predictor_core import obs

    backtest._report(_synthetic(60))

    # 1) a estratificação aparece na saída (alinhadas vs divergentes)
    out = capsys.readouterr().out
    assert "alinhadas" in out, f"estratificação 'alinhadas' ausente na saída:\n{out}"
    assert "divergentes" in out, f"estratificação 'divergentes' ausente na saída:\n{out}"
    assert "news_provider=" in out
    assert "collection_policy=" in out

    # 2) o evento estruturado foi emitido, com IC nas métricas e divergência nos metadados
    tolls = [e for e in obs.read_events(events) if e["event"] == "toll_passed"]
    assert len(tolls) == 1, f"esperava 1 toll_passed, veio {len(tolls)}"
    e = tolls[0]
    assert set(e.keys()) == set(obs.ENVELOPE_KEYS)            # envelope rígido de 7 chaves
    assert e["domain"] == "previsao_cripto"
    assert {"spearman", "ic_lower", "ic_upper", "n"} <= set(e["metrics"])
    assert -1.0 <= e["metrics"]["ic_lower"] <= 1.0
    assert e["metadata"]["horizon_days"] == 7
    assert e["metadata"]["n_divergentes"] >= 1 and e["metadata"]["n_alinhadas"] >= 1
    assert set(e["metadata"]["n_por_news_provider"]) == {"cryptopanic", "google_news_rss"}
    assert set(e["metadata"]["n_por_collection_policy"]) == {"policy-a", "policy-b"}
