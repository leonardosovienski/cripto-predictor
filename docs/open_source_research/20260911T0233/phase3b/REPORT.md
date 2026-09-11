# CRIPTO-PREDICTOR — Fase 3B

Iniciativa `20260911T0233`. Continuação estrita da fase 3.

**F03 = BLOCKED_CURRENT_EVIDENCE. F04 = BLOCKED_CURRENT_EVIDENCE. Nenhum escopo econômico da Fase 4 foi aberto.**

A fase termina por bloqueadores precisos e saturação do bundle delimitado, não por tentativa de fazer UNKNOWN desaparecer. Há progresso técnico local, mas nenhum contrato econômico completo certificado. A causa dos clocks permanece **CAUSE_UNKNOWN**.

## Escopo, baseline e preservação

Commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Foram preservados e verificados 381 arquivos, incluindo v2, v3, harness v3.1 e resultados anteriores. Nova extensão isolada: `F01-contract-temporal v3B.1`; nenhuma integração de produção. Baseline e protocolo foram registrados antes das baterias em `BASELINE.json` e `PROTOCOL.json`.

Foram examinadas 34 aquisições preservadas na matriz temporal: 26 recibos do diagnóstico (12 pares de livros e dois exchangeInfo), seis recibos BTC de candles/funding já usados na fase 3, um exchangeInfo do capability probe e o README oficial arquivado. Não são 34 novas coletas nem 34 fontes independentes. Artefatos auxiliares incluem o código do coletor, seu freeze, data_semantics e protocolo histórico. Nenhum resultado de estratégia foi recalculado.

O acervo adicional foi limitado a btc-execution-diagnostic-v1, basis-capability-probe e aos arquivos de código/freeze correspondentes. “Não localizado” abaixo significa não localizado nesse bundle e nos inputs enumerados; não significa uma busca exaustiva no disco ou na internet. Zero chamadas externas, backtests, rankings, F02 ou operações de capital.

## Matrizes dos contratos

PROVEN certifica o valor literal ou transformação explicitamente descrita da evidência, não uma hipótese econômica adicional. CURRENT_ONLY significa declaração recebida na coleta preservada, não consulta à documentação de hoje. Conteúdo idêntico em dois momentos não prova vigência ininterrupta entre eles. N/A exige motivo estrutural; nenhuma lacuna foi transformada em N/A para abrir replay.

### BTC_SPOT — BTCUSDT

| Campo | Valor | Status | Evidência | Clock da evidência | Pode valer retroativamente? |
|---|---|---|---|---|---|
| venue | "api.binance.com" | PROVEN | diagnostic.json `sources/0/url` | 1788833243963778600 | Não; CURRENT_ONLY |
| market_type | {"isSpotTradingAllowed": true} | PROVEN | spot_info.bin.gz `symbols/11/isSpotTradingAllowed` | 1788833243963778600 | Não; CURRENT_ONLY |
| base_asset | "BTC" | PROVEN | spot_info.bin.gz `symbols/11/baseAsset` | 1788833243963778600 | Não; CURRENT_ONLY |
| quote_asset | "USDT" | PROVEN | spot_info.bin.gz `symbols/11/quoteAsset` | 1788833243963778600 | Não; CURRENT_ONLY |
| settlement_asset | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| margin_asset | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| quantity_unit | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| price_unit | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| multiplier | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| linear_inverse | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| payoff | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| expiry | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| price_type | — | UNKNOWN | Instrument has multiple observations; type belongs to each receipt, not a single interchangeable instrument price. See OBSERVATION_SEMANTICS.json. | UNKNOWN | Não; NOT_PROVEN |
| funding_semantics | — | N/A | This row studies the spot metadata contract, not a funding event or margin loan. Any financing would require a separate contract. | UNKNOWN | Não; STRUCTURAL_SCOPE |
| contract_version | — | UNKNOWN | Only body content hash preserved; no effective economic specification version/change history. | UNKNOWN | Não; NOT_PROVEN |
| valid_from | — | UNKNOWN | onboardDate, where present, is a claim in later metadata, not publication/knowledge time or proof that all terms were effective since then. | UNKNOWN | Não; NOT_PROVEN |
| valid_until | — | UNKNOWN | No dated change log or end of validity for the full economic terms. | UNKNOWN | Não; NOT_PROVEN |

### BTC_PERPETUAL — BTCUSDT

