"""Descoberta de candidatos — só a lógica pura (rank_candidates), sem rede/.env.

O contrato: filtrar o que nunca é oportunidade (stable, wrapped, ilíquido) e
ranquear o resto por momentum. Rede (_fetch_*) fica fora — é casca fina de httpx.
"""

from GarimpoInvestimentos.collectors.discovery import rank_candidates


def _row(coin_id, symbol="xyz", price=100.0, volume=50_000_000.0, change_7d=0.0, change_24h=0.0):
    return {
        "id": coin_id,
        "symbol": symbol,
        "current_price": price,
        "total_volume": volume,
        "price_change_percentage_7d_in_currency": change_7d,
        "price_change_percentage_24h_in_currency": change_24h,
    }


def test_ranking_por_momentum_7d():
    markets = [
        _row("lento", change_7d=1.0),
        _row("rapido", change_7d=20.0),
        _row("medio", change_7d=10.0),
    ]
    assert rank_candidates(markets, top_n=3) == ["rapido", "medio", "lento"]


def test_24h_desempata_sem_dominar():
    # 7d igual → 24h decide; 24h pesa metade (7d 10 + 24h 4*0.5 = 12 < 7d 13)
    markets = [
        _row("a", change_7d=10.0, change_24h=0.0),
        _row("b", change_7d=10.0, change_24h=4.0),
        _row("c", change_7d=13.0, change_24h=0.0),
    ]
    assert rank_candidates(markets, top_n=3) == ["c", "b", "a"]


def test_top_n_limita():
    markets = [_row(f"coin{i}", change_7d=float(i)) for i in range(10)]
    assert len(rank_candidates(markets, top_n=3)) == 3


def test_filtra_stablecoin_por_simbolo():
    markets = [_row("tether", symbol="usdt", change_7d=50.0), _row("solana", change_7d=1.0)]
    assert rank_candidates(markets, top_n=5) == ["solana"]


def test_filtra_stablecoin_por_heuristica():
    # Stable desconhecida: preço ~$1 e 7d parado → fora, mesmo sem estar na lista
    markets = [
        _row("nova-stable", symbol="xusd", price=1.001, change_7d=0.02),
        _row("solana", change_7d=1.0),
    ]
    assert rank_candidates(markets, top_n=5) == ["solana"]


def test_moeda_de_1_dolar_que_anda_nao_e_stable():
    # Preço perto de $1 mas com momentum real: é ativo, não stable
    markets = [_row("barata-volatil", price=0.99, change_7d=15.0)]
    assert rank_candidates(markets, top_n=5) == ["barata-volatil"]


def test_filtra_wrapped():
    markets = [_row("wrapped-bitcoin", symbol="wbtc", change_7d=50.0), _row("solana")]
    assert rank_candidates(markets, top_n=5) == ["solana"]


def test_filtra_volume_baixo():
    markets = [
        _row("iliquida", volume=500_000.0, change_7d=90.0),
        _row("liquida", volume=20_000_000.0, change_7d=1.0),
    ]
    assert rank_candidates(markets, top_n=5) == ["liquida"]


def test_trending_da_bonus_mas_nao_garante_topo():
    markets = [
        _row("foguete", change_7d=30.0),
        _row("badalada", change_7d=5.0),
        _row("comum", change_7d=8.0),
    ]
    out = rank_candidates(markets, top_n=3, trending_ids=("badalada",))
    # bônus +10: badalada (15) passa comum (8) mas não o foguete (30)
    assert out == ["foguete", "badalada", "comum"]


def test_campos_ausentes_nao_quebram():
    markets = [
        {
            "id": "capenga",
            "symbol": None,
            "current_price": None,
            "total_volume": 20_000_000.0,
            "price_change_percentage_7d_in_currency": None,
            "price_change_percentage_24h_in_currency": None,
        },
        {"symbol": "semid", "total_volume": 20_000_000.0},  # sem id → ignorada
    ]
    assert rank_candidates(markets, top_n=5) == ["capenga"]
