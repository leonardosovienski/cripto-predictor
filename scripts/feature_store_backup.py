"""Backup verificavel e restore nao destrutivo do Feature Store SQLite.

O snapshot usa ``sqlite3.Connection.backup`` para permanecer consistente com
WAL e escritores concorrentes. O restore exige uma raiz inexistente e nunca
substitui ``output/feature_store.db`` de producao.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _default_database() -> Path:
    """O banco REAL, resolvido como o resto do projeto resolve.

    O default anterior era `<repo>/output/feature_store.db`, um caminho que nao
    existe em producao: `core.paths` poe o banco sob DATA_DIR (platformdirs, ou
    a variavel de ambiente), fora do checkout. Quem rodasse o backup sem
    `--database` recebia "Feature Store ausente" apontando para um lugar que
    nunca teve banco nenhum -- barulhento, mas confuso, e num utilitario cuja
    unica razao de existir e nao perder dado. O fallback preserva o
    comportamento antigo se o pacote nao puder ser importado.
    """
    try:
        from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
    except Exception:
        return ROOT / "output" / "feature_store.db"
    return FEATURE_STORE_DB


DEFAULT_DATABASE = _default_database()


def _default_backup_root() -> Path:
    """Onde os backups automaticos caem, ao lado dos dados e nunca no checkout."""
    try:
        from GarimpoInvestimentos.core.paths import DATA_DIR
    except Exception:
        return ROOT / "backups"
    return DATA_DIR / "backups"


DEFAULT_BACKUP_ROOT = _default_backup_root()
MANIFEST_NAME = "BACKUP_MANIFEST.json"
DATABASE_NAME = "feature_store.db"
SCHEMA_VERSION = "previsao-cripto-feature-store-backup/1.0"


class BackupError(RuntimeError):
    """Falha operacional segura de backup, verificacao ou restore."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integrity_check(path: Path) -> None:
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise BackupError("nao foi possivel verificar o SQLite") from exc
    if not result or result[0] != "ok":
        raise BackupError("integrity_check do SQLite falhou")


def create_backup(destination: Path, *, database: Path = DEFAULT_DATABASE) -> Path:
    """Cria snapshot consistente em um diretorio novo e retorna seu caminho."""
    destination = destination.resolve()
    database = database.resolve()
    if destination.exists():
        raise BackupError(f"destino ja existe: {destination}")
    if not database.is_file():
        raise BackupError(f"Feature Store ausente: {database}")

    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    temporary.mkdir(parents=True)
    snapshot = temporary / DATABASE_NAME
    try:
        source = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        _integrity_check(snapshot)
        manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "created_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "database": DATABASE_NAME,
            "sha256": _sha256(snapshot),
            "size_bytes": snapshot.stat().st_size,
        }
        (temporary / MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify_backup(backup: Path) -> dict[str, Any]:
    """Valida schema do manifesto, tamanho, hash e integridade SQLite."""
    backup = backup.resolve()
    try:
        manifest = json.loads((backup / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError("manifesto ausente ou ilegivel") from exc
    required = {"schema_version", "created_at_utc", "database", "sha256", "size_bytes"}
    if set(manifest) != required or manifest["schema_version"] != SCHEMA_VERSION:
        raise BackupError("manifesto invalido ou incompatível")
    if manifest["database"] != DATABASE_NAME:
        raise BackupError("nome de banco invalido no manifesto")
    database = backup / DATABASE_NAME
    if not database.is_file():
        raise BackupError("banco ausente no backup")
    if database.stat().st_size != manifest["size_bytes"] or _sha256(database) != manifest["sha256"]:
        raise BackupError("conteudo do backup diverge do manifesto")
    _integrity_check(database)
    return manifest


def restore_backup(backup: Path, destination_root: Path) -> Path:
    """Restaura em raiz nova; nunca sobrescreve arquivos existentes."""
    verify_backup(backup)
    destination_root = destination_root.resolve()
    if destination_root.exists():
        raise BackupError(f"raiz de restauracao ja existe: {destination_root}")
    temporary = destination_root.with_name(
        f".{destination_root.name}.{uuid.uuid4().hex}.restore.tmp"
    )
    output = temporary / "output"
    try:
        output.mkdir(parents=True)
        restored_database = output / DATABASE_NAME
        shutil.copy2(backup.resolve() / DATABASE_NAME, restored_database)
        _integrity_check(restored_database)
        temporary.rename(destination_root)
        return destination_root
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def timestamped_output(root: Path, *, now: datetime | None = None) -> Path:
    """`<root>/fs-AAAA-MM-DD-HHMMSS`, para agendamento.

    `create_backup` recusa destino existente de proposito (nao sobrescreve
    backup). Isso e certo para uso manual e fatal para uso agendado: sem um nome
    novo a cada execucao, a tarefa falharia da segunda vez em diante e ninguem
    perceberia ate precisar do backup.
    """
    carimbo = (now or datetime.now(UTC)).strftime("%Y-%m-%d-%H%M%S")
    candidato = root / f"fs-{carimbo}"
    # Duas execucoes dentro do MESMO segundo colidiriam, e create_backup recusa
    # destino existente (corretamente -- nao sobrescreve backup). Em vez de
    # transformar "rodei duas vezes seguidas" em falha, escolhe o proximo nome
    # livre. A garantia de nao-sobrescrita continua intacta: nunca reusamos uma
    # pasta que ja existe.
    sufixo = 2
    while candidato.exists() and sufixo <= 100:
        candidato = root / f"fs-{carimbo}-{sufixo}"
        sufixo += 1
    return candidato


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backup verificavel do Feature Store")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    destino = create.add_mutually_exclusive_group(required=True)
    destino.add_argument("--output", type=Path, help="pasta EXATA do backup")
    destino.add_argument(
        "--output-root",
        type=Path,
        nargs="?",
        const=DEFAULT_BACKUP_ROOT,
        help=f"pasta-mae; o nome vira fs-AAAA-MM-DD-HHMMSS (padrao: {DEFAULT_BACKUP_ROOT})",
    )
    create.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    verify = commands.add_parser("verify")
    verify.add_argument("--backup", required=True, type=Path)
    restore = commands.add_parser("restore")
    restore.add_argument("--backup", required=True, type=Path)
    restore.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            saida = args.output or timestamped_output(args.output_root)
            result = {"backup": str(create_backup(saida, database=args.database))}
        elif args.command == "verify":
            result = {
                "verified": str(args.backup.resolve()),
                "manifest": verify_backup(args.backup),
            }
        else:
            result = {"restored": str(restore_backup(args.backup, args.destination))}
    except (BackupError, OSError, sqlite3.Error) as exc:
        print(f"falha: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
