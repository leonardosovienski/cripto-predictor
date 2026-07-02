"""Carimbo do juiz (reprodutibilidade Modo B) + persistência no histórico oficial.

A assinatura do juiz só valida FORMATO (provider:modelo:hash) — não precisa de chave
real. Como `config.Settings()` exige chaves não-vazias no import, injetamos dummies
no ambiente antes de importar `ai_insights` (load_dotenv não sobrescreve env já setado).

Histórico: desde o passo 4 o repositório oficial é a Feature Store (tabela
predictions); o carimbo Juiz viaja na coluna `juiz`. A migração do CSV legado
é coberta em test_store_history.py.
"""


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


# --- histórico oficial: carimbo Juiz persiste na Feature Store ---------------

def test_history_writes_judge_column(tmp_path):
    from GarimpoInvestimentos.core import history
    from GarimpoInvestimentos.dpl import FeatureStore

    with FeatureStore(tmp_path / "fs.db") as store:
        history.append_history([{
            "ativo": "bitcoin", "sentimento": "positivo", "score": 72, "resumo": "x",
            "data": "2026-06-16 10:00:00", "price_usd": 50000,
            "judge": "gemini:gemini-2.5-flash:abcdef123456"}], store)
        preds = store.read_predictions()
    assert len(preds) == 1
    assert preds[0]["ativo"] == "BITCOIN"
    assert preds[0]["juiz"] == "gemini:gemini-2.5-flash:abcdef123456"


def test_history_upsert_nao_infla_o_n(tmp_path):
    """Mesma previsão (ativo+ts) gravada 2x → 1 linha. É o dedup que protege o n
    estatístico do backtest — antes por chave no CSV, agora estrutural (PK)."""
    from GarimpoInvestimentos.core import history
    from GarimpoInvestimentos.dpl import FeatureStore

    r = {"ativo": "bitcoin", "sentimento": "positivo", "score": 72, "resumo": "x",
         "data": "2026-06-16 10:00:00", "price_usd": 50000, "judge": "gemini:m:h"}
    with FeatureStore(tmp_path / "fs.db") as store:
        history.append_history([r], store)
        history.append_history([r], store)      # cache hit / reexecução
        assert len(store.read_predictions()) == 1
