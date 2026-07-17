# Pre-filtro de chamadas LLM

O pre-filtro é uma proteção de custo, não um modelo e não um ajuste do score. Ele
usa somente a Feature Store já materializada: volume USD, variação de 7 dias e a
direção técnica existente (SMA-200 + histograma MACD, com RSI como voto auxiliar).

Por padrão, ele não faz nada:

```dotenv
LLM_PREFILTER_ENABLED=false
```

Em uma nova trial forward, a configuração explícita é:

```dotenv
LLM_PREFILTER_ENABLED=true
LLM_PREFILTER_MIN_VOLUME_USD=10000000
LLM_PREFILTER_MIN_ABS_CHANGE_7D=2
```

O ativo só chama o LLM se tiver liquidez suficiente, movimento absoluto de sete dias
acima do piso e direção técnica `bull` ou `bear`. Os excluídos geram o evento JSONL
`llm_prefilter_skipped` com a razão, mas não criam previsão artificial.

Essa seleção muda a população observada e, portanto, não pode ser ativada na H5.
Registrar uma nova trial, manter a configuração congelada e avaliar a série forward
separadamente é obrigatório.
