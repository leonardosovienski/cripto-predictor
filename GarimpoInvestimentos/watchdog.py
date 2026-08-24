"""Watchdog da coleta H5 — roda às 19h, verificando a coleta mais recente
(GarimpoFase1, agendada às 22h da NOITE ANTERIOR — ver run_garimpo_fase1.bat).

Lição do OPS-1: a tarefa pode falhar em silêncio (máquina bloqueada, bateria,
429 dos provedores) e cada dia perdido é 1/30 da janela até 28/07. Este
script NÃO coleta nada — só VERIFICA e grita:

  1. existe um log logs/garimpo_fase1_*.log recente (< JANELA_HORAS) e ele
     termina com o marcador de conclusão ('=== concluído:')? O nome do
     arquivo usa data UTC (garimpo_fase1.py carimba com datetime.now(UTC)),
     que não bate com a data local do agendamento (22h local = ~01h UTC do
     dia seguinte) — por isso pegamos o log MAIS RECENTE por mtime em vez
     de tentar casar um nome de arquivo com "hoje" local.
  2. previsões de HOJE existem em output/feature_store.db (predictions)?
  3. quantos juízes distintos carimbaram hoje? (modo multi = espera-se 4;
     <4 pode ser cota/queda de provedor — vira aviso, não falha)

Falha (1 ou 2) => escreve ALERTA em logs/watchdog.log E cria o arquivo
C:\\Claude-projetos\\Claude\\ALERTA_COLETA_CRIPTO.txt (visível na raiz do
workspace — o ecosystem_health também o reporta). Sucesso remove o alerta.
"""

import json
import os
import sqlite3
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from GarimpoInvestimentos.core.paths import DATA_DIR, FEATURE_STORE_DB, LOGS_DIR
from GarimpoInvestimentos.jobs import _state_root

ROOT = Path(__file__).resolve().parent.parent


# ATE 2026-08-24 estas duas constantes (e o path hardcoded dentro de main(),
# ver DB_PATH abaixo) apontavam para ROOT/logs e ROOT/output -- o CHECKOUT,
# nao o banco/logs reais. core.paths resolve DATA_DIR/OUTPUT_DIR/LOGS_DIR via
# platformdirs (ou variavel de ambiente), fora do checkout; e' onde o banco
# de producao de fato vive (confirmado em 2026-08-22: C:\predictor\data\...,
# nao C:\predictor\prod\...). Com o path antigo, este watchdog NUNCA
# encontrava previsoes reais e reportava "0 previsoes gravadas" -- ou pior,
# achava um output/feature_store.db vazio/antigo deixado no checkout e lia
# dado errado em silencio. GARIMPO_LOGS_DIR/GARIMPO_ALERT_PATH continuam
# valendo, para quem ja os tiver configurado.
LOG = Path(os.getenv("GARIMPO_LOGS_DIR", str(LOGS_DIR))) / "watchdog.log"
ALERTA = (
    Path(os.getenv("GARIMPO_ALERT_PATH", str(DATA_DIR / "output"))) / "ALERTA_COLETA_CRIPTO.txt"
)
DB_PATH = FEATURE_STORE_DB
JUIZES_ESPERADOS = 4
JANELA_HORAS = 27  # > 24h para tolerar o offset UTC do nome do arquivo
MARCADOR_CONCLUSAO = "=== concluído:"
H6_BRIDGE_STALE_DIAS = 3  # ver _check_h6_bridge


