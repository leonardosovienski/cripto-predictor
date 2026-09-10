# Continuar o projeto Cripto

**Atualização mais recente:** [dependências executadas em 10/09](docs/manual_dependencies_20260910/EXECUCAO.md). Histórico Aave recuperado, cálculo de custos executável e executor/avaliador LLM implementado, testado e congelado. Confira os checks e o SHA atual; os cortes dos ZIPs antigos permanecem históricos.

Comece pelo estado Git real e por [RESOLUCAO_PR110.md](docs/continuity_20260909/RESOLUCAO_PR110.md). O código incorpora o PR #111 (909724e), que concluiu a revisão de engenharia. O #110 foi corrigido para preservar essa implementação e completar a continuidade. A captura intermediária de 22:31 UTC permanece no histórico 4ae9e3d.

A etapa posterior está em [retomada manual das dependências](docs/manual_dependencies_20260910/RETOMADA.md): explica os 542 dias de gaps dos 12 pares, corrige volume intradiário ausente e prepara uma janela separada de carry. Segurança da branch foi excluída pelo dono. Os ZIPs de continuidade mantêm seus cortes anteriores; os arquivos desta etapa estão diretamente no Git.

1. Leia [NEXT_CHAT_PROMPT.md](docs/NEXT_CHAT_PROMPT.md), preservado como mandato, e [a revisão de 09/09](docs/REVISAO_COMPLETA_20260909.md).
2. Confira os [pacotes e comandos de recuperação](docs/continuity_20260909/README.md), o [manifesto](docs/continuity_20260909/MANIFEST.json) e as [dependências restantes](docs/continuity_20260909/DEPENDENCIAS.md).
3. Confira o SHA atual e os quatro jobs de CI no GitHub. Uma conclusão de outro commit não valida este checkout.

Nesta máquina, código e operação ficam em C:\Cripto; C:\Cripto\CRIPTO.cmd é a entrada configurada. Não extraia arquivos sobre o banco operacional ou os snapshots históricos. O backup final de diagnóstico é separado e contém três previsões, um snapshot de mercado e um registro de inputs. Os dois bancos publicados representam instantes diferentes e não devem ser mesclados automaticamente.

O pacote reports-final-review-20260910.zip inclui a revisão completa, comprovantes finais e pós-merge do #111, scripts e a revisão do #110 anterior à correção. O estado corretivo posterior está em RESOLUCAO_PR110.md e no histórico/checks do próprio PR. Os horários de captura são explícitos no manifesto.

O piloto carry original perdeu sua janela de entrada. Um registro manual separado foi preparado para 12/09/2026 00:00 UTC; ainda não tem observações. Nenhum observador recorrente, agendamento ou capital foi ativado.

Pedido de retomada: leia estes documentos, confirme o estado real, preserve dados e definições congeladas, execute apenas pendências compatíveis com os limites autorizados e atualize o registro de evidências. Não repita coletas idênticas já malsucedidas nem substitua dados ausentes por estimativas.
