# Cripto Predictor — fase 2: validação experimental

**A fase reduziu incertezas de engenharia e inferência, mas não liberou uma nova hipótese econômica para validação prospectiva.** Os testes encontraram falhas reais no adapter experimental inicial e mostraram por que dependência, seleção e execução parcial precisam entrar na decisão.

Não houve novo discovery, repetição da auditoria/suíte anterior, nova chamada de mercado, ordem, conta, instalação ou alteração de protocolo congelado. O protocolo principal foi registrado antes do primeiro resultado. A revisão adversarial teve protocolo adicional e preservou os resultados que falharam.

## Resultado por experimento

| Experimento | Evidência produzida | Decisão |
| --- | --- | --- |
| F01 — identidade | 4 pares distintos; revisão tardia/FX verificados; v1 falhou em 6/6 controles adversariais, v2 rejeita 6/6 e mantém os controles originais | Adapter experimental corrigido e candidato a G2 técnico; não integrado |
| F02 — Aave | Hashes e bloqueio anterior confirmados; nenhum recibo novo; 0 chamadas | BLOCKED_DATA; infraestrutura não virou rejeição científica |
| F03 — universo PIT | 4/4 universos sintéticos corretos; filtro de sobreviventes atuais errado em 3/4; revisão semântica do painel antigo | Sem prova PIT completa para novo ranking; não calculamos IC/PnL |
| F04 — execução/capital | 9/9 cenários reconciliados; 2 violações recusadas; PnL−5,195 a+0,599 USD | Contabilidade demonstrada; robustez econômica não |
| F05 — incerteza/seleção | 400 séries AR1 e 256 randomizações exatas; bloqueio de labels tardios | IID e bloco 8 insuficientes no controle; maxT passa sob nulidade especificada |

## O que mudou na avaliação

**Identidade não é apenas adicionar campos.** A primeira versão separava quote/chain/venue/payoff, mas aceitava unidades incoerentes, liquidação incompatível, hash inválido, valores monetários não finitos e revisões conflitantes. Seis controles novos falsificaram sua suficiência. A correção v2 ocorreu somente no adapter de pesquisa; falhas, código antigo e hashes foram mantidos. Opções e contratos fora do escopo são recusados, em vez de receber uma identidade incompleta por aproximação.

**O gate PIT é semântico.** A primeira leitura por nomes de campos era excessivamente estrita; corrigimos essa interpretação. open_ms e finalized_at têm informação útil, mas fechamento do candle e aquisição posterior não comprovam primeira publicação histórica. O painel contém 661 pares e 727447 linhas; seus metadados registram 542 dias ausentes somados. BTC/ETH/FTT estão nas amostras, USDC não; isso descreve esse painel, não toda a cobertura possível. O registro de 13 eventos é explicitamente parcial e pós-hoc. Nenhum resultado antigo foi reclassificado, e a ausência de evidência não foi convertida em 0% de dados válidos.

**O caixa da outra venue não está automaticamente disponível.** O ledger mantém 110 USD no spot e 50 USD no futuro. Recusa margem na venue futura com caixa 0 mesmo havendo dinheiro no spot. Uma perna incompleta deixa exposição residual e pode consumir todo o ganho aparente. Custos, atrasos e preços de desmonte são cenários impostos, não estimativas de mercado.

| Fill futuro | Atraso(s) | Desmonte residual | PnL líquidoUSD | Conciliação |
| --- | --- | --- | --- | --- |
| 0 | 0 | 100 | -0.200 | PASS |
| 0 | 1 | 99 | -1.199 | PASS |
| 0 | 10 | 95 | -5.195 | PASS |
| 0.5 | 0 | 100 | 0.1995 | PASS |
| 0.5 | 1 | 99 | -0.3000 | PASS |
| 0.5 | 10 | 95 | -2.2980 | PASS |
| 1 | 0 | 100 | 0.599 | PASS |
| 1 | 1 | 99 | 0.599 | PASS |
| 1 | 10 | 95 | 0.599 | PASS |

Quatro dos nove cenários são positivos; isso não é uma chance estimada de lucro. O melhor resultado,0,599 USD sobre 160 USD de capital total, é também o teto de custos adicionais que esse exemplo suporta antes de perder o ganho. Funding e juros foram zero por hipótese; margem intraperíodo, default e impacto não foram simulados. Não é evidência de carry executável.

## Incerteza e multiplicidade: resultado controlado

O processo sintético AR(1) usa rho 0,6 e 160 pontos por série. Pela covariância conhecida, isso equivale a aproximadamente 40,47 observações independentes para estimar a média. O oracle existe porque geramos o processo; não está disponível por decreto em dados reais.

| Intervalo nominal 95% | Cobertura em 400 séries | Erro MonteCarlo(1 SE) | Largura média | Critério>=90% |
| --- | --- | --- | --- | --- |
| iid_normal | 248/400 (62.00%) | 2.43 pontos percentuais | 0.3042 | REJECT neste DGP |
| known_covariance | 374/400 (93.50%) | 1.23 pontos percentuais | 0.6162 | PASS |
| circular_block8 | 345/400 (86.25%) | 1.72 pontos percentuais | 0.5017 | REJECT neste DGP |

