"""Indicadores técnicos calculados em Python puro (sem dependências).

Os números são computados aqui — determinísticos e corretos — e injetados no prompt
para o LLM *interpretar* (ex.: "RSI=28 → sobrevendido"), em vez de pedir que o modelo
calcule sobre séries (no que LLMs são ruins). Entrada: lista de closes diários (ordem
cronológica, mais antigo → mais recente).
"""

import math


def sma(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _ema_series(prices: list[float], period: int) -> list[float]:
    if len(prices) < period:
        return []
    k = 2 / (period + 1)
    e = sum(prices[:period]) / period  # semeia com SMA
    out = [e]
    for p in prices[period:]:
        e = p * k + e * (1 - k)
        out.append(e)
    return out


def rsi(prices: list[float], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):  # suavização de Wilder
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def macd(prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """Retorna (macd_line, signal_line, histogram) ou (None, None, None)."""
    e_fast = _ema_series(prices, fast)
    e_slow = _ema_series(prices, slow)
    if not e_fast or not e_slow:
        return None, None, None
    n = min(len(e_fast), len(e_slow))
    macd_line = [e_fast[-n + i] - e_slow[-n + i] for i in range(n)]
    sig_series = _ema_series(macd_line, signal)
    line = macd_line[-1]
    sig = sig_series[-1] if sig_series else None
    hist = (line - sig) if sig is not None else None
    return line, sig, hist


def bollinger(prices: list[float], period: int = 20, mult: float = 2.0):
    """Retorna (upper, mid, lower, pct_b) — pct_b: 0=banda inf, 1=banda sup."""
    if len(prices) < period:
        return None
    window = prices[-period:]
    mid = sum(window) / period
    std = (sum((p - mid) ** 2 for p in window) / period) ** 0.5
    upper, lower = mid + mult * std, mid - mult * std
    price = prices[-1]
    pct_b = (price - lower) / (upper - lower) if upper != lower else 0.5
    return upper, mid, lower, pct_b


def compute_indicators(prices: list[float]) -> dict:
    """Pacote de indicadores prontos para o prompt (só inclui o que pôde ser calculado)."""
    if not prices:
        return {}
    price = prices[-1]
    out: dict = {}

    r = rsi(prices, 14)
    if r is not None:
        out["rsi_14"] = round(r, 1)

    can_compare = math.isfinite(price) and price > 0
    s50, s200 = sma(prices, 50), sma(prices, 200)
    if s50 is not None:
        out["sma_50"] = round(s50, 4)
        if can_compare and s50 > 0:
            out["preco_vs_sma50_pct"] = round((price / s50 - 1) * 100, 2)
    if s200 is not None:
        out["sma_200"] = round(s200, 4)
        if can_compare and s200 > 0:
            out["preco_vs_sma200_pct"] = round((price / s200 - 1) * 100, 2)

    line, sig, hist = macd(prices)
    if line is not None:
        out["macd"] = round(line, 4)
        if sig is not None and hist is not None:
            out["macd_signal"] = round(sig, 4)
            out["macd_histogram"] = round(hist, 4)

    bb = bollinger(prices)
    if bb is not None:
        out["bollinger_pct_b"] = round(bb[3], 2)  # 0=inferior, 0.5=média, 1=superior

    return out
