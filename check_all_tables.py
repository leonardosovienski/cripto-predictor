import sqlite3
for nome in [
    r"C:\predictor\data\failed-runs\feature_store-before-first-valid-run-2026-08-09.db",
    r"C:\predictor\data\failed-runs\feature_store-partial-rebuild-2026-08-09.db",
    r"C:\predictor\data\output\feature_store_backup_antes_limpeza.db",
]:
    print("====", nome)
    c = sqlite3.connect(nome)
    tabelas = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in tabelas:
        n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(" ", t, "->", n)
    print()
