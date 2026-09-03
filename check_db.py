import sqlite3
c = sqlite3.connect(r"C:\predictor\data\output\feature_store.db")
print("tabelas:", c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
