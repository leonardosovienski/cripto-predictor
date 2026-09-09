# Rodada econômica de 09/09/2026

A redução de giro nas renovações AR2 BTC **não resolve as perdas nos cenários adversos registrados**. O acesso histórico necessário para medir juros e resgate no Aave ficou bloqueado. A rodada terminou com essas duas decisões delimitadas; não demonstrou lucro líquido pessoal nem aprovou capital.

Este é o registro canônico de `ECONOMIC-ROUND-20260909-R1`. O [protocolo](protocol.json) foi registrado no commit `a88579c`, antes das novas observações de mercado. O [dossiê da alternativa](../../reopen_dossiers/ar2_renewal_turnover_20260909.json), commit `98d9f5b`, precedeu sua medição e declarou os resultados publicados já vistos durante o reconhecimento. Base: `48fd271b06486866289f3e93cdc80504259b196f`; branch `research/economic-round-20260909`, área Windows `C:\Cripto\pesquisa-20260909`. A base incorpora as entregas #105/#106 posteriores ao snapshot restaurado `522de73`; o checkout restaurado e os observadores foram preservados.

| Hipótese | Estado da rodada | Condição para retomar |
|---|---|---|
| H1: juros-base de USDC nativo no Aave V3 Arbitrum, sem alavancagem | Bloqueada por acesso histórico; resultado econômico inconclusivo | Fonte pública de estado histórico capaz de fornecer índices, identidade da reserva e liquidez de resgate nos blocos da janela fixa |
| H2: corrigir a perda adversa da AR2 BTC apenas evitando fechar/reabrir renovações | Rejeitada nesse escopo, período e modelo de custos | Evidência material de custos, execução ou receita que altere o limite calculado; novo protocolo antes de outra avaliação |

## Escolha e orçamento efetivamente usado

O juro pago por tomadores foi priorizado por poder reduzir as várias pernas de execução e o capital ocioso que consumiram receita no carry. A alternativa isola uma fricção específica usando dados preservados. Carry contínuo e futuros com vencimento já tinham resultados conhecidos; famílias direcionais congeladas não receberam um novo motivo material de reabertura. Market making exigiria evidência de fila, execução e seleção adversa indisponível neste teste. Esses mecanismos estacionados não foram declarados inviáveis.

Foram ativados dois mecanismos, conforme o limite registrado. H1 usou seis chamadas RPC, incluindo falhas, em dois endpoints públicos, abaixo do teto de 500 chamadas e esgotando as duas fontes permitidas. Não houve varredura de reservas, substituição da janela por APY atual nem aquisição adicional para H2. H2 manteve um ativo e um sinal, comparando dois tratamentos de execução nos três cenários de custo já fixados. As sensibilidades de capital são contas analíticas, não novos backtests. Houve duas execuções numéricas equivalentes: a segunda incorporou somente anotação de tipo e caminho de evidência portátil. Não foi aberta outra rodada para procurar um resultado positivo.

## H1: teste de acesso histórico, sem estimativa de rendimento

