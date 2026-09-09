# Estado vigente da pesquisa — 08/09/2026

**Continuidade em 09/09/2026:** a rodada econômica posterior está em [RESULTADOS](evidence/economic_round_20260909/RESULTADOS.md). Neste PC, todo o trabalho deve permanecer em `C:\Cripto`: veja [CONFIGURACAO_LOCAL.md](CONFIGURACAO_LOCAL.md) para código, dados, ambientes, saídas e credenciais locais. O restante desta página preserva as decisões de 08/09.

Esta é a referência vigente após a revisão e as correções. Relatórios anteriores permanecem como evidência histórica; suas afirmações devem ser lidas com as retificações abaixo. Não existe projeção validada de lucro futuro nem resultado de execução real.

**Situação técnica após a consolidação:** trabalho publicado na `main`, única branch local e remota. A suíte completa passou em **1.170 testes**; os quatro jobs do [CI da consolidação](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34228309330) passaram, incluindo container. Os registros abaixo de 1.167 testes se referem à etapa anterior. [Continuidade, arquivos e caminhos](SESSION_HANDOFF_20260908.md).

Atualização após o pedido de auditar agora: `docs/evidence/immediate_audit_20260908/RESULTADOS.md` registra a nova coleta pública. Nos 84 dias encerrados em 08/09, o carry hipotético ficou em +10,56 USDT no cenário base, −6,97 USDT no adverso e −21,65 USDT no estresse. Houve também onze observações de livros ao longo de cinco minutos, com conferência de preços na OKX. As contas passaram na reconstrução separada; o ganho histórico recente não resistiu aos custos adversos. Essa rodada não substituiu nem iniciou o piloto futuro de 84 dias. A suíte completa passou em 1.167 testes.

## Correções e versões

- `scripts.plan_btc_hedge_v3` é a entrada mantida para diagnóstico com livros salvos. Rejeita livros cruzados, números não finitos, horários inválidos, fontes duplicadas ou inconsistentes e amostras incompletas. Uma rejeição retorna código de saída 1. v1/v2 ficam congelados para reproduzir entregas anteriores; não devem ser usados para aceitar novos dados.
- `scripts.audit_basis_sources` refaz a leitura e a normalização histórica com implementação separada, somente biblioteca padrão. Não importa o normalizador de produção. A conferência de 532 respostas e 29 séries passou. Continua sendo trabalho do mesmo assistente, com dados da mesma origem; não é auditoria externa.
- `scripts.observe_carry_forward` é o novo observador público de uma posição hipotética de carry BTC. Protocolo e código são congelados antes da coleta. Não opera contas nem envia ordens. Registra decisões antes dos livros, preserva tentativas interrompidas, horários e dias ausentes, e distingue pré-teste de observação prospectiva.
- O observador anterior de altcoins segue separado. Seus resultados não podem confirmar o carry BTC.

Os executáveis históricos e seus registros de teste não foram substituídos. Use os pacotes antigos para reprodução e o suplemento desta correção para as novas entradas acima.

## O que os números permitem afirmar

Mesma referência de 5.000 USDT, intervalo de 01/01/2024 a 07/09/2026, cada cenário financiado separadamente:

| Estratégia | Lucro modelado base | Lucro modelado adverso | Interpretação |
|---|---:|---:|---|
| AR1 BTC, carry contínuo | 424,25 USDT | 341,13 USDT | 8,49% / 6,82% acumulados em 980 dias; não mensais |
| BR1 BTC, futuros com vencimento | 230,17 USDT | 110,07 USDT | Cinco operações; não melhorou o resultado histórico do AR1 |
| BR2 BTC, compressão intradiária | 0,00 USDT | Custo fixo modelado sem operações | Zero entradas; não há rentabilidade operacional demonstrada |

AR2 foi negativo com custos adversos; AR3 perdeu aproximadamente 99% no período. Preservar esses resultados é parte da pesquisa. Não somar lucros de cenários independentes como se viessem da mesma conta. A comparação anterior de 54,84 USDT usava outro período e outra alocação; não serve como comparação direta de melhoria.

O cenário adverso AR1 BTC contribuiu apenas 5,75 USDT em 2026 até o corte. O BR1 não abriu posição em 2026; seus custos fixos continuam sendo hipótese contábil. O intervalo descritivo do bootstrap BR1 adverso incluiu zero (aproximadamente −6,96 a 247,26 USDT). Os bootstraps antigos usam unidades distintas e não representam probabilidade de lucro futuro. Drawdowns com frequências diferentes também não são comparáveis diretamente.

A redução de BTC descoberto no planejador é uma correção de quantidade. O valor de aproximadamente 58 USDT anteriormente exposto não equivale a lucro criado pela correção. Nas 12 amostras válidas salvas, a nova validação preserva os planos econômicos.

## Evidência prospectiva e limites explícitos

O novo protocolo foi preparado para observar uma única posição durante 84 dias. Primeira janela: 08/09/2026 às 21h de Brasília; horário previsto de coleta às 21h15. Última janela: 01/12/2026 às 21h, coleta às 21h15. Cada janela dura uma hora. O pré-teste público passou e não abriu posição. O agendamento ainda não foi criado: o aplicativo recusou uma segunda automação nesta tarefa, que já contém a de altcoins. A autorização para criar uma tarefa separada foi solicitada ao usuário. Consulte `docs/evidence/carry_forward_20260908/scheduling.json` para o registro; a automação de altcoins não foi alterada.

Resultados intermediários são marcas hipotéticas de encerramento pelos livros públicos. Incluem spread, profundidade e cenários explícitos de custos, funding com sinal, caixa de margem separado e teste adicional de salto de 30%. O teste usa máximas de horas completas e não certifica liquidação real, horas incompletas ou simultaneidade dos negócios. A cobertura de funding verifica os intervalos de oito horas definidos no protocolo; não é uma certificação independente da integralidade do provedor em mudanças de calendário.

Taxas e ativo da comissão da conta, preenchimentos reais, tributos, conversão para reais e regras efetivas de margem permanecem desconhecidos neste escopo de dados públicos. O modelo usa taxas equivalentes em USDT; o diagnóstico separado mostra a alternativa de comissão em BTC. Esses limites não são corrigidos com números inventados. Uma única posição de 84 dias também não basta para comprovação estatística.

“Auditoria independente” nos relatos anteriores deve ser entendido como conferência por cálculo separado, feita pelo mesmo assistente. Independência de autoria e de fonte não foi obtida. Os modelos semelhantes pesquisados inspiraram adaptações; não são réplicas certificadas. A afirmação anterior específica sobre loans/RWA da Ethena não foi reconfirmada na revisão atual e não deve sustentar a decisão; nenhuma dessas receitas entrou no cálculo de lucro do projeto.

## Operação e reprodução

Leia `docs/evidence/carry_forward_20260908/RUNBOOK.md`. O registro `docs/evidence/corrections_20260908/issues.json` distingue correções implementadas de evidência futura pendente. Ausência de erro em testes não é prova de ausência de qualquer defeito.
