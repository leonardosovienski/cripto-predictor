# Como reproduzir a pesquisa

O pacote contém os bytes exatos do código usado, o protocolo registrado, a correção de causalidade, resultados anteriores e finais, testes, auditoria e `RESEARCH_DATA.zip` com 3.077 arquivos. O pacote de dados inclui todas as respostas brutas e séries normalizadas necessárias à nova pesquisa. Não depende dos caminhos da tarefa antiga para a reprodução.

Não extraia sobre outra pesquisa nem sobre o ledger do observador. Não altere hashes para aceitar finais de linha diferentes. Use os arquivos exatamente como vêm no ZIP. A restauração não transfere a automação, não ativa contas e não envia ordens.

No diretório `code` extraído, com Python 3.13 (ambiente validado) ou Python compatível:

```powershell
python -X utf8 -m scripts.reproduce_absolute_research --destination '..\verificacao-nova'
```

Esse comando usa somente a biblioteca padrão para conferir o código e o arquivo de dados, extrair em uma pasta nova, conferir cada SHA256 e recalcular a auditoria independente. A auditoria reordena os candidatos spot e reconstrói os payoffs e a margem com Decimal, sem importar o motor de backtest e sem fazer consultas públicas.

Para repetir também os cinco backtests completos, o ambiente precisa ter as dependências do projeto. Com `uv` disponível, a instalação reproduzível é:

```powershell
uv sync --locked --extra test --extra science --link-mode copy
.venv\Scripts\python.exe -X utf8 -m scripts.reproduce_absolute_research --destination '..\replay-novo' --full
.venv\Scripts\python.exe -m pytest tests/test_absolute_research.py tests/test_altcoin_payoff.py tests/test_altcoin_retro.py tests/test_altcoin_forward.py -q
```

A instalação das dependências pode precisar de rede. As etapas de auditoria e replay não precisam. Use outro destino novo a cada execução. `--full` compara os 19 arquivos gerados com os hashes dos resultados finais; nenhum resultado anterior é sobrescrito.

A validação desta entrega utilizou o Python 3.13.14 e as dependências já bloqueadas/validadas do projeto original, por caminho absoluto, executando o código deste novo worktree. Não copiamos a `.venv` nem instalamos pacotes no ambiente do observador. Os 58 testes dirigidos, Ruff, Pyright, a auditoria e o replay em pasta diferente passaram. Os 19 arquivos de resultados foram reproduzidos byte a byte após conferir os 3.077 arquivos de dados.

Arquivos de interesse:

- `docs/evidence/absolute_research_20260908/DECISAO.md`: explicação econômica completa.
- `protocol.json`, `causality_amendment.json`, `trials.json`, `run_history.md`: registro de hipóteses e correções.
- `absolute-results-v3/results.json`: resultados finais de todas as séries; subpastas `carry` e `spot` têm decisões e trajetórias.
- `absolute-results-v2`: primeira avaliação preservada; a correção causal não alterou suas contas econômicas.
- `independent-audit.json`, `reproduction_check.json`, `validation.json`: conferências.
- `automation_transfer.json`, `preservation_check.json`: vínculo nesta tarefa, leituras locais e preservação do ledger original.

O código continua localmente na branch `codex/cripto-absolute-research-20260908`, partindo de fbf4c71. A main e o worktree original foram preservados. Não houve push. O arquivo `git-changes.bundle`, quando fornecido na entrega, contém somente a evolução desde fbf4c71; requer esse commit já disponível no Git original ou no bundle anterior preservado. O ZIP de reprodução é independente para os novos testes e não depende desse bundle incremental.

O pacote não copia os grandes arquivos de recuperação de sessões antigas, ambientes virtuais, caches ou credenciais. Essas evidências antigas permanecem no Git comum e na cópia independente já documentada no encerramento anterior. A lista exata dos arquivos deste pacote está em `FILES_SHA256.json` na raiz.
