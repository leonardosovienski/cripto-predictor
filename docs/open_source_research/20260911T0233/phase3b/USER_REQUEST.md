# CRIPTO-PREDICTOR — FASE 3B

## Fechamento dos gates de contrato econômico e temporal para F03/F04

Continue a iniciativa `20260911T0233`.

Esta é uma continuação estrita da Fase 3.

Não reinicie discovery amplo.

Não pesquise novas estratégias.

Não treine modelos.

Não faça novo ranking econômico.

Não execute replay econômico completo.

Não reexecute F02.

Não opere capital.

Não altere experimentos, trials ou protocolos históricos.

---

# 1. MISSÃO

A Fase 3 demonstrou:

* 23 recibos HTTP/RPC reais + 1 artefato retrospectivo avaliados;
* 24 envelopes parciais fiéis;
* zero identidades econômicas completas certificadas para replay;
* 19/19 controles adversariais rejeitados;
* zero perdas de round-trip;
* zero admissões temporais indevidas nos testes finais;
* F03 = BLOCKED;
* F04 = BLOCKED.

Os dois principais bloqueadores restantes são:

### A. CONTRATO ECONÔMICO DO INSTRUMENTO

Determinar, somente com evidência admissível:

* unidade de quantidade;
* unidade de preço;
* base;
* quote;
* settlement;
* margin asset;
* contract type;
* linear/inverse;
* multiplier;
* payoff;
* expiry quando aplicável;
* semântica de trade/mark/index/funding;
* versão temporal da especificação.

### B. CONTRATO TEMPORAL

Determinar quais clocks podem ser reconciliados e qual informação estava efetivamente admissível no cutoff.

Em particular, investigar o caso preservado em que:

`event_time - receipt_time = +410,3008 ms`

sem assumir previamente:

* clock skew;
* erro do coletor;
* erro da exchange;
* semântica particular da fonte.

A causa deve permanecer UNKNOWN se a evidência não permitir distingui-la.

---

# 2. OBJETIVO DECISÓRIO

Esta fase deve responder apenas:

> **Existe evidência preservada suficiente para construir, sem inferência silenciosa, os contratos econômicos e temporais mínimos necessários para abrir F03 e/ou F04?**

Não é necessário que F03 e F04 tenham a mesma resposta.

Possíveis resultados:

```text
F03 = READY
F03 = PARTIALLY_READY
F03 = BLOCKED_CURRENT_EVIDENCE
F03 = STRUCTURALLY_UNRECOVERABLE_FOR_SCOPE

F04 = READY
F04 = PARTIALLY_READY
F04 = BLOCKED_CURRENT_EVIDENCE
F04 = STRUCTURALLY_UNRECOVERABLE_FOR_SCOPE
```

Não use apenas `BLOCKED` quando for possível distinguir ausência temporária de evidência de impossibilidade retrospectiva.

---

# 3. REGRA CENTRAL — NÃO INVENTAR HISTÓRIA

É proibido obter sucesso usando:

* documentação atual retropropagada automaticamente;
* exchangeInfo atual como prova de contrato histórico;
* convenções modernas da venue aplicadas ao passado;
* ticker para inferir settlement;
* marginAsset como sinônimo automático de settlement;
* precision como decimals econômicos;
* mark como fill;
* last como executable quote;
* informação descoberta posteriormente como elegibilidade passada;
* knowledge do agente sobre como “normalmente” funciona determinada exchange.

Se a prova histórica não existir:

`NOT_PROVEN`.

---

# 4. ESCOPO PRIMÁRIO — BUNDLE BTC PRESERVADO

Comece pelo menor conjunto capaz de decidir o gate.

Priorize os recibos já preservados relacionados a:

### BTC SPOT

* instrumento BTCUSDT;
* exchange metadata correspondente;
* preços/quotes/trades existentes;
* respectivos clocks.

### BTC PERPETUAL / FUTURES

* BTCUSDT perpetual;
* BTCUSDT_261225 quando relevante;
* trade;
* mark;
* funding;
* exchange metadata;
* clocks.

Não amplie imediatamente para todo o universo.

Primeiro tente estabelecer contratos completos para estes casos.

