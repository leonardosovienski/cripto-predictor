# Cripto Predictor — capability mining e implementação

Rodada 20260911T0525, continuidade da iniciativa 20260911T0233. O resultado é código aplicado: cinco capacidades de pesquisa integradas, 24 testes específicos aprovados, cinco famílias de controles diferenciais/oracles, nenhuma dependência obrigatória nova. A regressão completa terminou com 1528 aprovados e 1 ignorado(s). A comparação reutilizou o survey de 53 referências e aprofundou oito implementações delimitadas.

## WHAT THEY HAVE THAT WE DO NOT

Alphalens oferece workflow de painel e análise de fatores mais abrangente; Freqtrade tem ecossistema de filtros encadeados; skfolio oferece validação combinatória e estimadores de carteira; MLflow tem tracking multi-run/artefatos muito mais amplo; Qlib separa processadores infer/learn; Lean gerencia seleção/subscriptions; PyPortfolioOpt oferece solver de pesos. Hummingbot apresenta estado de ordens e conectores abrangentes, mas nosso lifecycle parcial já existia. “Superior” aqui significa cobertura da capacidade indicada, não rentabilidade ou qualidade global comprovada. Código, testes e licenças fixados constam no [landscape](COMPETITIVE_LANDSCAPE.md).

## WHAT WE TOOK FROM THE ECOSYSTEM

