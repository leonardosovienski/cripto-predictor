# Auditoria ampliada de 10/09/2026

Esta etapa corrige defeitos adicionais encontrados depois dos PRs #110–#114. A base real de desenvolvimento foi `ffd6c327e2d323758f6ab6abac4ab15ef5ca0881`, conferida com `origin/main`. O checkout de correção está em `C:\Cripto\auditoria-ampliada-20260910`; o operacional continua em `C:\Cripto\pesquisa-20260909`. A integração e seus SHAs/checks finais ficam no [registro vivo](C:/Cripto/operacao/relatorios/REVISAO_COMPLETA_20260909/REVISAO.md), seção 16, para não confundir a base com o resultado.

O resultado é engenharia de pesquisa corrigida, com limites econômicos explícitos. Não há operação do dono, autorização de capital ou lucro futuro validado. A extensão histórica Aave continua sendo o [resultado condicional já documentado](AAVE_VALIDACAO_20260910.md), com custos de cenário e uma fonte RPC. Nenhum ajuste da V3 transforma esse resultado em validação de trading.

## Evidências e nova linha de base

Antes de editar, `expansion_baseline01` executou a instalação com todos os extras, Ruff, formatação, Pyright, segredos, build, pacote e suíte com cobertura: **1.394 testes aprovados, um skip de symlink por privilégio do Windows**, sem falhas. A linha de base existe separadamente dos testes da correção.

As reproduções `expansion_before3`, `expansion_before4` e `expansion_before5` registraram, respectivamente, 49 falhas/3 aprovações, 12 falhas e 6 falhas/2 aprovações. São casos de teste, não contagem de causas independentes. `expansion_anchor_before` acrescentou duas falhas em quatro casos. Suítes intermediárias que falharam estão preservadas. A validação conjunta final, hashes de fontes, XML, cobertura e resultados dos quatro jobs no PR e no `main` estão no registro vivo; resultados intermediários não certificam a versão final.

A cobertura de testes segue `coverage-runtime.ini`; a tipagem segue o escopo configurado do Pyright. Nenhuma porcentagem de cobertura mede leitura manual integral do repositório. Os testes usam credenciais sintéticas e saídas em `C:\Cripto`. Não se atualizou snapshot científico para tornar um teste verde.

## Correções e contratos alterados

