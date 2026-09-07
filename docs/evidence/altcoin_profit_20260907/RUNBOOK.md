# Objetivo e acompanhamento v4

O usuário definiu o objetivo em 07/09/2026: **lucro líquido positivo**, sem comparação com outro investimento e sem preferência de corretora ou moeda. Não pedir novamente escolha de Selic, BTC, cesta ou corretora preferida como condição para continuar a pesquisa.

O critério econômico é terminar com mais dinheiro do que começou, depois dos custos aplicáveis, na mesma moeda. Custos desconhecidos permanecem desconhecidos. As marcas públicas em USDT ainda não certificam lucro líquido em reais, porque conta, conversão e tributação não foram verificadas. Nenhuma taxa específica foi informada pelo usuário. Ele autorizou liberdade de pesquisa, não contas, transferências ou ordens.

O adaptador disponível é Binance spot público. A busca foi ampliada da amostra original para todos os pares USDT atualmente negociáveis, respeitando exclusões declaradas e os mesmos filtros de 90 dias completos, atraso de um dia e liquidez. Outras corretoras e outras criptos são permitidas pelo objetivo; isso não significa que já exista cobertura de todas elas. Não remover critérios de dados ou custos apenas para produzir uma candidata.

O modelo de vizinhos e seus dados de treino continuam fixos. BTC permanece uma entrada estatística usada nas oito características já definidas, e também pode ser candidato; não existe carteira de comparação com BTC, cesta ou Selic nesta versão.

No worktree `work/cripto-v1.2`, executar:

```powershell
.venv\Scripts\python.exe -m scripts.observe_altcoin_forward --mode tick --base-data-dir '..\altcoin-data' --training '..\altcoin-payoff-results\samples_identity_corrected.json.gz' --data-dir '..\altcoin-profit-data' --evidence-dir 'docs\evidence\altcoin_profit_20260907'
```

Horário mantido: domingos às 21h de Brasília, primeira janela 13/09/2026; 12 entradas previstas, última saída 06/12/2026. O computador e o aplicativo precisam estar ativos. A janela de coleta termina 60 minutos depois da âncora. Não retroagir entradas nem substituir saídas ausentes por zero ou por uma cotação escolhida depois. O registro de decisão deve preceder a consulta das ofertas de entrada.

Conferir código de saída, `work/altcoin-profit-data/status.json`, livro `ledger.jsonl`, fontes, custos, candidatas e preços ausentes. Se `pilot_finished` for verdadeiro, registrar o balanço descritivo e pausar o próprio acompanhamento pelo recurso de automações. Atualizar `outputs/ACOMPANHAMENTO_CRIPTO.md` em linguagem simples, focando resultado líquido absoluto e suas limitações. Avisar apenas sobre mudança relevante, conclusão, falha ou informação necessária; ficar em silêncio quando nada relevante mudou.

Esta versão usa um livro separado. As versões anteriores permanecem como evidência histórica em seus arquivos e pacotes. A primeira coleta v4 é diagnóstico, não entrada prospectiva. Não ajustar a seleção após observar resultados. Os estudos sintéticos de tamanho de amostra não prometem lucro e não constituem atestação formal. As 12 semanas testam o funcionamento e acumulam dados; não estabelecem automaticamente rentabilidade.
