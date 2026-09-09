# Revisão iniciada em 09/09/2026 — contratos corrigidos e erratas

O registro vivo único desta revisão está em `C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\REVISAO.md`. Ele contém cobertura, matriz de afirmações, arquitetura, contas, falhas, validações por versão e dependências. Os JSONs e logs adjacentes são comprovantes. Este documento versiona os contratos e as erratas; não substitui o registro nem constitui evidência de CI aprovado.

## Contrato para novos diagnósticos

- Ingestão diária de cripto materializa `daily-v3-contiguous`. Indicadores usam somente o trecho diário contínuo após a última lacuna; sete observações espaçadas não equivalem a sete dias. Lotes vazios, duplicados, de identidade diferente ou OHLCV inválido falham antes da persistência inicial.
- O CoinGecko diário é uma série de preços com OHLC sintético, não candles completos de uma bolsa. Descarta o ponto parcial, trata o timestamp como fechamento e aplica o atraso documentado de dez minutos. `/ohlc` aceita somente as granularidades que o endpoint entrega (30 minutos ou quatro horas); não rotula barras de 30 minutos como barras de uma hora. Volume ausente não vira volume diário zero.
- O serving exige snapshot do contrato atual, fonte identificada, candle fechado, coleta posterior à disponibilidade e defasagem máxima de 26 horas. Sem isso, o ativo é excluído antes de gastar notícias/LLM. Rodar `--ingest` é necessário após atualizar o código; features `v1` antigas não são promovidas automaticamente.
- A migração aditiva 0019 preserva snapshots do mercado normalizado e os inputs de cada previsão: candles, sinais, features, fonte, notícias recebidas, prompt, resposta, juiz, política e horários. Hashes e triggers detectam alterações; previsão e inputs são persistidos na mesma transação, antes de cache/exportação. Conflitos de identidade falham. Os arquivos de resposta HTTP do mercado não estão incluídos nesse novo contrato; tampouco se reconstrói o que não foi salvo antes.
- Notícias guardam o instante de recebimento e expiram do cache após uma hora; esse instante não certifica publicação histórica. Respostas inválidas do LLM são fallback explícito e ficam fora da avaliação. Score continua experimental, sem interpretação de probabilidade calibrada.
- `future-daily-close-v1` mede do próximo fechamento UTC estritamente posterior à previsão até o fechamento do mesmo provedor, 1/7/30 dias depois (mais o horizonte configurado). Preço antigo do contexto não é preço de entrada. Ausência de fechamento deixa o retorno ausente, sem consulta a outro provedor. São proxies de preço bruto, sem fills ou lucro líquido certificado.
- `_load_rows(include_legacy=True)` e `build_snapshot(include_legacy=True)` existem para reprodução histórica explícita. O padrão exclui previsões sem o novo contexto. Resultados novos não alimentam a H6 encerrada. O hash do prompt e a política mudaram: não misturar as séries nem tratar os diagnósticos como nova trial prospectiva registrada.

## Erratas sobre capacidades

As expressões históricas “bitemporal”, “anti-lookahead”, “paridade total”, “valida o edge em tempo real” e “custo calibrado” não certificam os usos abaixo. Os documentos congelados permanecem intactos.

1. A Feature Store contém controles temporais, mas `raw_market_data` ainda faz upsert. Antes da migração 0019 não preservava integralmente inputs nem todas as revisões de candles. Os novos snapshots melhoram a reprodução futura; não recuperam H5 nem constituem um arquivo completo de vintages HTTP.
2. O pipeline V3 pode ajustar HMM/scaler sobre toda a série que recebe. Inferência forward é causal condicionada ao modelo fixo, mas seus sinais históricos não são automaticamente fora da amostra. O WFA treina por fold e possui purge; seu P&L usa proxies, funding constante aproximado e hipóteses de custo. `paper_trader` grava sinais teóricos, sem executar nem validar preenchimentos. Há lacunas de OI e janelas esparsas; a família continua congelada e não está pronta para validação econômica prospectiva por esse simples comando.
3. `trading.cost_policy.CALIBRATED_FOR_VERDICT` é um nome legado para aceitação da referência histórica de custos de perpétuos. Não há calibração de conta/fills demonstrada. O modelo walk-the-book de spot também é não calibrado. Nenhum deles demonstra lucro executável; custos realizados e aproximações são diferentes objetos.
4. Consenso não é confirmação independente de verdade: duas fontes reduzem a mediana à média, podem compartilhar dados e usar metodologias/unidades diferentes. O snapshot preserva a série fundida, não cada resposta bruta constituinte. Para o diagnóstico desta revisão, a fonte configurada é Binance diária em modo fallback. Consenso continua ferramenta experimental.
5. As camadas `services/*` são reexports, não serviços HTTP. Não há frontend público implantado nem adaptador financeiro real. Não é necessário criá-los para investigar os resultados econômicos atuais.

## Dados e economia

A revisão reconstruiu separadamente todas as 251.930 linhas da aquisição inicial e as 727.447 linhas da retrospectiva de altcoins, sem divergência frente aos brutos preservados. São aquisições sobrepostas. Permanecem 326/542 dias ausentes somados entre pares e 83/200 fechamentos não padrão; esses números não representam duração consecutiva nem cobertura completa do universo histórico. A auditoria do seletor reconferiu 32 vetores/scores e 560 contas semanais em Decimal, identificando zero qualificados entre 13.996 observações. Não se afrouxaram critérios para produzir operações.

Os auditores separados de carry, futuros e do diagnóstico de 84 dias reproduziram as contas originais. BR2 avaliou 23.520 decisões horárias; o maior basis foi 0,288805%, abaixo do gatilho fixo de 0,75%, explicando zero entradas. A nova consulta pública 1RPC confirmou a rede Arbitrum e falhou no estado histórico solicitado; Aave segue sem índice/liquidez nos 13 limites necessários.

Não houve aumento de lucro demonstrado. AR1/BR1 preservam resultados históricos positivos em cenários; AR2 permanece negativo no adverso mesmo sob a melhora limitada de renovação; AR3 perdeu aproximadamente 99% no cenário base. Cada cenário usa seus próprios 5.000 USDT hipotéticos. Custos pessoais, impostos, conversão, condições de conta, execução e amostra futura continuam dependências, não valores iguais a zero.

## Retomada e operação

Comece pelo registro vivo e seu estado de integração. Use `C:\Cripto\CRIPTO.cmd` e mantenha todo armazenamento em `C:\Cripto`. Preserve o diff preexistente de `NEXT_CHAT_PROMPT.md`, o banco anterior ao diagnóstico salvo em `REVISAO_COMPLETA_20260909\live\store_before.db`, os originais restaurados e os protocolos. Não reative observadores ou capital a partir de comandos históricos. O diagnóstico conectado desta revisão é pontual; resultados, consumo real do orçamento e eventuais falhas estão em `live/result.json`.