| Campo | Valor | Status | Evidência | Clock da evidência | Pode valer retroativamente? |
|---|---|---|---|---|---|
| venue | "fapi.binance.com" | PROVEN | diagnostic.json `sources/1/url` | 1788833244585202200 | Não; CURRENT_ONLY |
| market_type | "PERPETUAL" | PROVEN | future_info.bin.gz `symbols/0/contractType` | 1788833244585202200 | Não; CURRENT_ONLY |
| base_asset | "BTC" | PROVEN | future_info.bin.gz `symbols/0/baseAsset` | 1788833244585202200 | Não; CURRENT_ONLY |
| quote_asset | "USDT" | PROVEN | future_info.bin.gz `symbols/0/quoteAsset` | 1788833244585202200 | Não; CURRENT_ONLY |
| settlement_asset | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| margin_asset | "USDT" | PROVEN | future_info.bin.gz `symbols/0/marginAsset` | 1788833244585202200 | Não; CURRENT_ONLY |
| quantity_unit | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| price_unit | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| multiplier | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| linear_inverse | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| payoff | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| expiry | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| price_type | — | UNKNOWN | Instrument has multiple observations; type belongs to each receipt, not a single interchangeable instrument price. See OBSERVATION_SEMANTICS.json. | UNKNOWN | Não; NOT_PROVEN |
| funding_semantics | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| contract_version | — | UNKNOWN | Only body content hash preserved; no effective economic specification version/change history. | UNKNOWN | Não; NOT_PROVEN |
| valid_from | — | UNKNOWN | onboardDate, where present, is a claim in later metadata, not publication/knowledge time or proof that all terms were effective since then. | UNKNOWN | Não; NOT_PROVEN |
| valid_until | — | UNKNOWN | No dated change log or end of validity for the full economic terms. | UNKNOWN | Não; NOT_PROVEN |

### BTC_DATED — BTCUSDT_261225

| Campo | Valor | Status | Evidência | Clock da evidência | Pode valer retroativamente? |
|---|---|---|---|---|---|
| venue | "fapi.binance.com" | PROVEN | diagnostic.json `sources/1/url` | 1788833244585202200 | Não; CURRENT_ONLY |
| market_type | "NEXT_QUARTER" | PROVEN | future_info.bin.gz `symbols/801/contractType` | 1788833244585202200 | Não; CURRENT_ONLY |
| base_asset | "BTC" | PROVEN | future_info.bin.gz `symbols/801/baseAsset` | 1788833244585202200 | Não; CURRENT_ONLY |
| quote_asset | "USDT" | PROVEN | future_info.bin.gz `symbols/801/quoteAsset` | 1788833244585202200 | Não; CURRENT_ONLY |
| settlement_asset | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| margin_asset | "USDT" | PROVEN | future_info.bin.gz `symbols/801/marginAsset` | 1788833244585202200 | Não; CURRENT_ONLY |
| quantity_unit | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| price_unit | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| multiplier | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| linear_inverse | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| payoff | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| expiry | {"deliveryDate_raw": 1798185600000, "utc_under_preserved_ms_decoder": "2026-12-25T08:00:00+00:00"} | PROVEN | future_info.bin.gz `symbols/801/deliveryDate` | 1788833244585202200 | Não; CURRENT_ONLY |
| price_type | — | UNKNOWN | Instrument has multiple observations; type belongs to each receipt, not a single interchangeable instrument price. See OBSERVATION_SEMANTICS.json. | UNKNOWN | Não; NOT_PROVEN |
| funding_semantics | — | UNKNOWN | No explicit admissible economic specification in bounded saved bundle | UNKNOWN | Não; NOT_PROVEN |
| contract_version | — | UNKNOWN | Only body content hash preserved; no effective economic specification version/change history. | UNKNOWN | Não; NOT_PROVEN |
| valid_from | — | UNKNOWN | onboardDate, where present, is a claim in later metadata, not publication/knowledge time or proof that all terms were effective since then. | UNKNOWN | Não; NOT_PROVEN |
| valid_until | — | UNKNOWN | No dated change log or end of validity for the full economic terms. | UNKNOWN | Não; NOT_PROVEN |

Os clocks numéricos dessas tabelas são ns do relógio local, com hashes e ponteiros completos em `INSTRUMENT_CONTRACTS.json`. Para perpetual, deliveryDate=4133404800000 permanece um campo bruto não interpretado como vencimento real. Para o contrato datado, a data foi lida do campo, não do sufixo do ticker. `onboardDate` não comprova o instante em que um participante conheceu o listing nem a vigência de todos os termos desde então.

