"""Simulação retroativa do prefiltro de LLM sobre a Feature Store (100% offline).

Responde, ANTES de ligar o filtro, a pergunta que decide os thresholds: quantas
chamadas de LLM/dia o filtro deixaria passar, e por quê os excluídos caem fora?
Sem isso, calibrar LLM_PREFILTER_MIN_* é chute — e o custo do chute é poder
estatístico (menos n/dia = trial demora mais para maturar n>=30).

Uso:
  python scripts/simulate_prefilter.py                # grade default de thresholds
  python scripts/simulate_prefilter.py --days 30      # só os últimos N dias

Não altera nada: abre o SQLite em read-only e reimplementa APENAS a régua de
corte do prefilter.decide() com thresholds paramétricos (a lógica canônica segue
em analyzers/prefilter.py; este script é instrumento de calibração, e o teste
test_prefilter_simulation_parity garante a paridade das réguas).
"""
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

VOLUME_GRID = [5_000_000, 10_000_000, 20_000_000]
CHANGE_GRID = [1.0, 2.0, 3.0]


def simulate_decision(hard: dict, min_volume: float, min_change: float,
                      technical_direction) -> str:
    """Mesma régua de prefilter.decide(), com thresholds paramétricos.
    Retorna a razão ('selected' se passa)."""
    volume = hard.get("volume_usd")
    if not isinstance(volume, (int, float)) or volume < min_volume:
        return "low_or_missing_volume"
    change_7d = hard.get("change_7d")
    if not isinstance(change_7d, (int, float)):
        return "missing_change_7d"
    if abs(change_7d) < min_change:
        return "weak_7d_momentum"
    direction = technical_direction(hard.get("indicadores", {}))
    if direction not in {"bull", "bear"}:
        return "neutral_or_missing_technical_direction"
    return "selected"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=0,
                        help="limitar aos últimos N dias distintos (0 = tudo)")
    args = parser.parse_args()

    from GarimpoInvestimentos.analyzers.score_engine import technical_direction
    from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
    from GarimpoInvestimentos.dpl import FeatureStore
    from GarimpoInvestimentos.dpl.feature_engineering import to_hard_data

    with FeatureStore(FEATURE_STORE_DB) as store:
        symbols = store.list_symbols("1d")
        # (dia, ativo) -> hard_data (uma linha de features por ativo/dia)
        rows: dict[str, dict[str, dict]] = defaultdict(dict)
        for sym in symbols:
            for row in store.read_features(sym, "1d"):
                dia = row["ts"].strftime("%Y-%m-%d")
                rows[dia][sym] = to_hard_data(row)

    dias = sorted(rows)
    if args.days:
        dias = dias[-args.days:]
    n_ativos = len(symbols)
    print(f"Universo: {n_ativos} ativos | dias simulados: {len(dias)} "
          f"({dias[0]} a {dias[-1]})\n")

    header = f"{'volume>=':>12} {'|chg7d|>=':>10} {'pass/dia':>9} {'taxa':>6}   razões dos excluídos"
    print(header)
    print("-" * len(header))
    for min_vol in VOLUME_GRID:
        for min_chg in CHANGE_GRID:
            total = passed = 0
            reasons: Counter[str] = Counter()
            per_day: list[int] = []
            for dia in dias:
                day_pass = 0
                for sym, hard in rows[dia].items():
                    total += 1
                    r = simulate_decision(hard, min_vol, min_chg, technical_direction)
                    if r == "selected":
                        passed += 1
                        day_pass += 1
                    else:
                        reasons[r] += 1
                per_day.append(day_pass)
            media = sum(per_day) / len(per_day) if per_day else 0.0
            taxa = passed / total * 100 if total else 0.0
            top = ", ".join(f"{k}={v}" for k, v in reasons.most_common(3))
            print(f"{min_vol:>12,.0f} {min_chg:>9.1f}% {media:>9.1f} {taxa:>5.0f}%   {top}")
    print("\nLeitura: 'pass/dia' é o nº médio de chamadas de LLM por dia com o filtro "
          "ligado; hoje são ~%d/dia (universo inteiro). n>=30 por juiz leva "
          "~(30*4)/pass_dia dias." % n_ativos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
