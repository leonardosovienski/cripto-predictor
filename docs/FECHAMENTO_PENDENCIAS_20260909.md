# Preparação concluída e limites conhecidos — 09/09/2026

O pipeline foi executado neste PC, com dados públicos, notícias SerpAPI e análise Gemini, mantendo código, configuração e novas entregas em `C:\Cripto`. A preparação deixou de depender apenas de testes sintéticos. Isso não certifica lucro futuro, disponibilidade permanente das APIs nem recuperação de tudo que existiu no computador antigo.

## Correções demonstradas

| Problema reproduzido | Correção e verificação |
|---|---|
| CoinGecko ignorava a chave presente somente no arquivo dotenv | O domínio injeta a configuração resolvida na DPL e nos coletores. Teste verifica o cabeçalho recebido pelo transporte; uso independente por variável de ambiente continua possível |
| Pedir 200 candles à CCXT entregava 199 fechados | O conector solicita uma linha adicional, exclui o candle aberto e limita a saída. Execução real posterior: 200 candles fechados e SMA-200 presente |
| Volume em BTC era chamado de volume em USD | O bruto continua em moeda-base. A feature utiliza volume × fechamento como estimativa em moeda de cotação, identificada por `volume_usd_is_estimate`. Para CoinGecko, o volume já informado em USD não é multiplicado |
| Cache podia servir uma análise depois de mudar dados ou juiz | Identidade inclui mercado, modelo/juiz, fonte e política. Releitura real posterior: zero chamadas externas adicionais e mesmo número de previsões |
| Erros e tracebacks podiam carregar credenciais | Proteção antes de logging/eventos e saída da CLI. Falhas de configuração não mostram entradas privadas. O erro de caminho mantém uma mensagem fixa útil sem revelar o caminho rejeitado |

A estimativa de volume não é o volume financeiro exato somado negócio a negócio. Nos pares atuais USD/USDT, também não constitui uma conversão cambial medida. A política registra `daily-v2-closed-bars-quote-volume-estimate` e o horizonte do score; os resultados históricos congelados não foram reescritos.

## Serviços e execução real

- **Gemini:** modelo configurado listado e geração real aprovada.
- **SerpAPI:** chave aceita, plano com preço zero confirmado e notícias reais recebidas. Havia 160 buscas restantes antes das duas buscas de diagnóstico; a cota é compartilhada com outros usos da conta.
- **Groq:** chave aceita. O modelo antigo não apareceu na lista da conta; a configuração local passou para `openai/gpt-oss-120b`, com geração real aprovada. O juiz antigo permanece no histórico.
- **CoinGecko:** endpoint de verificação respondeu com o cabeçalho Demo. A propagação da configuração também tem teste de regressão; não se afirma que todo endpoint/cota esteja liberado.
- **Cerebras:** listagem de modelos respondeu, mas geração retornou **HTTP 402: pagamento necessário**. Não é um provedor gratuito utilizável nesta configuração verificada. Nenhum pagamento ou habilitação de cobrança foi feito.
- **GNews:** chave preservada no arquivo original, sem integração. Não é NewsAPI.ai. **Binance:** credenciais privadas não utilizadas; apenas endpoints públicos foram consultados.

O modo normal permanece Gemini + SerpAPI. As demais chaves opcionais não são pré-requisitos desse modo. A configuração privada é `C:\Cripto\configuracao\pipeline.env`; valores nunca devem entrar no Git ou nos relatórios.

A execução corrigida usou sete requisições HTTP observadas, incluindo o transporte aiohttp da CCXT, e uma geração Gemini. O primeiro diagnóstico havia contado apenas cinco chamadas httpx; suas chamadas CCXT não estavam instrumentadas. Esse limite da primeira contagem está registrado, sem apresentar uma soma física completa inventada. Os limites diários persistentes continuam ligados; não foram zerados para repetir cotas.

O banco novo está em `C:\Cripto\operacao\saidas\feature_store.db`, com mercado, sinais, proveniência e duas previsões de diagnóstico. A primeira usou as entradas anteriores à correção; sua cópia e os relatórios correspondentes foram preservados. Esses registros são **diagnóstico operacional**, não amostra prospectiva independente. Score 75 não significa 75% de acerto ou lucro.

## Dados recuperados e cobertura

As 48 observações horárias de 29/06/2026 foram recuperadas pela API pública para `BTCUSDT_260925_mark` e `BTCUSDT_261225_mark`. A base derivada está em `C:\Cripto\operacao\dados\basis-recovered-20260909`. Ela contém manifesto de origem, novas respostas brutas e passa na reconstrução separada das 534 fontes e 29 séries. A base original permanece preservada.

Os planos originais BR1/BR2 não entraram nesses dois contratos de 2026. O achado não altera os lucros publicados desses planos; não foi refeito um backtest para buscar resultado melhor.

Foram conferidos os 241 registros da aquisição inicial de altcoins e os 661 da retrospectiva, com sobreposição entre as bases. Nenhuma divergência dos hashes conferidos, duplicata ou OHLCV inválido foi encontrada. A retrospectiva contém 727.447 linhas, 12 pares com 542 dias internos ausentes e 200 linhas com horário de fechamento não padrão. As quantidades coincidem com os manifestos; não são uma base diária contínua perfeita. Uma consulta pública por intervalo ausente, 12 ao todo, não devolveu observações recuperáveis. As respostas ficaram preservadas; não houve interpolação ou exclusão para melhorar resultados.

