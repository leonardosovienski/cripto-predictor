# Backup e restauração do Feature Store

Neste PC, o banco ativo é `C:\Cripto\operacao\saidas\feature_store.db`. Ele é ignorado pelo Git. O utilitário [feature_store_backup.py](../scripts/feature_store_backup.py) usa a API de backup online do SQLite, inclusive em WAL, e publica a cópia somente após verificar sua integridade.

## Criar, verificar e testar a restauração

Execute pelo perfil local. Os destinos precisam ser novos e permanecer em `C:\Cripto`:

```powershell
$backupStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$backupPath = "C:\Cripto\backups\feature-store-$backupStamp"
$restorePath = "C:\Cripto\operacao\temporarios\restore-feature-store-$backupStamp"
C:\Cripto\CRIPTO.cmd python -m scripts.feature_store_backup create --database C:\Cripto\operacao\saidas\feature_store.db --output $backupPath
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar backup' }
C:\Cripto\CRIPTO.cmd python -m scripts.feature_store_backup verify --backup $backupPath
if ($LASTEXITCODE -ne 0) { throw 'Falha ao verificar backup' }
C:\Cripto\CRIPTO.cmd python -m scripts.feature_store_backup restore --backup $backupPath --destination $restorePath
if ($LASTEXITCODE -ne 0) { throw 'Falha ao testar restauração' }
```

O backup contém `feature_store.db` independente de WAL/SHM e `BACKUP_MANIFEST.json` com versão, instante UTC, tamanho e SHA-256. A verificação compara o manifesto e executa `PRAGMA integrity_check`. A restauração recusa destino existente e produz `DESTINO\output\feature_store.db`; ela não substitui o banco ativo.

Depois, consulte a cópia restaurada em modo somente leitura e compare o conteúdo com o backup. O banco ativo pode ter avançado após a captura; compare com o instante registrado, não apenas com uma contagem antiga da documentação. A conferência de 10/09 inclui um teste de restauração no [registro de arquivos](CONFERENCIA_ARQUIVOS_20260910.md).

## O que este backup cobre

Esta ferramenta cobre somente o Feature Store. A recuperação completa também depende do código Git, runtimes congelados, dados brutos, protocolos, diários, relatórios, configuração privada e banco `C:\Cripto\operacao\dados\api_guard_budget.db`. Preserve o estado das quotas; não apague, zere ou restaure uma versão antiga desse banco para contornar o orçamento.

O [mapa local](CONFIGURACAO_LOCAL.md), a [conferência de arquivos](CONFERENCIA_ARQUIVOS_20260910.md) e o [pacote histórico](continuity_20260909/README.md) identificam esses componentes e seus cortes. O pacote original e os arquivos restaurados são preservados integralmente. Não restaure sobre a instalação existente.

Backups nesta raiz compartilham o mesmo disco; eles não protegem contra sua perda física. O mandato atual mantém todo o armazenamento do projeto em `C:\Cripto` e não ativa rotina automática de backup. Retenção ou uma cópia externa exigem uma decisão específica; isso não impede o uso das cópias locais verificadas.
