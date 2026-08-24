"""Painel de qualidade: engenharia vs amostra científica não devem se confundir.

Cobre especificamente o ponto levantado na auditoria de 2026-08-19: previsões
recém-gravadas (mesmo dia, sem preço realizado ainda) NÃO podem aparecer como
maduras, e a contagem de "H6 valid n" tem que vir da mesma função que fecha o
veredito oficial (h6_spearman_verdict), não de uma reimplementação do filtro.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from GarimpoInvestimentos import quality_snapshot
from GarimpoInvestimentos.dpl import FeatureStore

ROOT = Path(__file__).resolve().parents[1]


def _row(ativo, ts, score, juiz, fonte="dpl:fallback", price=50000.0):
    return {
        "ativo": ativo,
        "ts": ts,
        "score": score,
        "sentimento": "neutro",
        "resumo": "ok",
        "price_usd": price,
        "juiz": juiz,
        "divergencia": 0,
        "fonte": fonte,
        "llm_fallback": 0,
    }


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "feature_store.db"
    monkeypatch.setattr("GarimpoInvestimentos.analyzers.backtest.FEATURE_STORE_DB", path)
    return path


def test_snapshot_com_banco_vazio(db_path):
    import asyncio

    with FeatureStore(db_path):
        pass  # só cria o schema

    snap = asyncio.run(quality_snapshot.build_snapshot())
    assert snap["sample"]["total_predictions"] == 0
    assert snap["sample"]["mature_d1"] == 0
    assert snap["sample"]["h6_valid_n"] == 0
    # não deve quebrar a renderização com amostra vazia
    text = quality_snapshot.render(snap)
    assert "PROJECT QUALITY SNAPSHOT" in text
    assert "NOT_AVAILABLE" in text


def test_previsao_do_mesmo_dia_nao_conta_como_madura(db_path):
    import asyncio

    now = datetime.now(UTC)
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    with FeatureStore(db_path) as store:
        store.write_predictions([_row("bitcoin", ts, 55.0, "mistral:mistral-small-latest:hash")])

    snap = asyncio.run(quality_snapshot.build_snapshot(now=now))
    assert snap["sample"]["total_predictions"] == 1
    assert snap["pipeline"]["predictions_today"] == 1
    # a previsão é de agora — D+1 ainda não existe, não pode aparecer madura
    assert snap["sample"]["mature_d1"] == 0
    assert snap["sample"]["h6_valid_n"] == 0
    assert snap["predictive_quality"]["accuracy_d1"] is None


def test_fallback_do_llm_nao_entra_na_contagem_de_predictions(db_path):
    import asyncio

    now = datetime.now(UTC)
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    with FeatureStore(db_path) as store:
        store.write_predictions(
            [
                _row("bitcoin", ts, 55.0, "mistral:mistral-small-latest:hash"),
                {**_row("ethereum", ts, 50.0, "groq:x:hash"), "llm_fallback": 1},
            ]
        )

    snap = asyncio.run(quality_snapshot.build_snapshot(now=now))
    # só a previsao real conta — fallback do LLM eh explicitamente diferente
    # de "fonte=dpl:fallback" (nome de dado de origem, nao de falha do juiz)
    assert snap["sample"]["total_predictions"] == 1
    assert "bitcoin" in snap["by_asset"]
    assert "ethereum" not in snap["by_asset"]


def test_directional_stats_ignora_score_neutro():
    enriched = [
        {"score": 60, "var_d1_pct": 2.0},  # acertou (score>50, retorno>0)
        {"score": 40, "var_d1_pct": -1.0},  # acertou (score<50, retorno<=0)
        {"score": 40, "var_d1_pct": 3.0},  # errou
        {"score": 50, "var_d1_pct": 1.0},  # neutro — deve ser ignorado
    ]
    stats = quality_snapshot._directional_stats(enriched, 1)
    assert stats["n"] == 3  # exclui o score=50
    assert stats["accuracy"] == pytest.approx(2 / 3)


def test_render_nao_quebra_com_stats_vazias(db_path):
    """Reusa o snapshot real de um banco vazio (não duplica o schema à mão —
    um dict sintético desatualiza sozinho toda vez que build_snapshot ganha
    um campo novo, como já aconteceu com maturity_stage)."""
    import asyncio

    with FeatureStore(db_path):
        pass
    snap = asyncio.run(quality_snapshot.build_snapshot())
    text = quality_snapshot.render(snap)
    assert "PROJECT QUALITY SNAPSHOT" in text
    assert "0 / 30" in text
    assert "VERY_EARLY" in text


def test_maturity_stage_thresholds():
    assert quality_snapshot._maturity_stage(0) == "VERY_EARLY"
    assert quality_snapshot._maturity_stage(9) == "VERY_EARLY"
    assert quality_snapshot._maturity_stage(10) == "IMMATURE"
    assert quality_snapshot._maturity_stage(29) == "IMMATURE"
    assert quality_snapshot._maturity_stage(30) == "PRELIMINARY"
    assert quality_snapshot._maturity_stage(99) == "PRELIMINARY"
    assert quality_snapshot._maturity_stage(100) == "DEVELOPING_EVIDENCE"
    assert quality_snapshot._maturity_stage(299) == "DEVELOPING_EVIDENCE"
    assert quality_snapshot._maturity_stage(300) == "SUBSTANTIAL_SAMPLE"
    assert quality_snapshot._maturity_stage(10_000) == "SUBSTANTIAL_SAMPLE"


def test_score_buckets_agrupa_corretamente():
    enriched = [
        {"score": 10, "var_d7_pct": -5.0},
        {"score": 25, "var_d7_pct": 1.0},
        {"score": 65, "var_d7_pct": 2.0},
        {"score": 100, "var_d7_pct": 3.0},  # extremo direito inclusivo
    ]
    buckets = quality_snapshot._score_buckets(enriched, 7)
    by_range = {b["range"]: b for b in buckets}
    assert by_range["0-20"]["n"] == 1
    assert by_range["0-20"]["avg_return"] == -5.0
    assert by_range["20-40"]["n"] == 1
    assert by_range["40-60"]["n"] == 0
    assert by_range["40-60"]["avg_return"] is None
    assert by_range["60-80"]["n"] == 1
    assert by_range["80-100"]["n"] == 1  # score=100 cai no último bucket


def test_majority_baseline_precisa_de_n_minimo():
    assert quality_snapshot._majority_baseline([{"var_d7_pct": 1.0}] * 3, 7) is None


def test_majority_baseline_calcula_direcao_majoritaria():
    enriched = [{"var_d7_pct": v} for v in (1.0, 2.0, 3.0, -1.0)]  # 3 up, 1 down
    baseline = quality_snapshot._majority_baseline(enriched, 7)
    assert baseline["majority_direction"] == "up"
    assert baseline["n"] == 4
    assert baseline["accuracy"] == pytest.approx(3 / 4)


def test_by_provider_quality_separa_por_juiz():
    enriched = [
        {"juiz": "mistral", "score": 60, "var_d7_pct": 1.0},
        {"juiz": "mistral", "score": 40, "var_d7_pct": -1.0},
        {"juiz": "groq", "score": 60, "var_d7_pct": -1.0},
    ]
    result = quality_snapshot._by_provider_quality(enriched, 7)
    assert result["mistral"]["n_total"] == 2
    assert result["mistral"]["accuracy"] == 1.0
    assert result["groq"]["n_total"] == 1
    assert result["groq"]["accuracy"] == 0.0


def test_append_history_e_realmente_append_only(tmp_path):
    history_path = tmp_path / "history.jsonl"
    snap1 = {
        "checked_at": "2026-08-19T00:00:00Z",
        "pipeline": {"llm_fallbacks_recent": 0.0, "status": "HEALTHY"},
        "sample": {
            "total_predictions": 2,
            "maturity_stage": "VERY_EARLY",
            "mature_d7": 0,
            "h6_valid_n": 2,
            "h6_gate": 30,
        },
        "predictive_quality": {
            "accuracy_d7": None,
            "balanced_accuracy_d7": None,
            "majority_baseline_d7": None,
            "spearman_d7": None,
        },
        "by_provider": {"mistral": 1, "groq": 1},
    }
    quality_snapshot.append_history(snap1, path=history_path)
    assert history_path.exists()
    lines_after_first = history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines_after_first) == 1
    record1 = json.loads(lines_after_first[0])
    assert record1["n"] == 2
    assert record1["maturity_stage"] == "VERY_EARLY"
    assert record1["providers"] == {"mistral": 1, "groq": 1}

    snap2 = {**snap1, "checked_at": "2026-08-20T00:00:00Z"}
    snap2["sample"] = {**snap1["sample"], "total_predictions": 5}
    quality_snapshot.append_history(snap2, path=history_path)

    lines_after_second = history_path.read_text(encoding="utf-8").splitlines()
    # a primeira linha continua exatamente igual — nada foi reescrito
    assert lines_after_second[0] == lines_after_first[0]
    assert len(lines_after_second) == 2
    record2 = json.loads(lines_after_second[1])
    assert record2["n"] == 5


def test_history_record_extrai_campos_pedidos():
    snap = {
        "checked_at": "x",
        "pipeline": {"llm_fallbacks_recent": 0.05, "status": "DEGRADED"},
        "sample": {
            "total_predictions": 12,
            "maturity_stage": "IMMATURE",
            "mature_d7": 8,
            "h6_valid_n": 8,
            "h6_gate": 30,
        },
        "predictive_quality": {
            "accuracy_d7": 0.625,
            "balanced_accuracy_d7": 0.6,
            "majority_baseline_d7": {"accuracy": 0.5, "n": 8, "majority_direction": "up"},
            "spearman_d7": {"rho": 0.12, "ic_lower": -0.1, "ic_upper": 0.3, "n": 8},
        },
        "by_provider": {"gemini": 4, "groq": 4},
    }
    record = quality_snapshot._history_record(snap)
    assert record["n"] == 12
    assert record["mature_n_d7"] == 8
    assert record["accuracy_d7"] == 0.625
    assert record["majority_baseline_accuracy_d7"] == 0.5
    assert record["spearman_d7"] == 0.12
    assert record["fallback_rate_recent"] == 0.05
    assert record["pipeline_status"] == "DEGRADED"
    assert record["providers"] == {"gemini": 4, "groq": 4}
    assert record["h6_valid_n"] == 8


# --- ponte produção -> git: artefato versionado do estado da H6 -------------
# O n real da H6 é calculado do feature_store.db, que é gitignored. Sem um
# artefato versionado, nenhum acompanhamento externo (revisão, handoff, o cron
# semanal "Watch H6 n>=30") enxerga o número — só o valor escrito à mão em
# docs/HYPOTHESES.md, que envelhece em silêncio.


def _snap(n, gate=30, h6=None, checked_at="2026-08-21T00:00:00+00:00", h6_power=None):
    return {
        "checked_at": checked_at,
        "h6": h6,
        "h6_power": h6_power,
        "sample": {"h6_valid_n": n, "h6_gate": gate, "h6_fonte_esperada": "dpl:fallback"},
    }


def test_payload_abaixo_do_gate_nao_expoe_rho_nem_veredito():
    """h6_spearman_verdict devolve rho/IC como None abaixo de n>=30 DE PROPÓSITO,
    para não tratar correlação imatura como sinal. O artefato preserva esse
    silêncio em vez de contorná-lo."""
    payload = quality_snapshot.h6_status_payload(_snap(6, h6={"n": 6, "veredito": "aguardando"}))
    assert payload["n"] == 6
    assert payload["gate"] == 30
    assert payload["gate_atingido"] is False
    assert payload["rho"] is None
    assert payload["ic_lower"] is None
    assert payload["ic_upper"] is None
    assert payload["trial"] == quality_snapshot.H6_TRIAL_NAME


def test_payload_publica_veredito_quando_o_gate_abre():
    h6 = {"n": 31, "rho": 0.21, "ic_lower": 0.05, "ic_upper": 0.36, "veredito": "validado"}
    payload = quality_snapshot.h6_status_payload(_snap(31, h6=h6))
    assert payload["gate_atingido"] is True
    assert payload["rho"] == 0.21
    assert payload["ic_lower"] == 0.05
    assert payload["veredito"] == "validado"


def test_payload_nao_inclui_poder_quando_ausente_do_snapshot():
    payload = quality_snapshot.h6_status_payload(_snap(6, h6={"n": 6, "veredito": "aguardando"}))
    assert payload["poder"] is None


def test_payload_inclui_poder_quando_o_snapshot_o_calculou():
    poder = {"n_referencia": 30, "poder": {0.2: 0.147, 0.3: 0.293}, "fonte": "B12"}
    payload = quality_snapshot.h6_status_payload(
        _snap(31, h6={"n": 31, "veredito": "validado"}, h6_power=poder)
    )
    assert payload["poder"] == poder


def test_render_mostra_poder_quando_presente():
    snap = _snap(45, h6={"n": 45, "veredito": "RUIDO (IC cruza 0)"})
    snap["h6_power"] = {"n_referencia": 30, "poder": {0.2: 0.147, 0.3: 0.293}, "fonte": "B12"}
    snap["pipeline"] = {
        "predictions_persisted": 25,
        "predictions_today": 17,
        "llm_fallbacks_recent": 0.1,
        "status": "HEALTHY",
        "last_successful_run": "2026-08-24 02:00:00",
        "watchdog_violations": [],
        "watchdog_degraded": [],
    }
    snap["sample"]["total_predictions"] = 25
    snap["sample"]["maturity_stage"] = "IMMATURE"
    snap["sample"]["mature_d1"] = 8
    snap["sample"]["mature_d7"] = 0
    snap["predictive_quality"] = {
        "accuracy_d1": 0.75,
        "accuracy_d7": None,
        "balanced_accuracy_d1": 0.5,
        "balanced_accuracy_d7": None,
        "spearman_d7": None,
        "majority_baseline_d7": None,
        "score_buckets_d7": [],
    }
    snap["by_asset"] = {}
    snap["by_provider"] = {}
    snap["by_fonte"] = {}
    snap["by_provider_quality_d7"] = {}
    snap["historical_state"] = {
        "H5": "UNKNOWN",
        "H6": "UNKNOWN",
        "V3_frozen_families": [],
        "capital_authorized": None,
    }
    saida = quality_snapshot.render(snap)
    linha = next(l for l in saida.splitlines() if "poder aprox" in l)
    assert "n_ref=30" in linha
    assert "rho=0,2 -> 15%" in linha or "rho=0,2 -> 14%" in linha  # arredondamento


def test_render_omite_poder_quando_ausente():
    snap = _snap(6, h6={"n": 6, "veredito": "aguardando"})
    snap["pipeline"] = {
        "predictions_persisted": 6,
        "predictions_today": 6,
        "llm_fallbacks_recent": 0.0,
        "status": "HEALTHY",
        "last_successful_run": "2026-08-24 02:00:00",
        "watchdog_violations": [],
        "watchdog_degraded": [],
    }
    snap["sample"]["total_predictions"] = 6
    snap["sample"]["maturity_stage"] = "VERY_EARLY"
    snap["sample"]["mature_d1"] = 0
    snap["sample"]["mature_d7"] = 0
    snap["predictive_quality"] = {
        "accuracy_d1": None,
        "accuracy_d7": None,
        "balanced_accuracy_d1": None,
        "balanced_accuracy_d7": None,
        "spearman_d7": None,
        "majority_baseline_d7": None,
        "score_buckets_d7": [],
    }
    snap["by_asset"] = {}
    snap["by_provider"] = {}
    snap["by_fonte"] = {}
    snap["by_provider_quality_d7"] = {}
    snap["historical_state"] = {
        "H5": "UNKNOWN",
        "H6": "UNKNOWN",
        "V3_frozen_families": [],
        "capital_authorized": None,
    }
    saida = quality_snapshot.render(snap)
    assert "poder aprox" not in saida


def test_escrita_e_idempotente_e_preserva_o_primeiro_observed_at(tmp_path):
    """Roda todo dia; um arquivo versionado que muda só no timestamp gera commit
    de ruído e treina o revisor a ignorá-lo."""
    destino = tmp_path / "h6_status.json"

    assert quality_snapshot.write_h6_status(_snap(6), destino) == quality_snapshot.H6_WRITTEN
    primeiro = json.loads(destino.read_text(encoding="utf-8"))
    assert primeiro["observed_at"] == "2026-08-21T00:00:00+00:00"

    # mesmo estado, execução posterior: arquivo NÃO é tocado
    mtime = destino.stat().st_mtime_ns
    inalterado = _snap(6, checked_at="2026-08-22T00:00:00+00:00")
    assert quality_snapshot.write_h6_status(inalterado, destino) == quality_snapshot.H6_UNCHANGED
    assert destino.stat().st_mtime_ns == mtime
    assert json.loads(destino.read_text(encoding="utf-8"))["observed_at"] == primeiro["observed_at"]

    # n mudou: grava e carimba quando ESTE estado foi visto pela primeira vez
    mudou = _snap(7, checked_at="2026-08-23T00:00:00+00:00")
    assert quality_snapshot.write_h6_status(mudou, destino) == quality_snapshot.H6_WRITTEN
    depois = json.loads(destino.read_text(encoding="utf-8"))
    assert depois["n"] == 7
    assert depois["observed_at"] == "2026-08-23T00:00:00+00:00"


def test_arquivo_corrompido_e_reescrito_em_vez_de_explodir(tmp_path):
    destino = tmp_path / "h6_status.json"
    destino.write_text("{lixo", encoding="utf-8")
    assert quality_snapshot.write_h6_status(_snap(6), destino) == quality_snapshot.H6_WRITTEN
    assert json.loads(destino.read_text(encoding="utf-8"))["n"] == 6


def test_arquivo_com_bytes_nao_utf8_tambem_e_reescrito(tmp_path):
    """read_text(encoding='utf-8') levanta UnicodeDecodeError, que NÃO é
    OSError nem JSONDecodeError. A primeira versão do guard só pegava essas
    duas e o painel inteiro morria por causa de um byte solto no arquivo."""
    destino = tmp_path / "h6_status.json"
    destino.write_bytes(b'{"n": 6, "x": "\xff\xfe"}')
    assert quality_snapshot.write_h6_status(_snap(6), destino) == quality_snapshot.H6_WRITTEN
    assert json.loads(destino.read_text(encoding="utf-8"))["n"] == 6


def test_artefato_nao_e_capturado_por_nenhuma_regra_do_gitignore():
    """Todo o ponto do artefato é ser VERSIONADO — se o .gitignore o capturar,
    a ponte produção->git volta a estar quebrada, e em silêncio.

    A versão anterior deste teste comparava H6_STATUS_PATH.parents com
    OUTPUT_DIR e era uma TAUTOLOGIA: OUTPUT_DIR é o diretório de dados do
    usuário (platformdirs, ex. ~/.local/share/cripto-predictor/output), nunca
    um ancestral do pacote — a asserção não podia falhar e portanto não
    guardava nada. Esta versão confronta as regras reais do .gitignore.

    Aproximação consciente: aplica fnmatch aos padrões, sem implementar
    negação (`!`) nem a semântica completa do Git. Cobre o caso realista —
    alguém adiciona `*.json`, `h6_status.json` ou `GarimpoInvestimentos/h6_*`."""
    import fnmatch

    alvo = quality_snapshot.H6_STATUS_PATH.relative_to(ROOT).as_posix()
    for linha in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        padrao = linha.strip()
        if not padrao or padrao.startswith(("#", "!")):
            continue
        limpo = padrao.rstrip("/")
        capturado = (
            fnmatch.fnmatch(alvo, limpo)
            or fnmatch.fnmatch(alvo, f"{limpo}/*")
            or fnmatch.fnmatch(quality_snapshot.H6_STATUS_PATH.name, limpo)
            or any(fnmatch.fnmatch(parte, limpo) for parte in alvo.split("/")[:-1])
        )
        assert not capturado, f".gitignore ('{padrao}') captura {alvo} — a ponte quebra"


def test_estado_degradado_nao_apaga_veredito_ja_publicado(tmp_path):
    """O achado mais grave da revisão. Previsões são append-only, então o n da
    H6 não cai por evolução legítima do dado — cai quando a EXECUÇÃO foi
    degradada (banco vazio/errado, falha de preço engolida), que produz n=0 sem
    erro nenhum. Sem a trava, isso sobrescrevia 'n=31 / validado' com
    'n=0 / veredito=null', resetava observed_at e ainda pedia commit: o
    veredito sumia sem rastro, do único lugar onde ele era visível de fora."""
    destino = tmp_path / "h6_status.json"
    publicado = _snap(
        31,
        h6={"n": 31, "rho": 0.21, "ic_lower": 0.05, "ic_upper": 0.36, "veredito": "validado"},
        checked_at="2026-09-01T00:00:00+00:00",
    )
    assert quality_snapshot.write_h6_status(publicado, destino) == quality_snapshot.H6_WRITTEN

    degradado = _snap(0, h6=None, checked_at="2026-09-02T00:00:00+00:00")
    assert (
        quality_snapshot.write_h6_status(degradado, destino)
        == quality_snapshot.H6_REFUSED_REGRESSION
    )
    intacto = json.loads(destino.read_text(encoding="utf-8"))
    assert intacto["n"] == 31
    assert intacto["veredito"] == "validado"
    assert intacto["observed_at"] == "2026-09-01T00:00:00+00:00"

    # avanço legítimo continua passando
    avanco = _snap(32, h6={"n": 32, "veredito": "validado"}, checked_at="2026-09-03T00:00:00+00:00")
    assert quality_snapshot.write_h6_status(avanco, destino) == quality_snapshot.H6_WRITTEN
    assert json.loads(destino.read_text(encoding="utf-8"))["n"] == 32


def test_reset_deliberado_exige_intencao_explicita(tmp_path):
    """A trava não pode virar prisão: existe uma via para reset, mas ela obriga
    a dizer que é isso que se quer."""
    destino = tmp_path / "h6_status.json"
    quality_snapshot.write_h6_status(_snap(31, h6={"n": 31, "veredito": "validado"}), destino)
    zerado = _snap(0, h6=None, checked_at="2026-09-02T00:00:00+00:00")
    assert (
        quality_snapshot.write_h6_status(zerado, destino, allow_regression=True)
        == quality_snapshot.H6_WRITTEN
    )
    assert json.loads(destino.read_text(encoding="utf-8"))["n"] == 0


def test_ponta_a_ponta_build_snapshot_publica_e_depois_recusa_banco_vazio(db_path, tmp_path):
    """Caminho REAL: FeatureStore -> build_snapshot -> write_h6_status.

    Os testes acima do artefato alimentam dicts sintéticos e nunca tocam o
    banco — provam a lógica de escrita, não a integração. Este exercita a
    cadeia inteira e reproduz o cenário que a revisão pegou: um banco com
    previsões publica um estado; o MESMO código apontado para um banco vazio
    (path errado, volume não montado, coleta que não rodou) calcula n=0 sem
    levantar exceção nenhuma e tentaria sobrescrever o que foi publicado.
    """
    import asyncio
    from datetime import timedelta

    from GarimpoInvestimentos.dpl.contracts import MarketDataPoint

    destino = tmp_path / "h6_status.json"
    now = datetime(2026, 8, 21, tzinfo=UTC)
    # DEPOIS do registered_at da H6 (2026-07-20): com data anterior a trava
    # anti-data-snooping zera o n e o teste passaria sem exercitar a contagem.
    pred = datetime(2026, 8, 1, tzinfo=UTC)
    with FeatureStore(db_path) as store:
        store.write_predictions(
            [_row("bitcoin", pred.strftime("%Y-%m-%d %H:%M:%S"), 70.0, "gemini:m:h")]
        )
        # OHLCV cobrindo previsão + horizontes. _realized_price é offline-first:
        # consulta a store e só cai na rede quando falta o dia. Sem isto o teste
        # sairia buscando preço em coingecko — a suíte deste projeto é offline,
        # e a versão anterior deste teste levava 36s por causa exatamente disso.
        store.write_raw(
            [
                MarketDataPoint(
                    symbol="bitcoin",
                    timestamp=pred + timedelta(days=d),
                    open=50000.0,
                    high=50100.0,
                    low=49900.0,
                    close=50000.0 + d,
                    volume=10.0,
                    source="dpl:fallback",
                    interval="1d",
                    published_at=pred + timedelta(days=d),
                )
                for d in range(0, 32)
            ]
        )

    snap = asyncio.run(quality_snapshot.build_snapshot(now=now))
    assert quality_snapshot.write_h6_status(snap, destino) == quality_snapshot.H6_WRITTEN
    publicado = json.loads(destino.read_text(encoding="utf-8"))
    assert publicado["gate"] == quality_snapshot.H6_MIN_N
    assert publicado["trial"] == quality_snapshot.H6_TRIAL_NAME
    assert publicado["n"] == 1  # a previsão elegível foi de fato contada
    assert publicado["gate_atingido"] is False
    # abaixo do gate o veredito segue em silêncio, mesmo vindo do caminho real
    assert publicado["rho"] is None

    # simula o estado já publicado ter avançado além do gate...
    publicado_maduro = dict(publicado, n=31, gate_atingido=True, veredito="validado", rho=0.2)
    destino.write_text(json.dumps(publicado_maduro, indent=2, sort_keys=True), encoding="utf-8")

    # ...e agora o painel roda contra um banco VAZIO, sem erro nenhum
    vazio = tmp_path / "outro.db"
    with FeatureStore(vazio):
        pass
    import GarimpoInvestimentos.analyzers.backtest as bt

    original, bt.FEATURE_STORE_DB = bt.FEATURE_STORE_DB, vazio
    try:
        snap_vazio = asyncio.run(quality_snapshot.build_snapshot(now=now))
    finally:
        bt.FEATURE_STORE_DB = original
    assert snap_vazio["sample"]["h6_valid_n"] == 0  # nenhuma exceção: só zero

    assert (
        quality_snapshot.write_h6_status(snap_vazio, destino)
        == quality_snapshot.H6_REFUSED_REGRESSION
    )
    assert json.loads(destino.read_text(encoding="utf-8"))["veredito"] == "validado"


# --- Mensagem da PRIMEIRA publicação ------------------------------------------


def _rodar_main(monkeypatch, capsys, destino, snap):
    """Roda main() sem tocar banco: só o caminho de publicação/mensagem."""
    import asyncio

    async def _fake_build(now=None):
        return snap

    monkeypatch.setattr(quality_snapshot, "build_snapshot", _fake_build)
    monkeypatch.setattr(quality_snapshot, "render", lambda s: "")
    monkeypatch.setattr(quality_snapshot, "append_history", lambda s: None)
    monkeypatch.setattr(quality_snapshot, "H6_STATUS_PATH", destino)
    assert asyncio.get_event_loop_policy() is not None  # sanidade do runner
    assert quality_snapshot.main() == 0
    return capsys.readouterr().out


def test_primeira_publicacao_nao_se_anuncia_como_MUDOU(tmp_path, monkeypatch, capsys):
    """ "MUDOU" pressupoe um estado anterior. Na primeira vez nao ha nenhum — e
    dizer que mudou treina quem le a commitar sem conferir."""
    destino = tmp_path / "h6_status.json"
    saida = _rodar_main(
        monkeypatch, capsys, destino, _snap(31, h6={"n": 31, "veredito": "validado"})
    )
    assert "primeira publicacao" in saida
    assert "MUDOU" not in saida
    assert destino.exists()


def test_primeira_publicacao_com_n_zero_pede_conferencia(tmp_path, monkeypatch, capsys):
    """A trava de nao-regressao so age com estado anterior para comparar, entao a
    PRIMEIRA publicacao e o unico momento em que um n degradado (banco vazio ou
    apontado errado) passa sem ser questionado. Como o artefato nunca foi
    commitado, essa primeira vez e o caso que todo mundo vai encontrar."""
    destino = tmp_path / "h6_status.json"
    saida = _rodar_main(monkeypatch, capsys, destino, _snap(0))
    assert "CONFIRA ANTES DE COMMITAR" in saida
    assert "n=0" in saida
    assert "feature_store.db" in saida, "precisa dizer QUAL banco conferir"


def test_primeira_publicacao_com_n_real_nao_alarma(tmp_path, monkeypatch, capsys):
    destino = tmp_path / "h6_status.json"
    saida = _rodar_main(monkeypatch, capsys, destino, _snap(12))
    assert "primeira publicacao" in saida
    assert "CONFIRA ANTES DE COMMITAR" not in saida


def test_publicacao_seguinte_volta_a_dizer_MUDOU(tmp_path, monkeypatch, capsys):
    destino = tmp_path / "h6_status.json"
    _rodar_main(monkeypatch, capsys, destino, _snap(12))
    saida = _rodar_main(monkeypatch, capsys, destino, _snap(18))
    assert "MUDOU" in saida
    assert "primeira publicacao" not in saida
