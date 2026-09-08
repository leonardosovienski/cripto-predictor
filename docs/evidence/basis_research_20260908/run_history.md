# Histórico da rodada

- Registro inicial: duas regras BTC, seis cenários contábeis. Nenhuma avaliação econômica nova realizada. Sondagem anterior inspecionou apenas disponibilidade, nomes de arquivos e datas de vencimento; preços de liquidação brutos ficaram em cache sem avaliação.

- v1: três cenários BR1 salvos; execução interrompida ao interpretar a nota contábil como cenário. Corrigida apenas a leitura do protocolo. v2 repete a mesma regra e completa BR2. Código v1 e resultados parciais preservados. Após correção: 37 testes, Ruff e Pyright aprovados.

- v2 concluída: BR1 +230,17 / +110,07 / +78,42 USDT, cinco hedges; BR2 zero entradas e zero resultado. Auditoria Decimal aprovada. Quatro arquivos v1 idênticos após a correção.
- Diagnóstico: 12 fotografias públicas, sem ordens; um cálculo adicional sobre os mesmos dados dimensiona a compra bruta para o hedge líquido após comissão em BTC. Nenhum retorno histórico ou parâmetro foi alterado.

- Reprodução a partir do ZIP extraído, com conexões de rede bloqueadas: nove arquivos históricos idênticos, auditoria PASS, planos das cotações idênticos e 28 testes novos aprovados no pacote. Essa repetição de verificação não acrescentou hipótese ou parâmetro. Pacote de código/dados: commit 23be49d.
