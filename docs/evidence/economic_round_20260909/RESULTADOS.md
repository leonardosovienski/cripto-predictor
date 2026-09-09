# Rodada econômica de 09/09/2026

Registro canônico da rodada `ECONOMIC-ROUND-20260909-R1`. O [protocolo](protocol.json) foi registrado antes de consultar novos resultados de mercado. Base: `48fd271`; trabalho separado em `C:\Cripto\pesquisa-20260909`, branch `research/economic-round-20260909`.

Prioridade: medir juros-base e resgate de USDC nativo no Aave V3 Arbitrum, sem alavancagem. Alternativa condicionada a bloqueio/rejeição: isolar giro evitável nas renovações AR2 BTC. Nenhuma das linhas autoriza capital ou altera os observadores.

Estado inicial: H1 registrada; H2 estacionada. Orçamento: uma reserva, uma janela histórica de 84 dias, até 13 observações semanais, até 500 chamadas RPC públicas contando falhas e oito GETs de apoio. H2, se ativada: um ativo/sinal e dois tratamentos de execução sobre dados já existentes. Capital e custos são cenários explícitos; taxas pessoais, impostos e preferências de risco não foram presumidos.

Comandos, fontes, tentativas, resultados, validações e próxima decisão serão registrados aqui durante a execução. A migração anterior foi validada; o snapshot `522de73` não continha as entregas #105/#106, que já estão incorporadas à base escolhida.

H1: seis chamadas públicas contadas, incluindo falhas. O nó oficial confirmou Arbitrum e um bloco atual fresco, mas o `eth_call` histórico retornou `missing trie node`; o único endpoint alternativo falhou em DNS. Estado: **bloqueada por acesso histórico**, sem conclusão sobre rentabilidade e sem substituir a janela ou a reserva por resultados favoráveis. Respostas originais preservadas em `work/h1-rpc-probe-v1`.

H2 foi ativada conforme a condição registrada. O [dossiê de giro](../../reopen_dossiers/ar2_renewal_turnover_20260909.json) registra o motivo material, os resultados publicados vistos no reconhecimento, as contas de limite superior e os critérios anteriores à nova medição. A primeira medição não retreina nem altera o sinal AR2: testa se a economia máxima de renovação poderia mudar a conclusão adversa.
