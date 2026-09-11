"""Argument parsing performs no runtime initialization."""

import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pipeline de análise de criptoativos com cache, histórico e exportação."
    )
    origem = parser.add_mutually_exclusive_group()
    origem.add_argument(
        "--assets",
        help="Lista de ativos separados por vírgula. Ex: bitcoin,ethereum,solana",
    )
    origem.add_argument(
        "--discover",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="Descobre N candidatos no mercado (CoinGecko: momentum 7d/24h + trending; "
        "filtra stablecoin, wrapped e volume < US$10M) em vez de usar lista fixa. "
        "N padrão: 10, máx: 20 (cota do LLM free tier). Exige --ingest: descoberta "
        "coleta mercado; a análise lê a Feature Store e consulta notícias/LLM na rede.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Score mínimo para destacar oportunidades fortes (escala 0-100).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignorar cache local e forçar nova coleta.",
    )
    parser.add_argument(
        "--output-dir",
        help="Diretório onde gravar CSV/XLSX (sobrescreve o padrão do projeto).",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Ao final, imprime apenas os ativos com score acima do limiar.",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Roda só a INGESTÃO (rede): coleta OHLCV + Fear&Greed, alinha e "
        "materializa na Feature Store local. O pipeline de análise lê dela.",
    )
    parser.add_argument(
        "--mode",
        choices=["fallback", "consensus"],
        default="fallback",
        help="Política de coleta de preço na ingestão: 'fallback' (sequencial "
        "Binance→CoinGecko, padrão) ou 'consensus' (mediana Binance+Kraken). "
        "Só afeta --ingest; o serving é indiferente a quantas fontes geraram o dado.",
    )
    args = parser.parse_args()
    if args.discover is not None and not args.ingest:
        parser.error(
            "--discover exige --ingest (descubra e ingira primeiro; "
            "depois rode a análise, que lê o mercado da Feature Store e consulta notícias/LLM)"
        )
    return args
