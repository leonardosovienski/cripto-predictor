"""Explicit legacy CSV import; never invoked by readers or analysis automatically."""

import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.csv.is_file():
        parser.error("explicit CSV does not exist")
    from GarimpoInvestimentos.core.history import migrate_csv_to_store
    from GarimpoInvestimentos.dpl.feature_store import FeatureStore

    with FeatureStore(args.database) as store:
        count = migrate_csv_to_store(store, str(args.csv))
    print(f"Imported legacy rows: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
