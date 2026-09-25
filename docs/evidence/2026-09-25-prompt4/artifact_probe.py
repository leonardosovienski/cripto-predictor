"""Inventário de artefatos para o Prompt 4: o que existe no PC 2 para reproduzir cada hipótese.

Uso (na raiz do repositório, sem rede): <python do venv> artifact_probe.py <saida.json>

Só lê: os arquivos rastreados pelo git, os membros dos zips versionados em docs/continuity_*,
a listagem de ~/predictors/data e as tabelas dos bancos SQLite versionados (cópia temporária,
modo somente leitura). Nenhum dado é baixado nem alterado.
"""

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path.cwd()
DATA = Path.home() / "predictors" / "data"
V3_NAMES = ("returns.json", "oi.csv", "funding.csv", "spot_binance_1h.csv")
LLM_NAMES = (".db", ".sqlite", ".sqlite3")
H6_MIN_N = 30  # charters/h6_definition_frozen.json: H6_MIN_N


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


tracked = subprocess.run(
    ["git", "ls-files"], capture_output=True, text=True, check=True, cwd=REPO
).stdout.splitlines()
zips = sorted(REPO.glob("docs/continuity_*/*.zip"))
members = {}
for z in zips:
    with zipfile.ZipFile(z) as f:
        members[str(z.relative_to(REPO))] = [i.filename for i in f.infolist() if not i.is_dir()]
data_files = sorted(str(p.relative_to(DATA)) for p in DATA.rglob("*") if p.is_file())


def hits(names):
    found = [
        f"git:{t}" for t in tracked if t.lower().endswith(names) and not t.startswith("tests/")
    ]
    for z, ms in members.items():
        found += [f"zip:{z}!{m}" for m in ms if m.lower().endswith(names)]
    found += [f"data:{d}" for d in data_files if d.lower().endswith(names)]
    return found


db_tables = {}
with tempfile.TemporaryDirectory(dir=Path.home() / "predictors" / "runtime" / "cripto") as tmp:
    for ref in hits(LLM_NAMES):
        if not ref.startswith("zip:"):
            continue
        z, m = ref[4:].split("!")
        target = Path(tmp) / hashlib.sha256(ref.encode()).hexdigest()[:12]
        with zipfile.ZipFile(REPO / z) as f:
            target.write_bytes(f.read(m))
        con = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
        names = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
        db_tables[ref] = {
            n: con.execute(f'select count(*) from "{n}"').fetchone()[0] for n in names
        }
        con.close()

v3_found = hits(V3_NAMES)
llm_candidates = {
    ref: {t: c for t, c in tables.items() if "prediction" in t} for ref, tables in db_tables.items()
}
llm_usable = [
    ref for ref, tables in llm_candidates.items() if any(c >= H6_MIN_N for c in tables.values())
]
d16 = [d for d in data_files if d.startswith("d16/cripto/")]
inventory = {
    "hypothesis_family": {
        "H1": "v3",
        "H2": "v3",
        "H3": "v3",
        "H4": "llm_d7",
        "H5": "llm_d7",
        "H6": "llm_d7",
        "H7": "v3",
        "H8": "llm_generator",
        "H9": "v3",
        "V3-grid (16)": "v3",
        "v1-ancestral": "llm_d7",
    },
    "families": {
        "v3": {
            "required": "série de retornos do WFA registrado (returns.json) ou CSVs de funding, OI "
            "e spot 1h do BTCUSDT na janela registrada, com hash",
            "searched_names": list(V3_NAMES),
            "found_candidates": v3_found
            + [f"data:{d}" for d in d16 if "fundingRate" in d or "-1d-" in d][:3],
            "usable_artifacts": [f for f in v3_found if f.endswith("returns.json")],
            "note": "d16/cripto tem só klines 1d e funding de 2025-09 a 2026-09 (sem OI nem spot "
            "1h, janela diferente da registrada): usá-lo seria reconstruir variante",
        },
        "llm_d7": {
            "required": f"pares previsão do LLM × retorno D+7 da coleta registrada (n >= {H6_MIN_N})",
            "searched_names": list(LLM_NAMES),
            "found_candidates": llm_candidates,
            "usable_artifacts": llm_usable,
        },
        "llm_generator": {
            "required": "propostas do gerador de hipóteses e seus IC (coleta não iniciada, "
            "docs/HYPOTHESES.md H8)",
            "searched_names": [],
            "found_candidates": [],
            "usable_artifacts": [],
        },
    },
    "scanned": {
        "git_tracked_files": len(tracked),
        "zips_sha256": {z: sha256(REPO / z) for z in members},
        "data_files": len(data_files),
    },
}
Path(sys.argv[1]).write_text(
    json.dumps(inventory, indent=1, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps({f: v["usable_artifacts"] for f, v in inventory["families"].items()}))
