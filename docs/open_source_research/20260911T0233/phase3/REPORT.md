# CRIPTO-PREDICTOR — Fase 3: identidade em recibos reais

Iniciativa `20260911T0233`. Resultado: **normalização parcial rastreável; identidade econômica completa ainda não certificada. F03 BLOCKED. F04 BLOCKED.**

Esta fase não calcula alpha, não reexecuta F02/F05, não altera hipóteses ou protocolos congelados e não autoriza validação prospectiva ou capital.

## Escopo e denominadores

23 recibos HTTP/RPC e um artefato retrospectivo formam 24 casos primários. Cada série fornece apenas sua primeira linha para o experimento de identidade; bytes completos e número de linhas são preservados. Amostragem deliberada por símbolo/endpoint, sem seleção por retorno. Nove enriquecimentos são apresentados separadamente, reutilizando os mesmos recibos: não aumentam a contagem de fontes independentes.

`VALID` significa identidade econômica completa, não simplesmente JSON válido. `AMBIGUOUS` inclui campos econômicos não comprovados; não significa que todos os campos sejam desconhecidos. Metadados/RPC são evidência auxiliar, não preços negociáveis. O round-trip mede fidelidade da representação parcial, não comprovação do que falta. Assim, zero VALID e 24 envelopes fiéis são resultados compatíveis.

## Protocolo e baseline

Commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. F01 v2 SHA-256 `b2636d2b290a8dd905a04263d6be501b16598e086eb525a3b3f617f9fab83a3a`. `BASELINE.json` identifica os arquivos somente leitura, a seleção exata e os caminhos experimentais; `PROTOCOL.json` precede a bateria. Foram verificados 277 arquivos protegidos, sem mudanças. Os documentos e manifestos anteriores não foram reescritos.

Hipótese: um contrato explícito consegue conservar o que os recibos comprovam e recusar usos que dependam de metadata ausente. Incerteza: instrumento, unidade e disponibilidade podem ser reconstruídos sem pressupostos? Controle: leitura direta de ponteiros e hashes; mesmas observações após serialização; pares reais com semântica diferente; mutações derivadas claramente identificadas. Métrica: perdas de round-trip, uso antes do cutoff, inferências e adversários aceitos. Custos: processamento local; zero coleta, conversão cambial, taxas ou premissas de rentabilidade.

Sucesso exige todos os casos suportados fiéis, nenhuma informação futura admitida, proveniência verificável e preservação da baseline. Rejeição: inconsistência aceita ou perda semântica. Inconclusão econômica: ausência de campos históricos ou contrato explícito. Passar o envelope não abre automaticamente o replay.

## Resultado original e extensão

`V2_FIRST_BATTERY.json` conserva a execução do v2 intacto: 24 casos não elegíveis para construção direta. O teste não preencheu Instrument e publication com valores supostos. É uma avaliação de representabilidade e recusa, não prova de uma colisão real na produção. O schema não tem tipo/unidade de observação, status UNKNOWN, revisão ou proveniência por campo. Isso limita seu escopo; não invalida os testes sintéticos da fase 2.

`EXTENSION_PROTOCOL.json` registra, depois desse resultado, a extensão v3 em arquivo separado. Os 23 campos pedidos estão em cada envelope, com PROVEN/UNKNOWN/N/A e justificativa; SOURCE_VERSION distingue protocolo de implementação no texto da transformação. Nada é classificado N/A apenas por faltar. Valores originais, ponteiros, transformação, hashes do arquivo físico e do corpo descomprimido ficam preservados. O gate econômico exige todos os campos necessários comprovados ou estruturalmente N/A.

O primeiro teste v3 também foi preservado, com adapter, harness e resultados em `preserved_first_v3/`. Houve uma expectativa incorreta no teste: assumir que todo recibo já estaria elegível quando recebido. `future_00` traz T=1788833245358 ms e recebimento=1788833244947699200 ns: diferença de **410,3008 ms**. A causa física (clock skew, relógio do coletor ou semântica da fonte) não foi estabelecida. O adapter recusou o registro nesse cutoff. O harness v3.1 passou a exigir o maior clock comprovado, preservando o valor real e registrando a inconsistência. O antigo campo TEMPORAL_VIOLATIONS=1 era uma divergência contra esse oráculo incorreto, não vazamento observado; a errata é esta seção e `CORRECTION_PROTOCOL.json`.

