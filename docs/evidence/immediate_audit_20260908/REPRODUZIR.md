# Auditoria pública imediata de BTC — 08/09/2026

O protocolo `btc-immediate-public-audit-20260908-v1` foi registrado no commit `46d52b9`; o código foi congelado no commit `9690e3b` antes das novas cotações. O pacote preserva essa rodada finita. Não é um executor de ordens nem uma observação futura de 84 dias.

O histórico cobre 16/06/2026 às 00h UTC até 08/09/2026 às 00h UTC: 84 dias, incluindo 83 dias que já estavam dentro do período histórico consultado. Dados baixados novamente não viram evidência temporal independente. A marca final usa somente a abertura do candle de corte; máxima, mínima e fechamento desse candle ficam excluídos.

A observação ao vivo usa onze momentos espaçados por 30 segundos, cerca de cinco minutos. O primeiro e o último momentos registrados são as únicas referências de abertura/encerramento. Uma falha nesses pontos gera resultado desconhecido; não se escolhe outro ponto depois de ver o preço. Binance spot/perp são as pernas do modelo; OKX spot BTC/USDT é somente uma conferência entre fontes. Não se simula arbitragem entre corretoras.

Requisitos da reprodução usada: Python 3.13.14, httpx 0.28.1 e pytest. No diretório extraído:

```text
python -m pytest -q tests/test_immediate_audit.py tests/test_research_corrections.py tests/test_carry_forward.py tests/test_carry_public.py
python -m scripts.audit_immediate_decimal --data data --protocol docs/evidence/immediate_audit_20260908/protocol.json --output NOVA_AUDITORIA.json
```

O auditor usa apenas a biblioteca padrão, reconstrói os valores a partir das respostas brutas, verifica hashes e o diário e compara contas com Decimal. O cálculo principal usa outra implementação. Ambos são do mesmo autor; a auditoria não é externa. Os testes usam dados sintéticos e não precisam de rede.

Os arquivos `data/results.json`, `data/live_samples.json`, `data/ledger.jsonl`, `data/sources.json` e `data/raw/` preservam resultados, horários, decisões e fontes. `FILES_SHA256.json` cobre os bytes distribuídos. A pasta `intra-hour-check/`, quando presente, contém somente uma consulta pública adicional de funding entre as duas cotações ao vivo, sem mudar as contas congeladas.

Reexecutar `run_immediate_audit` realiza uma nova coleta pública em tempo real e exige um diretório novo. Isso não reproduz os mesmos preços e não deve ser apresentado como a rodada original. Para reprodução idêntica, use somente os arquivos salvos e os comandos offline acima. Não copie esse diário para os observadores prospectivos existentes.

O diário do carry de 84 dias, o diário de altcoins, suas datas e a automação existente permanecem separados. Esta rodada imediata não ativa agendamento nem certifica taxas de conta, tributos, conversão, execução simultânea ou liquidação efetiva.

Fontes técnicas oficiais consultadas: [Binance Spot API](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md), [cálculo de taxas de futuros Binance](https://www.binance.com/en/support/faq/detail/360033544231), [API OKX](https://app.okx.com/docs-v5/en/). A tabela pública exemplifica taxas; não identifica a tarifa efetiva de uma conta.
