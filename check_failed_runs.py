import sqlite3
for nome in [
    r"C:\predictor\data\failed-runs\feature_store-before-first-valid-run-2026-08-09.db",
    r"C:\predictor\data\failed-runs\feature_store-partial-rebuild-2026-08-09.db",
    r"C:\predictor\data\failed-runs\feature_store-pre-live-collector-2026-08-09.db",
]:
    print("====", nome)
    try:
        c = sqlite3.connect(nome)
        tabelas = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print("tabelas:", tabelas)
        if "predictions" in tabelas:
            print("total predictions:", c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
            print("fontes:", c.execute("SELECT fonte, COUNT(*) FROM predictions GROUP BY fonte").fetchall())
            print("intervalo ts:", c.execute("SELECT MIN(ts), MAX(ts) FROM predictions").fetchone())
    except Exception as e:
        print("erro:", e)
    print()
