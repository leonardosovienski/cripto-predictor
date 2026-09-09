# Migração para Windows: código e dados dentro de C:\Cripto

**Neste PC a restauração já foi concluída.** O mapa atual e a execução estão em [CONFIGURACAO_LOCAL.md](CONFIGURACAO_LOCAL.md). Os comandos abaixo são para uma nova máquina, com destinos ainda inexistentes; não devem ser repetidos sobre a instalação atual.

O código atual, os testes, os utilitários de migração e as versões históricas identificadas estão no Git. O arquivo externo **`CRIPTO_DADOS_MIGRACAO_20260908.zip`** contém somente dados, diários, resultados, relatórios e configurações do snapshot de 08/09/2026. Seu manifesto confere a correspondência com o [índice de código](source_archive_20260908/sources.json).

O pacote antigo `CRIPTO_MIGRACAO_WINDOWS_20260908.zip`, de aproximadamente 1,6 GB, é o backup completo anterior. Para a separação solicitada, use o novo pacote de dados. Não misture os procedimentos dos dois formatos.

## No computador de destino

Tenha Git e uv disponíveis. Copie o novo ZIP e seu SHA256 para `C:\Cripto`. Configure os destinos do uv e dos temporários antes de instalar dependências; nenhuma pasta do projeto deve ser criada no perfil do usuário. Reserve 5 GB livres além do espaço necessário para clonar o repositório. A restauração usa uma pasta nova e recusa sobrescrever dados existentes.

No PowerShell, ajuste o caminho do ZIP. Primeiro confira o hash e compare com o arquivo recebido; só prossiga à restauração se coincidir:

```powershell
Get-FileHash -Algorithm SHA256 'C:\Cripto\CRIPTO_DADOS_MIGRACAO_20260908.zip'
```

Depois da comparação, execute:

```powershell
New-Item -ItemType Directory -Force 'C:\Cripto\operacao\temporarios' | Out-Null
$env:TEMP = 'C:\Cripto\operacao\temporarios'
$env:TMP = $env:TEMP
$env:UV_CACHE_DIR = 'C:\Cripto\pesquisa-20260909\work\uv-cache'
$env:UV_PYTHON_INSTALL_DIR = 'C:\Cripto\pesquisa-20260909\work\managed-python'
$env:UV_PYTHON_BIN_DIR = 'C:\Cripto\ferramentas\bin'
$env:PIP_CACHE_DIR = 'C:\Cripto\operacao\cache\pip'
git clone https://github.com/leonardosovienski/cripto-predictor.git 'C:\Cripto\pesquisa-20260909'
Set-Location 'C:\Cripto\pesquisa-20260909'
uv python install 3.13.14
uv sync --locked --all-extras
uv run --no-project --python 3.13.14 python -m scripts.research_migration restore --data-zip 'C:\Cripto\CRIPTO_DADOS_MIGRACAO_20260908.zip' --destination 'C:\Cripto\restaurado-20260908'
```

Depois de clonar e validar os dados, configure o perfil local no checkout e prepare o arquivo privado sem sobrescrever uma configuração existente:

```powershell
Set-Content -LiteralPath 'C:\Cripto\pesquisa-20260909\.cripto-root' -Value 'C:\Cripto' -Encoding utf8
New-Item -ItemType Directory -Force 'C:\Cripto\configuracao' | Out-Null
if (-not (Test-Path -LiteralPath 'C:\Cripto\configuracao\pipeline.env')) {
    Copy-Item -LiteralPath 'C:\Cripto\pesquisa-20260909\.env.example' -Destination 'C:\Cripto\configuracao\pipeline.env'
}
C:\Cripto\pesquisa-20260909\cripto.cmd status
```

O arquivo `.cripto-root` e a configuração privada são locais. O `status` não consulta APIs nem imprime credenciais. Use esse atalho para as próximas execuções; veja o mapa completo em [CONFIGURACAO_LOCAL.md](CONFIGURACAO_LOCAL.md).

O programa verifica todos os conteúdos, lê o código histórico do Git e recompõe as pastas operacionais com os bytes originais. Confira `restaurado-20260908/RESTAURACAO_DADOS.json`; o resultado deve ser `PASS`. O script não usa pacotes externos para restaurar, não consulta corretoras e não altera os dados de origem.

O checkout clonado `C:\Cripto\pesquisa-20260909` é o diretório para desenvolver e fazer commits. `restaurado-20260908/projeto` é uma fotografia do estado anterior. As pastas em `restaurado-20260908/sessoes` guardam as pesquisas e os observadores congelados; não as atualize com a main.

| Diretório dentro de `C:\Cripto\restaurado-20260908` | Uso |
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
$observadorCripto = 'C:\Cripto\restaurado-20260908\sessoes\20260907-altcoins\work\cripto-v1.2'
uv venv --python 3.13.14 "$observadorCripto\.venv"
uv pip install --python "$observadorCripto\.venv\Scripts\python.exe" --no-cache --link-mode copy --no-deps -r docs/source_archive_20260908/runtime-requirements.txt
uv pip install --python "$observadorCripto\.venv\Scripts\python.exe" --no-deps -e "$observadorCripto"
Set-Location $observadorCripto
& .\.venv\Scripts\python.exe -m scripts.verify_research_runtime
```

O verificador precisa retornar `PASS`. A instalação usa downloads novos e cópias independentes porque o cache compartilhado do PC de origem tinha arquivos divergentes em `distlib` e `virtualenv`. Confirme também os congelamentos e os diários pelos runbooks antes de retomar qualquer observação. Se faltar uma versão ou houver divergência, preserve os dados e investigue. Não atualize versões, parâmetros ou hashes para contornar uma falha. Os executáveis Python são criados para o caminho do novo computador.

## Acompanhamento

A configuração de altcoins foi exportada como registro; a automação continua vinculada ao computador e à tarefa antigos. A configuração das pastas não transfere nem ativa automações. Somente sob um pedido específico de agendamento use o recurso de automações do Codex, confira a desativação no computador anterior e mantenha os caminhos dentro de `C:\Cripto`. O horário registrado é domingo às 21h de Brasília, primeira entrada prevista em 13/09/2026 e última saída em 06/12/2026. O computador precisa estar ligado e o aplicativo aberto nos horários de coleta.

O agendamento de carry continua pendente e não é criado pela restauração. Não retrodate janelas perdidas. O snapshot não incorpora coletas posteriores a sua criação; transfira dados mais recentes antes de encerrar a operação no PC antigo.

Para continuar no Codex do outro computador, indique este guia, a pasta restaurada e [NEXT_CHAT_PROMPT.md](NEXT_CHAT_PROMPT.md). Os caminhos deste guia substituem os caminhos locais históricos dos documentos. Trabalhe sozinho, somente com dados públicos e marcas hipotéticas, sem contas de negociação ou ordens. Não há lucro real comprovado.
