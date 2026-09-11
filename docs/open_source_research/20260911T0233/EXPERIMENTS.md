# Experimentos executados e próximos gates

Baseline e protocolos precederam os respectivos resultados. B01/B02 foram executados na fase inicial; B03–B06 são uma extensão pré-registrada em EXTENDED_PROTOCOL.json às 03:01:59UTC, com hashes de código, fixtures e aceitação fixados. Nenhum input de mercado foi aberto para escolher esses casos.

| ID | Pergunta/entrada | Resultado | Escopo |
| --- | --- | --- | --- |
| B01 | Spearman/ranks; 100 pares sintéticos com empates | 0 divergências; erro máximo 1,11e−16; constante indefinida | C4/E5 técnico; SciPy1.18.0 |
| B02 | SMA/Bollinger; 231 prefixos | Erro máximo 2,84e−14; controle de média futura detectado em 230 prefixos | C4/E5 técnico; NumPy2.5.1; sem RSI/MACD |
| B03 | Serving:1 válido+8 clocks/identidade/preço inválidos | 9/9 conforme esperado | C4; não testa contrato completo de quote/chain |
| B04 | 3 VWAPs exatos +4 entradas inválidas | 100/101/99 concordantes; 4 rejeições corretas | C4; não estima probabilidade de fill |
| B05 | 30 labels,3 folds, gap 2; label 5 termina em 25 | Sobreposição nos 3 folds; purge por término remove todas | C4; limitação de desenho, não bug de sklearn |
| B06 | Hedge sintético: comissão spot, short e caixa 5000 | Net12,4875 versus short 12,487; dust 0,0005; caixa reconcilia; pouca profundidade futura rejeitada | C4; fees assumidos e ausência de execução real |
| T01 | Suíte inteira do projeto isolada | 1505 passed,1 skipped; 428,28s pytest | C3; rede de testes externa bloqueada; logs preservados |
| A01 | 1728 fluxos Aave do estudo preservado | Reconciliados por Fractions aos índices RPC e custos reservados | Reprodução histórica contábil; mesma amostra; sem E6 novo |
| A02 | 38 fronteiras por segunda rota, protocolo existente | ConnectTimeout na 1ª chamada; 0 bytes; 1 unidade ingestão reservada; 0 retries | BLOCKED_DATA; nenhum novo valor de mercado obtido |

Não houve benchmark de velocidade entre engines. O tempo do B01/B02 não inclui import/startup e não sustenta superioridade de desempenho. B04 rejeita quantidade além da profundidade publicada; isso não simula execução parcial empírica. B06 conserva caixa total no cenário, mas não demonstra transferência instantânea, tarifa pessoal ou margem real da conta.

A primeira execução de 33 testes teve 6 falhas pelo bloqueio indevido do loopback Windows; runner corrigido passou 33. A execução integral subsequente usou a correção. Falhas e recibos anteriores permanecem arquivados; não foram apagados para melhorar o histórico. Tentativa Aave não foi repetida: começou após verificar 28 unidades disponíveis no diaUTC e preservou started/result no diretório registrado. Os demais probes históricos malsucedidos não foram reabertos.

## Até cinco próximos experimentos, ordenados por informação

### F01 — O contrato distingue BTC/USD, BTC/USDT, linear/inverso e variantes por chain sem produzir preço USD fictício?

Estado: **READY_FOR_EXPERIMENT**; capacidade K01. Já executado: B03 executou 9 casos de serving, escopo mais estreito que identidade de instrumentos.

Teste mínimo: Adapter de pesquisa com quatro pares de identidade, dois controles de clock e uma revisão tardia; não alterar serving atual. Contrastar o mesmo input sem metadata e com contrato explícito.

Pré-requisitos: Especificar base/quote/settlement/venue/chain e unidade em novo artefato; snapshot atual não representa todas essas distinções.

Métrica: Todos os casos monetariamente diferentes permanecem separados; 0 conversões implícitas; 2 clocks inválidos recusados. Decisão: Se faltam campos, BLOCKED_SCHEMA; se adapter preserva identidades, G1 de engenharia aprovado para nova coleta.

Orçamento: 9 casos determinísticos; 0 rede; 1 adapter; sem dependência nova. Próximo gate: G1 isolado; qualquer integração é posterior.

### F02 — Uma rota archive disponível corrobora os mesmos 38 blocos Aave e a implementação histórica?

Estado: **BLOCKED_DATA**; capacidade K03. Já executado: Reprodução contábil 1728 casos passou; coleta segunda rota falhou ConnectTimeout.

Teste mínimo: Preservar a tentativa BlockREQ. Só abrir protocolo complementar após mudança comprovada de acesso; mesmos 38 blocos e mesmas comparações, sem procurar rendimento. Acrescentar vinculação proxy/implementation por bloco em contrato separado.

Pré-requisitos: Endpoint permitido e disponível; recebimento de eth_chainId e estado histórico; quota normal; identificar bytecode e implementação no bloco.

Métrica: Zero divergência de hash/índice/identidade em 38 fronteiras. Implementação histórica ligada a código verificável. Decisão: Concordância é corroboração da mesma cadeia; timeout não refuta rendimento. Nenhuma nova tentativa sem mudança do bloqueio.

