Quero evoluir meu projeto de pesquisa em criptomoedas para encontrar uma estratégia com lucro líquido mensurável e evidência confiável. Parta do trabalho existente, implemente melhorias justificadas e execute os testes históricos necessários.

Projeto:
C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2

Base da revisão econômica: commit 07794ac. O encerramento completo desta sessão está na tag local cripto-session-20260907-final, na branch codex/cripto-v1-2-execution-20260907. Verifique o HEAD atual antes de trabalhar; os 1.045 testes se referem à revisão de código, e o encerramento posterior acrescenta documentação e arquivos de recuperação.

Leia primeiro docs/SESSION_HANDOFF_20260907.md nesse repositório e depois:
C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2\docs\PROJECT_STATE_20260907.md

Relatório da revisão:
C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2\docs\session_archive_20260907\deliverables\CRIPTO_REVISAO_FINAL.md

Confira também os protocolos, o histórico de hipóteses, os dados preservados e o estado atual do acompanhamento.

CONTEXTO DO ÚLTIMO CHECKPOINT

- A revisão técnica terminou com 1.045 testes aprovados. Docker e CI remoto ficaram sem validação.
- O seletor atual de altcoins não selecionou nenhuma operação em 140 semanas históricas: lucro simulado zero.
- O carry de BTC apresentou +54,84 USDT e o de ETH +34,62 USDT em um ano, cada cenário usando separadamente 5.000 USDT hipotéticos.
- Esses resultados de carry descontam taxas e deslizamento assumidos. Execução, margem, custos reais, conversão e impostos ainda não estão certificados.
- A rejeição antiga do carry dependia de uma comparação externa que eu retirei.
- Existe um observador semanal de pesquisa, perfil v6 altcoin_reviewed_20260907. A automação observar-altcoins-semanalmente estava ACTIVE e vinculada ao chat antigo no encerramento. Não presuma que continua funcionando depois que esse chat for apagado. Preserve seus registros e verifique seu estado atual.
- O adaptador existente cobre Binance spot/USDT. Liberdade de escolha de corretora e moeda não significa cobertura universal já implementada.
- Ainda não há lucro real comprovado.

OBJETIVO

Quero lucro líquido positivo após os custos aplicáveis, na mesma moeda. Não exijo superar Selic, Bitcoin, uma cesta ou qualquer outro investimento. Você pode escolher moedas, corretoras e abordagens de pesquisa; não precisa me pedir novamente essas escolhas.

TRABALHO AUTORIZADO

1. Identifique o que impede as estratégias atuais de produzir resultados úteis: ausência de sinal, filtros inadequados, custos, dados ou execução.

2. Escolha poucas hipóteses justificadas economicamente. Você pode substituir o seletor atual ou desenvolver outra abordagem. Avalie o carry pelo objetivo de lucro absoluto e por sua viabilidade de execução.

3. Antes de avaliar cada variante, registre sua especificação, parâmetros, critérios de decisão e limite de tentativas. Preserve todos os resultados, inclusive negativos.

4. Implemente e execute os testes retrospectivos. Use separação temporal adequada e impeça informações futuras de influenciarem decisões. Trate migrações, deslistagens, liquidez, custos e observações ausentes explicitamente.

5. Os períodos já consultados continuam sendo pesquisa adaptativa. Não os apresente como validação independente. Reserve evidência nova para confirmação futura, enquanto conclui a investigação histórica possível agora.

6. Meça lucro/prejuízo, operações, exposição, semanas em caixa, perdas máximas, sensibilidade aos custos e concentração dos ganhos. Testes de software aprovados não comprovam rentabilidade.

7. Trabalhe em um worktree separado para preservar o observador existente. Versione qualquer atualização posterior e mantenha a evidência anterior. Não reabra silenciosamente famílias científicas congeladas.

8. Conclua as mudanças justificadas, valide-as e entregue código, dados, decisões e resultados reproduzíveis.

LIMITES

Trabalhe sozinho, sem coordenar outros agentes. Use dados públicos e recursos disponíveis. Não envie ordens, movimente dinheiro, use contas autenticadas ou contrate serviços pagos. Os 5.000 USDT são apenas uma referência de simulação.

Não force entradas nem escolha custos favoráveis para fabricar lucro. Resolva decisões técnicas rotineiras autonomamente; pergunte apenas quando faltar uma informação indispensável.

ENTREGA

Explique em português simples:
- O que mudou e por quê.
- Quais hipóteses foram testadas.
- Quanto cada uma ganhou ou perdeu nas condições declaradas.
- Se o resultado permanece positivo sob custos e condições desfavoráveis plausíveis.
- O que está demonstrado e o que continua desconhecido.

Se nenhuma abordagem demonstrar lucro confiável, diga isso claramente. Quero progresso concreto e uma conclusão sustentada pelos resultados.

CONTINUIDADE SEM O CHAT ANTIGO

As decisões, limitações, resultados, arquivos de entrega e dados de pesquisa estão preservados no Git. O documento original de Downloads já não estava disponível no encerramento; não afirme que o releu. Diferencie registros históricos de instruções atuais. As exigências antigas de comparação externa e a proibição de novos testes retrospectivos foram superadas pelos meus pedidos posteriores; as evidências antigas e as famílias congeladas continuam preservadas.

Ao iniciar esta nova tarefa, cuide da transferência do acompanhamento semanal para ela: procure a automação observar-altcoins-semanalmente e prefira atualizar seu destino para esta tarefa, preservando o horário, o prompt, os caminhos, as notificações e os registros. Use o recurso de automações. Se a antiga já não existir, recrie uma única automação nesta tarefa com a configuração documentada em docs/session_archive_20260907/automation_snapshot.json. Confira o vínculo e a leitura dos arquivos antes de afirmar que a transferência funcionou. Não crie um cron independente como substituição silenciosa. Não retrodate janelas perdidas.

O acompanhamento é domingo às 21h de Brasília, primeira entrada prevista em 13/09/2026, última saída em 06/12/2026. Avise somente sobre mudança relevante, falha, conclusão ou informação indispensável. Preservar o piloto fixo é compatível com pesquisar novas regras separadamente.

Os caminhos originais dos dados são irmãos do repositório, sob work/: altcoin-data, altcoin-payoff-results, altcoin-reviewed-data e altcoin-retro-data. Criar um worktree em outro lugar não copia esses diretórios nem a .venv; resolva explicitamente os caminhos dos novos experimentos. Não aponte uma regra alterada para o ledger do observador atual.

Se a pasta original estiver indisponível, o Git comum está em C:\Users\Superleo13\cripto-predictor\.git. Também há uma cópia independente em C:\Users\Superleo13\Documents\CriptoBackup\2026-09-07\CRIPTO_SESSAO.bundle. Clone o bundle em um diretório novo usando a tag cripto-session-20260907-final; não altere a main nem sobrescreva outra pesquisa.

Leia SESSION_HANDOFF_20260907.md para restaurar os dados preservados, verificar os hashes e reproduzir os resultados. A restauração para reprodução offline não migra automaticamente caminhos absolutos do ledger nem reativa a automação. O código congelado pode depender de bytes exatos e finais de linha; use as cópias originais nos pacotes quando necessário, sem recalcular hashes para aceitar diferenças.

Esta sessão fez commits locais. Não suponha que houve push para o GitHub. Não dependa da memória, do título nem do histórico do chat antigo para prosseguir.
