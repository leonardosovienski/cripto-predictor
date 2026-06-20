"""Carimbo do juiz (reprodutibilidade Modo B) + migração aditiva do histórico.

A assinatura do juiz só valida FORMATO (provider:modelo:hash) — não precisa de chave
real. Como `config.Settings()` exige chaves não-vazias no import, injetamos dummies
no ambiente antes de importar `ai_insights` (load_dotenv não sobrescreve env já setado).
"""
import csv
import importlib


def _import_ai(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "GEMINIKEY-0123456789-abcdef")
    monkeypatch.setenv("SERP_API_KEY", "SERPKEY-0123456789-abcdef")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    import GarimpoInvestimentos.analyzers.ai_insights as ai
    return ai


# --- assinatura do juiz ----------------------------------------------------

def test_judge_signature_format(monkeypatch):
    ai = _import_ai(monkeypatch)
    parts = ai.judge_signature().split(":")
    assert len(parts) == 3, "esperado provider:modelo:hash"
    assert parts[0] in ("gemini", "openai")
    assert parts[1]                      # modelo não-vazio
    assert len(parts[2]) == 12           # hash do prompt (12 hex)


def test_prompt_hash_stable(monkeypatch):
    ai = _import_ai(monkeypatch)
    assert ai._PROMPT_HASH == ai._PROMPT_HASH
    assert all(c in "0123456789abcdef" for c in ai._PROMPT_HASH)


# --- histórico: coluna Juiz + migração -------------------------------------

def _fresh_history(tmp_path, monkeypatch):
    monkeypatch.setenv("GARIMPO_OUTPUT_DIR", str(tmp_path))
    from GarimpoInvestimentos.core import paths
    importlib.reload(paths)
    from GarimpoInvestimentos.core import history
    importlib.reload(history)
    return history


def test_history_writes_judge_column(tmp_path, monkeypatch):
    history = _fresh_history(tmp_path, monkeypatch)
    history.append_history([{
        "ativo": "bitcoin", "sentimento": "positivo", "score": 72, "resumo": "x",
        "data": "2026-06-16 10:00:00", "price_usd": 50000,
        "judge": "gemini:gemini-2.5-flash:abcdef123456"}])
    lines = (tmp_path / "garimpo_historico.csv").read_text(encoding="utf-8-sig").splitlines()
    assert "Juiz" in lines[0]
    assert "gemini:gemini-2.5-flash:abcdef123456" in lines[1]


def test_history_migrates_old_header_without_data_loss(tmp_path, monkeypatch):
    old = tmp_path / "garimpo_historico.csv"
    old.write_text(
        "Ativo,Sentimento,Score,Resumo,Data,price_usd\n"
        "BITCOIN,positivo,70,velho,2026-06-01 09:00:00,40000\n",
        encoding="utf-8-sig")
    history = _fresh_history(tmp_path, monkeypatch)
    history.append_history([{
        "ativo": "ethereum", "sentimento": "neutro", "score": 55, "resumo": "novo",
        "data": "2026-06-16 10:00:00", "price_usd": 3000, "judge": "gemini:m:hash12345678"}])
    rows = list(csv.DictReader(old.open(encoding="utf-8-sig")))
    assert all("Juiz" in r for r in rows), "coluna Juiz não foi migrada para todas as linhas"
    old_row = next(r for r in rows if r["Ativo"] == "BITCOIN")
    assert old_row["Resumo"] == "velho", "dado antigo foi corrompido na migração"
    assert old_row["Juiz"] == "", "linha antiga deveria ter juiz desconhecido (vazio)"
    new_row = next(r for r in rows if r["Ativo"] == "ETHEREUM")
    assert new_row["Juiz"] == "gemini:m:hash12345678"


def test_history_persists_technical_snapshot(tmp_path, monkeypatch):
    """O snapshot técnico (RSI/MACD/SMA/Bollinger) DEVE ser gravado na hora da previsão —
    é o que permite residualizar o score contra o RSI no backtest. Sem isso, o forward
    test em t≈0 perde o dado para sempre."""
    import csv as _csv
    history = _fresh_history(tmp_path, monkeypatch)
    history.append_history([{
        "ativo": "bitcoin", "sentimento": "neutro", "score": 41, "resumo": "x",
        "data": "2026-06-20 08:00:00", "price_usd": 60000, "judge": "g:m:hash00000000",
        "rsi_14": 35.6, "macd_histogram": 436.5, "preco_vs_sma50_pct": -8.1,
        "preco_vs_sma200_pct": -18.1, "bollinger_pct_b": 0.32}])
    row = next(_csv.DictReader((tmp_path / "garimpo_historico.csv").open(encoding="utf-8-sig")))
    assert row["RSI14"] == "35.6"
    assert row["vs_SMA200_pct"] == "-18.1"
    assert row["MACD_hist"] == "436.5" and row["Bollinger_pctB"] == "0.32"
