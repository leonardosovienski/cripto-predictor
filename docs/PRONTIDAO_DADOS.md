# Prontidão de dados e pendências para concluir a preparação

Estado conferido em 09/09/2026, após a importação das chaves e a definição dos limites locais. A revisão de arquitetura pode começar com o material disponível. A operação completa com dados novos e a validação econômica ainda não estão concluídas. Este documento distingue essas entregas e seus critérios de conclusão.

## O que foi fechado

- Código, ambiente, configuração, dados preservados e novas entregas estão organizados dentro de `C:\Cripto`.
- A restauração anterior verificou os 66.360 arquivos do pacote recebido, respeitando quatro realocações de ambiente documentadas. Isso não certifica tudo que já existiu no computador antigo.
- Gemini, SerpAPI, Groq, Cerebras e CoinGecko estão preenchidas no arquivo privado; o modo Gemini + SerpAPI carrega sem erro. A validade externa ainda não foi testada.
- Os limites de API deixaram de ser ilimitados: 28 unidades de ingestão, 8 tentativas de notícias por provedor e 6 chamadas lógicas de LLM por provedor, por dia UTC. São os valores de referência de `API_GUARDS.md`; não representam garantia de gratuidade, teto monetário ou cobertura de todos os retries internos. Não houve chamada de API nem coleta iniciada. [Comprovante dos limites](C:/Cripto/operacao/relatorios/LIMITES_API_20260909T192125822404Z.json).
- Uma nova conferência local de dados de carry passou: protocolo, 68 respostas brutas, 10 arquivos normalizados, grade de preços e intervalos-base de funding. Uma reconstrução separada dos futuros também passou: 532 respostas brutas e 29 séries normalizadas de 12 contratos. Esses testes não são auditoria externa, novo backtest ou certificação de execução real.

## Catálogo principal disponível

| Base | Local dentro de C:\Cripto | Conteúdo verificado e limite |
|---|---|---|
| Carry histórico | `restaurado-20260908\sessoes\20260907-pesquisa\work\carry-research-data` | BTC e ETH: séries desde 01/12/2023 até o corte de 07/09/2026. Por ativo: 1.012 pontos diários spot, 1.012 perp, 24.265 pontos horários de marcação e 3.033 eventos de funding. O ponto final de preço contém somente a abertura; dezembro é preparação da janela econômica iniciada em janeiro |
| Futuros com vencimento | `restaurado-20260908\sessoes\20260907-pesquisa\work\basis-research-data` | 29 séries, 12 contratos e 532 respostas reconstruídas. Há duas lacunas horárias discriminadas abaixo |
| Aquisição inicial de altcoins | `restaurado-20260908\sessoes\20260907-altcoins\work\altcoin-data` | Manifesto: 240 ativos selecionados, 241 registros de pares incluindo referência, zero erros declarados de aquisição; coleta concluída em 07/09 |
| Retrospectiva ampliada de altcoins | `restaurado-20260908\sessoes\20260907-altcoins\work\altcoin-retro-data` | Manifesto: 661 pares, 727.447 linhas e zero erros declarados. Cobertura semântica por par ainda precisa ser detalhada nesta preparação |
| Observador de altcoins | `restaurado-20260908\sessoes\20260907-altcoins\work\altcoin-reviewed-data` | Status preservado de 08/09: duas linhas no diário, zero decisões prospectivas e zero observações maduras |
| Observador de carry | `restaurado-20260908\sessoes\20260907-pesquisa\work\carry-forward-data` | Status preservado de 08/09: uma linha no diário, entrada não observada. Nenhuma nova coleta iniciada |
| Operação nova | `operacao\dados` e `operacao\saidas` | Zero arquivos de dados e zero saídas de execução no momento da conferência. O fluxo conectado ainda não produziu sua primeira entrega |

O catálogo acima cobre as bases principais, não cada cópia de pacote, cache ou experimento antigo. Os status dos observadores foram lidos como registros históricos, sem recalcular sua agenda contra a data atual. Os hashes das aquisições de altcoins foram conferidos na migração anterior; nesta rodada foram lidos seus manifestos, sem uma nova certificação semântica de todos os pares.

## O que falta e quando estará concluído