## Fórmulas e dimensões

Nenhuma fórmula de notional, PnL, margin ou settlement foi atribuída aos três instrumentos reais: faltam termos suficientes para derivá-la da especificação admissível. Não se aplicou fórmula genérica de perpetual nem multiplier=1 por convenção.

O controle dimensional positivo verifica apenas a identidade algébrica com unidades **declaradas no teste**:

```
[BTC] × [USDT/BTC] = [USDT]
```

Os controles `[BTC] × [USD/BTC] → [USDT]` e `[contract] × [USDT/BTC] → [USDT]` falham. Isso comprova o verificador de dimensões, não atribui unidades aos preços reais. O README oficial arquivado descreve colunas distintas de quote/base volume para USD-M/COIN-M e avisa sobre atualizações dos arquivos; não fornece sozinho uma especificação completa de payoff, settlement ou vigência histórica para estes instrumentos.

## Semântica das observações e funding

Trade candle close, mark candle close e displayed ask são mantidos separados por recibo. Nenhum é fill garantido. Não existe index-price neste subset. A distinção literal dos endpoints/colunas permite recusar trade como mark e mark como executable quote, sem provar liquidez, fila, slippage ou hedge simultâneo.

Funding: `FUNDING_REPLAY_NOT_PROVEN`. O primeiro registro contém fundingRate=0.00004595, fundingTime=1787788800000 e rateType=Regular. A observação está comprovadamente no corpo recebido; predicted versus uma taxa economicamente liquidada não é certificado apenas por esse rótulo. O conjunto contém 33 registros e diferenças de tempo entre 28799974 e 28800013 unidades brutas; sob leitura em ms são aproximadamente oito horas, com variação. Esse fato não estabelece uma regra contratual fixa.

RATE é observável; POSITION BASIS, PAYMENT DIRECTION, PAYMENT CURRENCY e ELIGIBILITY TIME permanecem NOT_PROVEN. Original publication, posição efetivamente elegível e ledger de pagamentos não foram capturados nesses recibos. `markPrice` não vira base de pagamento sem fórmula comprovada. Nenhum cash flow foi calculado.

## Investigação temporal

O código preservado do coletor coincide exatamente com o hash congelado `5f316589e5bbbbebea18e4b4b67023f09d6593601b3d9d956176705b10889cd4`. Ele captura `time.time_ns()` antes de `client.send` e logo depois de seu retorno; lê e persiste o corpo em seguida. Isso identifica a origem e a unidade dos clocks locais. Não mede tempo de persistência, normalização, clock monotônico ou offset remoto.

No future_00:

```
LOCAL_REQUEST_TIME = 1788833244617086500 ns
LOCAL_RECEIPT_TIME = 1788833244947699200 ns
T bruto            = 1788833245358
E bruto            = 1788833245362

Se T estiver em milissegundos de epoch:
T × 10^6 − LOCAL_RECEIPT_TIME = 410300800 ns = 410,3008 ms
```

A aritmética é exata, sem float. A unidade local é comprovada pelo coletor. A leitura de T em ms é compatível com o epoch e com o decoder preservado, mas o bundle não contém a especificação histórica do endpoint depth que prove a unidade e o significado de T/E. Portanto, a diferença não é uma prova isolada de clock skew ou erro da fonte.

Nos 12 livros futures, todas as diferenças condicionais são positivas: mínimo 408.6478 ms, máximo 446.958 ms, mediana 438.8075 ms. T, E, request, receipt e lastUpdateId são estritamente crescentes na amostra. Todos os recebimentos são posteriores às requisições locais. Os inteiros locais têm granularidade observada de 100 ns; granularidade de representação não é precisão, exatidão ou sincronização. E−T varia de 2 a 5 ticks brutos.

As duas aquisições de future exchangeInfo têm o mesmo corpo, inclusive serverTime, apesar de horários de recebimento diferentes. Isso impede tomar o serverTime do corpo como horário fresco de resposta. Não prova qual mecanismo de cache/snapshot, se algum, ocorreu. Os 26 corpos do diagnóstico e os dois corpos docs/info do probe tiveram seus hashes conferidos contra os metadados preservados.

