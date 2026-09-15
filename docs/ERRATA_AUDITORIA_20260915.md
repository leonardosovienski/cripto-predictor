# Errata documental da auditoria de evidências — 15/09/2026

Baseline: `main`, commit `4eb96e141389b8390536716af3c4a0cb46edab23`.
Correção documental autorizada pelo responsável nesta rodada. Esta nota não altera
protocolos, resultados, critérios, estados científicos ou permissões de capital.
Os registros históricos citados conservam seus bytes. Esta nota deve acompanhá-los
quando suas afirmações forem reutilizadas.

## 1. H6: tamanho observado e poder simulado são diferentes

O [snapshot H6](../GarimpoInvestimentos/h6_status.json) registra `n=84`,
`rho=-0.05670370717295617`, intervalo `[-0.23117222203573654, 0.12942880780115093]`.
Seu objeto `poder` declara explicitamente `n_referencia=60`: 0,233 para rho=0,2
e 0,473 para rho=0,3. Portanto, as passagens de
[HYPOTHESES](HYPOTHESES.md) e [EVIDENCE_REGISTRY](EVIDENCE_REGISTRY.md)
que atribuem 23%/47% à amostra de 84 não são sustentadas por esse snapshot.
Não foi calculado poder para n=84 nesta auditoria. Permanecem o estado nativo
`CLOSED_INSUFFICIENT_SAMPLE` e a conclusão de intervalo cruzando zero;
não há refutação nem equivalência demonstrada.

## 2. BR2: ausência de entradas e custo zero no resultado registrado

A linha BR2 de [CURRENT_RESEARCH_STATE](CURRENT_RESEARCH_STATE_20260908.md)
contém a expressão “Custo fixo modelado sem operações”. Os
[resultados v2](evidence/basis_research_20260908/results-v2/results.json)
e a [comparação posterior](evidence/profit_comparison_20260908/DECISAO.md)
registram zero entradas, zero lucro e zero custo residual nos cenários BR2.
A despesa anual só começa após a primeira entrada. A despesa com estratégia
posteriormente em caixa aplica-se a BR1, que abriu posições, e não a BR2.
Zero entradas não comprova rentabilidade de uma estratégia operada.

## 3. Segunda fonte Aave: a tentativa posterior não concluiu a comparação

O estado de espera de quota em [CONFERENCIA_CHAT](CONFERENCIA_CHAT_20260910.md)
é histórico. O [resultado de 11/09](open_source_research/20260911T0233/aave_second_source_result.json)
registra `INCOMPLETE`, uma chamada, zero bytes, `ConnectTimeout`, conclusão às
03:01:56.941930 UTC. Não houve corroboração dos 38 pontos por essa tentativa.
Nenhuma chamada nova foi realizada nesta auditoria. Operador diferente tampouco
comprova infraestrutura independente.

## 4. Atestados de harness têm validade datada

Os atestados preservados
[V3](../GarimpoInvestimentos/trials.harness_attestation.json) e
[Fase1](../GarimpoInvestimentos/trials.phase1_harness_attestation.json)
expiram em 14/09/2026. São evidência histórica dos controles e não atestados
vigentes em 15/09. Não foram renovados nem executados nesta rodada.
Controles sintéticos aprovados não certificam eficácia econômica.

## 5. Contagens históricas não são o universo atual de tentativas

O [índice do congelamento](../CR_FREEZE_INDEX.md) ainda descreve o charter como
H1–H7 e o terceiro caso como sete hipóteses testadas. O
[caso preservado](case_studies/CASE-CR-003-multiplas-hipoteses-sem-falso-vencedor.md)
tem tabela H1–H9, mas conserva “sete tentativas” na lição final. No corte desta
auditoria, o charter contém nove hipóteses registradas; H7/H8 não estão ativadas.
O ledger contém 26 entradas: ancestral, nove trials vinculadas a H1–H9 e
16 variantes da grade. Há 23 Sharpes finitos. Essas contagens são de objetos
diferentes; nenhuma estabelece o número total de avaliações históricas ou de
amostras independentes. O sweep Kelly documentado fora do ledger impede tomar
26 como denominador universal. Não se revalida o DSR histórico por contagem.

## 6. Limites e verificações desta correção

- Leitura documental/JSON, metadados e hashes; nenhum cálculo científico novo.
- Manifestos Aave: `history` 396, `funded_costs` 3, `conversion_quote` 7,
  `execution_receipts` 113 e `execution_attempt01` 9: 528 arquivos comparados,
  nenhuma divergência. Hashes confirmam identidade dos bytes, não validade causal.
- H4 continua distinta de H5: cinco previsões declaradas, encerramento por decisão
  do responsável/risco de cota, sem veredicto estatístico. Não se inferem cinco
  observações independentes ou ausência de observações.
- Inputs originais H5 não recuperados conforme
  [rotas de recuperação](evidence/remaining_dependencies_20260910/historical_recovery_routes.json).
  Simulações posteriores não substituem previsões originais.
- Estados, dados, protocolos e evidências congeladas não foram corrigidos
  retroativamente. Não houve teste, backtest, inferência, coleta ou implantação.

Esta errata resolve as inconsistências documentais identificadas acima. Não
certifica completude histórica do acervo, instalação principal ou lucro futuro.