def contagem_previsoes_reais(db_path: Path, dia_iso: str) -> tuple[int, int]:
    """(n, juízes distintos) das previsões REAIS do dia — mesma semântica de
    FeatureStore.predictions_on: linha de fallback do LLM (llm_fallback=1) não
    é coleta. Sem o filtro, uma execução manual de main.py que persistisse
    fallbacks no dia mascararia a falha da coleta noturna (n>0 falso)."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return con.execute(
            "select count(*), count(distinct juiz) from predictions "
            "where substr(ts,1,10) = ? and coalesce(llm_fallback, 0) = 0",
            (dia_iso,),
        ).fetchone()
    finally:
        con.close()


def _log_mais_recente() -> Path | None:
    candidatos = sorted(
        (ROOT / "logs").glob("garimpo_fase1_*.log"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return candidatos[0] if candidatos else None


def log(msg: str) -> None:
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"{stamp} {msg}", flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{stamp} {msg}\n")


def _check_h6_bridge(problemas: list[str]) -> None:
    """A ponte producao->git do `n` da H6 (`GarimpoInvestimentos/h6_status.json`)
    so atravessa por commit humano (decisao registrada em 2026-08-21: artefato
    + commit manual, nao push automatizado). Ate 2026-08-22 ela nunca tinha
    sido atravessada NENHUMA vez -- nao porque fosse dificil, mas porque nada
    avisava que ela estava parada.

    Este check compara o `n` LOCAL, lido do historico append-only que o job
    `quality-snapshot` grava a cada execucao (`quality_snapshot_history.jsonl`,
    fora do git), com o `n` PUBLICADO no `h6_status.json` committed. Se o local
    ja avancou e o arquivo publicado ficou parado por dias, reclama -- sem
    tentar commitar sozinho: quem decide o que entra no git continua sendo
    humano, este check so impede que a decisao seja esquecida em silencio."""
    history_path = DATA_DIR / "output" / "quality_snapshot_history.jsonl"
    status_path = ROOT / "GarimpoInvestimentos" / "h6_status.json"

    if not history_path.exists():
        return  # quality-snapshot ainda nao rodou aqui; nada para comparar

    ultima = None
    try:
        with open(history_path, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    ultima = json.loads(linha)
    except (OSError, json.JSONDecodeError):
        return  # historico ilegivel nao e' motivo para alarmar sobre A PONTE
    if ultima is None:
        return

    n_local = ultima.get("h6_valid_n")
    if not isinstance(n_local, int):
        return

    if not status_path.exists():
        if n_local > 0:
            problemas.append(
                f"h6_status.json nunca foi publicado, mas a coleta local ja tem "
                f"n={n_local} previsao(oes) madura(s) da H6 — rode "
                f"quality_snapshot e commite o arquivo"
            )
        return

    try:
        publicado = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        problemas.append(f"h6_status.json ilegivel: {e}")
        return

    n_publicado = publicado.get("n")
    if not isinstance(n_publicado, int):
        return

    observed_raw = str(publicado.get("observed_at") or "")
    try:
        observed_at = datetime.fromisoformat(observed_raw.replace("Z", "+00:00"))
        idade_dias = (datetime.now(UTC) - observed_at).total_seconds() / 86400
    except ValueError:
        idade_dias = None

    if n_local > n_publicado and idade_dias is not None and idade_dias > H6_BRIDGE_STALE_DIAS:
        problemas.append(
            f"h6_status.json desatualizado ha {idade_dias:.1f} dia(s) "
            f"(publicado n={n_publicado}, local n={n_local}) — commite o "
            f"arquivo atualizado para que o acompanhamento externo enxergue"
        )


def _check_backtest_heartbeat(problemas: list[str]) -> None:
    """O backtest diário (job `cripto-backtest`, 2ª etapa da GarimpoFase1) pode
    falhar em silêncio — o exit code do .bat vai para o Task Scheduler, que
    ninguém lê todo dia. O heartbeat JSON do predictor_ops é a evidência barata.

    ATE 2026-08-24 este check olhava `ROOT/logs/operations/
    GarimpoBacktest.heartbeat.json` e a chave `status` — um path e um nome de
    campo de uma era PRE-predictor_ops. O runner real (`predictor_ops.runner.
    run_job`) escreve em `<state_root>/<job.id>/heartbeat.json` (job.id =
    "cripto-backtest") com a chave `run_status`, verificado rodando um job de
    verdade e lendo o heartbeat gravado. Com o path/chave antigos, esta funcao
    reportava "backtest diario nunca rodou" TODO dia, tenha o backtest rodado
    ou nao — o alerta nunca discriminava nada."""
    hb = _state_root() / "cripto-backtest" / "heartbeat.json"
    if not hb.exists():
        problemas.append("heartbeat.json do backtest inexistente — backtest diario nunca rodou")
        return
    idade_h = (datetime.now().timestamp() - hb.stat().st_mtime) / 3600
    if idade_h > JANELA_HORAS:
        problemas.append(
            f"heartbeat do backtest tem {idade_h:.1f}h — backtest nao rodou na ultima janela"
        )
        return
    try:
        status = json.loads(hb.read_text(encoding="utf-8")).get("run_status")
    except Exception as e:
        problemas.append(f"heartbeat do backtest ilegivel: {e}")
        return
    if status != "SUCCEEDED":
        problemas.append(f"backtest diario com status {status!r} (esperado SUCCEEDED)")
    else:
        log("OK: backtest diario SUCCEEDED (heartbeat recente)")


def _notify_webhook(texto: str) -> None:
    """Push best-effort do alerta (operação headless não pode depender de alguém
    olhar um .txt). Configure ALERTA_WEBHOOK_URL (ex.: topico ntfy.sh ou webhook
    proprio); sem a variável, mantém só o arquivo — comportamento antigo."""
    url = os.getenv("ALERTA_WEBHOOK_URL", "").strip()
    if not url:
        return
    try:
        req = urllib.request.Request(
            url,
            data=texto.encode("utf-8"),
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Title": "ALERTA coleta H5 (previsao-cripto)",
            },
        )
        urllib.request.urlopen(req, timeout=10).close()
        log("alerta enviado ao webhook configurado")
    except Exception as e:
        log(f"AVISO: webhook de alerta falhou ({e}) — alerta segue no arquivo")


def main() -> int:
    hoje_iso = datetime.now().strftime("%Y-%m-%d")
    problemas = []

    coleta_concluida = False
    prefilter_skips = 0
    recente = _log_mais_recente()
    if recente is None:
        problemas.append("nenhum log garimpo_fase1_*.log encontrado — coleta nunca rodou")
    else:
        idade_h = (datetime.now().timestamp() - recente.stat().st_mtime) / 3600
        if idade_h > JANELA_HORAS:
            problemas.append(f"{recente.name} tem {idade_h:.1f}h — coleta pode nao ter rodado hoje")
        else:
            texto = recente.read_text(encoding="utf-8", errors="replace")
            coleta_concluida = MARCADOR_CONCLUSAO in texto
            # com LLM_PREFILTER_ENABLED, um dia parado pode legitimamente gerar 0
            # previsões — as linhas 'pre-filtro: ... fora' distinguem isso de falha.
            prefilter_skips = texto.count("pre-filtro:")
            if not coleta_concluida:
                problemas.append(f"{recente.name} sem marcador de conclusão — rodada incompleta")

    juizes = 0
    try:
        n, juizes = contagem_previsoes_reais(DB_PATH, hoje_iso)
        if n == 0:
            if coleta_concluida and prefilter_skips > 0:
                log(
                    f"OK: 0 previsoes em {hoje_iso}, mas a coleta concluiu e o "
                    f"pre-filtro excluiu {prefilter_skips} ativo(s) — dia parado "
                    "legitimo, nao e' falha"
                )
            else:
                problemas.append(f"0 previsoes gravadas em {hoje_iso}")
        else:
            log(f"OK: {n} previsoes de {hoje_iso} com {juizes} juiz(es)")
            if juizes < JUIZES_ESPERADOS:
                log(
                    f"AVISO: so {juizes}/{JUIZES_ESPERADOS} juizes hoje — "
                    "cota/queda de provedor? (nao e' falha da coleta)"
                )
    except Exception as e:
        problemas.append(f"feature_store.db ilegivel: {e}")

    _check_backtest_heartbeat(problemas)
    _check_h6_bridge(problemas)

    if problemas:
        for p in problemas:
            log(f"ALERTA: {p}")
        texto = (
            "ALERTA da coleta H5 (previsao-cripto) — "
            f"{datetime.now().isoformat(timespec='seconds')}\n"
            + "\n".join(f"- {p}" for p in problemas)
            + "\n\nAcao: rodar manualmente run_garimpo_fase1.bat HOJE para nao "
            "perder o dia da janela H5 (decisao 28/07); investigar o "
            "agendador (schtasks /Query /TN GarimpoFase1).\n"
        )
        ALERTA.write_text(texto, encoding="utf-8")
        _notify_webhook(texto)
        return 1
    if ALERTA.exists():
        ALERTA.unlink()
        log("alerta anterior resolvido — removido")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