| Hipótese | Evidência favorável | Evidência contrária / limite | Teste possível | Conclusão |
|---|---|---|---|---|
| H_CLOCK_1 — Offset between local and remote clocks | T minus local receipt positive in 12/12, range 408.6478 to 446.958 ms; Both local and source series monotonic in observed sample | No synchronization log or independent simultaneous time reference; Stable-looking difference also compatible with timestamp generation semantics | Contemporaneous calibrated clock/NTP/PTP evidence and documented source timestamp meaning; current clock measurement cannot back-prove offset | COMPATIBLE_NOT_IDENTIFIED |
| H_CLOCK_2 — Local wall-clock adjustment or timestamp instrumentation error | time.time_ns is wall clock; no monotonic clock recorded; No record of clock corrections or timing accuracy | No backward step in the 12 observed request/receipt sequences; all receipts after requests; Stable offset across samples disfavors one isolated transient, without ruling out a persistent local bias | Saved system clock-adjustment logs and paired monotonic/wall timestamps at collection; none in this capture | NOT_IDENTIFIED; observed reversal absent, accuracy unknown |
| H_CLOCK_3 — Wrong unit conversion or arithmetic | Archived depth schema documenting T/E units is absent from bounded bundle | Integer calculation independently exact: T*10^6 - received_ns = 410300800 ns; Milliseconds align source T with the collection epoch; seconds/microseconds do not; Frozen local source proves request/receipt nanoseconds | Historical depth API schema for exact endpoint/version; separate raw-unit validation | ARITHMETIC_ERROR_REJECTED; primary source unit/semantic proof still incomplete |
| H_CLOCK_4 — T/E describe a different instant from the event/publication assumed | Only literal T/E keys preserved; exact economic semantics absent; E greater than T by 2 to 5 raw ticks in saved books | Ordering and monotonicity are consistent with ordinary event/response labeling, but do not identify it | Archived source specification and corresponding release/version; no automatic interpretation from current docs | COMPATIBLE_NOT_IDENTIFIED |
| H_CLOCK_5 — Wrong body/receipt association or simple cache explanation | Two exchangeInfo acquisitions have identical body and older body serverTime; freshness cannot follow body timestamp alone | All diagnostic bodies match per-name SHA-256; frozen collector records response metadata around same send; Old cached data alone would not explain future timestamps if clocks were synchronized and timestamp meant an occurred event | Verify preserved name/hash associations (executed); inspect HTTP Age/Date/cache headers and trace IDs (not retained) | HASH_MISASSOCIATION_NOT_OBSERVED; cache mechanism not proven and insufficient alone |
| H_CLOCK_6 — Remote timestamp-generation error | Remote timestamps exceed local receipt under ms interpretation | No independent accurate reference; the same observation is explained by local offset or semantic difference | Independent contemporary remote/local reference or provider incident evidence specific to capture interval | NOT_IDENTIFIED; no attribution of fault to exchange |

Nenhuma hipótese causal foi selecionada. Não há base para subtrair 410,3008 ms, ajustar timestamps pela mediana ou culpar o coletor/exchange.

## Os três estados

**OBSERVED:** o corpo foi recebido até o cutoff no mesmo domínio de relógio local. Não exige fingir que o clock remoto está sincronizado.

**EVENT_OCCURRED:** um timestamp associado foi preservado; ocorrência efetiva até um cutoff local continua NOT_PROVEN enquanto unidade, significado ou ligação entre relógios estiverem sem prova.

**ECONOMICALLY_ELIGIBLE:** requer o contrato econômico e sua validade para o escopo, além da admissibilidade temporal. Recebimento é condição necessária, não suficiente.

`CUTOFF_SEMANTICS_COMPARISON.json` executa os dois predicados no mesmo future_00. Em `max(T convertido, receipt)`, o filtro técnico v3 retorna true; a nova extensão mantém OBSERVED=true e ECONOMICALLY_ELIGIBLE=false. Não se reinterpretam os resultados anteriores como validação econômica. O máximo numérico de relógios não reconciliados deixa de servir como justificativa de elegibilidade.

## Matriz de clocks dos recibos

Os valores de evento são brutos; os locais são ns. U=UNKNOWN. PUB, RESP, ING e NORM permanecem U: E/serverTime não foram promovidos a publicação/resposta, e receipt não foi renomeado para ingestão. O header HTTP Date disponível em um recibo é preservado como candidato com resolução textual de um segundo, não primeira publicação ou resposta calibrada.

