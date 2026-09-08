"""Restore the complete project snapshot into a NEW folder. Windows x64 only."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import zipfile


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def run(args, cwd=None):
    result = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def relocate_environment(destination, manifest):
    alt = destination/'sessoes/20260907-altcoins/work/cripto-v1.2'
    cfg = alt/'.venv/pyvenv.cfg'
    lines = cfg.read_text(encoding='utf-8').splitlines()
    cfg.write_text('\n'.join('home = '+str(destination/'runtime') if s.startswith('home = ') else s for s in lines)+'\n', encoding='utf-8')
    pth = alt/'.venv/Lib/site-packages/_editable_impl_cripto_predictor.pth'
    pth.write_text(str(alt)+'\n', encoding='utf-8')
    changed = [cfg, pth]
    # The uv launchers embed the former absolute Python path. The standard
    # CPython venv launchers supplied with this exact runtime honor pyvenv.cfg.
    for name, launcher in [('python.exe','venvlauncher.exe'), ('pythonw.exe','venvwlauncher.exe')]:
        target = alt/'.venv/Scripts'/name
        shutil.copyfile(destination/'runtime/Lib/venv/scripts/nt'/launcher, target)
        changed.append(target)
    originals = {row['path']: row['sha256'] for row in manifest['files']}
    return [{'path':p.relative_to(destination).as_posix(), 'before': originals[p.relative_to(destination).as_posix()], 'after':sha(p)} for p in changed]


def restore(destination, package):
    if os.name != 'nt' or sys.maxsize < 2**32:
        raise RuntimeError('Este pacote operacional requer Windows de 64 bits (x64).')
    if destination.exists():
        raise RuntimeError('A pasta de destino ja existe. Escolha uma pasta nova; nada foi sobrescrito.')
    manifest = json.loads((package / 'MANIFESTO.json').read_text(encoding='utf-8'))
    required = manifest['logical_bytes'] + manifest['runtime_bytes'] + 600_000_000
    ancestor = destination.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    if shutil.disk_usage(ancestor).free < required:
        raise RuntimeError('Espaco livre insuficiente para os arquivos e o historico Git.')
    # Validate all content before creating the destination.
    with zipfile.ZipFile(package/'dados.zip') as archive:
        objects = {row['sha256'] for row in manifest['files']}
        if set(archive.namelist()) != {'objetos/'+h for h in objects}:
            raise RuntimeError('Indice de objetos divergente.')
        for i, digest in enumerate(sorted(objects), 1):
            with archive.open('objetos/'+digest) as handle:
                if hashlib.file_digest(handle, 'sha256').hexdigest() != digest:
                    raise RuntimeError('Objeto corrompido: '+digest)
            if i % 5000 == 0:
                print(f'Objetos verificados: {i}/{len(objects)}', flush=True)
        destinations = set()
        for row in manifest['files']:
            rel = PurePosixPath(row['path'])
            if rel.is_absolute() or any(p in ('..', '.') or ':' in p for p in rel.parts):
                raise RuntimeError('Caminho invalido no manifesto.')
            key = row['path'].casefold()
            if key in destinations:
                raise RuntimeError('Caminho duplicado no manifesto: '+row['path'])
            destinations.add(key)
        for row in manifest['runtime_files']:
            if sha(package/'runtime'/row['path']) != row['sha256']:
                raise RuntimeError('Runtime divergente: '+row['path'])
        destination.mkdir(parents=True)
        for i, row in enumerate(manifest['files'], 1):
            target = destination / row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open('objetos/'+row['sha256']) as source, target.open('xb') as dest:
                shutil.copyfileobj(source, dest)
            if sha(target) != row['sha256']:
                raise RuntimeError('Arquivo restaurado divergente: '+row['path'])
            if i % 5000 == 0:
                print(f'Arquivos restaurados e verificados: {i}/{len(manifest["files"])}', flush=True)
    shutil.copytree(package/'runtime', destination/'runtime')
    for row in manifest['runtime_files']:
        if sha(destination/'runtime'/row['path']) != row['sha256']:
            raise RuntimeError('Runtime restaurado divergente: '+row['path'])
    for name in ('MANIFESTO.json', 'LEIA-ME.md', 'validar.py', 'RETOMAR_NO_CODEX.md'):
        shutil.copyfile(package/name, destination/name)

    # Only the environment configuration and Python launchers change.
    alt = destination/'sessoes/20260907-altcoins/work/cripto-v1.2'
    relocated = relocate_environment(destination, manifest)
    report = {
        'files_verified': len(manifest['files']), 'destination': str(destination),
        'source_snapshot_utc': manifest['created_utc'],
        'relocated_environment_files': relocated,
        'automation_installed': False, 'git_restored': False,
    }
    git = shutil.which('git')
    if git:
        repo = destination/'projeto'
        run([git, 'init', '-b', 'main', repo])
        run([git, '-C', repo, 'config', 'core.autocrlf', 'true'])
        run([git, '-C', repo, 'config', 'core.longpaths', 'true'])
        run([git, '-C', repo, 'fetch', destination/'git/repositorio-completo.bundle', 'refs/heads/main:refs/remotes/origin/main', 'refs/tags/*:refs/tags/*'])
        run([git, '-C', repo, 'update-ref', 'refs/heads/main', manifest['git_head']])
        run([git, '-C', repo, 'read-tree', 'HEAD'])
        run([git, '-C', repo, 'remote', 'add', 'origin', manifest['git_remote']])
        run([git, '-C', repo, 'branch', '--set-upstream-to=origin/main', 'main'])
        head = run([git, '-C', repo, 'rev-parse', 'HEAD'])
        if head != manifest['git_head']:
            raise RuntimeError('HEAD restaurado incorreto.')
        report['git_restored'] = True
        report['git_head'] = head
        report['git_status'] = run([git, '-C', repo, 'status', '--short'])
    else:
        report['git_pending'] = 'Instalar Git; fontes e bundle ja foram restaurados. Instrucoes no LEIA-ME.md.'
    python = alt/'.venv/Scripts/python.exe'
    report['validation'] = run([python, destination/'validar.py', destination])
    (destination/'RESTAURACAO.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print('Restauracao concluida. Leia RETOMAR_NO_CODEX.md; nenhuma automacao foi ativada.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destino', type=Path)
    args = parser.parse_args()
    restore(args.destino.resolve(), Path(__file__).resolve().parent)
