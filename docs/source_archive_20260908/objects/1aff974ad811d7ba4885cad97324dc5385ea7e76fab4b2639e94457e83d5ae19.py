import sqlite3
c = sqlite3.connect(r"C:\predictor\data\output\feature_store_backup_antes_limpeza.db")
print("tabelas:", c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
print("total predictions:", c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
print("fontes:", c.execute("SELECT fonte, COUNT(*) FROM predictions GROUP BY fonte").fetchall())
print("intervalo ts:", c.execute("SELECT MIN(ts), MAX(ts) FROM predictions").fetchone())