| Recibo | SOURCE_EVENT_TIME | SOURCE_PUBLICATION_TIME | SOURCE_RESPONSE_TIME | LOCAL_REQUEST_TIME | LOCAL_RECEIPT_TIME | INGESTION_TIME | NORMALIZATION_TIME |
|---|---|---|---|---|---|---|---|
| spot_info | U | U | U | 1788833242989838400 | 1788833243963778600 | U | U |
| future_info | U | U | U | 1788833244226826000 | 1788833244585202200 | U | U |
| spot_00 | U | U | U | 1788833244616702600 | 1788833244931863300 | U | U |
| future_00 | 1788833245358 | U | U | 1788833244617086500 | 1788833244947699200 | U | U |
| spot_01 | U | U | U | 1788833249958387800 | 1788833250300863700 | U | U |
| future_01 | 1788833250710 | U | U | 1788833249958777000 | 1788833250271010600 | U | U |
| spot_02 | U | U | U | 1788833255305352800 | 1788833255603519800 | U | U |
| future_02 | 1788833256054 | U | U | 1788833255306222500 | 1788833255608173200 | U | U |
| spot_03 | U | U | U | 1788833260610417000 | 1788833261089530100 | U | U |
| future_03 | 1788833261498 | U | U | 1788833260610742000 | 1788833261051042000 | U | U |
| spot_04 | U | U | U | 1788833266091512900 | 1788833266393979000 | U | U |
| future_04 | 1788833266838 | U | U | 1788833266091736600 | 1788833266410020400 | U | U |
| spot_05 | U | U | U | 1788833271412417400 | 1788833271725381800 | U | U |
| future_05 | 1788833272166 | U | U | 1788833271412984300 | 1788833271727374400 | U | U |
| spot_06 | U | U | U | 1788833276730588100 | 1788833277048756200 | U | U |
| future_06 | 1788833277483 | U | U | 1788833276731169000 | 1788833277042482100 | U | U |
| spot_07 | U | U | U | 1788833282051736600 | 1788833282395155000 | U | U |
| future_07 | 1788833282815 | U | U | 1788833282052401000 | 1788833282382306200 | U | U |
| spot_08 | U | U | U | 1788833287399056200 | 1788833287698544300 | U | U |
| future_08 | 1788833288148 | U | U | 1788833287399593200 | 1788833287708834000 | U | U |
| spot_09 | U | U | U | 1788833292711136400 | 1788833293058404300 | U | U |
| future_09 | 1788833293466 | U | U | 1788833292711687700 | 1788833293057352200 | U | U |
| spot_10 | U | U | U | 1788833298061177600 | 1788833298367365700 | U | U |
| future_10 | 1788833298803 | U | U | 1788833298061678400 | 1788833298367310100 | U | U |
| spot_11 | U | U | U | 1788833303371185100 | 1788833303694443100 | U | U |
| future_11 | 1788833304125 | U | U | 1788833303371701500 | 1788833303685024800 | U | U |
| spot_BTCUSDT | 1601510400000 | U | U | U | 1788807095427008000 | U | U |
| perp_trade | 1762588800000 | U | U | 1788832141566494000 | 1788832141857317000 | U | U |
| perp_mark | 1787788800000 | U | U | 1788832143595224000 | 1788832143883309000 | U | U |
| future_trade | 1788220800000 | U | U | 1788832234972590000 | 1788832235281079000 | U | U |
| future_mark | 1788220800000 | U | U | 1788832236187483000 | 1788832236466911000 | U | U |
| funding | 1787788800000 | U | U | 1788832149442542000 | 1788832149740362000 | U | U |
| probe_info | U | U | U | U | 1788831601761587000 | U | U |
| probe_docs | U | U | U | U | 1788831601260933000 | U | U |

As unidades, domínios e ressalvas por célula estão em `CLOCK_MATRIX.json`; não se impõe uma ordem total entre esses clocks.

## Evidence requirement map

“Irrecuperável do capture” significa que os bytes e campos registrados não identificam aquela propriedade; não declara que todo arquivo histórico possível inexiste. Uma fonte nova precisa ser contemporânea ao evento ou explicitamente versionada para provar o passado. Documentação de hoje e novos timestamps não recuperam clocks antigos.

