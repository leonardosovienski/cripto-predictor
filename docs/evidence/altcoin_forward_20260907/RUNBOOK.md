# Piloto semanal de observação — 7 de setembro de 2026

Este procedimento registra decisões hipotéticas e preços futuros. Não é um adaptador de ordens, uma recomendação de compra ou uma certificação de lucro. A regra de seleção v2 permanece fixa. A promoção formal continua bloqueada pelas pendências descritas no protocolo.

Executar no worktree `work/cripto-v1.2`, usando seu Python local:

```powershell
.venv\Scripts\python.exe -m scripts.observe_altcoin_forward --mode tick --base-data-dir '..\altcoin-data' --training '..\altcoin-payoff-results\samples_identity_corrected.json.gz' --data-dir '..\altcoin-forward-data'
```

O agendamento é domingo às 21h em America/Sao_Paulo, equivalente à segunda-feira 00h UTC. Primeiro registro em 13/09/2026 às 21h; última entrada em 29/11; última observação de saída em 06/12 às 21h. São 12 janelas de entrada e 13 execuções previstas. Manter computador ligado e aplicativo aberto. O agendamento local não promete pontualidade nem disponibilidade contínua.

`tick` usa o relógio real: coleta dentro da primeira hora após a âncora, grava a decisão no livro antes de consultar ofertas de entrada e, na semana seguinte, observa ofertas de saída. Uma execução fora da janela marca a observação perdida; não procura retrospectivamente um preço favorável. Um resultado sem preço fica pendente/censurado, com seu peso original. Não contar registros ausentes como zero retorno da estratégia. Caixa de referência sem posição tem zero rendimento em USDT, não em reais.

Arquivos operacionais em `work/altcoin-forward-data`: `ledger.jsonl`, `status.json`, `snapshots/` e `raw/`. A cadeia de hashes detecta alterações simples e duplicação; ela é local e não fornece carimbo de tempo externo independente. Cada fonte guarda hora real de obtenção. A data publicada de um anúncio não substitui essa hora. Os catálogos completos obtidos têm títulos e links; interpretar todos os efeitos de eventos continua sendo uma pendência.

Após cada execução, conferir código de saída, integridade da cadeia, contagens de decisões/saídas, alterações no estado dos pares, candidatas, custos simulados e motivos de dados ausentes. Não alterar a regra quando ela ficar em caixa. Guardar custos da conta como desconhecidos até confirmação verificável; nenhum segredo ou chave é necessário para este piloto. Não tocar nos coletores de produção, nos registros congelados, nas famílias HMM/funding/OI ou no capital.

Se uma execução falhar, preservar os arquivos e informar o motivo. Um arquivo `observer.lock` remanescente requer primeiro verificar se seu processo ainda existe; não apagar o arquivo cegamente e não sobrepor escritores. Corrigir defeitos de operação com uma versão documentada e novos hashes antes de decisões posteriores. Nunca apagar ou reconstruir observações antigas como se fossem novas.

Quando `status.json` indicar `pilot_finished: true`, produzir balanço de viabilidade e pausar o próprio acompanhamento pelo recurso de automações do Codex. Sem avisos repetidos quando não houver mudança relevante. Avisar sobre conclusão, falha, candidata nova, mudança relevante de dados/custos ou informação necessária do usuário. Comparar as marcas à cesta contemporânea e BTC no mesmo período, mantendo custos, moeda e ausência de dados explícitos.

As 12 semanas medem funcionamento e fornecem novas observações. Não constituem, por si só, prazo suficiente para demonstrar lucro. `design.json` contém apenas controles sintéticos e cenários de tamanho de amostra. Não reutilizar a atestação do modelo antigo para aprovar este modelo.