Absorvemos composição de filtros, diagnóstico transversal, desenho de splits financeiros, eventos parciais idempotentes e organização de experimentos. Implementamos APIs pequenas usando Core Spearman, NumPy e atomic I/O existentes. A CLI agora conecta universo, fatores, splits, cenário de caixa e RunStore. Nenhum framework externo foi incorporado por cópia de fonte. Fontes diretas: [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade/blob/243ddaef420f64ae3978ddacd6ffff706e8fb0d7/freqtrade/plugins/pairlist/VolumePairList.py), [stefan-jansen/alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded/blob/f0a07c22d554e4b4036983cc80320b432714fe7e/src/alphalens/performance.py), [skfolio/skfolio](https://github.com/skfolio/skfolio/blob/085485b0f35576c1b36b4c4253cb7b944fee0c6f/src/skfolio/model_selection/_combinatorial.py), [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot/blob/2bfaccc48dd49e71a5b6d9b3011808e127dd00cd/hummingbot/core/data_type/in_flight_order.py), [mlflow/mlflow](https://github.com/mlflow/mlflow/blob/3b3760a077bc85c757eed4886bba47d970793875/mlflow/store/tracking/file_store.py).

## WHAT WE SHOULD NOT COPY

Não copiar código GPL para o pacote proprietário; não substituir o engine inteiro por conveniência; não instalar servidor de tracking sem necessidade; não transportar equivalência nominal USD/BUSD/USDT para caixa; não interpretar fill imposto ou backtest favorável como observação prospectiva. A rejeição é da integração/premissa especificada, não do mérito integral dos projetos.

## WHAT WE SHOULD KEEP NATIVE

Preservar métricas Core verificadas, atomic I/O/path guards, registro científico congelado, contratos de sinais/TradeIntent, ciclo de ordens/reconciliação, risco de carteira e livro local/sequenciamento. São sete grupos cuja integração existente torna substituição sem benefício demonstrado. Isso não prova que sejam universalmente superiores. O pacote novo utiliza os dois primeiros diretamente e mantém os demais intactos.

## LEAPFROG OPPORTUNITIES

A combinação plausível é diagnóstico de fatores + disponibilidade explícita de labels + contratos monetários + artefatos reproduzíveis. O demo já demonstra essa composição técnica. Uma vantagem competitiva econômica ainda precisa ser medida. O próximo experimento de maior valor informacional é otimização restrita de carteira/caixa contra equal-weight e solução analítica de dois ativos: cobre G06, usa o risco nativo, pode começar com dados sintéticos e revela se o solver adiciona uma capacidade necessária antes de qualquer backtest.

## Respostas às 25 perguntas

1. **Sistemas mais úteis:** Alphalens, Freqtrade, skfolio, MLflow e Hummingbot no escopo implementado; Qlib, PyPortfolioOpt e Lean em necessidades restantes.
2. **Onde são superiores:** cobertura de painel, catálogo de filtros, CPCV/otimização, tracking, conectores, processadores e subscriptions respectivamente; não inferir superioridade de PnL.
3. **Capacidades recorrentes faltantes:** composição reutilizável, runs comparáveis, validação parametrizável e integração das análises; cinco incrementos foram entregues.
4. **Gaps reais:** painel por grupo/data, versões/filtros explícitos, intervalos disponíveis, reserva monetária de cenário e RunStore genérico. Solver/fila calibrada permanecem.
5. **Cosméticos:** nome run/trial, representação JSON/DataFrame e grafia de estados. Partial fill, risco básico e L2 já eram nativos.
6. **Reuso direto:** Spearman do Core, atomic write, JSON estrito/path guards e NumPy existente; nenhum novo pacote obrigatório externo.
7. **Adapters:** despacho da CLI e composição das APIs locais implementados; nenhum adapter de engine externo instalado. G06 segue candidato opcional.
8. **Conceitos reimplementados:** filtros, estatísticas de painel, split por disponibilidade, contabilidade de cenário e organização de runs.
9. **Validação independente:** SciPy para IC (mesma linhagem estatística de Alphalens, não réplica independente do framework), Fraction para caixa, oracle de intervalos, solução fechada OLS e lifecycle nativo. Frameworks lidos permanecem referências C1/C2.
10. **Não copiamos:** as seis decisões de integração/premissas do plano; não alegamos abandono de projeto sem evidência.
11. **Preservar:** sete grupos nativos enumerados acima e todos os protocolos congelados.
12. **Código novo:** sete módulos Python em `GarimpoInvestimentos/research`, README de uso e `tests/test_research_capabilities.py`.
13. **Código existente melhorado:** despacho `research` em `GarimpoInvestimentos/cli.py`; README principal aponta para toolkit. Pipeline científico não foi reescrito.
14. **Dependências:** zero obrigatórias adicionadas; sem mudanças em pyproject/uv.lock. NumPy já pertence ao extra science.
15. **Differential tests:** IC versus SciPy em oito combinações; residual versus solução fechada; splitter versus oracle de intervalos; saldos versus Fraction; transições comuns versus execução nativa. Roundtrip/hash é verificação adicional de persistência, não validação econômica.
16. **Passaram:** as cinco capacidades, demo composto e reexecução determinística; 24 testes específicos finais.
17. **Falharam:** serialização inicial de índices e primeira chamada do teste nativo; corrigidas, recibos preservados. Nenhuma hipótese econômica foi rejeitada por isso.
18. **Ganhos concretos:** novas APIs reutilizáveis, workflow único, exclusões explicadas, capital reservado e detecção de alteração em artefatos. Medidas locais e limites em [IMPLEMENTED_CAPABILITIES](IMPLEMENTED_CAPABILITIES.md).
19. **Possibilidades econômicas:** estudar fatores residuais, turnover, restrições de capital e carteiras. Possibilidade de pesquisa não é oportunidade validada.
20. **Bloqueadas por dados:** universo PIT, derivativos históricos completos, calibração de execução e corroboração Aave onde indisponível. A contabilidade spot não fecha F04 histórico.
21. **Pesquisar agora:** comparar painéis/grupos/quantis, regras de universo, janelas de labels e cenários de capital sob o mesmo registro local. Antes havia peças e scripts; faltava esta API composta.
22. **Rejeitar agora:** entradas dimensionais incompatíveis, versões futuras, labels ainda indisponíveis, uso duplicado de saldo e runs adulterados; isso rejeita inputs/cenários inválidos, não novas hipóteses de alpha.
23. **Mais rápido:** menos montagem manual e execução medida; 20 mil linhas de painel em ~0,197 s. Não houve estudo cronometrado antes/depois da produtividade nem speedup externo demonstrado.
24. **Mais mercados/estratégias:** maior flexibilidade analítica e cenários spot explícitos. Não foram adicionados conectores, suporte real a derivativos/opções ou mercados certificados.
25. **Backlog ordenado:** G06, G07, G10, G08, G09, G11, G12, G13, G14, G15, G17, G16, G18, G20, G19; contratos e custo na [matriz](CAPABILITY_TRANSFER_MATRIX.md). Não requer novo discovery amplo.

## Estado científico herdado e sete perguntas da validação

Incertezas eliminadas: viabilidade técnica das cinco APIs, igualdade nos controles especificados e preservação dos artefatos. Hipóteses enfraquecidas/rejeitadas: nenhuma hipótese econômica nova; duas falhas de implementação/teste corrigidas. Valor incremental demonstrado: composição e contratos testáveis das cinco capacidades. Inconclusivos: rentabilidade, execução empírica, qualidade histórica do universo e calibração estatística fora dos testes sintéticos. Hipóteses que justificam experimento econômico completo: nenhuma foi promovida por esta rodada; fatores residuais e capital fragmentado justificam preparação técnica, condicionada aos dados. Próximo experimento informacional: solver restrito com controle analítico. Evidência suficiente para validação prospectiva: **não**.

F01–F05 conservam os estados científicos da baseline; H1/H2/H3/H5 CLOSED_NO_GO, H4/H6/H9 insuficientes, H7/H8 inativos, funding_oi_hmm_v3 e pilotos congelados. Nenhum capital, conta ou ordem foi ativado. Falha de infraestrutura não foi convertida em rejeição científica e nenhuma hipótese encerrada foi reaberta.

## Entrega

Código aplicado localmente, sem commit/push. Seis documentos, registry, recibos de testes, benchmark, preservação, entrada demo, arquivos novos, patch dos dois arquivos existentes e wheel estão no pacote de entrega. O registry liga as decisões aos arquivos e fontes. O README do toolkit contém comandos e contrato JSON para uso imediato.
