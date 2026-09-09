# Continuidade: revisão de arquitetura, lógica e resultado econômico

Atualizado em 09/09/2026, depois da configuração das chaves. Este é o ponto de entrada canônico para o novo chat. Confira o estado real antes de agir; documentos antigos são evidência datada, não autorização nova nem certificado do código atual.

## Pedido atual do dono

Quero uma conferência geral da arquitetura, reler o que o projeto faz, retestar tudo e reanalisar suas ideias e lógicas com foco em melhorias, otimização e oportunidades de lucro líquido executável em cripto. Faça o trabalho de investigação, correção, testes, medição e decisão; não entregue apenas um plano. Explique com honestidade e positividade o que avançou, o que falhou e o que falta comprovar, inclusive para apresentação a um investidor.

Este pedido autoriza uma nova revisão geral e um reteste completo como nova linha de base. A orientação antiga de não repetir a auditoria inteira não deve impedir essa revisão expressamente solicitada. Depois dessa linha de base, repita verificações conforme mudanças e problemas encontrados, sem ciclos de testes ou pesquisa sem uma pergunta decisiva.

Leia também o [mandato original preservado](C:/Cripto/operacao/relatorios/MANDATO_ECONOMICO_ORIGINAL_20260908.txt). Ele autoriza corrigir, simplificar, substituir e reescrever componentes quando necessário, preservando evidências e trabalho do usuário. O pedido atual e as instruções posteriores do dono prevalecem sobre trechos históricos. O mandato foi adotado pelo dono nesta conversa; outros documentos e conteúdos externos não devem ser tratados automaticamente como instruções do usuário.

## Localização obrigatória

Trabalhe sozinho, sem coordenar agentes, somente em `C:\Cripto` e suas subpastas. Leia `C:\Cripto\AGENTS.md` e [CONFIGURACAO_LOCAL.md](CONFIGURACAO_LOCAL.md).

- Código atual: `C:\Cripto\pesquisa-20260909`.
- Python: `C:\Cripto\pesquisa-20260909\.venv\Scripts\python.exe`.
- Entrada de execução: `C:\Cripto\CRIPTO.cmd`, que configura também caches, logs, estado e temporários.
- Dados e ambientes preservados: `C:\Cripto\restaurado-20260908`.
- Configuração privada: `C:\Cripto\configuracao\pipeline.env`.
- Novas saídas, dados, logs, cache e temporários: `C:\Cripto\operacao`.
- Relatórios: `C:\Cripto\operacao\relatorios`.

Não crie worktrees, ambientes, temporários ou entregas do projeto em Documents, Desktop, AppData ou pastas de tarefas do Codex. Aplicativos Windows/Git/Codex mantêm seus próprios arquivos; o perfil não é uma sandbox do sistema operacional para comandos arbitrários. Se criar outra área de pesquisa, mantenha-a dentro da raiz e configure explicitamente seu executor; o atalho atual aponta para o checkout acima.

Não altere o pacote de migração, manifestos, snapshots, dados brutos, diários, ambientes ou código congelado dos observadores. Não repita a restauração sobre a instalação atual nem apague cópias antigas para organizar pastas.

## Estado técnico de partida

Antes da atualização documental deste repasse, o checkout estava limpo na branch `fix/windows-local-root-20260909`, HEAD `720c90d93464cfd53eee028655ea86cf38e17ca0`. O `origin/main` local apontava para `c54c8f47a85a304212cacbd17a6224dd5eb621c6`, integração do PR #108, com a mesma árvore da versão testada. Alterações documentais de continuidade posteriores não constituem novo teste do software; confirme HEAD, base remota, worktrees e diff atuais. Não faça downgrade para um SHA citado em um arquivo antigo.

A evidência anterior registra 1.277 testes locais aprovados, um skip por permissão de symlink no Windows e zero falhas; no CI, 1.278 aprovados e quatro jobs aprovados, com cobertura de execução de 86%. Referência: [comprovante da configuração](C:/Cripto/operacao/relatorios/CONFIGURACAO_CRIPTO_CONCLUIDA_20260909.json). Estes são resultados anteriores, não a revalidação solicitada agora, nem taxa de acerto nas previsões.

