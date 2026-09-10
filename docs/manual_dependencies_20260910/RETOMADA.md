# Retomada manual das dependências

Esta etapa segue a revisão e a integração dos PRs #111 e #110. O dono excluiu **as configurações de segurança da branch**. As checagens de conteúdo e CI antes/depois do merge continuam. O registro vivo permanece em `C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\REVISAO.md`; este arquivo reúne os comandos e contratos necessários à retomada, sem substituir aquele relatório.

## Calendário e identidade das altcoins

Os 542 dias ausentes somados entre 12 pares foram confrontados com anúncios oficiais. Todos os intervalos cabem integralmente entre a interrupção e a reabertura documentadas. Essa é uma classificação retrospectiva sustentada pelos anúncios e pelas consultas anteriores sem observações; **zero candles foram recuperados ou fabricados**. A obrigação de buscar 542 dias de negociação que o par não oferecia deixa de ser uma pendência de coleta.

| Par | Dias | Interrupção → retomada, UTC | Evento / unidades antigas:novas |
|---|---:|---|---|
| BNXUSDT | 5 | 16/02/2023 03:00 → 22/02/2023 08:00 | Troca, 1:100; retomada antecipada em anúncio posterior |
| BTCSTUSDT | 3 | 15/03/2021 07:00 → 19/03/2021 07:00 | Troca, 1:10 |
| COCOSUSDT | 3 | 19/01/2021 02:00 → 23/01/2021 02:00 | Troca, 1000:1 |
| CVCUSDT | 153 | 09/12/2022 03:00 → 12/05/2023 08:00 | Par retirado e relistado |
| DREPUSDT | 3 | 29/03/2021 04:00 → 02/04/2021 04:00 | Troca, 100:1; datas adiadas em anúncio posterior |
| FTTUSDT | 310 | 15/11/2022 04:30 → 22/09/2023 08:00 | Par retirado e relistado; FTT/BUSD não substitui FTT/USDT |
| KEYUSDT | 27 | 10/02/2023 03:00 → 10/03/2023 08:00 | Par retirado e relistado |
| LUNAUSDT | 17 | 13/05/2022 00:40 → 31/05/2022 06:00 | Ticker reutilizado: Terra Classic → Terra 2.0; não é troca por fator único |
| QUICKUSDT | 3 | 17/07/2023 03:00 → 21/07/2023 08:00 | Troca, 1:1000 |
| STRAXUSDT | 7 | 20/03/2024 03:00 → 28/03/2024 08:00 | Troca, 1:10 |
| SUNUSDT | 3 | 14/06/2021 04:00 → 18/06/2021 04:00 | Troca, 1:1000 |
| VIDTUSDT | 8 | 31/10/2022 03:00 → 09/11/2022 08:00 | Datalink → DAO, 1:10 |

O [registro dos eventos](market_events.json) traz as referências oficiais, a data publicada e a distinção de identidade de cada linha. [Entrada preservada](gap_input.json) e [classificação derivada](market_calendar_audit.json) permitem reproduzir a soma:

```powershell
C:\Cripto\CRIPTO.cmd python -m scripts.audit_market_calendar --gaps C:\Cripto\pesquisa-20260909\docs\manual_dependencies_20260910\gap_input.json --output C:\Cripto\operacao\relatorios\calendario-altcoins-nova-verificacao.json
```

O comando recusa sobrescrita e não altera dados. Mantêm-se as exclusões de janelas com gaps e candles parciais, sem recalibrar os estudos congelados. O registro adquirido agora não é um sinal historicamente disponível nem certifica todo o universo, liquidez, possibilidade de manter posições ou regras de conta. Antes de outro uso, separar episódios de negociação; não calcular retorno diretamente entre unidades antigas e novas. Em LUNA, nem um ajuste escalar resolve a troca de ativo. Os 200 fechamentos não padrão permanecem identificados e excluídos onde exigida uma barra diária completa.

## CoinGecko

