# `scripts/forense/` — sondas de banco preservadas da branch de backup

Cinco scripts de uma linha só, recuperados de
`claude/entender-3-projetos-cfvrck-backup-2026-09-03` em 2026-09-06, pouco antes
de aquela branch ser apagada. Eram os **únicos cinco arquivos** de todo o
repositório de branches que não existiam no `main`.

## Por que valeram a pena preservar

Como código, valem pouco: têm caminho `C:\` fixo, não têm tratamento de erro e
só imprimem `COUNT(*)`. Como **documentação**, valem — são a única fonte que
registra quais snapshots do Feature Store existem na máquina de produção, e
foram escritos por quem estava sentado nela.

Em particular, `check_backup.py` faz exatamente a consulta que responde a única
ressalva de proveniência que sobrou em aberto no registro científico: o `n` por
trás do Sharpe **+0,4766** da H6, registrado em `trials.json` com maturidade
**DESCONHECIDA** (ver `docs/HYPOTHESES.md`). Sem estes arquivos, nem o caminho
do backup seria conhecido fora da máquina.

O mapa completo do que existe na máquina está em
[`docs/MAQUINA_DE_PRODUCAO.md`](../../docs/MAQUINA_DE_PRODUCAO.md).

## O que cada um faz

| Script | Alvo | Responde |
|---|---|---|
| `check_db.py` | `feature_store.db` (ativo) | quais tabelas existem |
| `check_db2.py` | `feature_store.db` (ativo) | `COUNT(*)` das 8 tabelas + migrações aplicadas |
| `check_backup.py` | `feature_store_backup_antes_limpeza.db` | **total de `predictions`, quebra por fonte, intervalo de `ts`** |
| `check_all_tables.py` | 2 `failed-runs` + o backup | `COUNT(*)` de toda tabela de cada um |
| `check_failed_runs.py` | 3 `failed-runs` | tabelas, total de `predictions`, fontes e intervalo `ts` |

## Como usar

Rodam com o Python do sistema, sem dependência nenhuma além da stdlib
(`sqlite3`). **Só funcionam na máquina de produção** — os bancos são gitignored
e não existem em nenhum outro lugar.

```powershell
cd C:\predictor\prod
python scripts\forense\check_backup.py
```

Abrem os bancos em modo leitura-escrita por descuido do autor original
(`sqlite3.connect` puro). Eles só executam `SELECT`, mas se você quiser
garantia, copie o arquivo antes ou troque a conexão por
`sqlite3.connect("file:...?mode=ro", uri=True)`.

`scripts/forense` está em `extend-exclude` do ruff (`pyproject.toml`) pelo mesmo
motivo: o lint quereria reordenar os imports, e isso já seria reescrever.

**Preservados como estão, sem correção.** São registro histórico: reescrevê-los
apagaria a informação de quais caminhos existiam de fato em 2026-09-03.
