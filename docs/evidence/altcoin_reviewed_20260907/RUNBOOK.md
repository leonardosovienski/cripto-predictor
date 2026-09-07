# Objetivo e acompanhamento v6 após revisão

O usuário definiu o objetivo em 07/09/2026: **lucro líquido positivo**, sem comparação com outro investimento e sem preferência de corretora ou moeda. Não pedir novamente escolha de Selic, BTC, cesta ou corretora preferida como condição para continuar a pesquisa.

O critério econômico é terminar com mais dinheiro do que começou, depois dos custos aplicáveis, na mesma moeda. Custos desconhecidos permanecem desconhecidos. As marcas públicas em USDT ainda não certificam lucro líquido em reais, porque conta, conversão e tributação não foram verificadas. Nenhuma taxa específica foi informada pelo usuário. Ele autorizou liberdade de pesquisa, não contas, transferências ou ordens.

O adaptador disponível é Binance spot público. A busca foi ampliada da amostra original para todos os pares USDT atualmente negociáveis, respeitando exclusões declaradas e os mesmos filtros de 90 dias completos, atraso de um dia e liquidez. Outras corretoras e outras criptos são permitidas pelo objetivo; isso não significa que já exista cobertura de todas elas. Não remover critérios de dados ou custos apenas para produzir uma candidata.

O modelo de vizinhos e seus dados de treino continuam fixos. BTC permanece uma entrada estatística usada nas oito características já definidas, e também pode ser candidato; não existe carteira de comparação com BTC, cesta ou Selic nesta versão.

No worktree `work/cripto-v1.2`, executar:

```powershell
.venv\Scripts\python.exe -m scripts.verify_research_runtime
.venv\Scripts\python.exe -m scripts.observe_altcoin_forward --mode tick --base-data-dir '..\altcoin-data' --training '..\altcoin-payoff-results\samples_identity_corrected.json.gz' --data-dir '..\altcoin-reviewed-data' --evidence-dir 'docs\evidence\altcoin_reviewed_20260907'
```

Executar o segundo comando somente se o primeiro retornar código zero. Uma divergência de integridade exige diagnóstico; não ignorar a checagem nem ajustar hashes para aceitá-la.

Horário mantido: domingos às 21h de Brasília, primeira janela 13/09/2026; 12 entradas previstas, última saída 06/12/2026. O computador e o aplicativo precisam estar ativos. A janela de coleta termina 60 minutos depois da âncora. Não retroagir entradas nem substituir saídas ausentes por zero ou por uma cotação escolhida depois. O registro de decisão deve preceder a consulta das ofertas de entrada.

Conferir código de saída, `work/altcoin-reviewed-data/status.json`, livro `ledger.jsonl`, fontes, custos, candidatas e preços ausentes. Se `pilot_finished` for verdadeiro, registrar o balanço descritivo e pausar o próprio acompanhamento pelo recurso de automações. Atualizar `outputs/ACOMPANHAMENTO_CRIPTO.md` em linguagem simples, focando resultado líquido absoluto e suas limitações. Avisar apenas sobre mudança relevante, conclusão, falha ou informação necessária; ficar em silêncio quando nada relevante mudou.

Esta versão usa um livro separado. As versões anteriores permanecem como evidência histórica em seus arquivos e pacotes. A primeira coleta v4 é diagnóstico, não entrada prospectiva. Não ajustar a seleção após observar resultados. Os estudos sintéticos de tamanho de amostra não prometem lucro e não constituem atestação formal. As 12 semanas testam o funcionamento e acumulam dados; não estabelecem automaticamente rentabilidade.


Revisão de 07/09: o teste histórico v5 terminou com 140 semanas em caixa e zero operações. A regra continua sem lucro demonstrado. O piloto mantém essa regra para observação, não para buscar parâmetros até aparecer lucro.

O arquivo observer.lock agora pode continuar existindo com o processo encerrado: a exclusão mútua depende do bloqueio do sistema operacional, liberado quando o processo termina. Não apagar o arquivo para tentar obter acesso paralelo.

Ler observation_quality em status.json: known_due_weeks, missing_due_weeks, cash_due_weeks e active_due_weeks. Nenhuma observação significa lucro desconhecido, não zero. Semanas faltantes nunca são apagadas do denominador. standardized_completed_week_profit_usdt soma apenas semanas conhecidas; standardized_pilot_profit_usdt só existe quando todas as 12 semanas têm resultado. São experimentos semanais com tamanho fixo de 5.000 USDT: não apresentar a soma como saldo de uma conta composta. realized_profit e investor_net_brl_profit continuam null.

Se last_run_error não for null ou o processo sair com erro, comunicar a falha conforme a preferência já registrada. Se pilot_finished for verdadeiro, divulgar também as semanas ausentes e o veredito de qualidade; concluir o calendário não significa validar lucro.

O estudo separado de carry tem cenários históricos positivos após custos assumidos. A antiga rejeição por comparação externa foi revista. Isso não muda o seletor spot nem autoriza futuros, margem ou capital.