O endpoint [OHLC](https://docs.coingecko.com/reference/coins-id-ohlc) tem cinco campos, sem volume. O adaptador anterior produzia volume zero para 30m/4h. A reprodução local confirmou o erro; agora o contrato público recusa esses intervalos antes de rede/retry. O roteador pode tentar outro fornecedor de OHLCV e informa indisponibilidade quando nenhum satisfaz o pedido. O fallback diário continua como série de fechamento com volume agregado em USD; não certifica OHLC nem volume de uma bolsa específica. Não foi criado um serviço de preços intradiários sem consumidor.

## Carry: registro separado pronto, observação ainda futura

A janela original de 09/09 foi perdida e seu diário permanece intacto. Foi preparado um registro distinto em `C:\Cripto\operacao\dados\carry-manual-20260912-v2`, com entrada em **12/09/2026, 00:00–01:00 UTC** (11/09, 21:00–22:00 Brasília) e saída 84 dias depois, **05/12/2026, 00:00–01:00 UTC** (04/12 à noite em Brasília). O [protocolo](carry_protocol.json) e o [registro](carry_registration.json) são cópias públicas exatas da preparação local. A data foi escolhida com mais de 24 horas de antecedência; não significa que alguém já se comprometeu a observar a janela.

O novo lançador verifica os bytes do congelamento anterior, runtime Python 3.13.14/httpx 0.28.1, seu próprio código e protocolo. Somente ID, datas e instrução de execução manual mudam. Capital hipotético de 5.000 USDT, orçamento spot de 1.250 USDT, custos, quantidades e política de falhas permanecem os anteriores. Não há registro de entrada, posição financeira, chamadas de rede ou agendamento nesta preparação.

A preparação anterior em `carry-manual-20260912` permanece intacta e foi substituída antes de qualquer coleta para reforçar a conferência de fontes e horários no status offline. Use a pasta `carry-manual-20260912-v2` acima; não apague a anterior ou atualize seus hashes.

Consultar agora, sem rede e sem criar diário:

```powershell
C:\Cripto\CRIPTO.cmd python -m scripts.carry_forward_registration --directory C:\Cripto\operacao\dados\carry-manual-20260912-v2
```

Uma invocação manual futura, dentro da janela, usa `--mode tick`. `--mode preflight` faz apenas diagnóstico e não substitui a entrada. Cada invocação conectada exige a guarda de 28 unidades/dia UTC e consome uma unidade antes da fonte pública, mantendo o máximo interno de 16 requisições/20 MB. Os modos conectados **não foram executados nesta preparação**. Não há tarefa agendada esperando a data.

Se a janela passar sem entrada, `status` informa `MISSED_ENTRY`. Não editar esse registro para empurrar datas nem preencher o diário retrospectivamente. Para outro período, preparar um diretório ainda inexistente com `--mode prepare --start <meia-noite UTC futura>`, pelo menos 24 horas antes, preservar este registro e publicar a nova especificação antes de observar. Para uma falha de congelamento/runtime, restaurar a versão registrada; não atualizar hashes para aceitar código desconhecido. O registro é verificado por integridade relativa, não por assinatura de terceiro.

## LLM/notícias e custos privados

O [desenho de avaliação](llm_evaluation_draft.json) deixa fixados universo, braços, temporalidade, métricas, limite de chamadas e destino dos resultados. É **rascunho de piloto diagnóstico, não experimento ativado nem reabertura de H6**. Ainda precisa congelar o executor completo e a data antes das novas observações. O piloto de 84 dias fornece no máximo 12 blocos semanais não sobrepostos; não certifica poder para afirmar contribuição incremental. Uma avaliação confirmatória posterior exige tamanho amostral justificado e novo período preservado.

O [formulário de custos e execução](operator_inputs.json) especifica unidade, evidência e campo ausente. Valores desconhecidos permanecem `null`; zero só poderá representar um custo comprovadamente zero. Não são pedidos de chaves ou permissão de capital. Custos pessoais, tributação aplicável e preenchimentos reais não podem ser inferidos de candles públicos. As contas históricas e sensibilidades anteriores permanecem úteis no escopo hipotético.

## Recuperação ainda condicionada à fonte

- **Aave:** a nova fonte pública [OnFinality Arbitrum](https://onfinality.io/en/networks/arbitrum) confirmou a rede (chainId 42161), mas recusou a consulta histórica com HTTP 429/JSON-RPC -32029, pedindo chave/acesso ampliado. Foram duas chamadas sem retries e uma unidade da guarda, sem conta criada. Isso comprova restrição de acesso daquela consulta, não ausência universal de arquivo. A sonda dRPC anterior e seus erros ficam preservados. Faltam índice normalizado e liquidez da reserva nos 13 limites semanais; uma série de APY de agregador não substitui esses campos.
- **H5:** além dos backups examinados, a busca em todos os refs Git disponíveis não encontrou banco ou exportação das previsões/inputs antigos. Permanecem necessários os registros originais de mercado, notícias, prompts, respostas e juiz com horários. A busca não cobre contas de terceiros ou objetos Git inacessíveis; não há evidência de que outra cópia esteja disponível.
- **Revogação histórica de credenciais:** a declaração do dono foi mantida. A comprovação do uso/revogação no passado depende dos painéis dos provedores; não publicar chaves ou pedir sua repetição. Não há novo incidente demonstrado.
- **V3/AR3:** os resultados negativos e decisões de não promoção são conclusões de pesquisa, não dependências corrigíveis por instalar uma biblioteca ou afrouxar filtros. Permanecem visíveis.

Essas limitações impedem conclusões específicas de rendimento, causalidade antiga e execução real. A correção técnica não autoriza afirmar lucro melhorado, ativar automações ou mexer na segurança da branch excluída pelo dono.
