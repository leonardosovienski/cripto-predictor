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
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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

    if problemas:
        for p in problemas:
            log(f"ALERTA: {p}")
        ALERTA.write_text(
            "ALERTA da coleta H5 (previsao-cripto) — "
            f"{datetime.now().isoformat(timespec='seconds')}\n"
            + "\n".join(f"- {p}" for p in problemas)
            + "\n\nAcao: rodar manualmente run_garimpo_fase1.bat HOJE para nao "
              "perder o dia da janela H5 (decisao 28/07); investigar o "
              "agendador (schtasks /Query /TN GarimpoFase1).\n",
            encoding="utf-8")
        return 1
    if ALERTA.exists():
        ALERTA.unlink()
        log("alerta anterior resolvido — removido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