O intervalo IID cobriu apenas 62% e o bootstrap circular com bloco 8 cobriu 86,25%. Ambos falharam o critério registrado; não ajustamos o bloco depois para tornar o resultado favorável. O intervalo de covariância conhecida cobriu 93,5%, dentro da faixa do controle.

Ao selecionar a maior média entre quatro candidatos, o teste individual rejeitou indevidamente 41/256 padrões de sinais (16,0156%). A correção maxT rejeitou 12/256 (4,6875%), abaixo do limite 5% no desenho exato. Isso vale para a nulidade global e a simetria de sinais por bloco definidas; não prova validade sob dependência arbitrária, seleção não registrada ou nulidades parciais.

Também foram eliminados labels cujo término ou recepção ocorre no corte ou depois dele. Remover apenas labels longos não basta quando a informação chega atrasada. Não aplicamos nenhum desses resultados a uma trial encerrada nem calculamos significância econômica com uma matriz incompleta de tentativas.

## Respostas às sete perguntas finais

| Pergunta | Resposta |
| --- | --- |
| 1. Incertezas efetivamente eliminadas | Nos casos testados: distinção de quatro identidades, bloqueio de revisões/FX não disponíveis, seis falhas do adapter experimental, conservação de caixa em nove cenários e efeitos de dependência/seleção sob nulidade conhecida. Não eliminamos incerteza sobre verdade dos providers ou lucro. |
| 2. Hipóteses enfraquecidas/rejeitadas | Rejeitada suficiência da v1 de identidade; rejeitados IID e bootstrap 8 para cobertura mínima 90% no DGP fixado; rejeitada significância individual do candidato escolhido como controle familiar; enfraquecida robustez de spread positivo com fill ideal. Ranking residual e Aave não foram refutados economicamente. |
| 3. Valor incremental demonstrado | F01 passa a recusar inconsistências antes silenciosas; F03 impede transformar catálogo parcial/acesso tardio em universo PIT; F04 torna visíveis exposição residual e caixa indisponível por venue; F05 quantifica erro inferencial em controles verificáveis. |
| 4. Resultados inconclusivos | Corroboração Aave/implementation histórica; PIT do universo completo e ranking residual; probabilidade/custo real de fills; risco de margem intraperíodo; método de incerteza adequado à nova família em mercado. |
| 5. Hipóteses econômicas prontas para experimento completo | Nenhuma recebeu promoção econômica G2 nesta fase. Aave continua candidata condicional; ranking espera gate PIT/hedge; carry espera dados de execução e protocolo preservado. Há justificativa para G2 técnico de F01 e F04, o que não equivale a um backtest econômico completo. |
| 6. Próximo experimento de maior valor informacional | F01 com dados reais já preservados: mapear spot/perp e versões de um dado, incluindo unidades/settlement e recibos. Sucesso: round-trip sem perda, zero inferência monetária implícita, rejeição dos campos ausentes e das versões futuras. Isso decide se o contrato habilita F03/F04 sem nova coleta ampla. |
| 7. Evidência suficiente para validação prospectiva? | Não para promover qualquer nova hipótese econômica nesta fase. Os controles justificam aprofundamento técnico. Pilotos prospectivos previamente congelados mantêm suas próprias condições/janelas, sem ativação ou alteração aqui. Nenhuma evidência E6-P nova. |

## Próxima decisão concreta

Priorizar **F01 em recibos reais preservados**, com teste de round-trip e falsificação de metadata, antes de novo ranking ou replay econômico. O teste deve falhar quando a evidência não representa instrumento/unidade/versão — não inventar a informação faltante. F02 só volta à execução após mudança comprovada de acesso. Para F05, não reutilizar o mesmo exercício até achar um bloco que passe.

Os estudos históricos favoráveis mantêm seu alcance original. A fase 2 não acrescentou lucro observado, corroboração de segunda fonte ou evidência prospectiva. A conclusão é avançar em validação técnica específica, mantendo bloqueados os saltos econômicos que os dados ainda não sustentam.

## Rastreabilidade

- [Fichas completas](EXPERIMENTS.md): os 15 campos solicitados para F01–F05.
- [Registro estruturado](REGISTRY.json): resultados, estados e respostas finais.
- [Protocolo principal](PROTOCOL.json) e [protocolo adversarial](ADVERSARIAL_PROTOCOL.json).
- [Resultados iniciais](RESULTS.json), [F01 v1 reprovada](F01_ADVERSARIAL_V1.json), [F01 v2](F01_ADVERSARIAL_V2.json) e [gate semântico F03](F03_SEMANTIC_GATE.json).
- [Preservação](PRESERVATION.json) e [manifesto](MANIFEST.json).

Nenhum revisor externo participou. Controles analíticos usam métodos distintos, mas foram implementados pelo mesmo agente. Nenhuma independência empírica inexistente é atribuída a essa concordância.