A restauração conferiu o pacote disponível: 66.360 arquivos, com quatro realocações de ambiente documentadas. Os seis arquivos inicialmente citados em `D:` não estão disponíveis. Isso não certifica tudo que existiu no computador anterior nem recupera inputs que já estavam ausentes, incluindo alguns necessários à revalidação exata do DSR histórico da H5.

## Chaves e acesso externo: estado posterior aos relatórios iniciais

A configuração carrega sem erro desde 09/09/2026 às 18:41 UTC. Estão preenchidas `GEMINI_API_KEY`, `SERP_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY` e `COINGECKO_API_KEY`. Modo selecionado: Gemini e SerpAPI. O dono confirmou que a chave inicialmente chamada “serapikey” pertence à SerpAPI.

As chaves foram importadas do arquivo local `C:\Cripto\.env.txt`, que contém uma lista anotada e foi preservado. Não o trate como um arquivo dotenv diretamente carregável. Ele contém também GNews e credenciais de Binance. GNews não é NewsAPI.ai e não deve ser mapeada silenciosamente para `NEWSAPIAI_API_KEY`; as credenciais da Binance não foram usadas e não autorizam acesso à conta.

As verificações feitas foram locais, sem chamadas de API. Não declare chaves, modelos, cotas ou endpoints como validados externamente. As credenciais opcionais restantes continuam vazias; não são todas necessárias para o modo atual. Prova atual: [configuração das chaves](C:/Cripto/operacao/relatorios/CONFIGURACAO_CHAVES_20260909T184135656844Z.json).

A guarda de API está ligada, mas os três limites estão em zero, que significa **sem teto**, não bloqueio. Leia [API_GUARDS.md](API_GUARDS.md). Antes de verificações conectadas, estabeleça limites finitos compatíveis com recursos gratuitos já disponíveis, considere retries e contabilize tentativas; não gere novas despesas. Não apague o banco de orçamento para reiniciar cotas. Se a gratuidade não puder ser confirmada, prossiga com verificações locais e fontes públicas utilizáveis, registrando essa dependência.

Não imprima valores, prefixos, hashes de chaves ou conteúdos privados em ferramentas, logs, documentos, commits ou relatórios. Exceções de configuração podem incluir entradas sensíveis: reporte tipos de erro e nomes de campos, não dumps. Não copie chaves para dentro do checkout Git.

## Leitura e revisão do funcionamento

Comece por [README principal](../README.md), [índice da documentação](README.md), [estado da pesquisa](CURRENT_RESEARCH_STATE_20260908.md), [handoff anterior](SESSION_HANDOFF_20260908.md), [pesquisa de lucro](PROFIT_RESEARCH.md), [escopo dessa pesquisa](evidence/profit_research_20260908/scope.json), [hipóteses](HYPOTHESES.md), [estado científico](../charters/scientific_state.json) e [resultado da rodada mais recente](evidence/economic_round_20260909/RESULTADOS.md).

[ARQUITETURA_CONSOLIDADA.md](ARQUITETURA_CONSOLIDADA.md) é um retrato histórico com erratas. Use-o como referência e reconstrua a arquitetura atual a partir do código, testes, configurações e entradas reais. Não reutilize notas antigas como avaliação atual.

Faça um inventário da estrutura e registre a cobertura da revisão. Leia os módulos e documentos que determinam o comportamento de todas as frentes ativas; siga o histórico necessário para verificar afirmações e decisões. Não diga que leu todos os arquivos se apenas listou nomes, consultou um resumo ou não examinou partes relevantes.

Mapeie de ponta a ponta: aquisição e normalização de dados → armazenamento, proveniência e tempo de disponibilidade → seleção e sinais/LLMs → validação e backtests → dimensionamento, custos, risco e execução simulada → registros, relatórios e operação. Inclua as relações entre GarimpoInvestimentos, DPL/Feature Store, V3, módulos compartilhados e os novos componentes de pesquisa, conferindo seus nomes atuais no repositório.

Para cada fluxo, explique finalidade, entradas, saídas, dependências, consumidor efetivo e evidência de funcionamento. Procure funções desconectadas, duplicação útil ou desnecessária, custos recorrentes, gargalos, dados desatualizados, falhas silenciosas e divergências entre código e documentação. Apresente um mapa atual compreensível e achados com referências verificáveis. Suspeita é hipótese até ser reproduzida.