| Pendência | Trabalho necessário | Critério verificável de conclusão |
|---|---|---|
| 1. Validar serviços externos usados | Conferir validade das chaves, modelos/endpoints disponíveis, plano gratuito ou cota existente e comportamento de falhas, dentro dos limites definidos | Respostas reais úteis dos provedores necessários, erros tratados, consumo registrado e nenhum segredo exposto; presença de chave não basta |
| 2. Fazer a primeira execução completa | Coletar uma amostra controlada, normalizar, persistir, processar e produzir saída legível; testar também leitura e reexecução | Dados e resultados reais gravados nos caminhos corretos, proveniência e datas preservadas, sem duplicação indevida e com falhas parciais visíveis. Diagnóstico operacional não vira uma amostra científica por renomeação |
| 3. Completar a cobertura das bases | Detalhar datas, ativos, campos, duplicatas, intervalos ausentes, atualidade e origem para as bases utilizadas por cada fluxo, especialmente altcoins e o histórico operacional antigo | Cada fluxo tem contrato de dados e entradas rastreáveis; faltas estão recuperadas quando possível ou explicitamente limitam o uso e a conclusão |
| 4. Esclarecer o banco operacional antigo | Localizar backup/exportação suficiente da Feature Store se for necessária a reprodução integral de previsões e trials antigos | Banco ou exportação com origem e integridade verificadas, ou registro preciso do que não pode ser recuperado/reproduzido. Não inventar previsões antigas nem confundir snapshots de código com dados |
| 5. Resolver dados específicos de hipóteses selecionadas | Para o estudo Aave: índices históricos e liquidez de retirada na janela registrada. Para outros mecanismos, adquirir somente os dados que podem mudar sua decisão | Evidência suficiente para o teste definido, ou encerramento/estacionamento explícito por falta de dados. Aave não é dependência de toda a arquitetura |
| 6. Executar a revisão e o reteste geral pedidos | Reconstruir a arquitetura atual, corrigir problemas demonstrados e executar suíte completa, qualidade, tipos, build, pacote, Windows e CI aplicável | Nova evidência no código efetivamente revisado, com skips e limites declarados. Os 1.278 testes anteriores não substituem esse trabalho |
| 7. Fechar a conta econômica | Consolidar premissas de capital e perda, tarifas, execução, financiamento, conversão e infraestrutura; separar desenvolvimento já incorrido de custo recorrente | Resultados conciliados na moeda e período corretos, custos desconhecidos visíveis e critérios de viabilidade. Dados do dono ausentes continuam cenários, não fatos |
| 8. Obter avaliação futura | Respeitar um protocolo registrado antes da observação e colher a amostra necessária ao estudo elegível | Evidência posterior à escolha da estratégia, com tentativas, dias ausentes e riscos registrados. Não é possível completar dados futuros imediatamente ou garantir que a conclusão será lucro |

Os itens 1, 2, 3 e 6 são trabalho técnico a executar com os recursos autorizados. O item 4 pode depender de backup adicional do computador antigo. O item 5 depende da fonte adequada e da hipótese escolhida. O item 7 requer informações pessoais/operacionais para uma conta final, embora cenários permitam continuar a pesquisa. O item 8 depende de observações novas e de calendário; esta preparação não ativa automações ou operações financeiras.

## Lacunas concretas encontradas

Duas séries de marcação de futuros, `BTCUSDT_260925_mark` e `BTCUSDT_261225_mark`, passam de 28/06/2026 às 23h UTC para 30/06/2026 às 00h UTC. Faltam 24 pontos horários de 29/06 em cada uma, 48 ao todo. A reconstrução confirma que os arquivos normalizados correspondem às respostas preservadas; isso não torna o período completo.

A revisão deve conferir como cada decisão, posição e cálculo de risco usa esses intervalos, tentar recuperar a informação quando a pergunta exigir e documentar a indisponibilidade quando não for recuperável. O motor já tem tratamento explícito de resultado ausente; este achado, isoladamente, não comprova bug de software nem mudança do lucro publicado. Não preencher preços por conveniência, esconder ausências ou excluir períodos para melhorar o resultado.

Não foram localizados arquivos soltos `.db`, `.sqlite` ou `.sqlite3` na árvore restaurada examinada. A leitura dos índices de 85 ZIPs preservados também não encontrou entradas com essas extensões ou os sufixos de backup buscados. A busca não abriu arquivos compactados dentro de outros compactados nem examinou bancos sem essas extensões. Assim, a recuperação integral da antiga Feature Store permanece **não certificada**, sem afirmar que seus dados sejam universalmente irrecuperáveis. Os seis arquivos inicialmente citados em `D:` continuam indisponíveis.

## Informação que pode depender do dono

Se existir, indicar o local de outro backup do banco operacional ou dos arquivos originais em `D:`. Para fechar custos e viabilidade pessoal: capital que deseja usar como referência, perda tolerável, corretora e tabela de taxas aplicáveis, gastos mensais de serviços/infraestrutura e total já gasto no desenvolvimento. Não é necessário fornecer acesso de negociação ou mais chaves opcionais apenas para começar a revisão; contas financeiras não serão acessadas.

Até essas informações existirem, manter os 5.000 USDT como hipótese declarada, mostrar sensibilidades e custos de equilíbrio, sem afirmar retorno líquido pessoal ou retorno sobre o investimento no projeto.

## Evidências desta preparação

- [Catálogo de dados e intervalos observados](C:/Cripto/operacao/relatorios/PRONTIDAO_DADOS_20260909T190147Z/CATALOGO_DADOS.json).
- [Conferência dos dados de carry](C:/Cripto/operacao/relatorios/PRONTIDAO_DADOS_20260909T190147Z/carry_validation.json), executada por `scripts.backtest_absolute_carry.load_dataset` com o protocolo registrado.
- [Reconstrução dos futuros](C:/Cripto/operacao/relatorios/PRONTIDAO_DADOS_20260909T190147Z/basis_validation.json), executada por `scripts.audit_basis_sources.audit` com saída nova.
- [Lacunas horárias identificadas](C:/Cripto/operacao/relatorios/PRONTIDAO_DADOS_20260909T190147Z/lacunas_futuros.json).
- [Busca limitada de bancos nos backups](C:/Cripto/operacao/relatorios/PRONTIDAO_DADOS_20260909T190147Z/busca_bancos_em_backups.json).
- [Limites de API configurados](C:/Cripto/operacao/relatorios/LIMITES_API_20260909T192125822404Z.json).
- [Escopo completo da próxima revisão](NEXT_CHAT_PROMPT.md).

Nenhum resultado econômico foi alterado, nenhum dado histórico foi preenchido, nenhuma API foi chamada e nenhum agendamento ou operação financeira foi ativado nesta preparação. As verificações de dados executadas aqui são específicas; não equivalem à revisão completa de arquitetura e testes solicitada para a próxima etapa.
