import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

WORK = Path(__file__).resolve().parent
ROOT = WORK / "cripto-research"
OUT = WORK.parent / "outputs"
DIRTY = Path("C:/Users/Superleo13/Documents/Codex/2026-08-26/contexto-e-papel-atue-como-um/work/git-final")
MAIN = Path("C:/Users/Superleo13/cripto-predictor")


def git(*args, cwd=ROOT, check=True):
    p = subprocess.run(["git", "-c", "core.safecrlf=false", *args], cwd=cwd, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace"))
    return p


refs = []
for line in git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/remotes/origin").stdout.decode().splitlines():
    name, commit = line.split()
    if name == "refs/remotes/origin/HEAD":
        continue
    ancestor = git("merge-base", "--is-ancestor", commit, "origin/main", check=False).returncode == 0
    research_ancestor = git("merge-base", "--is-ancestor", commit, "HEAD", check=False).returncode == 0
    delta = git("rev-list", "--left-right", "--count", "origin/main..." + commit).stdout.decode().strip()
    cherry = [] if ancestor else git("cherry", "origin/main", commit).stdout.decode().splitlines()
    refs.append({"ref":name,"sha":commit,"ancestor_origin_main":ancestor,"ancestor_research":research_ancestor,"main_vs_ref_counts":delta,
                 "patches_not_in_main":sum(r.startswith("+") for r in cherry),"patches_equivalent_in_main":sum(r.startswith("-") for r in cherry)})
tracked = git("ls-files", "-z", cwd=DIRTY).stdout.decode().split("\0")
untracked = git("ls-files", "--others", "--exclude-standard", "-z", cwd=DIRTY).stdout.decode().split("\0")
names = [n for n in tracked + untracked if n]
comparisons = {}
for ref in ("HEAD", "76bab87", "origin/main"):
    differences = []
    for name in names:
        path = DIRTY / name
        if not path.is_file():
            differences.append({"path":name,"reason":"missing locally"})
            continue
        current = path.read_bytes().replace(b"\r\n", b"\n")
        saved = git("show", ref + ":" + name, cwd=DIRTY, check=False)
        if saved.returncode or saved.stdout.replace(b"\r\n", b"\n") != current:
            differences.append({"path":name,"reason":"not in ref" if saved.returncode else "content differs"})
    comparisons[ref] = differences

snapshot = {"refs":refs,"actual_remote_heads":git("ls-remote","--heads","origin").stdout.decode().splitlines(),
    "dirty_worktree_comparisons_ignoring_line_endings":comparisons,
    "dirty_status":git("status","--porcelain=v1","-z",cwd=DIRTY).stdout.decode().split("\0"),
    "main_untracked":git("ls-files","--others","--exclude-standard","-z",cwd=MAIN).stdout.decode().split("\0")}
WORK.joinpath("git-consolidation-before.json").write_text(json.dumps(snapshot,indent=2),encoding="utf-8")
backup = OUT / "GIT_ALTERACOES_LOCAIS_PRESERVADAS_20260908.zip"
manifest = {}
with ZipFile(backup,"x",compression=ZIP_DEFLATED) as archive:
    for path_name in names:
        path = DIRTY / path_name
        if path.is_file():
            raw = path.read_bytes()
            name = "git-final/" + path_name
            manifest[name] = hashlib.sha256(raw).hexdigest()
            archive.writestr(name,raw)
    for name in snapshot["main_untracked"]:
        if name and (MAIN/name).is_file():
            raw = (MAIN/name).read_bytes()
            manifest["main-untracked/"+name] = hashlib.sha256(raw).hexdigest()
            archive.writestr("main-untracked/"+name,raw)
    archive.writestr("git-final-diff.patch",git("diff","--binary","HEAD",cwd=DIRTY).stdout)
    archive.writestr("status-and-refs.json",json.dumps(snapshot,indent=2))
    archive.writestr("FILES_SHA256.json",json.dumps(manifest,indent=2))
with ZipFile(backup) as archive:
    assert all(hashlib.sha256(archive.read(n)).hexdigest()==digest for n,digest in manifest.items())
print(json.dumps({"refs":refs,"dirty_differences_vs_v2":comparisons["76bab87"],"local_backup_files":len(manifest),"local_backup_bytes":backup.stat().st_size},indent=2))