| Campo ausente | Por que importa | Evidência necessária | Existe localmente? | Recuperável legitimamente? | Bloqueia | Próxima ação |
|---|---|---|---|---|---|---|
| quantity_unit | Defines exposure; contracts and base units differ | Dated exact spot/depth and USD-M contract specifications defining order/book quantity and lot unit | PARTIAL: quantity/volume labels and LOT_SIZE values; no complete unit contract | Historical source could prove it; receipt fields alone cannot | F04 | Future targeted historical specification search; no convention default |
| price_unit | Distinguishes USDT/BTC from USD/BTC or inverse quotation | Dated quote/price definition tied to instrument and metric | PARTIAL: base/quote fields and named prices; explicit full unit linkage absent | Potentially recoverable from archived contract/API specification, not ticker | F04 | Keep NOT_PROVEN until exact dated specification |
| settlement_asset | Defines actual payout currency | Historical contract settlement rule for BTCUSDT and BTCUSDT_261225, and spot settlement terms | NOT_FOUND; marginAsset=USDT is preserved but not settlement | Not derivable from marginAsset; requires separate dated terms | F04 | Seek specific archived contract settlement specification in a later authorized phase |
| multiplier | Converts contractual quantity to exposure | Instrument-specific contract size/multiplier, or explicit one-unit relationship, versioned | NOT_FOUND; no contractSize in sampled rows; LOT_SIZE step is not multiplier | Not derivable from precision/lot filters; external historical terms may recover | F04 | Keep UNKNOWN; do not default to 1 |
| linear_inverse / payoff | Determines PnL equation and currency | Dated payoff equation, price basis and payout currency for exact instrument | NOT_FOUND; U_MARGINED/PERPETUAL labels alone insufficient | Not uniquely identifiable from sample prices or code assumptions | F04 | No generic perpetual equation; archive specification needed |
| margin/collateral semantics | Defines capital constraints and treatment of collateral | Dated margin mode, collateral rules, haircuts, valuation, tiers and relevant account configuration | PARTIAL: marginAsset and percent fields; no complete rule/account context | Public historical rules may be recoverable; absent historical account state cannot be synthesized | F04 | Separate public contract gate from future scoped account/capital assumptions |
| expiry semantics | Defines maturity; not source availability | Contract deliveryDate with exact unit/event definition and dated specification | PARTIAL: BTCUSDT_261225 raw deliveryDate present; decoded 2026-12-25 08:00 UTC | Raw declared date recovered; old-calendar extrapolation and perpetual sentinel not proven | F04 dated | Use literal field only at collection; do not infer from ticker |
| price_type / executable status | Mark/trade/book have different uses | Endpoint/field mapping and, for actual execution, explicit fill evidence | PARTIAL: trade/mark endpoint distinction and displayed ask preserved; fill absent | Metric distinction recoverable now; realized fills unrecorded cannot be fabricated | F04 | Allow semantic checks; refuse mark-as-fill and trade-as-mark |
| funding position basis / direction / currency | A rate is insufficient to calculate cash | Versioned funding event formula, eligible position, payer/payee direction, currency and schedule | NOT_FOUND; 33 rate observations with fundingTime and markPrice preserved | Requires historical rules; actual account settlements require account ledger that was not captured | F04 funding | FUNDING_REPLAY_NOT_PROVEN |
| funding interval / eligibility | Determines which event applies to a position | Historical rule for interval/event boundary and eligibility | PARTIAL: observed deltas 28799974–28800013 candidate ms; not proof of fixed 8h schedule | Specific historical schedule may recover; actual eligibility not in rates alone | F04 funding | Keep rule unknown; no cash conversion |
| contract_version / valid_from / valid_until | Prevents applying later terms to old observations | Effective-dated terms, immutable source version and change history | NOT_FOUND; content hashes and collection times only | Potentially from historical archived specifications; hashes alone cannot recover absent revisions | F03,F04 | CURRENT_ONLY; earlier use is RETROACTIVE_ASSUMPTION |
| source publication time | Needed for historical information availability | Original publication/distribution timestamp or contemporaneous receipt before cutoff | NOT_FOUND; later ingestion, candle open/close and HTTP Date are not original publication | Not reconstructible from captured fields; an independent contemporary archive could help | F03 | Block earlier cutoff; do not use date labels as availability |
| listing/delisting/eligibility history | Avoids survivorship and universe backfill | Complete effective-dated membership events with information availability | NOT_FOUND; current status/onboardDate and BTC-only bundle do not cover universe | Structurally absent from this BTC bundle; separate historical universe evidence required | F03 | No broad collection now; maintain BLOCKED_CURRENT_EVIDENCE |
| revision control | Prevents selecting future-corrected values | All necessary as-of versions and when each became available | PARTIAL: exact observed hashes; official saved README says archives can be updated | Unrecorded versions cannot be regenerated from final body or checksum; external dated copies may exist | F03,F04 | Preserve observed versions; refuse historical first-vintage claim |
| T/E unit and meaning | Prevents assigning remote time to wrong event | Archived depth endpoint schema with release mapping | NOT_FOUND in scope; candidate ms interpretation only | Specific historical API reference may recover meaning, not clock calibration | F04 temporal | Keep literal raw fields and conditional arithmetic |
| remote/local offset and uncertainty | Allows valid cross-clock cutoff comparison | Contemporaneous clock calibration and uncertainty bounds, or independently timestamped synchronized trace | NOT_FOUND; no NTP/PTP, monotonic pairs, trusted response timing | Not identifiable from these recorded clocks alone; current calibration cannot recover past offset | F04 temporal | CAUSE_UNKNOWN; OBSERVED only, no economic eligibility by max |
| source response time | Distinguishes event from response production | Documented response-time clock or trustworthy server timing headers with calibration | NOT_FOUND for diagnostic; body serverTime repeated across acquisitions | Absent header/trace cannot be recovered from body alone | F04 temporal | Do not label E or serverTime as response time |
| ingestion/normalization time | Separates receive from persist/transform | Contemporaneous write/normalization event log | NOT_FOUND in original collector; only time around send retained | STRUCTURALLY_UNRECOVERABLE_FROM_CAPTURED_FIELDS unless an independent original log is later found | Temporal provenance | Use UNKNOWN; current file mtime/normalization execution is not historical evidence |