| Fluxo | Defeito e consequência | Correção e evidência de regressão |
|---|---|---|
| Ordens, fills e reconciliação | Repetição ou conflito podia alterar a posição; reconciliação não confrontava todos os campos econômicos; quantidades pequenas podiam desaparecer | Identidade, tempo UTC, finitude, quantidade, preço, taxa e liquidez validados; replay exato idempotente, conflito recusado; contratos e ledger testados |
| Livro e coleta de microestrutura | Snapshot inválido podia deixar estado parcialmente alterado; reconexão deixava tarefas/estado; leitura densa perdia identidade e decodificava todo o histórico | Atualização atômica, reset de sessão, encerramento de tarefas, cobertura por minuto/sequência e consultas limitadas; compactação compara conteúdo antes de remover linhas verificadas |
| Feature Store e CSVs | Conflitos no mesmo lote/vintage eram ignorados, ou a gravação ficava parcial | Transação serializa comparação e inserção; valores/metadados conflitantes recusados; CSVs validam símbolo, chave temporal, finitude e paginação antes de escrita atômica |
| Arquivos e manifestos | JSON inválido podia ser descartado; concorrência perdia atualizações; um manifesto público inválido podia ser substituído | Locks Windows/POSIX e substituição atômica; rejeição de chaves JSON repetidas/NaN; estado corrompido preservado; publicação exige cadeia válida e continuidade com o manifesto anterior |
| Cadeia de previsões | Inserção não selada antes da ponta não era detectada | Verificação recusa inserção retroativa; selagem atômica; manifesto `null`/corrompido ou de outro histórico bloqueia publicação do H6 |
| Binance Vision | Arquivo chamado spot era baixado do namespace de futuros; cache não revalidava checksum; spot de 2025+ tinha unidade diferente | Namespace spot explícito, conversão de microssegundos para ms, checksum obrigatório inclusive no cache, recibo/hash da resposta e novo nome `spot_binance_1h.csv` |
| Disponibilidade de fontes | Data de observação era usada como publicação; caches/revisões podiam dar falsa causalidade | DXY, BCB, Fear & Greed, derivativos e calendário registram a versão recebida. Histórico sem disponibilidade comprovada não serve para conclusão causal. Fear & Greed usa TTL monotônico e cópias |
| Alinhamento e features | Revisão de observação velha substituía observação mais recente; janelas descontínuas/abertas contaminavam indicadores | Escolha por observação e versão disponível, rejeição de lacunas materiais, 24 retornos/25 fechamentos para volatilidade; RSI constante=50; versão diária `daily-v4-audited` |
| HMM, sinais e cache | Cache podia reutilizar treinamento diferente; refit malsucedido deixava estado misto; sinal/configuração mudava sem identidade nova | Hash dos dados de treino, schema do modelo 2, fit transacional, cache/escrita atômicos, sinal imutável e hash de parâmetros; schema de sinal 3.2.0 e modo de replay explícito |
| Harness, DSL e H8 | Empates davam Spearman incorreto; zero comparações podia aprovar equivalência; lag mudava comprimento; alvo era deslocado por índice | Ranks médios, amostra/duplicatas/finite validados, receitas rejeitadas na construção, lag preserva tamanho, alvo pelo timestamp/horizonte exato e histórico com escrita serializada |
| Backtest V3 | Retorno log usado como aritmético; barreira preenchida a preço inventado; funding ignorava calendário/mark; Sharpe escalava com tamanho da amostra | Retorno aritmético e preço observado, duração real, eventos de funding e cobertura explícitos, taxas pelos nocionais de entrada/saída; Sharpe por sinal sem `sqrt(n)` |
| Sweep e evidência | Tentativas sem registro completo e arquivo de retornos sobrescrito | Família congelada bloqueada antes de dados/registro; parâmetros registrados antes de resultados; cada run possui diretório, hashes de inputs, parâmetros e retornos próprios |
| Paper e promoção econômica | Replay passado podia ser chamado prospectivo; relatório confundia soma de trades com carteira; custo fixo era chamado calibrado | Entrada atual e família aberta exigidas; relatório distingue soma bruta de P&L de carteira e ausente de zero; nenhum modelo marcado calibrado por mera existência histórica; WFA retorna `UNVALIDATED` |
| Saúde e saída | Heartbeat futuro/malformado ou falta de dias podia aparecer saudável; texto exportado virava fórmula | Watchdogs recusam horários inválidos/futuros e banco corrompido; semana exige sete dias distintos; exportação CSV/XLSX neutraliza fórmulas em texto não confiável |
| Estado científico e configuração | Plugin anunciava H6 ativo mesmo encerrado; atrasos inválidos podiam travar retry | Plugin consulta charter atual; limites numéricos finitos; Retry-After excessivo/NaN/inf recusa nova tentativa |
| Orçamento de API nos testes | `reset_for_test` apagava o banco configurado, inclusive operacional em execução direcionada sem redirecionamento | Helper agora só limpa aviso em memória; nunca remove contadores. Fixture isola o banco e regressão prova que uso persistente sobrevive ao reset de aviso |

## Datas, fontes e dados recuperados

