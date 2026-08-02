# Backup e restore do Feature Store

O banco `output/feature_store.db` e um artefato operacional ignorado pelo Git.
O utilitario `scripts/feature_store_backup.py` cria snapshots consistentes pela
API de backup online do SQLite, inclusive quando o banco usa WAL.

## Criar e verificar

Use um destino fora do repositorio, idealmente em outro volume com politica de
retencao definida pelo operador:

```powershell
py -3.14 scripts/feature_store_backup.py create --output E:\backups\cripto\2026-07-20
py -3.14 scripts/feature_store_backup.py verify --backup E:\backups\cripto\2026-07-20
```

O comando recusa um destino existente. O diretorio so e publicado depois de
`PRAGMA integrity_check=ok` e contem:

- `feature_store.db`, sem arquivos WAL/SHM dependentes;
- `BACKUP_MANIFEST.json`, com versao do formato, timestamp UTC, tamanho e
  SHA-256 do banco.

## Restaurar sem tocar producao

O restore aceita somente uma raiz que ainda nao exista:

```powershell
py -3.14 scripts/feature_store_backup.py restore `
  --backup E:\backups\cripto\2026-07-20 `
  --destination C:\restore-tests\previsao-cripto-20260720
```

O banco restaurado fica em `DESTINO\output\feature_store.db`. A copia e feita
em diretorio temporario, passa novamente por `integrity_check` e so entao e
renomeada para o destino final. O utilitario nunca sobrescreve o banco ativo.

## Retencao e teste periodico

A ferramenta resolve criacao, integridade e recuperacao local. Frequencia,
retencao, criptografia e volume externo continuam sendo decisoes operacionais
humanas. Um teste periodico deve criar o backup, verifica-lo, restaura-lo para
uma raiz descartavel e consultar o banco restaurado em modo read-only.


