# Consolidação das branches — 08/09/2026

Pedido vigente do dono: publicar o trabalho na main, conferir todas as branches e manter somente main. Este pedido substitui a restrição anterior de não alterar main; os worktrees operacionais, dados e ambientes continuam preservados.

`reconciliation.json` registra 21 referências locais/remotas anteriores à limpeza, seus commits e a comprovação de ancestralidade no histórico consolidado. Inclui referências locais a branches que já haviam sido apagadas no servidor. Na consulta inicial, o GitHub tinha quatro branches; não havia PR aberta.

## Decisões de integração

| Histórico | Tratamento |
|---|---|
| Pesquisa 2668865 e execução fbf4c71 | Incorporadas integralmente; todos os commits ficam alcançáveis pela main. |
| main remota 816341c | Mantido o digest Docker c6ead215, que era a única atualização remota além da pesquisa. |
| 07fc6e6, 4ecf410, 0d5ef3, b864ac1 | `git cherry` confirmou zero patches exclusivos e equivalência dos patches já aplicados. Merge de ancestralidade sem substituir o código posterior. |
| f0ed60f, correção temporal H6 | A correção e seus testes já estavam presentes; conflito apenas no digest Docker antigo, resolvido mantendo o atual. |
| d9d90b6, auditoria antiga | Recursos já reaplicados e ampliados. Preservados DSR estrito, migração de imutabilidade, detecção de adulteração, planilha vazia, contabilidade por eventos e corte temporal. |
| a19ed0e, runbook H6 | Preservadas as correções posteriores do agendamento, backup e retirada do prompt que consumia o comando seguinte no PowerShell. |
| 4129035, revisão operacional | Descoberta de ativos, alerta de status e contexto de poder já estavam presentes. Incorporados o registro histórico do incidente SerpAPI e a mensagem de pré-requisito do wheel. Mantidos os encerramentos científicos posteriores. A proposta antiga de DSR H6 não substitui a recusa atual de calcular variância com Sharpes sem unidade comprovada. |
| 10024a3, dependências | Ops 4.1 já incorporado; mantida a migração posterior para Core 3.2 em todos os pins. O diagnóstico de migração pendente em 06/09 continua no histórico, superado pela implementação de 07/09. |
| 8bf0977, macro/FRED | Mantidos o calendário mais completo, a coluna correta observation_date e os dias úteis. Cinco scripts avulsos de diagnóstico foram preservados em `legacy_debug/*.py.txt`: possuem caminhos fixos e não devem ser executados como ferramentas atuais. |
| Demais referências | Já eram ancestrais; nenhuma alteração adicional necessária. |

Os merges conciliam trabalho divergente; não significam que versões obsoletas de cada arquivo foram copiadas sobre as correções atuais. Cada versão original continua recuperável pelo seu commit na main.

## Bytes congelados e entregas

Uma criação de worktree com `core.autocrlf=true` alterou finais de linha e fez falhar os hashes dos programas científicos. `.gitattributes` agora impede conversão nos arquivos congelados e manifestos. Os bytes foram recuperados das cópias originais e conferidos contra os SHA256 já publicados, sem alterar qualquer hash esperado para aceitar diferenças. O novo teste confere os arquivos reais do checkout, cobrindo também Linux no CI.

Trinta arquivos de entrega desta pesquisa, incluindo os pacotes de código e dados, estão em `docs/session_archive_20260908/deliverables`, com manifesto próprio. As afirmações antigas de "sem push" ou nome de branch nesses arquivos descrevem sua data de emissão; a continuidade vigente está em `docs/SESSION_HANDOFF_20260908.md`.

O primeiro push foi recusado sem alterar a main remota: o sdist padrão incluiu os arquivos de recuperação e atingiu 437 MiB. O empacotamento agora lista somente as fontes necessárias ao build, e `dist/` deixa de ser versionado. O contexto Docker também exclui a documentação volumosa. O pacote fonte e o wheel continuam sendo construídos e verificados pelo CI; as entregas de pesquisa permanecem versionadas separadamente. Somente o trecho de consolidação ainda não publicado foi reorganizado para retirar o blob excessivo; nenhum commit das branches originais foi reescrito.

## Alterações locais não commitadas

O worktree antigo `git-final` continha alterações locais e arquivos sem commit. Eles foram preservados no lugar e em ZIP com 337 arquivos verificados por hash, junto com `fred_test.csv` não rastreado no checkout principal. Não foram publicados como código vigente: a comparação com a branch v2 identifica versões preliminares, formatação e correções já substituídas. A remoção de referências de branches não elimina esses arquivos.

Há também um Git bundle local validado, com o histórico completo das referências anteriores. Os hashes dos dois backups constam em `reconciliation.json`. Os backups estão na pasta de entregas da tarefa; não foram adicionados ao repositório público.

O fechamento e a limpeza só devem ser declarados concluídos depois de verificar o push, o CI do commit final, a main local/remota e a ausência de outras branches. Os diretórios dos observadores permanecem em seus commits originais, com HEAD destacado, para preservar código, hashes e caminhos.