A busca pelo banco antigo examinou 52.890 arquivos soltos e 125.575 entradas de 95 aberturas de ZIP, incluindo nove arquivos internos, sem erro ou corte do orçamento registrado. Não encontrou assinatura SQLite nem candidatos de banco/SQL. Os 132 candidatos por nome eram principalmente registros de trials, atestados e relatórios. Sem outra cópia disponível, a recuperação integral das previsões e inputs antigos da H5 continua **não certificada**. Dados públicos de preços não recriam respostas passadas de LLM.

## Arquitetura efetivamente conferida

| Fluxo | Entrada → processamento → saída | Limite e consumidor |
|---|---|---|
| Operação local | `CRIPTO.cmd` → `local_runtime` → `cli`/`main` | Aplica caminhos e configuração. `status` não consulta APIs; `--ingest` coleta mercado; análise consulta notícias e LLM |
| Dados de mercado | Fachada DPL → CCXT/CoinGecko + sinais → alinhamento, features e SQLite | Brutos e proveniência sustentam a análise. Routers, contratos e parte da persistência são consumidos de `predictor-core`, sem duplicar um segundo motor |
| Análise | Features locais → seleção/orçamento → notícias → LLM → score e divergência → cache, histórico e relatórios | Juiz, política, fallback e degradação distinguem registros. O LLM não envia ordens |
| Interfaces e operação | `services/*` reexportam funções; `persistence.py` define protocolos; `jobs.py` usa `predictor-ops` | Não são serviços independentes em execução. A saúde do plugin não comprova, por si só, todos os fluxos conectados |
| V3 e observação | Funding, OI e spot → qualidade e features → HMM/sinais; backtest separado em janelas | O fit sobre toda a série no pipeline é in-sample. Seus sinais históricos não equivalem ao walk-forward do backtest. `v3.daily` encaminha coleta/qualidade, sem operação financeira |
| Execução simulada | Sinais → custos, carteira, ciclo de ordem e ledger | O adaptador fornecido é simulado; coletor de microestrutura público não é integração de ordens reais |
| Pesquisa econômica | Aquisições versionadas → protocolos fixos carry/basis/altcoins → resultados e observadores separados | Dados e diários restaurados ficam congelados. Novos preços recuperados têm identidade própria; observação futura não é retrodatada |

A revisão de preparação leu os módulos determinantes desses caminhos e seguiu os problemas até testes e execução real. Não representa leitura linha a linha de todos os arquivos históricos. A nova conferência arquitetural pode partir deste mapa e das evidências, mantendo explícitos os trechos ainda não examinados em detalhe.

## Validação e evidências

A linha de base nova passou com 1.277 testes e um skip de symlink do Windows. Os testes adicionais cobrem configuração, candle fechado, unidade do volume, cache e erros. Uma rodada posterior detectou que a proteção da CLI ocultava a razão de recusar caminho externo; isso foi corrigido preservando o teste existente. A versão instalada fora do checkout passou no contrato de pacote. O wheel examinado tinha 162 entradas, sem credenciais, ambientes ou dados operacionais.

**Resultado final, cobertura, commits e quatro jobs de CI:** [VALIDACAO_FINAL.json](C:/Cripto/operacao/relatorios/FECHAMENTO_PENDENCIAS_20260909/VALIDACAO_FINAL.json). A integração de engenharia está no [PR #109](https://github.com/leonardosovienski/cripto-predictor/pull/109). A evidência final deve ser lida pelo SHA, não substituída pelo número da linha de base.

As evidências locais estão em `C:\Cripto\operacao\relatorios\FECHAMENTO_PENDENCIAS_20260909`: `execution_scope.json`, `provider_preflight.json`, `provider_metadata_followup.json`, `live_pipeline_corrected_result.json`, `basis_gap_recovery.json`, `basis_recovered_validation.json`, `altcoin_data_quality.json`, `altcoin_gap_probe_results.json`, `old_store_extended_search.json`, `old_export_candidates_classification.json` e `economic_cost_reconciliation.json`. Scripts de aquisição/verificação e respostas públicas estão junto das evidências. Nenhum deles altera os originais restaurados.

## O que permanece dependente de informação externa ou tempo

O estudo Aave segue estacionado por acesso histórico: as seis chamadas adicionais não obtiveram o índice antigo. A PublicNode exigiu token pessoal de arquivo histórico; o RPC público de Arbitrum não tinha o estado solicitado. Não foi criado serviço, conta ou cobrança. Índices e liquidez dos 13 limites semanais do protocolo continuam necessários; não foi estimado rendimento.

O dono confirmou 5.000 USDT como referência e planos gratuitos. Custos próprios de infraestrutura, desenvolvimento, câmbio, taxas pessoais e tolerância de perda não foram informados. A conciliação mantém esses campos desconhecidos e mostra cenários, sem inventar ROI pessoal.

Os resultados econômicos preservados não mudaram: AR1 BTC +424,25 USDT base/+341,13 adverso e BR1 +230,17/+110,07 em 980 dias, cada cenário com seus próprios 5.000 USDT. AR2 continua negativo no adverso; AR3 teve perda modelada próxima de 99%. Não somar as estratégias como se compartilhassem capital sem restrição. O carry recente permanece fraco após custos. Fontes e detalhes: [resultados econômicos registrados](evidence/economic_round_20260909/RESULTADOS.md).

Para o investidor: avançamos na confiabilidade e descobrimos erros concretos antes de comprometer capital. Isso melhora a qualidade da decisão; ainda não demonstra aumento de lucro ou rentabilidade futura. O próximo marco econômico é evidência posterior à escolha da estratégia, sob protocolo registrado e custos explícitos. Observadores preservados, automações e capital não foram ativados por esta preparação.
