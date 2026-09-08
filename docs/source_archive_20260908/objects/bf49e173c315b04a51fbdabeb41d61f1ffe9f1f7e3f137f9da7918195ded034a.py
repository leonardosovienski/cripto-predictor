"""COTAHISTProvider — cotações históricas da B3 (arquivo posicional) → MarketDataPoint.

O COTAHIST é um arquivo de layout posicional fixo (registro tipo 01 = cotação). Preços
vêm como inteiros ×100 (sem ponto decimal). Esta é lógica ESPECÍFICA do domínio de ações
— vive como conector concreto, mas emite o contrato universal MarketDataPoint.

Sem rede: lê arquivo local (.TXT ou .ZIP). Parser opera sobre linhas (str), testável com
fixtures sintéticas. Filtra por CODBDI (lote padrão) e TPMERC (à vista) por padrão.

Layout (posições 1-indexadas, registro tipo 01):
  TIPREG 1-2 | DATAPRE 3-10 (YYYYMMDD) | CODBDI 11-12 | CODNEG 13-24 | TPMERC 25-27
  PREABE 57-69 | PREMAX 70-82 | PREMIN 83-95 | PREULT 109-121 | VOLTOT 171-188
  (preços e volume com 2 casas decimais implícitas → dividir por 100)
"""

from __future__ import annotations

import zipfile
from collections.abc import Set as AbstractSet
from datetime import UTC, datetime, timedelta
from pathlib import Path

from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint

_REGISTRO_COTACAO = "01"


def _slice_int(line: str, start: int, end: int) -> int:
    """Fatia 1-indexada inclusiva → inteiro (campos numéricos vêm zero-preenchidos)."""
    raw = line[start - 1 : end].strip()
    return int(raw) if raw else 0


def _slice_str(line: str, start: int, end: int) -> str:
    return line[start - 1 : end].strip()


def parse_cotahist_lines(
    lines,
    *,
    codbdi_filter: AbstractSet[str] | None = frozenset({"02"}),
    tpmerc_filter: AbstractSet[str] | None = frozenset({"010"}),
    publish_lag_hours: int = 18,
    on_error=None,
) -> list[MarketDataPoint]:
    """Parseia linhas do COTAHIST em MarketDataPoint. Linhas inválidas são puladas
    (chama `on_error(line, motivo)` se fornecido) — um registro malformado não aborta
    o lote. `publish_lag_hours`: o pregão de D só fica público após o fechamento.
    """
    out: list[MarketDataPoint] = []
    for line in lines:
        line = line.rstrip("\n").rstrip("\r")
        if len(line) < 121 or line[:2] != _REGISTRO_COTACAO:
            continue  # cabeçalho (00), trailer (99) ou linha curta
        codbdi = _slice_str(line, 11, 12)
        tpmerc = _slice_str(line, 25, 27)
        if codbdi_filter is not None and codbdi not in codbdi_filter:
            continue
        if tpmerc_filter is not None and tpmerc not in tpmerc_filter:
            continue
        try:
            data = _slice_str(line, 3, 10)
            ts = datetime.strptime(data, "%Y%m%d").replace(tzinfo=UTC)
            ticker = _slice_str(line, 13, 24)
            o = _slice_int(line, 57, 69) / 100
            h = _slice_int(line, 70, 82) / 100
            l = _slice_int(line, 83, 95) / 100
            c = _slice_int(line, 109, 121) / 100
            v = _slice_int(line, 171, 188) / 100 if len(line) >= 188 else 0.0
            if not ticker or h < l or c <= 0:
                raise ValueError("campos fora de faixa (ticker vazio / high<low / close<=0)")
            out.append(
                MarketDataPoint(
                    symbol=ticker,
                    timestamp=ts,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=v,
                    source="cotahist",
                    interval="1d",
                    published_at=ts + timedelta(hours=publish_lag_hours),
                )
            )
        except (ValueError, KeyError) as exc:
            if on_error is not None:
                on_error(line, str(exc))
            continue
    return out


def _read_lines(path: Path):
    """Itera linhas de um .TXT ou do primeiro membro de um .ZIP (latin-1: layout B3)."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            name = zf.namelist()[0]
            with zf.open(name) as fh:
                for raw in fh:
                    yield raw.decode("latin-1")
    else:
        with open(path, encoding="latin-1") as fh:
            yield from fh


class COTAHISTProvider(DataProvider):
    name = "cotahist"

    def __init__(
        self,
        file_path: str | Path | None = None,
        *,
        codbdi_filter=frozenset({"02"}),
        tpmerc_filter=frozenset({"010"}),
        publish_lag_hours: int = 18,
    ):
        self._file_path = Path(file_path) if file_path else None
        self._codbdi = codbdi_filter
        self._tpmerc = tpmerc_filter
        self._lag = publish_lag_hours
        self._cache: dict[str, list[MarketDataPoint]] | None = None
        self.parse_errors: list[tuple[str, str]] = []

    def parse_all(self, lines=None) -> dict[str, list[MarketDataPoint]]:
        """Parseia o arquivo (ou `lines`) UMA vez e indexa por ticker (cache)."""
        if lines is None:
            if self._cache is not None:
                return self._cache
            if self._file_path is None:
                raise ValueError("cotahist: sem file_path nem lines")
            lines = _read_lines(self._file_path)
        self.parse_errors = []
        pts = parse_cotahist_lines(
            lines,
            codbdi_filter=self._codbdi,
            tpmerc_filter=self._tpmerc,
            publish_lag_hours=self._lag,
            on_error=lambda ln, why: self.parse_errors.append((ln[:24], why)),
        )
        index: dict[str, list[MarketDataPoint]] = {}
        for p in pts:
            index.setdefault(p.symbol, []).append(p)
        for series in index.values():
            series.sort(key=lambda x: x.timestamp)
        if lines is None or self._file_path is not None:
            self._cache = index
        return index

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        if interval != "1d":
            raise ValueError("cotahist: só intervalo diário ('1d')")
        index = self.parse_all()
        series = index.get(symbol)
        if not series:
            raise RuntimeError(f"cotahist: sem candles para {symbol}")
        return series[-limit:]

    async def health_check(self) -> bool:
        return self._file_path is not None and self._file_path.exists()