Orçamento: Protocolo tentado: até 350 RPC/20MB,1 ingestão,0 retries; consumiu 1 chamada e 0 bytes. Novo acesso exige orçamento explícito.. Próximo gate: G1 complementar antes de coleta; G2 de proveniência, sem promoção econômica.

### F03 — Ranking residual líquido de beta/custos melhora a seleção direcional sem depender dos sobreviventes atuais?

Estado: **BLOCKED_DATA**; capacidade K04. Já executado: B01 validou aritmética do IC; paper R42 mostra que mudar hedge altera resultados.

Teste mínimo: Primeiro gate de dados de um painel PIT: incluir falhas/delistings e pelo menos uma moeda excluída pelo filtro atual. Depois registrar uma baseline momentum e uma alternativa residual, mesmos ativos/datas, rebalanceamento semanal e hedge BTC explicitamente financiado.

Pré-requisitos: K01, universo/custos/borrow e horizonte definidos; período reservado novo. As140 semanas vistas e 727447 linhas antigas não são holdout. Não ativar uma terceira família econômica.

Métrica: Gate dados:100% das linhas usadas com elegibilidade/clock/fonte comprovados; caso contrário não calcular alpha. Fase econômica: IC por semana, turnover, beta e incremento líquido, com intervalo temporal pré-especificado. Decisão: Upper bound de ganho líquido<=0 refuta o contraste; intervalo cruzando 0 ou amostra insuficiente => INCONCLUSIVE; lower bound>0 apenas candidata a ablação/validação adicional.

Orçamento: 2 variantes,0 sweep; gate offline primeiro; nenhuma aquisição paga autorizada. Próximo gate: G1 econômico ainda não aberto: datas, amostra e bootstrap dependem do painel admissível, não de lucros observados.

### F04 — O ganho sobrevive à falha de uma perna e ao custo de caixa segregado?

Estado: **READY_FOR_EXPERIMENT (somente sintético)**; capacidade K06. Já executado: B04/B06 verificaram VWAP, rejeição por profundidade e hedge líquido. Partial fills permanecem fase distinta.

Teste mínimo: Estudo analítico fixo: total, parcial, sem fill; latência como cenário, não estimativa. Para replay econômico exigir primeiro L2/trades com sequência e relógios. Contabilizar desmonte adverso e caixa indisponível por venue.

Pré-requisitos: K01/K07; taxas reais ou cenários identificados; capital por local. Livros esparsos não identificam fila.

Métrica: Conservação exata de quantidade/caixa; intervalos de shortfall e caixa imobilizado; reportar fração não identificada. Decisão: Se resultado só positivo no fill otimista, não promover. Sem L2, apenas limites condicionais, nunca fill rate empírico.

Orçamento: 3 estados de fill e 3 cenários de atraso pré-fixados; 0 tuning; 0 mercado. Próximo gate: G1 técnico, depois gate de dados; nenhum envio de ordem.

### F05 — A validação de uma nova família remove informação sobreposta e registra todas as escolhas?

Estado: **READY_FOR_EXPERIMENT**; capacidade K05. Já executado: B05 já demonstrou limite de row-gap em 3 folds; arch/skfolio inspecionados, não instalados.

Teste mínimo: Aplicar oracle de intervalos do B05 ao contrato real de labels antes de observar retorno; comparar amostra antes/depois e auditar lista completa de variantes. Só então avaliar SPA/PBO/DSR compatíveis.

Pré-requisitos: Manifesto de label_start/label_end/available_at e versões de seleção; dados de família nova. Não recalcular julgamento de hipóteses fechadas.

Métrica: Zero sobreposição proibida; todas as tentativas contabilizadas; amostra efetiva e poder reportados. Decisão: Qualquer overlap bloqueia avaliação. Não aumentar tuning para recuperar significância após purga.

Orçamento: Uma auditoria de fronteiras e dois controles; 0 novos modelos ou rede. Próximo gate: G1 de desenho científico; G2 depende de perdas comparáveis e hipótese estacionária justificada.

F01/F05 são habilitadores prontos, F02 está tecnicamente bloqueado, F03 é uma hipótese econômica com gate de dados, F04 permite apenas cenário sintético. A ordem não é autorização para cinco estratégias paralelas. Nenhum destes protocolos antecipa as janelas prospectivas já congeladas.

## Reprodução

Com o checkout/ambiente preservados, os runners em reproduction/ documentam exatamente os comandos e fixtures. `full_suite.py` e `extended_benchmarks.py` importam o projeto existente; não são distribuição autônoma do sistema. Reexecutar escreve novos resultados no diretório resolvido pelo runner, portanto copie para novo diretório de auditoria antes de uma repetição. Não execute compare_aave_second_source.py novamente: a tentativa foi consumida e o próprio script protege a evidência parcial.

Evidências: EXTENDED_PROTOCOL.json, extended_results.json, full_suite.xml, full_suite.log, full_suite_receipt.json, aave_second_source_result.json, ci_jobs.json e MANIFEST.json. Recibos volumosos e PDFs permanecem no diretório de pesquisa, referenciados por hash; não são redistribuídos no pacote final.