## Síntese da bateria final

```json
{
  "TOTAL_CASES": 24,
  "REAL_HTTP_RPC_RECEIPTS": 23,
  "RETROSPECTIVE_ARTIFACTS": 1,
  "VALID": 0,
  "CORRECTLY_REJECTED": 1,
  "AMBIGUOUS": 22,
  "UNSUPPORTED": 1,
  "BUGS_FOUND": 1,
  "BUGS_FIXED": 1,
  "BUG_SCOPE": "test oracle only; zero demonstrated v2 production bugs",
  "REPRESENTATION_GAPS_ADDRESSED": 2,
  "TEMPORAL_VIOLATIONS": 0,
  "SOURCE_CLOCK_INCONSISTENCIES": 1,
  "SILENT_INFERENCES": 0,
  "ROUND_TRIP_FAILURES": 0,
  "FAITHFUL_PARTIAL_ENVELOPES": 24,
  "COMPLETE_ECONOMIC_IDENTITIES": 0,
  "ADVERSARIAL_TESTS": 19,
  "ADVERSARIAL_REJECTED": 19,
  "TEMPORAL_CHECKS": 92
}
```

Os 19 testes incluem 15 mutações/recusas derivadas e quatro pares reais. As famílias A–H estão cobertas; ausência de recibo coin-margined real limita a abrangência do teste de settlement. A recusa de mutação comprova integridade de evidência, não a verdade econômica do servidor. A recusa dos pares reais verifica diferenças explícitas; recusas por UNKNOWN conservam a lacuna. Noventa e dois checks incluem antes/no limite de recebimento, maior clock e revisão futura derivada. Não foi encontrada revisão econômica real autenticada para testar reconstrução histórica entre versões; dois headers repetidos são duas aquisições, não duas versões econômicas.

SILENT_INFERENCES=0 significa que os campos normalizados desta bateria têm evidência/transformação explícita ou UNKNOWN, não que qualquer decoder arbitrário futuro esteja certificado. Nenhuma paridade USD/USDT foi aplicada. UNIT de um call RPC permanece raw ABI; não se promove um inteiro a valor monetário.

## Matriz primária

| Caso | Fonte | Instrumento | Unidade | Settlement | Versão | Temporalidade | Round-trip | Adversarial | Resultado |
|---|---|---|---|---|---|---|---|---|---|
| spot_BTCUSDT | api.binance.com | BTCUSDT | UNKNOWN | UNKNOWN | body df0add0687 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| spot_ETHUSDT | api.binance.com | ETHUSDT | UNKNOWN | UNKNOWN | body c4d146a149 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| spot_FTTUSDT | api.binance.com | FTTUSDT | UNKNOWN | UNKNOWN | body b1ae9ed297 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| spot_WBETHUSDT | api.binance.com | WBETHUSDT | UNKNOWN | UNKNOWN | body d2502ef8e3 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| perp_trade | fapi.binance.com | BTCUSDT | UNKNOWN | UNKNOWN | body 608f95667e | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| perp_mark | fapi.binance.com | BTCUSDT | UNKNOWN | UNKNOWN | body 55c4509367 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| future_trade | fapi.binance.com | BTCUSDT_261225 | UNKNOWN | UNKNOWN | body 26f7c61b55 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| future_mark | fapi.binance.com | BTCUSDT_261225 | UNKNOWN | UNKNOWN | body 50a2c24bab | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| funding | fapi.binance.com | BTCUSDT | UNKNOWN | UNKNOWN | body 25810cacc6 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| spot_info | api.binance.com | BTCUSDT | N/A | UNKNOWN | body b0b5e41545 | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| future_info | fapi.binance.com | BTCUSDT | N/A | UNKNOWN | body 18a1918fe2 | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| spot_00 | api.binance.com | BTCUSDT | UNKNOWN | UNKNOWN | body 2420facb21 | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| future_00 | fapi.binance.com | BTCUSDT | UNKNOWN | UNKNOWN | body e97769e5af | evento > receipt: bloqueado no recebimento | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_001 | arb-mainnet.g.alchemy.com | UNKNOWN | chain identifier | UNKNOWN | body b000147798 | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_018 | arb-mainnet.g.alchemy.com | UNKNOWN | hash bytes | UNKNOWN | body 547a3aab42 | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_019 | arb-mainnet.g.alchemy.com | 0x794a61358d6845594f94dc1db02a252b5b4814ad | raw ABI bytes | UNKNOWN | body 52e3892d67 | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_021 | arb-mainnet.g.alchemy.com | 0x794a61358d6845594f94dc1db02a252b5b4814ad | raw ABI bytes | UNKNOWN | body 91fef22f7b | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_023 | arb-mainnet.g.alchemy.com | 0x724dc807b04555b71ed48a6896b6f41593b8c637 | raw ABI bytes | UNKNOWN | body c25290f8f8 | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_025 | arb-mainnet.g.alchemy.com | 0x724dc807b04555b71ed48a6896b6f41593b8c637 | raw ABI bytes | UNKNOWN | body ebeec3a29c | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_027 | arb-mainnet.g.alchemy.com | 0xaf88d065e77c8cc2239327c5edb3a432268e5831 | raw ABI bytes | UNKNOWN | body 8f9db08bf6 | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_block_002 | arb-mainnet.g.alchemy.com | UNKNOWN | block number | UNKNOWN | body 911dcd83a9 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| aave_block_004 | arb-mainnet.g.alchemy.com | UNKNOWN | block number | UNKNOWN | body 9db2797b07 | evento + receipt; publicação UNKNOWN | fiel, parcial | conjunto A–H / pares | AMBIGUOUS |
| empty_FTT | api.binance.com | FTTUSDT | UNKNOWN | UNKNOWN | body 4f53cda18c | receipt; evento UNKNOWN | fiel, parcial | conjunto A–H / pares | CORRECTLY_REJECTED |
| late_identity_mapping | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | body 85759f042e | acesso posterior; PIT proibido | fiel, parcial | conjunto A–H / pares | UNSUPPORTED |