A reserva escolhida foi USDC nativo, não USDC.e: underlying `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`, pool `0x794a61358D6845594F94dc1DB02A252b5b4814aD`, aToken `0x724dc807b04555b71ed48a6896b6F41593b8C637`, conforme o [address book oficial](https://github.com/aave-dao/aave-address-book/blob/main/src/AaveV3Arbitrum.sol). A identidade histórica completa em cadeia permaneceu por validar.

Em 09/09/2026, `https://arb1.arbitrum.io/rpc` confirmou chain ID 42161 e o bloco 503409488, de 15:32:13 UTC, com idade observada de aproximadamente 1,9 segundo. A consulta histórica `eth_call` retornou `missing trie node` / estado indisponível. O fallback `https://arbitrum-one-rpc.publicnode.com` falhou na resolução DNS. O bloco antigo usado foi apenas uma sonda de disponibilidade aproximada de 84 dias, não uma observação substituta dos 13 limites semanais registrados. As [seis respostas originais](h1_rpc/report.json) e a [implementação da sonda](h1_probe_implementation.source) estão preservadas e têm hashes no [manifesto](source_manifest.json).

O índice normalizado poderia medir o crescimento do saldo-base, mas não certifica a disponibilidade do saque; a medição precisaria também da liquidez não emprestada e do estado da reserva nos mesmos blocos. Fontes: [contrato Pool](https://aave.com/docs/aave-v3/smart-contracts/pool), [regras de retirada](https://aave.com/help/supplying/withdraw-tokens) e [RPCs da Arbitrum](https://docs.arbitrum.io/for-devs/dev-tools-and-resources/chain-info). Falha desses acessos não demonstra ausência de oportunidade. Nenhum rendimento, APY ou lucro foi atribuído a H1; os cenários de capital/custo e riscos de principal, stablecoin e resgate continuam apenas registrados no protocolo.

## H2: reconstrução e limite de economia

Os 68 arquivos brutos e dez normalizados foram verificados contra o manifesto original. Somente BTC foi simulado, de 01/01/2024 a 07/09/2026, com threshold AR2 original de 0,0135. Os três cenários reproduziram exatamente os totais do motor de referência. Um caminho separado em `Decimal` reconciliou receitas de funding a partir dos eventos assinados, variação da base, custos, caixa e patrimônio final, com diferenças inferiores a `1e-7` USDT em relação aos floats de referência.

A referência de 5.000 USDT é hipotética. Houve **três posições, 84 dias de exposição em 980 dias decorridos e somente uma renovação adjacente**; todas as posições ocorreram em 2024. Na renovação de 22/04/2024, cada perna passou de 0,018 para 0,019 BTC. Fechar/reabrir movimenta 0,037 BTC por perna; ajustar quantidade movimentaria 0,001 BTC. O custo modelado dessa fronteira cai de 6,0060 para 0,1623 USDT no caso base e de 16,8166 para 0,4545 USDT no adverso. As 12 transações de pernas da referência virariam dez nesse contrafactual com delta não nulo; não são preenchimentos observados.

Todos os valores abaixo são USDT acumulados no mesmo período, antes de despesas pessoais desconhecidas. As economias ficam em caixa, sem redimensionar posições.

| Cenário | Referência | Economia por ajustar quantidade | Parcial após somente essa economia | Limite com taxas de renovação zeradas | Limite otimista ampliado |
|---|---:|---:|---:|---:|---:|
| Base | +17,7911 | +5,8437 | +23,6348 | +23,7971 | +23,8515 |
| Adverso | -82,2580 | +16,3621 | -65,8959 | -65,4414 | **-65,3870** |
| Compressão | -117,4194 | +16,3621 | -101,0573 | -100,6028 | **-94,4062** |

O limite ampliado concede mais que a implementação delta: elimina até o custo do delta, dispensa o choque de renovação aplicável e credita funding positivo na fronteira com a maior quantidade adjacente. Funding negativo já devido no histórico é mantido; eventos negativos adicionais na fronteira só podem ser omitidos nesse limite explicitamente otimista e ficam discriminados. Um diagnóstico separado usa funding assinado sobre a menor quantidade contínua. Na única fronteira observada, o crédito positivo máximo é 0,05438 USDT (metade na compressão) e não há funding adicional negativo. Na compressão, a dispensa adicional de choque é 6,16941 USDT. Mesmo essas concessões não tornam os cenários adversos positivos.

A reconciliação adversa original é `33,370259` de funding + `2,712980` de base − `51,217938` de execução − `67,123288` de custo fixo = `−82,257986` USDT. Evitar giro acrescenta `16,362097` USDT. Os 25 USDT/ano de custo fixo pertencem ao cenário original, não são uma despesa efetiva confirmada do dono. **Antes desse custo fixo e dos custos pessoais, o resultado adverso com ajuste de quantidade seria +1,227399 USDT em 980 dias**, compatível com custo fixo de equilíbrio de aproximadamente **0,4571 USDT/ano**. Isso é uma sensibilidade condicional pequena, não rejeição de toda possibilidade de lucro sob qualquer custo. No caso base, o parcial positivo também permanece visível.

Sensibilidade analítica do limite ampliado, escalando as posições proporcionalmente e mantendo o custo fixo original:

| Capital hipotético (USDT) | Adverso (USDT) | Compressão (USDT) |
|---:|---:|---:|
| 1.000 | -66,7760 | -72,5799 |
| 5.000 | -65,3870 | -94,4062 |
| 25.000 | -58,4419 | -203,5380 |

Essa escala não respeita necessariamente a grade mínima de cada novo tamanho, não incorpora impacto de mercado e não demonstra capacidade. Não se somam cenários nem se equiparam USDT e USDC.

## Risco e validade da conclusão

Os indicadores de risco pertencem à trajetória original, não a um novo motor completo de execução delta. O drawdown modelado foi aproximadamente 0,121%, 1,710% e 2,348% nos cenários base, adverso e compressão. O teste original de salto de 30% não apresentou quebra modelada de margem; seus menores excedentes foram cerca de 3.131, 3.124 e 3.115 USDT. Isso depende das simplificações de margem, hedge e preços diários, não certifica liquidação, disponibilidade de saldo ou saída reais.

Os cinco melhores períodos semanais respondem por 66,7% da soma das semanas positivas no caso base; removê-los deixa −1,6923 USDT na referência. O bootstrap circular original de blocos de quatro semanas, em 128 semanas de caixa, forneceu intervalos para a **média semanal** de aproximadamente `[-0,0252; +0,3560]`, `[-0,8145; -0,3899]` e `[-1,2158; -0,5496]` USDT. Eles não são intervalos do lucro acumulado, do tratamento delta, nem probabilidades de lucro futuro. Poucas posições e ganhos concentrados limitam a evidência.

Toda essa história já influenciou a pesquisa; a reexecução não produz amostra independente. A hipótese não foi retreinada e não houve seleção de threshold nesta rodada. Preços diários são proxies, a grade e as condições de execução históricas não foram certificadas, taxas pessoais/tributação/conversão permanecem desconhecidas e não há validação operacional ou autorização de capital. Perdas permanentes, indisponibilidade de saque e liquidação não são descartadas por drawdown pequeno. A rejeição se limita a **renovação como correção suficiente da perda adversa registrada**, sem condenar todos os regimes, custos ou formas de AR2.

## Implementação, validação e reprodução

`GarimpoInvestimentos/renewal_research.py` implementa as contas separadas com validação de instrumento, grade, ordem temporal, eventos de funding e reconciliação. `scripts/diagnose_ar2_renewals.py` verifica os dados preservados, reproduz a referência e gera novos arquivos sem sobrescrever uma saída existente. Os motores, thresholds, protocolos científicos e resultados antigos não foram alterados. Há 25 novos testes materiais, incluindo quantidades diferentes, custos iniciais/finais, funding negativo, eventos duplicados e recibos fabricados. Os resultados financeiros completos estão em [market_results.json](market_results.json); hashes em [source_manifest.json](source_manifest.json); verificações de engenharia em [validation.json](validation.json).

Ambiente de pesquisa independente: Windows, Python 3.13.14, uv 0.12.1 e dependências de `uv.lock`, com todos os extras. A suíte completa, lint, tipagem, build e contrato do wheel são registrados separadamente do experimento econômico. Container e Python 3.14 exigem os jobs de CI do projeto; aprovação pendente não equivale a aprovação. O CI e o SHA publicado devem ser confirmados no PR, sem deduzir integração a partir deste arquivo.

Na raiz do worktree, usando a `.venv` de pesquisa, a reprodução requer os dados restaurados. Escolha um diretório de saída ainda inexistente:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.diagnose_ar2_renewals --data 'C:\Cripto\restaurado-20260908\sessoes\20260907-pesquisa\work\carry-research-data' --output 'work\h2-reproducao-nova'
```

O comando não baixa novos preços nem usa contas. Dados existentes de mercado possuem sua própria trilha de aquisição e manifesto; o SHA-256 do protocolo de aquisição é `078f130eba63dfdae35fc6cc6a7da65b368731faaa3a5ab14522456a5e440d0f`. `work/h2-renewals-v1` e `work/h2-renewals-v2` guardam as duas execuções locais e suas referências, sem substituir evidência original.

## Decisão e próxima informação

**Qual descoberta mais mudou a decisão?** Existe apenas uma renovação adjacente; sua economia adversa de 16,36 USDT não fecha a perda de 82,26 USDT. Até o limite ampliado continua negativo. Isso elimina a justificativa de construir agora um motor completo de renovação para resolver essa perda.

**Qual hipótese perdeu prioridade?** H2 como correção suficiente da AR2 nos cenários adversos registrados. H1 perdeu prioridade operacional nesta rodada por bloqueio de dados, sem rejeição econômica.

**Qual informação decidiria o próximo passo?** Para H1, uma fonte pública utilizável de estado histórico e liquidez de resgate na janela fixa. Para H2, comprovação de custos/receita materialmente diferentes que alterem o limite, seguida de avaliação temporal ainda não consultada e execução/capacidade compatíveis. Custos efetivos de infraestrutura e pessoais ajudariam a interpretar o pequeno parcial antes dessas despesas. Não há candidata suficientemente sustentada para apresentar condições de lucro líquido executável ou recomendar alocação.

A rodada está encerrada; não foi ativada coleta recorrente, operação real ou trabalho em segundo plano.