---

# 5. MATRIZ DE CONTRATO DO INSTRUMENTO

Para cada instrumento construa:

| Campo             | Valor | Status             | Evidência | Clock da evidência | Pode valer retroativamente? |
| ----------------- | ----- | ------------------ | --------- | ------------------ | --------------------------- |
| venue             |       | PROVEN/UNKNOWN/N/A |           |                    |                             |
| market_type       |       |                    |           |                    |                             |
| base_asset        |       |                    |           |                    |                             |
| quote_asset       |       |                    |           |                    |                             |
| settlement_asset  |       |                    |           |                    |                             |
| margin_asset      |       |                    |           |                    |                             |
| quantity_unit     |       |                    |           |                    |                             |
| price_unit        |       |                    |           |                    |                             |
| multiplier        |       |                    |           |                    |                             |
| linear_inverse    |       |                    |           |                    |                             |
| payoff            |       |                    |           |                    |                             |
| expiry            |       |                    |           |                    |                             |
| price_type        |       |                    |           |                    |                             |
| funding_semantics |       |                    |           |                    |                             |
| contract_version  |       |                    |           |                    |                             |
| valid_from        |       |                    |           |                    |                             |
| valid_until       |       |                    |           |                    |                             |

Nenhuma célula UNKNOWN deve ser silenciosamente preenchida para permitir replay.

---

# 6. DEFINA O CONTRATO MATEMATICAMENTE

Quando houver evidência suficiente, expresse explicitamente a relação econômica.

Exemplo genérico:

```text
NOTIONAL_QUOTE =
    QUANTITY_BASE * PRICE_QUOTE_PER_BASE
```

ou, para contrato derivativo:

```text
NOTIONAL
PNL
MARGIN
SETTLEMENT
```

com fórmulas derivadas da especificação realmente comprovada.

Não use uma fórmula genérica de perpetual se a especificação histórica correspondente não tiver sido demonstrada.

Teste propriedades dimensionais.

Exemplo:

```text
BTC * USDT/BTC = USDT
```

Uma operação dimensionalmente inconsistente deve falhar.

---

# 7. TESTES DE UNIDADE ECONÔMICA

Crie controles que tentem introduzir:

* preço em moeda errada;
* quantidade interpretada como contratos quando é base asset;
* multiplier incorreto;
* settlement incompatível;
* margin asset confundido com PnL currency;
* linear tratado como inverse;
* trade price tratado como mark;
* mark tratado como executable quote.

Todos devem ser:

`REJECTED`

ou

`UNSUPPORTED`.

Nunca convertidos silenciosamente.

---

# 8. FUNDING

Para os recibos de funding, diferencie explicitamente:

* predicted;
* published;
* realized/settled;
* interval;
* timestamp de referência;
* direção do pagamento;
* moeda do pagamento;
* base de cálculo.

Não use `fundingRate` como prova automática de cash flow executado.

Para permitir replay de funding devem estar comprovados, no mínimo:

```text
RATE
INTERVAL / EVENT
POSITION BASIS
PAYMENT DIRECTION
PAYMENT CURRENCY
ELIGIBILITY TIME
```

Caso contrário:

`FUNDING_REPLAY_NOT_PROVEN`.

---

# 9. RECONCILIAÇÃO DOS CLOCKS

Construa para cada recibo:

```text
SOURCE_EVENT_TIME
SOURCE_PUBLICATION_TIME
SOURCE_RESPONSE_TIME
LOCAL_REQUEST_TIME
LOCAL_RECEIPT_TIME
INGESTION_TIME
NORMALIZATION_TIME
```

Use UNKNOWN quando ausente.

Não force uma ordem total se os relógios não forem comparáveis.

---

# 10. CASO +410,3008 MS

Investigue especificamente a observação:

```text
event_time > receipt_time
difference = 410.3008 ms
```

Tente determinar, somente com evidência preservada:

1. unidade correta de ambos os clocks;
2. origem de cada timestamp;
3. transformação aplicada;
4. precisão/resolução;
5. monotonicidade;
6. relógio local versus remoto;
7. possibilidade de clock skew;
8. possibilidade de timestamp representar momento diferente do assumido.