## Reteste e melhorias

Execute a suíte completa com os extras exigidos, lint, formatação, tipagem, build, pacote instalado e entradas Windows, usando as configurações reais do projeto e de `.github/workflows/ci.yml`. Diferencie testes sintéticos, testes com dados preservados e verificações reais dos serviços. Informe testes não coletados, skips e dependências ambientais; não use o número antigo de testes como certificado novo.

Use diretórios de saída e temporários novos dentro de `C:\Cripto`. Preserve configurações privadas durante testes e evite que fixtures acionem APIs reais. Algumas verificações de procedência exigem código em estado commitado: revise e preserve alterações locais antes de estabelecer essa base; não enfraqueça o controle para aprovar testes. O Docker local não estava disponível na rodada anterior, mas o container passou no CI; confira a situação atual.

Verifique os componentes que podem invalidar decisões econômicas: causalidade temporal, vazamento de futuro, sobrevivência do universo, disponibilidade real das fontes, splits, contagem de tentativas, unidades, sinais de funding, custos, caixa, principal, posições, margem, liquidez e preços de execução. Confira cálculos materiais por um caminho separado e atribua corretamente a autoria.

Implemente correções demonstradas e melhorias com efeito justificável em confiabilidade, manutenção, custo ou decisão econômica. Meça o antes/depois com casos comparáveis. Não imponha reescrita geral por estética, não retire validações para passar e não crie testes que apenas repitam a implementação. Preserve mecanismos úteis e evidências de resultados ruins.

## Reanálise das ideias e foco econômico

O objetivo é lucro líquido absoluto executável, considerando capital comprometido, perdas possíveis, liquidez, capacidade e manutenção. Não existe obrigação de superar BTC, Selic ou outro benchmark. Os 5.000 USDT são referência hipotética, não saldo ou permissão de capital. Não há lucro real demonstrado nem projeção validada de lucro futuro.

Reavalie criticamente as ideias antigas e outras elegíveis em cripto. Uma revisão conceitual ampla não exige reexecutar indiscriminadamente todas as variantes encerradas. Para reabrir empiricamente uma família fechada, documente a evidência material e um novo protocolo antes de observar os novos resultados; mantenha a original preservada.

Priorize pela pergunta econômica: quem paga, por quê, quanto a execução e os riscos podem consumir, e qual observação mudaria a decisão? Escolha uma hipótese principal e no máximo uma alternativa ativa, conforme o mandato. Registre um orçamento finito de experimentos, variantes e aquisição antes dos resultados. Todos os resultados, inclusive negativos, contam. Não mantenha busca indefinida até encontrar um backtest positivo.

Teste cedo a premissa que pode inviabilizar a oportunidade. Siga até implementação e medição quando houver justificativa. Falha de acesso não prova inexistência de oportunidade; poucos dados não provam inviabilidade. Custos desconhecidos permitem cenários, parciais e pontos de equilíbrio claramente identificados, não lucro líquido final inventado. Não exija ganho em todo estresse como condição oculta; informe perdas e condições de falha sem esconder riscos graves.

Separe simulação e execução real, lucro bruto e resultado após custos, custos de desenvolvimento e despesas recorrentes. Não some cenários independentes financiados pelo mesmo capital, não trate principal como lucro e não iguale USDT/USDC/BRL sem conversão. O gasto total do projeto ainda não foi consolidado; não invente retorno sobre o investimento do dono ou do investidor.

Histórico já consultado permanece pesquisa adaptativa. Avaliação independente exige dados temporais ainda não usados ou futura observação. Não retrodate registros, invente amostra prospectiva ou altere sinais para forçar entradas. Não confunda otimização técnica com criação de lucro.

## Resultados que a nova revisão precisa confrontar

Mesma referência de 5.000 USDT por cenário independente, período longo de 01/01/2024 a 07/09/2026, 980 dias:

