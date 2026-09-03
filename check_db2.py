import sqlite3
c = sqlite3.connect(r"C:\predictor\data\output\feature_store.db")
tabelas = ["_migrations", "raw_market_data", "ingestion_provenance", "raw_signals",
           "predictions", "features_aligned", "source_quality_scorecards", "observation_scorecards"]
for t in tabelas:
    n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(t, "->", n)
print()
print("migrations:", c.execute("SELECT * FROM _migrations").fetchall())
