# Decisões consolidadas

1. **KEEP** métricas simples, validação diária e contabilidade já existentes no escopo testado. B01–B06 e 1505 testes não justificam substituir o núcleo por um framework.
2. **IMPROVE / READY_FOR_EXPERIMENT K01/K07**: identidade de instrumento, quote/settlement, clocks e eventos reais devem preceder novas fontes. O snapshot atual recusa data inválida, mas não representa sozinho todo contrato econômico.
3. **AUGMENT / READY_FOR_EXPERIMENT K05**: usar intervalo de label e registrar seleção completa. Gap de linhas não substitui purge; SPA/DSR/PBO respondem perguntas diferentes e não podem ser empilhados para obter significância.
4. **VALIDATE / BLOCKED_DATA K03**: contabilidade Aave é reproduzível; segunda rota falhou. Preservar resultado histórico condicional e não confundir ausência de corroboração com refutação. Não repetir a rota sem mudança real de acesso.
5. **RESEARCH / BLOCKED_DATA K04**: ranking residual é candidato com mecanismo e contraexemplo externo. Antes de retorno, resolver universo histórico e hedge financiável.140 semanas já vistas não são holdout.
6. **AUGMENT / BLOCKED_DATA K06**: diagnóstico de profundidade/hedge passou; fila, latência, falha parcial e margem entre venues precisam modelo/dados próprios. Engine externo não cria esses dados.
7. **DEFER K13/K14/K17 como implementação**: LP, opções e RL têm questões úteis, mas não há ganho incremental executável medido que justifique custo e novas dependências agora. Lending/staking continuam separados de universo direcional.
8. **REJECT premissas**, não projetos inteiros: stablecoins equivalentes por substring, APY exibido como renda realizada, preço last/mark como fill, fórmula 8h universal, retorno de duas pernas calculado sobre capital de uma só.

## Reuso concreto

| Capacidade | Forma de reuso escolhida | Por quê |
| --- | --- | --- |
| K02/SciPy | Referência de teste, implementação local mantida | Já instalado, custo baixo, diferencial passou |
| K05/sklearn | Dependência já existente para split explícito + oracle intervalar isolado | B05 mostra limite exato; não instalar outro CV como solução automática |
| K04/Alphalens | Adapter de pesquisa candidato, não integração | Contrato cripto e pandas/compatibilidade ainda pendentes |
| K05/arch/skfolio | Código de referência, futura execução isolada | Testes lidos, mas bloco/multiplicidade/labels precisam desenho primeiro |
| K06/Nautilus/hftbacktest | Processo isolado candidato, não trocar engine | API/licença e dados L2/capital dominam custo |
| K06/cryptofeed | Fonte de desenho; adoção direta adiada | AGPL e migração 3.x aumentam acoplamento; não inferir licença permissiva |
| K03/Aave | Referência matemática e recibos RPC existentes | Implantação por bloco importa mais que importar contrato antigo |
| K13/Uniswap | Referência parcial de arredondamento, não engine econômico | Licença convertida e modelo de posição/fees distintos |
| K14/QuantLib | Referência numérica isolada futura | Instrumento cripto e histórico executable quotes faltam |

## Limites encerrados com estado explícito

Foi concluída a rodada de pesquisa/benchmark prevista no mandato: baseline, descoberta ampla, aprofundamento focado, comparação, mínimos admissíveis e decisão. Não foi concluída validação econômica de todas as hipóteses — o próprio mandato condiciona execução a dados, protocolo e proteção de amostras. As pendências agora são gates concretos, não a promessa genérica de terminar leitura depois.

Dados PIT externos contratados, histórico L2/opções/fila staking e implementação histórica do proxy Aave não foram obtidos. Repositórios fora dos 23 aprofundados seguem triagem. Não se afirma auditoria integral de 364 arquivos ou dos pacotes Core/Ops. Issues são relatos externos. Sem replicação econômica externa nem superioridade de retorno. E6-P só pode existir após janela/maturação real.

Preservados: H1/H2/H3/H5 CLOSED_NO_GO; H4/H6/H9 CLOSED_INSUFFICIENT_SAMPLE; H7/H8 não ativadas; família funding_oi_hmm_v3 congelada. Carry manual v2: entrada 12/09/2026 00–01UTC e saída 05/12; LLM paired v3:84 slots diários a partir 12/09 12–13UTC, último target 13/12. Não executamos observadores antes da janela nem alteramos código congelado.

Única alteração operacional de estado: consumo normal de 1 unidade de quota pelo protocolo limitado de corroboração Aave, sem resposta de dados. Nenhuma ordem, pagamento, agendamento, instalação, alteração de código/lock, commit, PR, push ou merge. O documento preexistente do usuário foi preservado byte a byte.
