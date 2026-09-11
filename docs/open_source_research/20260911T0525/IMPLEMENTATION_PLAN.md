# Plano executado e backlog

## Top 10 transfers e top 5 implementados

1. G01 — ampliar métricas nativas para painel transversal; entregue.
2. G02 — implementar composição de filtros com versões conhecidas; entregue.
3. G03 — API de split temporal por intervalos/availability; entregue.
4. G04 — cenário de reservas e caixa spot, preservando execução nativa; entregue sintético.
5. G05 — workflow e registro local imutável; entregue e integrado à CLI.
6. G06 — adapter opcional de otimização: validar primeiro carteira de dois ativos com solução analítica e restrições; baseline equal-weight + risco nativo. Não exige backtest vencedor.
7. G07 — contrato de processadores fit/infer por fold: teste de prefixos antes de qualquer modelo novo.
8. G08 — comparação/calibração de fila e latência: primeiro replay controlado com recibos e hipóteses explícitas; sem chamar fill imposto de execução observada.
9. G09 — seleção e remoção multi-instrumento: antes de engine completo, eventos sintéticos com instrumento removido e posição remanescente.
10. G10 — fixture Alphalens em ambiente opcional: igualdade em grupos/ties/bins definidos; diferenças semânticas explícitas.

## Implementação concluída

Pacote `GarimpoInvestimentos/research/`, sete arquivos Python, README e uma bateria de testes. A CLI existente despacha `research` antes de carregar o pipeline. O workflow aceita JSON fornecido, roda análises independentes e registra entradas/resultados/hashes. Não mistura automaticamente o universo com o painel, evitando seleção retrospectiva silenciosa.

Dependências obrigatórias novas: zero. Spearman e atomic I/O reutilizados nativamente; residualização usa NumPy já disponível no extra science. SciPy é referência de teste existente. Não foram instalados pandas, MLflow, Qlib, Hummingbot, Freqtrade ou solver. A opção de reimplementação pequena evita incorporar um framework inteiro para funções delimitadas.

Critério de entrada cumprido: contrato explícito + casos negativos + referência calculável + demonstração CLI + verificação de empacotamento. Critério econômico separado: nenhum resultado deste toolkit remove bloqueios de dados F01–F05 nem reabre hipóteses encerradas.

## Rejeições de integração nesta rodada

- Copiar código GPL do Freqtrade para o pacote proprietário: rejeitado; absorvido apenas conceito geral de filtros.
- Substituir lifecycle/risk/book nativos por Hummingbot: rejeitado; capacidades já existem e integração não demonstrou benefício.
- Instalar MLflow server/Qlib stack para cinco análises locais: rejeitado neste escopo por custo sem ganho medido.
- Migrar todo engine para Lean/.NET ou Nautilus: rejeitado neste escopo; nenhum workload demonstrou necessidade.
- Tratar tokens com “USD” no nome como saldo intercambiável: rejeitado; moedas e venues permanecem separados.
- Tratar resultado de fill imposto como prova de liquidez ou queue position: rejeitado como inferência inválida.

Backlog restante ordenado: G06, G07, G10, G08, G09, G11, G12, G13, G14, G15, G17, G16, G18, G20, G19. A ordem de execução pode colocar G10 antes de G08 pelo custo; não é nova rodada de discovery.
