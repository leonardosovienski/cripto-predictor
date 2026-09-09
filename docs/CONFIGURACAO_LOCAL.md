# Configuração deste PC: somente C:\Cripto

A raiz de trabalho autorizada neste computador é **`C:\Cripto`**. Código, ambientes do projeto, dados, configuração privada, saídas, logs, estado dos jobs, caches, temporários e novas entregas devem ficar dentro dela. Use este mapa para executar e continuar o projeto; caminhos de máquinas anteriores nos arquivos históricos não são destinos operacionais.

| Caminho | Uso atual |
|---|---|
| `C:\Cripto\pesquisa-20260909` | Checkout de desenvolvimento atualizado; confira a branch e o HEAD com Git |
| `C:\Cripto\pesquisa-20260909\.venv` | Python e dependências do projeto atual |
| `C:\Cripto\pesquisa-20260909\work` | Runtimes gerenciados, cache uv e execuções de pesquisa já existentes |
| `C:\Cripto\restaurado-20260908` | Os 66.360 arquivos do pacote restaurado, incluindo runtime e sessões |
| `C:\Cripto\restaurado-20260908\projeto` | Snapshot preservado da migração; não é o checkout de desenvolvimento atual |
| `C:\Cripto\configuracao\pipeline.env` | Configuração privada das APIs; nunca publicar ou imprimir valores |
| `C:\Cripto\operacao\dados` | Dados de novas execuções do pipeline geral |
| `C:\Cripto\operacao\saidas` | Saídas do pipeline e seu `feature_store.db` |
| `C:\Cripto\operacao\cache` | Cache do pipeline, pip e bibliotecas auxiliares |
| `C:\Cripto\operacao\logs` | Logs e `events.jsonl` |
| `C:\Cripto\operacao\estado` | Estado, locks e heartbeats dos jobs |
| `C:\Cripto\operacao\temporarios` | TEMP, TMP, TMPDIR e temporários de bibliotecas |
| `C:\Cripto\operacao\relatorios` | Relatórios e comprovantes entregues ao dono |
| `C:\Cripto\ferramentas` | Ferramentas e atalhos criados futuramente pelo uv |

Os dados históricos continuam em suas sessões originais. A configuração não funde bancos, não alimenta um banco novo com resultados retrospectivos e não altera diários ou congelamentos. Em particular, os dados da AR2 ficam em `C:\Cripto\restaurado-20260908\sessoes\20260907-pesquisa\work\carry-research-data`.

## Como executar

No PowerShell ou no Prompt de Comando, mesmo começando em outra pasta:

```powershell
C:\Cripto\CRIPTO.cmd status
C:\Cripto\CRIPTO.cmd pipeline --help
C:\Cripto\CRIPTO.cmd python -m scripts.diagnose_ar2_renewals --help
```

O atalho usa o Python de `C:\Cripto\pesquisa-20260909\.venv`, estabelece o diretório de trabalho e configura o ambiente somente do processo e de seus filhos. Para comandos de manutenção use `C:\Cripto\CRIPTO.cmd uv ...`; assim os caches e instalações gerenciados também permanecem nesta raiz. Nenhum atalho agenda ou executa coletas sozinho.

O arquivo local e ignorado pelo Git `C:\Cripto\pesquisa-20260909\.cripto-root` contém `C:\Cripto`. O código atual lê esse marcador ao carregar seus caminhos ou configurações, inclusive pela entrada direta `cripto-predictor`. A variável `CRIPTO_ROOT` também permite selecionar explicitamente o mesmo perfil. Rodar comandos auxiliares pelo atalho aplica o perfil antes de importar bibliotecas.

Dentro desse perfil, `DATA_DIR`, `OUTPUT_DIR`, `CACHE_DIR`, `LOGS_DIR`, as variantes `GARIMPO_*`, `PREDICTOR_OPS_STATE_DIR`, `PREDICTOR_EVENTS_PATH` e `CRIPTO_ENV_FILE` precisam resolver para dentro da raiz. Caminhos relativos são relativos a `C:\Cripto`. Um caminho externo ou um link que escape da raiz é recusado antes da criação dos diretórios. Não use `--output-dir` apontando para Desktop, Documents, AppData ou outro disco.

