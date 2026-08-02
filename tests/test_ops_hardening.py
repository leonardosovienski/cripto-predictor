"""Hardening operacional (triagem 2026-07-16/17): redação de segredos no log,
lock órfão auto-recuperável, idempotência por judge_signature completo e a API
pública FeatureStore.predictions_on. Offline, sem chaves reais."""

import importlib
import logging
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _load_fase1():
    return importlib.import_module("GarimpoInvestimentos.phase1")


@pytest.fixture(scope="module")
def fase1():
    return _load_fase1()


@pytest.fixture()
def store(tmp_path):
    from GarimpoInvestimentos.dpl import FeatureStore

    with FeatureStore(tmp_path / "fs.db") as s:
        yield s


def _pred(ativo, ts, juiz, fallback=0):
    return {
        "ativo": ativo,
        "ts": ts,
        "score": 55.0,
        "sentimento": "neutro",
        "resumo": "t",
        "price_usd": 1.0,
        "juiz": juiz,
        "divergencia": 0,
        "fonte": "direct",
        "input_degradado": 0,
        "llm_fallback": fallback,
    }


# ---------------- FeatureStore.predictions_on ----------------


def test_predictions_on_filtra_dia_e_fallback(store):
    store.write_predictions(
        [
            _pred("bitcoin", "2026-07-17T01:00:00Z", "gemini:m:abc"),
            _pred("ethereum", "2026-07-17T01:05:00Z", "groq:m:abc", fallback=1),
            _pred("solana", "2026-07-16T01:00:00Z", "mistral:m:abc"),
        ]
    )
    pares = store.predictions_on("2026-07-17")
    assert pares == [("bitcoin", "gemini:m:abc")]  # fallback e outro dia ficam de fora


# ---------------- idempotência por assinatura completa ----------------


def test_judges_done_today_compara_assinatura_completa(fase1, store):
    store.write_predictions(
        [
            _pred("bitcoin", "2026-07-17T01:00:00Z", "gemini:modelo-antigo:h1"),
        ]
    )
    done = fase1.judges_done_today(store, "2026-07-17")
    assert ("bitcoin", "gemini:modelo-antigo:h1") in done
    # mesmo provedor com modelo/prompt diferente NÃO conta como coletado
    assert ("bitcoin", "gemini:modelo-novo:h2") not in done


def test_fallback_nao_conta_como_coletado(fase1, store):
    store.write_predictions(
        [
            _pred("bitcoin", "2026-07-17T01:00:00Z", "gemini:m:h", fallback=1),
        ]
    )
    assert fase1.judges_done_today(store, "2026-07-17") == set()


# ---------------- lock ----------------
#
# Regressão (auditoria hostil 2026-07-17): garimpo_fase1.py
# tinha seu próprio lock (garimpo.lock, O_EXCL + detecção de PID órfão),
# duplicando o que predictor_ops já provê. Confirmado que
# run_garimpo_fase1.bat já envolve o processo INTEIRO no lock do runner
# (--task GarimpoFase1) — o lock interno era redundante para o caminho
# sancionado de produção. Removido; os testes de lock órfão/PID morto agora
# vivem nos contract tests de predictor_ops, a fonte canônica.
# O runner externo continua garantindo single-instance; a única lacuna real
# é uma execução manual concorrente de `python scripts/garimpo_fase1.py`
# fora do .bat, um cenário de baixo risco não coberto por nenhum lock aqui.


def test_lock_interno_foi_removido_nao_reintroduzido(fase1):
    assert not hasattr(fase1, "acquire_lock")
    assert not hasattr(fase1, "release_lock")
    assert not hasattr(fase1, "LOCK_FILE")


# ---------------- redação de segredos (delega a predictor_ops.redaction) ----------------
#
# _RedactSecrets agora é um adaptador logging.Filter fino sobre
# predictor_ops.redaction.redact_text — a implementação canônica
# compartilhada do ecossistema (ver Onda 3/3A). O marcador mudou de "***"
# para "[REDACTED]"; a cobertura ficou estritamente
# maior (padrões genéricos, não só valores conhecidos). Todos os segredos
# usados abaixo são sintéticos.

from GarimpoInvestimentos.security import redaction as _canonical_redaction

FAKE_KEY = "chave-super-secreta-123456"
FAKE_TOKEN = "fake_token_987654321"


def test_redact_filter_usa_a_implementacao_canonica_de_predictor_ops(fase1):
    # Prova estrutural (não só comportamental) de que não há uma 3a
    # implementação: o adaptador chama a MESMA função do pacote instalado, importada
    # do módulo canônico, sem regex/lista de nomes sensíveis próprias.
    import inspect

    module_source = inspect.getsource(fase1)
    class_start = module_source.index("class _RedactSecrets")
    class_source = module_source[class_start : module_source.index("\n\n\n", class_start)]
    assert "from GarimpoInvestimentos.security.redaction import safe_redact_text" in module_source
    assert fase1._RedactSecrets.filter.__code__.co_names.__contains__("safe_redact_text")
    assert "re.compile" not in class_source  # sem regex própria
    assert "SENSITIVE" not in class_source  # sem lista de nomes sensíveis própria


