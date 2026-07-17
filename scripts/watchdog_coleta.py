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
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))
from tools.operational_runner import write_heartbeat

LOG = ROOT / "logs" / "watchdog.log"
ALERTA = Path(r"C:\Claude-projetos\Claude\ALERTA_COLETA_CRIPTO.txt")
JUIZES_ESPERADOS = 4
JANELA_HORAS = 27  # > 24h para tolerar o offset UTC do nome do arquivo
MARCADOR_CONCLUSAO = "=== concluído:"


def _log_mais_recente() -> Path | None:
    candidatos = sorted(
        (ROOT / "logs").glob("garimpo_fase1_*.log"),
        key=lambda p: p.stat().st_mtime, reverse=True)
    return candidatos[0] if candidatos else None


def log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"{stamp} {msg}", flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{stamp} {msg}\n")


def _check_backtest_heartbeat(problemas: list[str]) -> None:
    """O backtest diário (GarimpoBacktest, 2ª etapa da GarimpoFase1) pode falhar
    em silêncio — o exit code do .bat vai para o Task Scheduler, que ninguém lê
    todo dia. O heartbeat JSON do operational_runner é a evidência barata."""
    hb = ROOT / "logs" / "operations" / "GarimpoBacktest.heartbeat.json"
    if not hb.exists():
        problemas.append("GarimpoBacktest.heartbeat.json inexistente — backtest diario nunca rodou")
        return
    idade_h = (datetime.now().timestamp() - hb.stat().st_mtime) / 3600
    if idade_h > JANELA_HORAS:
        problemas.append(f"heartbeat do backtest tem {idade_h:.1f}h — backtest nao rodou na ultima janela")
        return
    try:
        status = json.loads(hb.read_text(encoding="utf-8")).get("status")
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
            url, data=texto.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8",
                     "Title": "ALERTA coleta H5 (previsao-cripto)"})
        urllib.request.urlopen(req, timeout=10).close()
        log("alerta enviado ao webhook configurado")
    except Exception as e:
        log(f"AVISO: webhook de alerta falhou ({e}) — alerta segue no arquivo")


def main() -> int:
    hoje_iso = datetime.now().strftime("%Y-%m-%d")
    problemas = []

    recente = _log_mais_recente()
    if recente is None:
        problemas.append("nenhum log garimpo_fase1_*.log encontrado — coleta nunca rodou")
    else:
        idade_h = (datetime.now().timestamp() - recente.stat().st_mtime) / 3600
        if idade_h > JANELA_HORAS:
            problemas.append(
                f"{recente.name} tem {idade_h:.1f}h — coleta pode nao ter rodado hoje")
        else:
            texto = recente.read_text(encoding="utf-8", errors="replace")
            if MARCADOR_CONCLUSAO not in texto:
                problemas.append(f"{recente.name} sem marcador de conclusão — rodada incompleta")

    juizes = 0
    try:
        con = sqlite3.connect(
            f"file:{ROOT / 'output' / 'feature_store.db'}?mode=ro", uri=True)
        n, juizes = con.execute(
            "select count(*), count(distinct juiz) from predictions "
            "where substr(ts,1,10) = ?", (hoje_iso,)).fetchone()
        if n == 0:
            problemas.append(f"0 previsoes gravadas em {hoje_iso}")
        else:
            log(f"OK: {n} previsoes de {hoje_iso} com {juizes} juiz(es)")
            if juizes < JUIZES_ESPERADOS:
                log(f"AVISO: so {juizes}/{JUIZES_ESPERADOS} juizes hoje — "
                    "cota/queda de provedor? (nao e' falha da coleta)")
    except Exception as e:
        problemas.append(f"feature_store.db ilegivel: {e}")

    _check_backtest_heartbeat(problemas)

    if problemas:
        for p in problemas:
            log(f"ALERTA: {p}")
        texto = (
            "ALERTA da coleta H5 (previsao-cripto) — "
            f"{datetime.now().isoformat(timespec='seconds')}\n"
            + "\n".join(f"- {p}" for p in problemas)
            + "\n\nAcao: rodar manualmente run_garimpo_fase1.bat HOJE para nao "
              "perder o dia da janela H5 (decisao 28/07); investigar o "
              "agendador (schtasks /Query /TN GarimpoFase1).\n")
        ALERTA.write_text(texto, encoding="utf-8")
        _notify_webhook(texto)
        return 1
    if ALERTA.exists():
        ALERTA.unlink()
        log("alerta anterior resolvido — removido")
    return 0


if __name__ == "__main__":
    started = datetime.now(timezone.utc)
    heartbeat = ROOT / "logs" / "operations" / "cripto-watchdog-coleta.heartbeat.json"
    record = {
        "run_id": __import__("uuid").uuid4().hex,
        "task_name": "cripto-watchdog-coleta",
        "project": "previsao-cripto",
        "started_at_utc": started.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "finished_at_utc": None,
        "duration_seconds": None,
        "status": "STARTED",
        "exit_code": None,
        "command": [sys.executable, str(Path(__file__).resolve())],
        "script_path": str(Path(__file__).resolve()),
        "working_directory": str(ROOT),
        "python_executable": sys.executable,
        "core_provenance": {"status": "NOT_APPLICABLE", "scope": "watchdog does not import predictor_core"},
        "expected_artifact": str(ROOT / "output" / "feature_store.db"),
        "error_summary": None,
        "log_path": str(LOG),
        "heartbeat_path": str(heartbeat),
    }
    write_heartbeat(heartbeat, record)
    try:
        exit_code = main()
        record["status"] = "SUCCEEDED" if exit_code == 0 else "FAILED"
        record["exit_code"] = exit_code
    except Exception as exc:
        record["status"] = "FAILED"
        record["exit_code"] = 1
        record["error_summary"] = str(exc)[:1000]
        raise
    finally:
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        record["duration_seconds"] = round((datetime.now(timezone.utc) - started).total_seconds(), 3)
        write_heartbeat(heartbeat, record)
    sys.exit(record["exit_code"])