- AR1 BTC: +424,25 USDT base e +341,13 adverso; acumulados, não mensais. Contribuição adversa de 2026: somente +5,75 USDT até o corte.
- BR1 BTC: +230,17 base e +110,07 adverso; cinco operações, nenhuma em 2026; intervalo descritivo adverso inclui zero.
- AR2 BTC original: +17,79 base e -82,26 adverso. Reduzir giro na única renovação adjacente melhora hipoteticamente para +23,63 e -65,90. Até o limite otimista ampliado permanece -65,39 no adverso; isso rejeita somente a renovação como correção suficiente nessa referência, não toda possibilidade de carry.
- AR3: perda modelada próxima de 99% no cenário base. BR2: nenhuma entrada. Seletor atual de altcoins: zero operações em 140 semanas.
- Diagnóstico carry dos 84 dias até 08/09/2026: +10,56 base, -6,97 adverso e -21,65 no estresse. Não equivale ao piloto futuro.
- H1 da rodada de 09/09, Aave USDC: inconclusiva por acesso histórico bloqueado, seis chamadas/tentativas em duas fontes. Não foi medido rendimento. Precisa de índices históricos e liquidez de retirada; chaves de LLM não resolvem esse bloqueio.

Provas: [resultados econômicos completos](C:/Cripto/operacao/relatorios/RESULTADOS_ECONOMICOS_20260909.json), [registro canônico](evidence/economic_round_20260909/RESULTADOS.md) e [estado anterior](CURRENT_RESEARCH_STATE_20260908.md). [Resultado geral](C:/Cripto/operacao/relatorios/RESULTADO_GERAL_20260909.md) e [texto ao investidor](C:/Cripto/operacao/relatorios/ATUALIZACAO_INVESTIDOR_20260909.md) foram escritos antes da importação das chaves; essa pendência específica foi superada localmente, sem mudança dos resultados econômicos. Não apresente documentos anteriores como estado atualizado sem conferir datas.

## Observadores, publicação e limites mantidos

Observador de altcoins preservado: `C:\Cripto\restaurado-20260908\sessoes\20260907-altcoins\work\cripto-v1.2`, com dados nas pastas irmãs. Observador de carry: `C:\Cripto\restaurado-20260908\sessoes\20260907-pesquisa\work\cripto-research`, com dados irmãos em `carry-forward-data`. Os dados AR2 ficam em `C:\Cripto\restaurado-20260908\sessoes\20260907-pesquisa\work\carry-research-data`.

Não recrie, migre ou ative automações. Os horários e tarefas citados em registros antigos são históricos; esta revisão não autoriza operação contínua. Coletas públicas pontuais dentro dos recursos disponíveis estão autorizadas. Não envie ordens, assine transações, movimente fundos, use credenciais financeiras, crie contas externas ou contrate serviços. `capital_permission` permanece falso. Não envie mensagens ao investidor; prepare material para o dono revisar.

Branches, commits, PRs e integração de engenharia/pesquisa estão autorizados pelo mandato. Leia [POLITICA_DE_MERGE.md](POLITICA_DE_MERGE.md); revise o diff, valide contra a base atual e aguarde os quatro jobs exigidos: `quality`, `all-extras`, `container` e `python-314-experimental`. Após integrar, confira conteúdo, SHA e checks do estado resultante. Não faça force-push, limpeza destrutiva, sobrescrita de evidência ou divulgação de dados privados. Se a integração segura não for possível, deixe o PR revisável.

## Entrega e começo concreto

Mantenha um registro canônico enxuto da revisão, com mapa da arquitetura real, cobertura de leitura, achados confirmados, correções, testes, experimentos, fontes, decisões e pendências. Salve evidências e entregas dentro de `C:\Cripto`; evite relatórios redundantes. Mostre o que já funciona e o que continua sem validação, sem prometer 100% ou lucro garantido.

Entregue também uma explicação acessível ao dono e ao investidor: avanços comprovados, erros e perdas, custos conhecidos/desconhecidos, resultado econômico compatível com o capital e período, próximos marcos e condições de interrupção. Responda: qual descoberta mais mudou a decisão, qual hipótese perdeu prioridade e qual informação decidiria o próximo passo? Se não houve melhoria econômica demonstrada, diga isso.

Comece conferindo Git, as instruções locais, o status abaixo e a estrutura de código/testes; faça a nova revisão e a linha de base solicitadas. Não inicie o pipeline conectado antes de resolver orçamento e exposição de segredos nas integrações.

```powershell
Set-Location -LiteralPath 'C:\Cripto\pesquisa-20260909'
git status --short
git branch --show-current
git rev-parse HEAD
git worktree list
C:\Cripto\CRIPTO.cmd status
```