## Testes, decisões e parada

{
  "positive": 27,
  "negative": 28,
  "unknown": 3,
  "total_controls": 58,
  "failed": 0,
  "temporal_controls": 114,
  "temporal_failed": 0,
  "economic_admissions": 0,
  "scope": "Positive economic algebra uses declared units only; no complete real contract implied"
}

Foram 27 controles positivos, 28 negativos e 3 de UNKNOWN, sem falhas, além de 114 verificações de estados temporais. Positivos verificam campos explicitamente evidenciados, round-trip, distinção de métricas e álgebra declarada; não existe controle positivo de payoff real completo. As tentativas de moeda errada, contratos como quantidade base, multiplier suposto, settlement incompatível, margem como moeda de PnL, linear/inverse trocados e trade/mark/fill confundidos foram REJECTED ou UNSUPPORTED. UNKNOWN não foi preenchido para satisfazer o teste. A segunda execução produziu RESULTs idênticos byte a byte.

F03: identidade parcial CURRENT_ONLY; listing/delisting/eligibility históricos não demonstrados; disponibilidade apenas por recebimento local; publicação original ausente; revisões limitadas aos hashes adquiridos. **BLOCKED_CURRENT_EVIDENCE**, sem subset de ranking habilitado.

F04: campos literais parciais e tipos de preço distinguíveis; quantidade, unidade de preço como contrato, settlement, payoff, multiplier e collateral incompletos; domínio temporal não reconciliado. **BLOCKED_CURRENT_EVIDENCE**, sem subset econômico habilitado. Não exigir o universo completo não elimina essas faltas no próprio BTC.

Os dois gates ficam em BLOCKED_CURRENT_EVIDENCE porque fontes históricas específicas poderiam trazer termos ou informações ausentes. Algumas propriedades são não identificáveis a partir deste capture: offset/calibração não registrados, ingestão/normalização não registradas e vintages ausentes. Isso não é suficiente para declarar o projeto inteiro STRUCTURALLY_UNRECOVERABLE_FOR_SCOPE. Encerra-se esta rodada pela regra B (bloqueio preciso), com C para propriedades não identificáveis nos campos capturados e D para o bundle de especificações delimitado.

## Respostas finais

1. BTC spot: o recibo spot exchangeInfo comprova o namespace api.binance.com, a flag isSpotTradingAllowed=true, baseAsset=BTC e quoteAsset=USDT no momento de recebimento. Não há contrato econômico completo de quantidade, preço, multiplier, payoff ou settlement certificado neste bundle.

2. BTC perpetual: o recibo fapi comprova symbol=BTCUSDT, contractType=PERPETUAL, baseAsset=BTC, quoteAsset=USDT e marginAsset=USDT. Isso não prova linearidade, payout em USDT ou multiplier=1.