Todos os campos e hashes completos estão em `NORMALIZED_CASES.json`; a matriz não substitui esse registro. MARKET_TYPE desconhecido em candles não é preenchido por sufixo de ticker. VENUE é namespace do host evidenciado, não certificação da contraparte legal. O preço de livro é displayed ask, nunca fill garantido. O candle é close trade/mark, nunca executable quote. Uma resposta vazia é corretamente rejeitada como observação; não é preço zero ou prova suficiente de delisting.

## Evidências recuperáveis, sem backfill

`EXPLICIT_ENRICHMENT.json` contém oito descrições de instrumentos derivadas de exchangeInfo, incluindo BTC, ETH, WBETH e stablecoins quando presentes. Base/quote e marginAsset/contractType são copiados de campos explícitos e só conhecidos a partir do recebimento daquele recibo. Não se aplicou metadata de setembro/2026 a candles antigos. Precision não virou decimals; marginAsset não virou settlement. A categorização econômica de WBETH como wrapped/staked não foi inferida apenas do ticker.

No bundle Aave, a resposta de chainId é 42161 no endpoint consultado. O recibo web3_sha3 liga `getReserveNormalizedIncome(address)` ao selector usado pelo call. Pool, argumento de token, bloco e inteiro concordam com month-00 preservado. O inteiro 1069973262775083814190632012, dividido exatamente por 10^27 conforme decoder local preservado, produz **1.069973262775083814190632012**. Essa transformação é reproduzível e não produz USDC monetário. A concordância com month-00 usa a mesma linhagem; não é fonte independente nem reexecução F02.

O registro derivado preservado tem decimals=6 e o call aave_027 retorna inteiro 6. O recibo específico de selector decimals() não pertence a esta amostra exata; a extensão não declara uma nova certificação histórica do ABI. Código de implementação histórica e primeira disponibilidade ao trader continuam NOT_PROVEN. Não foram encontrados nesta seleção recibos de OI, index-price, coin-margined, logs de eventos ou revisão econômica autenticada; não houve busca externa para suprir essas classes.

## Respostas finais

1. Foram avaliados 23 recibos HTTP/RPC reais distintos e 1 artefato retrospectivo de identidade. Para recibos com séries, normalizou-se a primeira observação; não se certificaram todas as linhas. Há ainda 9 casos derivados de enriquecimento, sem novos recibos. Dois recibos exchangeInfo contêm vários símbolos: os derivados incluem stablecoins.

2. Zero receberam certificação de identidade econômica completa para replay. Os 24 envelopes preservam fielmente evidência parcial e ausências. Nos derivados, 8 descrições de instrumentos têm base/quote explícitas; o nono reconstrói o índice Aave. Não são 9 instrumentos economicamente certificados.

