# Migração para Windows: código pelo Git e dados separados

O código atual, os testes, os utilitários de migração e as versões históricas identificadas estão no Git. O arquivo externo **`CRIPTO_DADOS_MIGRACAO_20260908.zip`** contém somente dados, diários, resultados, relatórios e configurações do snapshot de 08/09/2026. Seu manifesto confere a correspondência com o [índice de código](source_archive_20260908/sources.json).

O pacote antigo `CRIPTO_MIGRACAO_WINDOWS_20260908.zip`, de aproximadamente 1,6 GB, é o backup completo anterior. Para a separação solicitada, use o novo pacote de dados. Não misture os procedimentos dos dois formatos.

## No computador de destino

Instale Git e uv. Copie o novo ZIP e o arquivo SHA256 que o acompanha. Reserve 5 GB livres além do espaço necessário para clonar o repositório. A restauração usa uma pasta nova e recusa sobrescrever dados existentes.

No PowerShell, ajuste o caminho do ZIP e execute:

```powershell
git clone https://github.com/leonardosovienski/cripto-predictor.git "$env:USERPROFILE\cripto-predictor"
Set-Location "$env:USERPROFILE\cripto-predictor"
uv python install 3.13.14
Get-FileHash -Algorithm SHA256 'D:\CRIPTO_DADOS_MIGRACAO_20260908.zip'
uv run --no-project --python 3.13.14 python -m scripts.research_migration restore --data-zip 'D:\CRIPTO_DADOS_MIGRACAO_20260908.zip' --destination "$env:USERPROFILE\CriptoDados"
```

Compare o hash com o arquivo recebido antes da restauração. O programa verifica todos os conteúdos, lê o código histórico do Git e recompõe as pastas operacionais com os bytes originais. Confira `CriptoDados/RESTAURACAO_DADOS.json`; o resultado deve ser `PASS`. O script não usa pacotes externos para restaurar, não consulta corretoras e não altera os dados de origem.

O checkout clonado `cripto-predictor` é o diretório para desenvolver e fazer commits. `CriptoDados/projeto` é uma fotografia do estado anterior. As pastas em `CriptoDados/sessoes` guardam as pesquisas e os observadores congelados; não as atualize com a main.

| Diretório dentro de `CriptoDados` | Uso |
|---|---|
| `sessoes/20260907-altcoins/work/cripto-v1.2` | Código congelado de altcoins recuperado do Git |
| `sessoes/20260907-altcoins/work/altcoin-reviewed-data` | Diário, snapshots e fontes públicas de altcoins |
| `sessoes/20260907-altcoins/work/altcoin-data` | Aquisição e universo de treinamento |
| `sessoes/20260907-altcoins/work/altcoin-payoff-results` | Amostras fixas do treinamento |
| `sessoes/20260907-pesquisa/work/cripto-research` | Código congelado de carry recuperado do Git |
| `sessoes/20260907-pesquisa/work/carry-forward-data` | Diário e fontes brutas de carry |
| `sessoes/20260907-pesquisa/work` | Dados históricos de carry/basis e auditorias |
| `configuracao` | Versões dos ambientes e fotografia da automação |

Os demais dados históricos também são recompostos. Arquivos ZIP mistos foram abertos para separar dados de código; seu conteúdo fica em caminhos terminados em `.extraido`. Cópias idênticas desses contêineres são representadas uma vez, com os nomes equivalentes registrados em `expanded_containers`. Backups Git, instaladores, wheels e partes de backups não são dados operacionais e não entram no novo ZIP. O manifesto registra essas exclusões.

## Recriar o ambiente do observador

O novo ZIP não transporta Python nem bibliotecas. Reinstale as versões fixas a partir do Git. Execute na raiz do checkout clonado:

```powershell
$observadorCripto = "$env:USERPROFILE\CriptoDados\sessoes\20260907-altcoins\work\cripto-v1.2"
uv venv --python 3.13.14 "$observadorCripto\.venv"
uv pip install --python "$observadorCripto\.venv\Scripts\python.exe" --no-cache --link-mode copy --no-deps -r docs/source_archive_20260908/runtime-requirements.txt
uv pip install --python "$observadorCripto\.venv\Scripts\python.exe" --no-deps -e "$observadorCripto"
Set-Location $observadorCripto
& .\.venv\Scripts\python.exe -m scripts.verify_research_runtime
```

O verificador precisa retornar `PASS`. A instalação usa downloads novos e cópias independentes porque o cache compartilhado do PC de origem tinha arquivos divergentes em `distlib` e `virtualenv`. Confirme também os congelamentos e os diários pelos runbooks antes de retomar qualquer observação. Se faltar uma versão ou houver divergência, preserve os dados e investigue. Não atualize versões, parâmetros ou hashes para contornar uma falha. Os executáveis Python são criados para o caminho do novo computador.

## Acompanhamento

A configuração de altcoins foi exportada como registro; a automação continua vinculada ao computador e à tarefa antigos. Use o recurso de automações do Codex para efetivar a transferência, atualizar os caminhos e manter somente uma execução operacional. O horário registrado é domingo às 21h de Brasília, primeira entrada prevista em 13/09/2026 e última saída em 06/12/2026. O computador precisa estar ligado e o aplicativo aberto nos horários de coleta.

O agendamento de carry continua pendente e não é criado pela restauração. Não retrodate janelas perdidas. O snapshot não incorpora coletas posteriores a sua criação; transfira dados mais recentes antes de encerrar a operação no PC antigo.

Para continuar no Codex do outro computador, indique este guia, a pasta restaurada e [NEXT_CHAT_PROMPT.md](NEXT_CHAT_PROMPT.md). Os caminhos deste guia substituem os caminhos locais históricos dos documentos. Trabalhe sozinho, somente com dados públicos e marcas hipotéticas, sem contas de negociação ou ordens. Não há lucro real comprovado.