O perfil configura o armazenamento do projeto, não é uma sandbox do Windows para comandos Python arbitrários. Windows, Git e Codex são aplicativos do computador e mantêm seus próprios arquivos. Os snapshots e relatórios anteriores fora da raiz não são apagados; as cópias de trabalho necessárias ficam em `C:\Cripto`.

## Configuração privada e estado real

`pipeline.env` parte do exemplo público com as chaves vazias. Configure valores reais somente nesse arquivo local ou em um ambiente de processo privado. Não cole segredos no chat, documentação, commits ou relatórios. O perfil não importa credenciais do computador antigo nem inventa chaves.

**Atualização de 09/09/2026, 18:41 UTC:** foram importadas Gemini, SerpAPI (confirmada pelo dono), Groq, Cerebras e CoinGecko do arquivo local fornecido pelo usuário. O modo Gemini + SerpAPI carrega sem erro. Nenhuma API foi chamada para validar as credenciais. GNews e Binance permanecem somente no arquivo de origem, sem integração ou uso de conta. Os três limites de API continuam em zero, que significa sem teto; configure um orçamento finito antes do uso conectado. Veja o [comprovante local](C:/Cripto/operacao/relatorios/CONFIGURACAO_CHAVES_20260909T184135656844Z.json) e o [novo escopo de revisão](NEXT_CHAT_PROMPT.md).

**Atualização posterior, 09/09/2026:** os limites antes zerados foram configurados para 28 unidades de ingestão, 8 tentativas de notícias por provedor e 6 chamadas lógicas de LLM por provedor, por dia UTC. Nenhuma API foi chamada. Isso não certifica cotas gratuitas nem limita diretamente gastos ou todos os retries internos. Consulte [PRONTIDAO_DADOS.md](PRONTIDAO_DADOS.md) para o catálogo, as verificações feitas e os critérios que ainda faltam.

O comando `status` mostra os caminhos e se a configuração do pipeline carrega, sem imprimir credenciais nem fazer requisições. Enquanto faltarem as chaves exigidas pelos provedores selecionados, ele informa a falha de configuração e o pipeline mantém a recusa existente. Pesquisa local e diagnóstico AR2 não exigem essas APIs. Configurar pastas não comprova conectividade, disponibilidade de dados históricos ou lucro.

Os observadores preservados ficam separados:

- Altcoins: `C:\Cripto\restaurado-20260908\sessoes\20260907-altcoins\work\cripto-v1.2`; dados irmãos em `altcoin-reviewed-data`, `altcoin-data`, `altcoin-payoff-results` e `altcoin-retro-data`.
- Carry: `C:\Cripto\restaurado-20260908\sessoes\20260907-pesquisa\work\cripto-research`; dados irmãos em `carry-forward-data`.

Seus códigos e runtimes congelados permanecem preservados. Esta configuração não ativa agendamentos, coletas recorrentes, LLMs, operações financeiras ou capital. Eventuais comandos futuros devem manter seus dados e saídas em `C:\Cripto` e respeitar os protocolos vigentes.

## Continuidade e recuperação

Leia este arquivo, [NEXT_CHAT_PROMPT.md](NEXT_CHAT_PROMPT.md) e o [resultado econômico de 09/09](evidence/economic_round_20260909/RESULTADOS.md). Não use `C:\Users\Superleo13`, `USERPROFILE`, `AppData` ou as antigas pastas de tarefas do Codex como destinos para novos arquivos do projeto. Entregue novos relatórios em `C:\Cripto\operacao\relatorios`.

O pacote original na raiz e seus guias preservam os hashes da migração. O arquivo local `C:\Cripto\LEIA_PRIMEIRO.md` aponta para este mapa atual. Não reescreva evidências, manifestos ou documentos congelados para trocar seus caminhos históricos. Para outra máquina, consulte [MIGRACAO_WINDOWS.md](MIGRACAO_WINDOWS.md); não restaure novamente sobre as pastas já existentes neste PC.