Produza hipóteses concorrentes:

```text
H_CLOCK_1
H_CLOCK_2
...
```

Para cada uma:

* evidência favorável;
* evidência contrária;
* teste possível;
* conclusão.

Se nenhuma puder ser distinguida:

`CAUSE_UNKNOWN`.

Isso é resultado válido.

---

# 11. ADMISSIBILIDADE TEMPORAL

Não use:

```text
max(event_time, receipt_time)
```

como solução universal sem justificar o significado econômico.

Defina separadamente:

### OBSERVED

A fonte foi recebida.

### EVENT_OCCURRED

O evento possui timestamp associado.

### ECONOMICALLY_ELIGIBLE

Temos evidência suficiente de que aquela informação podia participar da decisão.

Esses estados podem ocorrer em tempos diferentes.

---

# 12. HISTORICAL SPECIFICATION PROBLEM

Determine explicitamente se as especificações preservadas são:

* contemporâneas à observação;
* posteriores;
* sem timestamp suficientemente forte;
* versionadas;
* não versionadas.

Classifique cada uso como:

### HISTORICALLY_PROVEN

Há evidência adequada da especificação naquele período.

### CURRENT_ONLY

A especificação é comprovada somente no momento da coleta.

### RETROACTIVE_ASSUMPTION

Seria necessário assumir que especificação atual valia no passado.

### UNKNOWN

Não há base suficiente.

`RETROACTIVE_ASSUMPTION` não abre replay econômico.

---

# 13. NÃO CONFUNDA CONTRATO COM FILL

Mesmo que o contrato econômico fique completo, isso não prova:

* disponibilidade;
* liquidez;
* bid/ask;
* fill;
* queue;
* slippage;
* impact;
* hedge simultâneo.

Esta fase pode abrir o **contrato necessário para F04**, mas não validar a execução econômica.

---

# 14. GATE F03

F03 exige capacidade de reconstruir universo/informação point-in-time.

Avalie separadamente:

```text
INSTRUMENT_IDENTITY
LISTING_STATE
DELISTING_STATE
ELIGIBILITY
DATA_AVAILABILITY
PUBLICATION_TIMING
REVISION_CONTROL
```

F03 só pode ser `READY` se o escopo definido puder ser reconstruído sem:

* survivorship;
* backfill silencioso;
* metadata futura;
* universo atual retropropagado.

Caso o bundle BTC prove somente identidade do instrumento mas não membership histórica:

`F03 = BLOCKED_CURRENT_EVIDENCE`.

Não amplie a coleta para “fazer passar”.

---

# 15. GATE F04

Para o escopo BTC preservado, F04 exige ao menos:

```text
INSTRUMENT
QUANTITY UNIT
PRICE UNIT
SETTLEMENT
PAYOFF
MULTIPLIER
MARGIN/COLLATERAL SEMANTICS
PRICE TYPE
CLOCK ADMISSIBILITY
```

Se todos forem demonstrados para um subconjunto específico, classifique:

`F04 = PARTIALLY_READY`

e indique exatamente qual subset está habilitado.

Não exija que todo o universo esteja resolvido para reconhecer avanço local.

---

# 16. REGRA DE PARADA

Esta fase deve acabar quando ocorrer uma destas condições:

### A — PROVA SUFICIENTE

Os contratos necessários foram demonstrados.

### B — BLOQUEIO PRECISO

Sabemos exatamente qual evidência falta e onde deveria estar.

### C — IMPOSSIBILIDADE RETROSPECTIVA

A propriedade necessária não pode ser reconstruída legitimamente do acervo disponível.

### D — SATURAÇÃO

Novas inspeções dos mesmos artefatos não acrescentam evidência.

Não continue pesquisando indefinidamente tentando preencher UNKNOWN.

---

# 17. SAÍDA OBRIGATÓRIA — EVIDENCE REQUIREMENT MAP

Para cada UNKNOWN material produza:

| Campo ausente    | Por que importa | Evidência necessária | Existe localmente? | Recuperável legitimamente? | Bloqueia |
| ---------------- | --------------- | -------------------- | ------------------ | -------------------------- | -------- |
| settlement       |                 |                      |                    |                            | F04      |
| multiplier       |                 |                      |                    |                            | F04      |
| publication_time |                 |                      |                    |                            | F03      |
| listing state    |                 |                      |                    |                            | F03      |

Essa tabela deve determinar se a próxima ação é:

* usar evidência local;
* buscar fonte histórica específica futuramente;
* manter UNKNOWN;
* encerrar aquela linha de replay.

---

# 18. TESTES

Preserve:

* adapter v2;
* adapter v3;
* harness v3.1;
* resultados das Fases 2 e 3.

Qualquer extensão deve receber nova versão.

Execute:

### POSITIVE CONTROLS

Casos cuja semântica está explicitamente comprovada.

### NEGATIVE CONTROLS

Unidades, settlement e clocks incompatíveis.

### UNKNOWN CONTROLS

Casos incompletos devem permanecer incompletos.

Uma implementação que “resolve” UNKNOWN automaticamente deve falhar.

---

# 19. CRITÉRIOS DE SUCESSO DA FASE 3B

A fase passa se produzir uma decisão confiável, não necessariamente `READY`.

Sucesso significa:

* nenhuma inferência silenciosa;
* contratos comprovados quando possível;
* UNKNOWN preservado quando necessário;
* causa temporal não inventada;
* evidência histórica distinguida da atual;
* blockers precisos;
* decisão inequívoca sobre abertura ou não de F03/F04.

---

# 20. NÃO FAZER

Não:

* executar backtest completo;
* calcular Sharpe;
* calcular PnL de estratégia nova;
* otimizar threshold;
* selecionar moedas;
* testar Transformer/RL;
* mudar block bootstrap;
* buscar nova estratégia;
* promover Aave;
* reabrir hipótese encerrada;
* operar capital;
* transformar documentação atual em história.

---

# 21. PERGUNTAS FINAIS

Responda:

1. Qual é o contrato econômico comprovado para BTC spot?
2. Qual é o contrato econômico comprovado para BTC perpetual?
3. Qual é o contrato comprovado para BTC future datado, se aplicável?
4. Quantity, price, multiplier, payoff e settlement estão comprovados?
5. Quais propriedades são históricas e quais são apenas atuais?
6. Funding pode ser interpretado como cash flow histórico ou apenas como observação de taxa?
7. A divergência de 410,3008 ms foi explicada?
8. Se não, qual é exatamente a incerteza restante?
9. Existe algum replay parcial que agora possa ser construído sem metadata inventada?
10. F03 está READY, PARTIALLY_READY ou continua bloqueado?
11. F04 está READY, PARTIALLY_READY ou continua bloqueado?
12. Que informação faltante é irrecuperável com o acervo atual?
13. Qual é a próxima decisão econômica que essa evidência permite ou impede?

---

# 22. DECISÃO SOBRE A FASE 4

A Fase 4 só pode começar para um determinado escopo se os dados necessários daquele escopo estiverem admissíveis.

Não existe promoção global do projeto inteiro.

Exemplo:

```text
BTC SPOT/PERP CONTRACT
    READY
        ↓
F04 ECONOMIC REPLAY BTC
```

enquanto simultaneamente:

```text
HISTORICAL CROSS-SECTIONAL UNIVERSE
    BLOCKED
        ↓
NO F03 ECONOMIC RANKING
```

Essa separação é obrigatória.

---

# 23. RESULTADO ESPERADO

Não termine com:

> “Precisamos de mais dados.”

Termine com algo do tipo:

> **“Para o instrumento X, os campos A/B/C estão comprovados e os campos D/E continuam desconhecidos. Isso permite o experimento Y, mas impede Z. Para recuperar D seria necessária a evidência histórica W; essa evidência não existe no acervo atual / existe no arquivo Q. A inconsistência temporal K permanece sem causa identificada e, portanto, aplicamos a regra conservadora R.”**

A finalidade desta fase é transformar UNKNOWN genérico em:

**KNOWN**
ou
**PRECISELY_UNKNOWN**
ou
**UNRECOVERABLE**

para que o projeto saiba exatamente onde pode e onde não pode produzir evidência econômica.