def test_redact_filter_mascara_segredo_conhecido(fase1):
    filt = fase1._RedactSecrets([FAKE_KEY])
    rec = logging.LogRecord(
        "httpx",
        logging.INFO,
        "x",
        1,
        f"GET https://serpapi.com/search?api_key={FAKE_KEY}&q=btc",
        None,
        None,
    )
    assert filt.filter(rec) is True
    assert FAKE_KEY not in rec.getMessage()
    assert _canonical_redaction.REDACTED in rec.getMessage()


def test_redact_filter_ignora_segredos_curtos(fase1):
    # segredos < 8 chars não entram no filtro (evita mascarar texto legítimo)
    filt = fase1._RedactSecrets(["", "curto"])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, "texto curto normal", None, None)
    filt.filter(rec)
    assert rec.getMessage() == "texto curto normal"


def test_redact_filter_authorization_header(fase1):
    filt = fase1._RedactSecrets([])
    rec = logging.LogRecord(
        "x", logging.INFO, "x", 1, f"Authorization: Bearer {FAKE_TOKEN}", None, None
    )
    filt.filter(rec)
    assert FAKE_TOKEN not in rec.getMessage()


def test_redact_filter_bearer_token(fase1):
    filt = fase1._RedactSecrets([])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, f"Bearer {FAKE_TOKEN}", None, None)
    filt.filter(rec)
    assert FAKE_TOKEN not in rec.getMessage()


def test_redact_filter_api_key_generico_sem_estar_na_lista(fase1):
    # cobertura NOVA vs. a implementação antiga: valor desconhecido (não
    # passado no construtor) ainda é mascarado pela regra estrutural.
    filt = fase1._RedactSecrets([])
    rec = logging.LogRecord(
        "x", logging.INFO, "x", 1, "api_key=" + "valor_desconhecido_12345", None, None
    )
    filt.filter(rec)
    assert "valor_desconhecido_12345" not in rec.getMessage()


def test_redact_filter_header_estilo_coingecko_sem_literal_no_codigo(fase1):
    # x-cg-demo-api-key não é um literal em NENHUM lugar do código (nem
    # aqui, nem na dependência compartilhada); a cobertura vem da regra
    # genérica de "*api*key*".
    filt = fase1._RedactSecrets([])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, f"x-cg-demo-api-key: {FAKE_KEY}", None, None)
    filt.filter(rec)
    assert FAKE_KEY not in rec.getMessage()


def test_redact_filter_url_com_query_param_sensivel(fase1):
    filt = fase1._RedactSecrets([])
    rec = logging.LogRecord(
        "x",
        logging.INFO,
        "x",
        1,
        f"https://api.example.test/v1?api_key={FAKE_KEY}&page=2",
        None,
        None,
    )
    filt.filter(rec)
    assert FAKE_KEY not in rec.getMessage()
    assert "page=2" in rec.getMessage()


def test_redact_filter_multiplos_segredos_na_mesma_mensagem(fase1):
    filt = fase1._RedactSecrets([FAKE_KEY])
    rec = logging.LogRecord(
        "x", logging.INFO, "x", 1, f"api_key={FAKE_KEY} token={FAKE_TOKEN}", None, None
    )
    filt.filter(rec)
    msg = rec.getMessage()
    assert FAKE_KEY not in msg and FAKE_TOKEN not in msg


def test_redact_filter_record_args_tuple(fase1):
    # record.msg usa %-format com args — getMessage() já mescla antes do
    # filtro rodar; args deve ser limpo (None) quando algo foi redigido, do
    # mesmo jeito que a implementação antiga fazia.
    filt = fase1._RedactSecrets([FAKE_KEY])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, "chamando com api_key=%s", (FAKE_KEY,), None)
    filt.filter(rec)
    assert FAKE_KEY not in rec.getMessage()
    assert rec.args is None


def test_redact_filter_valor_vazio_nao_e_mascarado(fase1):
    filt = fase1._RedactSecrets([])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, "api_key=", None, None)
    filt.filter(rec)
    assert rec.getMessage() == "api_key="


def test_redact_filter_valor_curto_sob_chave_sensivel_ainda_mascarado(fase1):
    # cobertura NOVA: mesmo abaixo do limiar de 8 chars usado para valores
    # CONHECIDOS, um valor curto sob uma chave sensível (regra estrutural)
    # ainda é mascarado — o limiar de 8 só se aplica a "known values".
    filt = fase1._RedactSecrets([])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, "token=abc", None, None)
    filt.filter(rec)
    assert "abc" not in rec.getMessage()


