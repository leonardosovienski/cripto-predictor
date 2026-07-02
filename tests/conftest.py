"""Paths comuns dos testes do cripto — adiciona vendor/ (predictor_core) ao sys.path
e injeta credenciais de teste para bypassar a trava P0 de settings.py sem .env."""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
_vendor = ROOT / "vendor"
if str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))

# Injetar credenciais mínimas ANTES que qualquer módulo que importe config.py
# seja coletado. A trava P0 exige ≥ 16 chars e não-placeholder. Estes valores
# são válidos para testes offline — nunca chegam à rede.
_TEST_CREDS = {
    "GEMINI_API_KEY":  "test-gemini-key-for-unit-tests-only",
    "OPENAI_API_KEY":  "test-openai-key-for-unit-tests-only",
    "SERP_API_KEY":    "test-serp-key-for-unit-tests-only-xx",
    "LLM_PROVIDER":    "gemini",
    "GEMINI_MODEL":    "gemini-2.5-flash",
    "OPENAI_MODEL":    "gpt-4o-mini",
    "LIMIAR_SCORE_MINIMO": "60",
    "DEFAULT_ASSETS":  "bitcoin,ethereum",
    "CACHE_TTL_HOURS": "6",
    "ENABLE_CACHE":    "true",
    "SCORE_HORIZON_DAYS": "7",
}
for _k, _v in _TEST_CREDS.items():
    os.environ.setdefault(_k, _v)

# emit_event agora é chamado por cache.py/logger.py durante os testes — redireciona
# o JSONL para a pasta de build dos testes para não poluir o cwd do projeto.
os.environ.setdefault("PREDICTOR_EVENTS_PATH", str(ROOT / "tests" / "_events_test.jsonl"))
