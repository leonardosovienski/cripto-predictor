# Evidência datada da conferência e recuperação — 10/09/2026

Esta é uma captura pública da etapa posterior ao PR #116 (`ac4184e`), não um segundo registro vivo. O registro canônico permanece em `C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\REVISAO.md`. O [snapshot desse relatório](review_snapshot.md) conserva seu texto e os caminhos locais exatamente como estavam; links relativos dele exigem a árvore local da revisão. Para navegar na publicação, use este índice e a [conferência resumida](../../CONFERENCIA_CHAT_20260910.md).

- [Conferência das afirmações](conversation_reconciliation.json): recorte de mensagens efetivamente relido, decisões e referências. A conversa privada não está publicada.
- [Snapshot aplicado](snapshot/applied.json), [controles e backup lógico](snapshot/prepared.json), [payload reproduzível](snapshot/payload.json): 200 barras fechadas e features v4, recebimento original de 10/09 02:12 UTC e processamento separado. Nenhum SQLite operacional foi publicado.
- [Manifesto original dos recibos](original_receipts/result.json): incluídos apenas os dois recibos públicos Binance de mercado/relógio; textos de notícias e respostas LLM permanecem locais. Os hashes dos demais recibos são referências históricas, não arquivos omitidos silenciosamente do manifesto desta publicação.
- [Comparação Aave preparada](aave_second_source/protocol.json), [replay offline](aave_second_source/offline_validation.json), [status](aave_status.json): 38 pontos, no máximo 350 RPCs, uma unidade de ingestão, sem retries. Nenhuma resposta da segunda fonte foi obtida nesta etapa.
- [Carry](carry_status.json), [LLM](llm_status.json), [limites de acesso](access_check.json) e [rotas históricas/custos](historical_recovery_routes.json).
- [Verificação operacional](verification.json) e [comprovantes anteriores de integração](prior_integrations/): resultados pertencem às versões/datas declaradas, não ao futuro.

`executed_sources/*.source` preserva os programas locais exatos usados ou preparados, com seus caminhos originais. Eles são evidência de execução e não novas entradas do pacote instalado. A reprodução depende da árvore original indicada e dos recibos/históricos anteriores; não copiar scripts de escrita sobre bases existentes nem alterar seus protocolos para contornar a guarda. O [protocolo Aave](aave_second_source/protocol.json) vincula os hashes dos inputs e código originais.

`manifest.json` cobre todos os arquivos desta pasta, exceto ele próprio. Configuração privada, chaves, bancos operacionais/de orçamento, caches, logs brutos, textos de notícias/respostas LLM e transcript do chat não fazem parte da publicação. A fonte é pública, mas o segundo operador pode compartilhar infraestrutura: resultado igual não comprovará automaticamente independência dos nós.

O frescor do snapshot encerra em 11/09/2026 02:00 UTC. Horários futuros exigem execução manual dentro do protocolo; nada foi agendado. Lucro pessoal ou prospectivo continua não validado.