O índice usado como DXY no projeto é **DTWEXBGS, índice amplo nominal do dólar**, não o contrato/índice ICE DXY. Dados diários não significam publicação diária: H.10 publica a semana anterior. A página FRED consultada em 10/09 mostrava observação de 04/09 publicada em 08/09. Uma coluna de lag presumido não comprova quando aquela versão estava disponível. O replay macro exige `published_at` documentado por versão e calendário com disponibilidade/cobertura explícita. [Federal Reserve H.10](https://www.federalreserve.gov/releases/h10/about.htm), [FRED DTWEXBGS](https://fred.stlouisfed.org/series/DTWEXBGS).

A Binance documenta namespaces distintos para spot/futuros, timestamps spot em microssegundos desde janeiro de 2025 e revisões posteriores dos arquivos. Hash confere integridade contra a fonte observada hoje, não a versão conhecida pelo mercado no passado. [Esquema e checksums oficiais](https://github.com/binance/binance-public-data/blob/master/README.md).

Uma verificação pública pontual recuperou **743 candles horários por ativo, BTCUSDT e ETHUSDT**, de agosto/2026, e comparou os primeiros 24 de cada série com `/api/v3/klines`: 48 timestamps, fechamentos e volumes iguais. O corte é 31/08/2026 23:59:59.999 UTC; por isso o candle aberto às 23h de 31/08 ainda não está fechado nesse corte e foi corretamente excluído. Total: 1.486 registros. São dois arquivos mensais/checksums e duas chamadas REST, seis requisições, sem retry. Brutos, recibos, respostas e CSVs novos estão em `C:\Cripto\operacao\dados\spot-source-audit-20260910`. A verificação não certifica anos inteiros de histórico nem independência entre dois serviços da mesma bolsa.

Os arquivos antigos `spot_1h.csv`, modelos, relatórios e ledgers congelados não foram renomeados nem sobrescritos. Novo consumidor exige o nome que identifica spot Binance; reusar dados antigos exige reconstrução explícita com procedência. O novo dado de auditoria não foi inserido automaticamente em experimento congelado.

## Incidente de isolamento dos testes e orçamento

Na conferência conectada, a tabela operacional de orçamento estava vazia antes das duas unidades de ingestão. A leitura dos testes demonstrou que dois casos chamavam o helper antigo sem banco temporário. Isso invalida a interpretação de zero como uso anterior medido. O estado foi preservado em backup SQLite e os limites do dia **10/09 UTC foram reservados conservadoramente** para impedir novas chamadas de ingestão/notícias/LLM. Reserva administrativa não é contagem medida de consumo; não há reposição ou ampliação de quota.

Evidências e estado antes/depois: `C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\expansion_budget_incident\result.json`. A próxima janela é o próximo dia UTC, sem reset manual. Atualizações Git/CI não são chamadas aos provedores de dados/LLM. O helper corrigido e a fixture impedem a repetição deste defeito. O histórico de uso apagado não pode ser reconstruído exatamente só pelo banco remanescente.

## Erratas econômicas e científicas

- Um parâmetro de fee/slippage em bps é um cenário. `CALIBRATED_FOR_VERDICT` fica vazio enquanto não houver evidência por conta, instrumento, tamanho e execução. Isto corrige a antiga descrição de perp calibrado; não recalcula decisões congeladas.
- V3 usa preços spot como proxy para derivativos e execução horária observada. Não modela de forma suficiente fills pessoais, liquidação/margem ou liquidez executável. `final_verdict=UNVALIDATED`; `diagnostic_verdict` preserva apenas o resultado dos critérios numéricos. PSR IID sobre retornos sobrepostos é diagnóstico, não confiança confirmatória.
- Sharpe/Sortino são razões por sinal sem anualização. Calmar e drawdown usam equity de trades fechados com alocação; não medem o pior drawdown intratrade por marcação a mercado. Intervalos de retorno são descritivos e não corrigem seleção de hipóteses.
- Paper sem alocação, fills, custos e trajetória de marcação não tem P&L/MaxDD de carteira comprovado. A soma de retornos brutos por registro é apresentada com esse nome; ausência é `None`, não zero.
- Calendário publicado antecipadamente não prova que o arquivo atual era conhecido antes. H7 exige procedência e cobertura temporal; `legacy_assumption` existe somente para reprodução explícita de hipóteses antigas.
- H6 continua encerrada. H7/H8 e os protocolos manuais futuros não foram ativados. Código, testes verdes e fontes acessíveis não substituem amostra independente.

## Cobertura real da revisão

| Componente/alegação | Profundidade nesta ampliação | Limite |
|---|---|---|
| Trading, microestrutura, store, custos e reconciliação | Leitura direta dos módulos alterados, casos adversariais e testes de integração | Sem conta/fills reais ou benchmark em infraestrutura de bolsa |
| DPL, provedores ativos, alinhamento, features e ingestão | Leitura direta dos contratos e caminhos alterados; fontes oficiais; dados spot reais e regressões | Recebimento atual não recupera versões históricas ausentes; comparação REST é amostra |
| V3/HMM, WFA, paper, DSL, H8 e harness | Leitura direta dos cálculos, cache, persistência e consumidores alterados; regressões econômicas/temporais | Correção do método não reabre famílias nem valida lucro |
| Configuração, watchdogs, snapshot, exportação e plugin | Leitura direta das rotas alteradas; JSON/SQLite/tempo/estado inválidos exercitados | Saúde sintética não comprova continuidade de observação futura |
| CI, empacotamento, extras e entradas Windows | Configuração examinada; build/suíte/pacote/entradas executados; CI final registrado separadamente | Container validado pelo CI Linux, não executado como alegação local no Windows |
| Demais wrappers e scripts do repasse | Inventário e verificações das etapas anteriores, mantidos no registro vivo; suíte conjunta nesta etapa | Não se afirma nova leitura integral de cada script nesta ampliação |
| Arquivos restaurados, notebooks, diários e snapshots | Integridade/preservação e amostragem conforme seções anteriores do registro vivo | Não se afirma auditoria manual universal nem completude histórica |
| Fontes sem consumidor, pilotos de outros domínios e propostas antigas | Inventariados; não usados para concluir sobre cripto | Não recebem validação operacional por disponibilidade de código |

## Registros futuros conferidos após a correção

O status offline do carry confirmou `WAITING`, zero linhas e nenhuma entrada. O registro LLM v2 recusou corretamente as mudanças em configuração e guarda de API. Foi preparado `C:\Cripto\operacao\dados\llm-paired-manual-20260912-v3`, preservando v2 sem observações. Protocolo, datas e ambiente são iguais. Mudam os hashes dos dois arquivos corrigidos, a data de registro e o hash de `local_runtime.py` por LF/CRLF, sem mudança lógica nesse último. O executor está vinculado aos bytes de `C:\Cripto\auditoria-ampliada-20260910`; preserve essa área e use o lançador explícito documentado, não o checkout operacional diretamente. O status v3 confirmou 84 horários futuros, sem diário, rede ou ativação. O [registro público novo](manual_dependencies_20260910/llm_audit_registration_v3.json) e os [comandos atualizados](manual_dependencies_20260910/EXECUCAO.md) são a referência de retomada.

## Dependências restantes e critério de encerramento

### Conferência adicional do pedido e da conversa

A releitura integral do pedido e das mensagens encontrou uma lacuna adicional de engenharia: o isolamento de credenciais e caminhos dependia do lançador de validação. O `tests/conftest.py` preservava variáveis herdadas e podia carregar a configuração privada em uma chamada direta de pytest. A correção cria uma área exclusiva por processo de testes, escolhe um dotenv sintético, substitui as credenciais exigidas e remove as opcionais herdadas antes dos imports de configuração/armazenamento. Não altera contadores operacionais nem os bytes do executor LLM registrado.

Uma regressão em subprocesso usa credenciais e diretórios fictícios de operador e realiza uma escrita de orçamento. Ela demonstra a falha na versão anterior e exige configuração isolada, credenciais sintéticas, orçamento em outro diretório e preservação do diretório original. Os resultados completos desta conferência, os SHAs e os checks de integração ficam na seção 17 do registro vivo. A validação da seção 16 continua sendo evidência do PR #115, sem atribuição retroativa ao código novo.

O objetivo completo ainda não está certificado: há cobertura manual delimitada, versões históricas ausentes e observação futura pendente. Na conferência posterior, o snapshot `daily-v4-audited` foi recuperado offline de um recibo Binance preservado, mantendo o v3 e as previsões originais. Recebimento: 10/09 02:12 UTC; última barra fechada: 10/09 00UTC; frescor até 11/09 02UTC. A dependência do snapshot foi resolvida nessa janela, sem consumir quota; novas chamadas seguem limitadas. Consulte CONFERENCIA_CHAT_20260910.md. Uma dependência de evidência não é pacote ausente; uma futura ingestão tampouco é validação prospectiva de lucro.

| Dependência concreta | O que já foi resolvido | O que falta e qual conclusão impede |
|---|---|---|
| Inputs originais H5 | Busca local/Git/arquivos e lacuna documentadas; novos inputs preservados | Backup autêntico de prompts, notícias, respostas e dados originais. Sem ele não há reprodução exata da H5; preços atuais não o substituem |
| Versões históricas macro | Recebimento correto e rejeição de lag inventado implementados | Prova de disponibilidade de cada valor/calendário na época. Sem ela não há backtest macro causal confirmatório |
| Modelo de execução e custos | Contabilidade, cenários e guardas corrigidos | Fees/tier/size, fills reconciliados, spread/slippage e funding/mark do instrumento; requisitos para lucro pessoal executável. Não se enviam ordens para obter essa prova sem novo mandato específico |
| Amostra independente futura | Executores/avaliadores e registros manuais de 84 dias preparados nas etapas anteriores | Observações reais futuras e protocolo respeitado. Começo previsto em 12/09, sem agendamento ativo; tempo futuro não é preenchível manualmente agora |
| Aave independente e pessoal | 13 fronteiras originais e 25 fronteiras da extensão recuperadas; cenários reconciliados | Segunda fonte de estado histórico e custos/execução pessoal pareada. Resultado permanece histórico positivo condicional |
| Cobertura histórica fora dos recortes auditados | 542 dias de interrupções explicados, identidades registradas, amostra spot correta recuperada | Fonte/recorte específico para qualquer nova alegação de completude; não se preenche ausência com interpolação nem se chama arquivo antigo de spot verificado |
| Uso antigo de APIs | Causa de apagamento corrigida e reserva conservadora aplicada | Contabilidade exata anterior exige logs externos autênticos; novas chamadas operacionais aguardam próximo dia UTC |
| Histórico de chaves | Chaves atuais mantidas por orientação do dono; redação de logs corrigida | Revogação antiga/uso anterior não comprovados, P2 histórico sem bloquear a pesquisa. Nenhuma revogação atual exigida ou executada |
| Segurança administrativa da branch | Integração acompanhada manualmente com os quatro jobs | Configuração permanente foi expressamente excluída pelo dono; não alterada |

As pendências acima não são pacotes que faltou instalar nem erros conhecidos que foram ocultados para liberar a integração. Instalação/engenharia são verificadas nos checks; evidência histórica ausente, custos pessoais e tempo futuro têm critérios próprios. Uma auditoria finita não garante ausência de todo defeito possível. Novas falhas demonstradas exigem nova correção e regressão, preservando a mesma disciplina de evidência.
