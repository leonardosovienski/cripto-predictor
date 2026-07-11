"""Watchdog da coleta H5 — roda 1h depois da ColetaDiaria (19h).

Lição do OPS-1: a tarefa pode falhar em silêncio (máquina bloqueada, bateria,
429 dos provedores) e cada dia perdido é 1/30 da janela até 28/07. Este
script NÃO coleta nada — só VERIFICA e grita:

  1. o log de hoje (logs/cron_<hoje>.log) existe e terminou (linha '==== fim')?
  2. previsões de HOJE existem em output/feature_store.db (predictions)?
  3. quantos juízes distintos carimbaram hoje? (modo multi = espera-se 4;
     <4 pode ser cota/queda de provedor — vira aviso, não falha)

Falha (1 ou 2) => escreve ALERTA em logs/watchdog.log E cria o arquivo
C:\\Claude-projetos\\Claude\\ALERTA_COLETA_CRIPTO.txt (visível na raiz do
workspace — o ecosystem_health também o reporta). Sucesso remove o alerta.
"""
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "watchdog.log"
ALERTA = Path(r"C:\Claude-projetos\Claude\ALERTA_COLETA_CRIPTO.txt")
JUIZES_ESPERADOS = 4


def log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"{stamp} {msg}", flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{stamp} {msg}\n")


def main() -> int:
    hoje = datetime.now().strftime("%Y%m%d")
    hoje_iso = datetime.now().strftime("%Y-%m-%d")
    problemas = []

    cron = ROOT / "logs" / f"cron_{hoje}.log"
    if not cron.exists():
        problemas.append(f"cron_{hoje}.log NAO existe — ColetaDiaria nao rodou")
    else:
        texto = cron.read_text(encoding="utf-8", errors="replace")
        if "==== fim" not in texto:
            problemas.append(f"cron_{hoje}.log sem '==== fim' — rodada incompleta")

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

    if problemas:
        for p in problemas:
            log(f"ALERTA: {p}")
        ALERTA.write_text(
            "ALERTA da coleta H5 (previsao-cripto) — "
            f"{datetime.now().isoformat(timespec='seconds')}\n"
            + "\n".join(f"- {p}" for p in problemas)
            + "\n\nAcao: rodar manualmente scripts/run_daily.ps1 HOJE para nao "
              "perder o dia da janela H5 (decisao 28/07); investigar o "
              "agendador (schtasks /Query /TN GarimpoInvestimentos-ColetaDiaria).\n",
            encoding="utf-8")
        return 1
    if ALERTA.exists():
        ALERTA.unlink()
        log("alerta anterior resolvido — removido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