3. BTCUSDT_261225: o recibo declara NEXT_QUARTER, BTC/USDT, marginAsset=USDT e deliveryDate=1798185600000; o decoder preservado em milissegundos o representa como 2026-12-25 08:00 UTC. Esses termos são declarados na coleta; não validam períodos anteriores nem a regra de settlement.

4. Não estão todos comprovados. Quantity unit, price unit como contrato completo, multiplier, payoff e settlement permanecem NOT_PROVEN. Metadados de base/quote não substituem a definição da unidade de ordem, e filtros LOT_SIZE não definem multiplier.

5. São historicamente comprovados os bytes recebidos e os registros locais de aquisição, com a limitação de precisão do relógio não calibrado. As declarações de exchangeInfo são CURRENT_ONLY, isto é, apenas como coletadas em 08/09/2026, não documentação atual consultada hoje. Vigência passada ou continuidade entre duas coletas iguais permanece desconhecida. Uso em candles anteriores exigiria RETROACTIVE_ASSUMPTION.

6. Funding permanece observação de taxa: FUNDING_REPLAY_NOT_PROVEN. Há 33 registros, deltas entre 28799974 e 28800013 no campo de tempo (sob interpretação ms), mas isso não certifica intervalo fixo, posição elegível, direção, moeda de pagamento ou cash flow realizado.

7. Não. A aritmética de +410,3008 ms está confirmada condicionalmente à leitura de T em ms. O fenômeno aparece nos 12 livros futures, entre +408,6478 e +446,958 ms. CAUSE_UNKNOWN.

8. Faltam significado/unidade historicamente documentados de T/E para esse endpoint e uma ligação calibrada entre relógio remoto e local naquele intervalo. Não há logs contemporâneos de sincronização, offset, monotonicidade de relógio do sistema ou headers de resposta suficientes para distinguir offset, semântica e erro de geração.

9. Nenhum replay econômico parcial BTC spot/perp/future foi habilitado. São possíveis reconstrução literal de metadata, cronologia local de recebimento, separação trade/mark/book e testes dimensionais com unidades explicitamente declaradas. Esses controles não calculam notional/PnL de instrumentos reais nem fills.

10. F03 = BLOCKED_CURRENT_EVIDENCE. Faltam membership/listing/delisting/eligibility históricos, disponibilidade e versões apropriadas aos cutoffs. O pequeno bundle BTC não contém um universo histórico.

11. F04 = BLOCKED_CURRENT_EVIDENCE. Nenhum subconjunto satisfaz simultaneamente unidade, settlement, payoff, multiplier, collateral e admissibilidade temporal. Não se usa PARTIALLY_READY para chamar preparação técnica de autorização econômica.

12. Não se recuperam dos campos capturados: relógio monotônico e offset passado, instante de persistência/normalização não registrado, primeiras publicações e versões ausentes. Logs ou arquivos contemporâneos independentes poderiam mudar alguns estados; dados atuais não recompõem essa história. Essa impossibilidade é relativa ao acervo delimitado, não uma alegação sobre todos os arquivos possíveis.

13. A evidência impede abrir Fase 4 econômica, ranking F03 e replay de funding. Permite decidir a próxima busca estrita: especificação histórica exata de unidade, multiplier, payoff e settlement para BTCUSDT/BTCUSDT_261225 válida na janela escolhida. Se não houver prova, encerrar aquele replay histórico; resolver fórmulas por convenção não é alternativa admissível.

## Reproduzir

```
C:\Cripto\CRIPTO.cmd python -X utf8 C:\Cripto\operacao\relatorios\OPEN_SOURCE_20260911T0233\phase3b\work\test_contracts.py C:\Cripto\operacao\temporarios\fase3b-repro-novo
```

Use uma pasta de saída nova. Não reexecute prepare.py sobre a baseline. O teste usa contratos/matrizes desta entrega e os recibos locais preservados. `PRESERVATION.json`, `REPRODUCIBILITY.json` e `MANIFEST.json` registram as verificações. O pacote inclui os inputs específicos adicionais para rastreabilidade; os caminhos originais são mantidos como proveniência.

Para BTC, base/quote e alguns campos de mercado estão comprovados como recebidos; settlement, multiplier, payoff e temporalidade econômica continuam precisamente desconhecidos. Isso permite reconstrução documental e controles técnicos, mas impede replay econômico. Não haverá promoção global para Fase 4.
