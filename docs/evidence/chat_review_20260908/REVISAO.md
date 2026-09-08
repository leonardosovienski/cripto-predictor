**Minha avaliação: o trabalho é útil e as conclusões econômicas centrais permanecem sustentadas, mas eu não diria que tudo estava perfeito nem repetiria exatamente a mesma sequência.** Encontrei e corrigi uma falha de validação no planejador de quantidades. Também preciso corrigir a força de algumas expressões que usei.

Reli todas as mensagens disponíveis desta tarefa: os cinco pedidos concluídos, suas respostas e atualizações, o texto original anexado e o histórico de comandos. Cruzei as alegações com protocolos, registros de tentativas, logs, código de simulação, auditores, testes, resultados e manifests no Git. A leitura do histórico pela aplicação pode truncar saídas de ferramentas; os registros salvos foram usados para conferir as alegações relevantes. Esta é uma revisão feita pelo mesmo assistente, sozinho como solicitado. Não é uma revisão externa nem uma garantia de ausência de outros defeitos em todo o projeto herdado.

| Etapa do chat | Julgamento após a revisão |
|---|---|
| Preservar o projeto e transferir o observador | Correto dentro da autorização. O repositório original, main, configuração e ledger continuam preservados. A transferência de configuração não prova que uma execução futura ocorrerá. |
| Diagnosticar o seletor e registrar AR1–AR3 | Correto como pesquisa adaptativa. As três hipóteses e cinco séries foram registradas; os resultados negativos e as correções ficaram preservados. Isso não criou uma amostra independente. |
| Pesquisar sete modelos semelhantes | Mecanismos economicamente justificados, com limitações de custos e amostras explicitadas. A nota não comprovou o lucro líquido atual de operadores externos. |
| Implementar BR1 e BR2 | Implementações próprias inspiradas nos mecanismos pesquisados, com regras congeladas. Não são replicações fiéis dos artigos. BR1 tem cinco posições concluídas; BR2 não opera sob o gatilho fixado. |
| Testar se a projeção melhorou | A comparação do lucro histórico foi válida nas condições declaradas. Não foi um teste de qualidade de uma previsão futura. Não existe uma projeção de lucro futuro validada para elevar. |
| Explicar o valor de +424,25 USDT | Os números e percentuais estão corretos: são 980 dias sobre 5.000 USDT, não uma renda mensal. Meu cuidado com a escala é adequado; o julgamento de que o valor é alto ou baixo pertence ao seu objetivo. |

**Falha concreta encontrada e corrigida.** A função isolada `net_hedge_plan` da versão original aceitava um livro de ofertas cruzado. Demonstrei isso com dados sintéticos: melhor compra spot a 1.100 e melhor venda a 1.000. Ela gerava um plano, embora esse livro devesse ser rejeitado. O diagnóstico inicial tinha uma verificação de cruzamento, mas a função nova de planejamento não a repetia; a proteção era incompleta quando chamada diretamente.

A nova entrada `scripts/plan_btc_hedge_v2.py` valida ambos os lados dos dois livros, incluindo níveis além da quantidade a preencher: preços e tamanhos finitos e positivos, ordenação, duplicatas e cruzamento. Também valida as restrições numéricas e recusa amostras salvas com falha ou problemas de tempo. Ela usa a aritmética de quantidades original após essas verificações. A versão congelada continua disponível para reprodução exata dos pacotes antigos; para novos diagnósticos, o ponto de entrada indicado passa a ser v2.

**Impacto:** nenhum dos 12 exemplos públicos usados no relatório foi invalidado. As quantidades, despesas, sobras e margens dos 12 planos v2 são exatamente iguais aos campos econômicos dos planos v1. Os backtests não usam esse planejador, e seus arquivos congelados não foram modificados. Portanto, a correção não aumenta nem reduz o lucro histórico informado.

**O que preciso corrigir na comunicação.**

- “Auditoria independente” foi uma expressão ampla demais. O que existe é uma segunda implementação contábil, escrita por mim. A auditoria BR usa Decimal e não importa o motor econômico, mas compartilha funções de carregamento e normalização dos dados. Pode detectar erros diferentes da simulação; não elimina erros comuns às premissas, à fonte ou ao normalizador. A expressão correta é **conferência contábil por implementação separada, do mesmo autor**.
- Arquivos iguais byte a byte demonstram reprodução do mesmo cálculo. Testes aprovados demonstram os comportamentos cobertos. Nenhum deles, isoladamente, demonstra que a estratégia terá lucro no futuro.
- A melhora de quantidades reduziu a sobra desprotegida do exemplo de 58,26 para 0,40 USDT. Foi necessário comprar menos BTC excedente, preservando caixa. Essa diferença não é receita nem lucro adicional; o histórico já pressupunha quantidades iguais protegidas.
- “Líquido” significa líquido dos custos explicitamente modelados. A despesa de 25 USDT/ano é uma premissa de sensibilidade, não uma fatura observada. Impostos, comissões efetivas, elegibilidade e execução real continuam desconhecidos.
- O observador preservado é o piloto fixo de **altcoins**. Ele **não está confirmando o carry BTC** e sua preservação não preenche essa lacuna. Não acrescentei agora outra automação nem alterei o piloto.

Os lucros centrais conferem:

| Modelo; 5.000 USDT separados, 01/01/2024–07/09/2026 UTC | Base | Custos adversos | Estresse registrado |
|---|---:|---:|---:|
| AR1 BTC contínuo | +424,25 | +341,13 | +104,12 |
| AR1 ETH contínuo | +328,94 | +250,01 | +65,94 |
| AR2 BTC com filtro de funding | +17,79 | −82,26 | −117,42 |
| AR2 ETH com filtro de funding | +30,69 | −80,18 | −130,09 |
| BR1 BTC com vencimento | +230,17 | +110,07 | +78,42 |
| BR2 convergência BTC | 0,00 | 0,00 | 0,00 |

Valores em USDT no período inteiro. AR3 permanece com −4.945,35 USDT no cenário base. O checkpoint anterior de +54,84 USDT em BTC usa outro ano e outra alocação, portanto não foi tratado como melhora comparável. Não há resultado de uma carteira única obtido somando as linhas.

Os +424,25 sobre 5.000 representam 8,49% no período inteiro; +341,13 representam 6,82%. A contribuição adversa do AR1 BTC em 2026 até o corte é +5,75 USDT; no estresse, −21,95. A queda recente impede tratar a média histórica como um rendimento estável. O BR1 ficou 231,06 USDT abaixo do AR1 BTC no cenário adverso, porém teve exposição e períodos em caixa diferentes: isso não demonstra equivalência de risco nem inferioridade em todos os critérios.

**O que eu faria novamente:** usar poucas hipóteses registradas, preservar perdas e tentativas, manter o worktree original intacto, dar prioridade ao carry por seus fluxos identificáveis, cobrar custos desfavoráveis e separar lucro da carteira de capacidade de sustentar margem. Também manteria o resultado zero de BR2 e a rejeição da regra específica de momentum, sem reduzir filtros até fabricar lucro.

**O que faria diferente:** colocaria a validação de execução, dos dados e das restrições no começo da implementação. Testaria cedo o caminho completo do leitor de cenários, que já falhou nesta sessão, e as condições inválidas de entrada do planejador. Após a primeira rodada, concentraria mais esforço em tornar o carry BTC mensurável em observações futuras previamente registradas, antes de ampliar o número de modelos. A coleta curta de 12 pares de livros, em cerca de um minuto, foi um diagnóstico pontual; não mede disponibilidade, deslizamento em várias condições, falhas e preenchimentos parciais ao longo do tempo.

Eu também definiria desde o início uma apresentação comum para capital, moeda, período e custos, distinguindo os critérios estatísticos. O AR1 usa bootstrap descritivo de quatro semanas sobre a média de incrementos semanais; o BR1 usa blocos de 13 semanas sobre o total. Não são intervalos diretamente comparáveis. A seleção de uma única entrada longa e os cinco hedges de BR1 continuam oferecendo pouca diversidade de episódios econômicos. Não calcularia uma suposta probabilidade de lucro futuro com esses números.

Ao retomar a pesquisa bibliográfica, reconferi os mecanismos do [BIS](https://www.bis.org/publications/working-paper-1087-crypto-carry), as taxas e a estratégia de [He e coautores](https://arxiv.org/html/2212.06888v3), o uso de [EFP na CME](https://www.cmegroup.com/articles/2025/bitcoin-futures-exchange-for-physical-transactions.html), a segmentação entre mercados no [MIT](https://mitsloan.mit.edu/cfi/trading-and-arbitrage-cryptocurrency-markets), a amostra e as carteiras compradas/vendidas no [artigo hospedado em Yale](https://economics.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf) e o risco de inventário e informação no [modelo de formação de mercado](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf). O artigo de perpétuos inclui critérios calibrados com dados passados que não foram reproduzidos por nossa regra fixa; BR2 é uma adaptação restrita. A página `.md` de receita da Ethena citada antes não abriu nesta revisão; a [documentação alternativa oficial](https://docs.ethena.fi/solution-overview/protocol-revenue-explanation) sustenta a combinação de staking, funding/basis e ativos estáveis, mas não reconfirma aqui a composição atual nem a extensão de empréstimos/RWA mencionada na leitura anterior. Não uso isso como evidência de lucro do projeto.

Validação executada nesta revisão: **109 testes passaram**, sendo 86 casos anteriores e 23 novos; Ruff aprovado e Pyright sem erros. Foram conferidos os hashes de **24 arquivos congelados** e **28 arquivos de resultados históricos**. A reprodução dos **12 planos** ocorreu com conexões de rede bloqueadas. As entregas antigas, o repositório original, main, automação e ledger continuam preservados. A suíte completa antiga de 1.045 testes não foi repetida. Não executei outra vez os 18 backtests nesta revisão, pois os motores e dados ficaram inalterados e a reprodução do pedido anterior já os tinha conferido; a mudança atual foi testada no componente afetado.

**Decisão final:** eu repetiria o núcleo da pesquisa e seus controles. Corrigiria a validação agora encontrada, a terminologia de auditoria e a prioridade dada à execução e à confirmação futura. Continuo sustentando lucro histórico condicionado aos custos modelados. Continuo sem sustentar lucro real comprovado, uma projeção futura confiável ou que os modelos acrescentados melhoraram a rentabilidade.