def test_redact_filter_case_insensitive(fase1):
    filt = fase1._RedactSecrets([])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, f"X-CG-Demo-API-Key: {FAKE_KEY}", None, None)
    filt.filter(rec)
    assert FAKE_KEY not in rec.getMessage()


def test_redact_filter_sem_segredo_preserva_mensagem_original(fase1):
    # quando nada é redigido, record.msg/args NÃO são tocados (preserva
    # formatação lazy para handlers downstream) — mesmo contrato de antes.
    filt = fase1._RedactSecrets([FAKE_KEY])
    original_msg = "mensagem normal sem segredo, ativo=%s"
    rec = logging.LogRecord("x", logging.INFO, "x", 1, original_msg, ("bitcoin",), None)
    filt.filter(rec)
    assert rec.msg == original_msg
    assert rec.args == ("bitcoin",)


def test_redact_filter_falha_interna_nao_expoe_segredo(fase1, monkeypatch):
    # predictor_ops.redaction.redact_text nunca levanta e nunca retorna
    # o conteúdo bruto — mesmo se o redator interno falhar internamente.
    import GarimpoInvestimentos.security.redaction as canonical

    def _boom(*_a, **_k):
        raise RuntimeError("falha simulada no redator")

    monkeypatch.setattr(canonical, "redact_text", _boom)
    filt = fase1._RedactSecrets([FAKE_KEY])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, f"api_key={FAKE_KEY}", None, None)
    filt.filter(rec)
    assert FAKE_KEY not in rec.getMessage()
    assert canonical.REDACTION_FAILED in rec.getMessage()


# ---------------- ordenação anti-buraco do api_guard ----------------


def test_order_by_staleness_prioriza_mais_antigo_e_nunca_previsto(fase1, store):
    store.write_predictions(
        [
            _pred("bitcoin", "2026-07-16T01:00:00Z", "gemini:m:h"),
            _pred("ethereum", "2026-07-10T01:00:00Z", "groq:m:h"),
        ]
    )
    ordem = fase1.order_by_staleness(["bitcoin", "ethereum", "solana"], store)
    # solana nunca prevista vem primeiro; depois a previsão mais antiga (ethereum)
    assert ordem == ["solana", "ethereum", "bitcoin"]


def test_order_by_staleness_ignora_fallback(fase1, store):
    # fallback não conta como previsão real: ativo só-com-fallback = nunca previsto
    store.write_predictions(
        [
            _pred("bitcoin", "2026-07-16T01:00:00Z", "gemini:m:h", fallback=1),
            _pred("ethereum", "2026-07-10T01:00:00Z", "groq:m:h"),
        ]
    )
    ordem = fase1.order_by_staleness(["ethereum", "bitcoin"], store)
    assert ordem == ["bitcoin", "ethereum"]


# ---------------- paridade simulação x prefiltro canônico ----------------


def test_prefilter_simulation_parity(monkeypatch):
    """A régua paramétrica do simulate_prefilter deve decidir IGUAL ao
    prefilter.decide() canônico com os mesmos thresholds — senão a calibração
    retroativa mente."""
    import importlib.util as _ilu

    spec = _ilu.spec_from_file_location(
        "simulate_prefilter", ROOT / "scripts" / "simulate_prefilter.py"
    )
    sim = _ilu.module_from_spec(spec)
    spec.loader.exec_module(sim)

    from GarimpoInvestimentos.analyzers import prefilter
    from GarimpoInvestimentos.analyzers.score_engine import technical_direction
    from GarimpoInvestimentos.config import settings

    monkeypatch.setattr(settings, "LLM_PREFILTER_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PREFILTER_MIN_VOLUME_USD", 10_000_000.0)
    monkeypatch.setattr(settings, "LLM_PREFILTER_MIN_ABS_CHANGE_7D", 2.0)

    casos = [
        {},  # sem nada -> low_or_missing_volume
        {"volume_usd": 5e6, "change_7d": 9.0},
        {"volume_usd": 5e7},  # sem change_7d
        {"volume_usd": 5e7, "change_7d": 0.5},
        {"volume_usd": 5e7, "change_7d": 9.0},  # sem indicadores -> neutral/missing
        {
            "volume_usd": 5e7,
            "change_7d": 9.0,
            "indicadores": {"preco_vs_sma200_pct": 5.0, "macd_histogram": 1.0},
        },
        {
            "volume_usd": 5e7,
            "change_7d": -9.0,
            "indicadores": {"preco_vs_sma200_pct": -5.0, "macd_histogram": -1.0},
        },
        {
            "volume_usd": 5e7,
            "change_7d": 9.0,
            "indicadores": {"preco_vs_sma200_pct": 5.0, "macd_histogram": -1.0},
        },  # neutro
    ]
    for hard in casos:
        canonico = prefilter.decide(hard)
        simulado = sim.simulate_decision(hard, 10_000_000.0, 2.0, technical_direction)
        assert (simulado == "selected") == canonico.selected, hard
        if not canonico.selected:
            assert simulado == canonico.reason, hard