3. BTCUSDT aparece em namespaces spot e futures; candles trade e mark têm semânticas diferentes; fundingRate não prova pagamento nem intervalo; marginAsset não prova settlement; precision não prova decimals on-chain. No livro future_00, evento está 410,3008 ms depois do recebimento local. Headers repetidos do mesmo bloco têm recibos distintos, sem evidência de revisão econômica.

4. Não foi demonstrado novo bug de produção no F01 v2. Foram documentadas duas lacunas de representação. Um bug apareceu no oráculo do novo teste: presumir elegibilidade no instante de recebimento apesar de evento posterior. A implementação já bloqueava esse caso; corrigiu-se o teste, preservando sua falha.

5. Sim, foi criada a extensão experimental F01-real v3: statuses explícitos, semântica da observação, proveniência e gate conservador. O arquivo F01 v2 permanece idêntico. A correção posterior foi no harness v3.1, sem alterar os bytes do adapter v3. Nenhuma integração em produção.

6. Faltam, conforme a fonte, settlement explícito, payoff/multiplier, identidade histórica de tokens, unidades econômicas, publicação original, revisão/provedor/implementação históricos, elegibilidade datada do universo e clocks reconciliados. SOURCE_VERSION=2.0 nos RPC descreve apenas o envelope JSON-RPC, nunca versão da implementação Aave.

7. Os recibos exchangeInfo preservados permitem recuperar base, quote, marginAsset e contractType no instante da coleta, com seus próprios clocks. O bundle Aave permite ligar chain observada no endpoint, selector, pool, endereço do argumento e inteiro de normalized income ao registro derivado do bloco. O decoder local documenta RAY=10^27. São evidências separadas; não foram retropropagadas aos candles.

8. A amostra não permite recuperar a primeira publicação ou revisões não arquivadas, nem afirmar elegibilidade de universo em datas antigas. Metadados de setembro/2026 não certificam especificações de 2020–2024. Isso é impossibilidade nesta evidência, não prova de que nenhum arquivo histórico externo exista.

9. Sim: BTCUSDT spot e PERPETUAL são instrumentos distintos mesmo com o mesmo símbolo; pool Aave e token USDC são contratos diferentes. Trade versus mark são métricas distintas, que podem referir o mesmo instrumento. Não foi demonstrado que a produção tenha efetivamente unido esses registros antes; mostrou-se o risco e a recusa no experimento.

10. F03: BLOCKED. O envelope preserva incertezas e impede o uso antecipado dos recibos, mas não fornece publicação histórica nem membership/listing/delisting completos. Metadados recentes não abrem ranking point-in-time histórico.

11. F04: BLOCKED para replay econômico. Já distingue namespaces, metric types, endereços e moedas explicitamente observadas, mas ainda faltam contratos de settlement/payoff/unidade e reconciliação dos clocks; não há comprovação de fills. Isso não impede estudos técnicos isolados de identidade.

12. A próxima incerteza de maior valor é se o bundle preservado de BTC spot/futures contém especificação explícita, temporalmente compatível, de unidade de quantidade, multiplier, payoff e settlement. Deve-se verificar esse gate necessário antes de replay e explicar a divergência de 410,3008 ms por evidência do coletor. Se faltar, manter UNKNOWN e registrar precisamente o contrato de evidência requerido.

## Reprodução e limites

Com o ambiente e recibos locais preservados, execute:

```powershell
C:\Cripto\CRIPTO.cmd python -X utf8 C:\Cripto\operacao\relatorios\OPEN_SOURCE_20260911T0233\phase3\work\run.py C:\Cripto\operacao\temporarios\f01-real-repro-novo
```

Escolha um diretório de saída novo. Não reexecute prepare.py sobre a baseline. `REPRODUCIBILITY.json` registra uma segunda execução com mesmos bytes dos envelopes/adversários e mesma síntese; horários de execução não fazem parte da igualdade. `PRESERVATION.json` compara todos os arquivos enumerados na baseline. `MANIFEST.json` sela esta entrega. O código experimental usa a biblioteca padrão e imports já existentes do ambiente, sem novas bibliotecas.

O resultado autoriza continuar investigando contratos de dados. Não autoriza ranking, replay econômico completo, promoção de hipótese, validação prospectiva, ordens ou capital.
