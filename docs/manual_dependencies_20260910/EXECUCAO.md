# Dependências implementadas e recuperadas em 10/09/2026

**Atualização após #116:** [conferência do chat e seis itens](../CONFERENCIA_CHAT_20260910.md). Snapshot v4 recuperado offline; segunda fonte Aave preparada, ainda sem consulta por quota. Chaves atuais mantidas; fatos históricos de uso/revogação não bloqueiam a pesquisa. As seções abaixo preservam as datas e resultados de cada etapa.

**Errata da auditoria ampliada de 10/09:** o registro LLM atual é `llm-paired-manual-20260912-v3`. A versão v2 ficou preservada, sem observações, e recusa corretamente as mudanças em `config.py` e `core/api_guard.py`. O novo registro mantém protocolo, datas e ambiente, vincula o código corrigido antes da coleta e passou no status offline com 84 horários futuros. Os registros antigos não tiveram hashes alterados. Carry permanece no registro v2.

**Executor vinculado ao registro:** os comandos LLM abaixo usam explicitamente `C:\Cripto\auditoria-ampliada-20260910` por meio do lançador `work\isolated_python.py` do relatório. Preserve essa área e seus bytes. `local_runtime.py` também difere no hash por LF/CRLF, embora seu conteúdo lógico seja igual; usar o checkout operacional diretamente não satisfaz esse congelamento. O ambiente Python continua em `C:\Cripto\pesquisa-20260909\.venv`. O carregador verifica código e ambiente antes de qualquer coleta.

Esta etapa fecha o trabalho de implementação que havia sido deixado como preparação. O registro vivo completo continua em `C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\REVISAO.md`. O mandato, os estudos e os diários anteriores permanecem preservados. As proteções administrativas da branch continuam excluídas pelo dono.

## Aave: histórico recuperado e cálculo disponível

O endpoint público gratuito da [Alchemy para Arbitrum](https://www.alchemy.com/rpc/arbitrum) respondeu ao mesmo teste histórico que os provedores anteriores recusaram. Uma extensão de aquisição foi registrada antes da medição: mesma reserva nativa USDC, mesma janela **17/06–09/09/2026**, mesmas 13 fronteiras semanais, capitais e custos do protocolo original. Nenhuma escolha de pool ou período foi feita depois de observar retornos.

Foram necessárias **189 chamadas RPC**, sem retries, abaixo do limite registrado de 500; 214.667 bytes de respostas. A sonda de disponibilidade anterior usou duas chamadas. A aquisição conferiu chainId 42161, último bloco em cada fronteira e seu sucessor, hashes e parentesco, aToken/underlying/pool, seis decimais, índice, liquidez não emprestada, pausa, congelamento, limite de oferta e um bloco atual finalizado. O índice foi reconstruído a partir de índice armazenado, taxa e tempo de atualização: os 13 pontos e o ponto atual coincidiram.

Identidades: pool `0x794a61358d6845594f94dc1db02a252b5b4814ad`, USDC nativo `0xaf88d065e77c8cc2239327c5edb3a432268e5831`, aToken `0x724dc807b04555b71ed48a6896b6f41593b8c637`. A conferência em cadeia evita confundir essa reserva com USDC.e. Referências de contrato: [address book Aave](https://github.com/aave-dao/aave-address-book/blob/main/src/AaveV3Arbitrum.sol) e [layout de ReserveDataLegacy](https://github.com/aave-dao/aave-v3-origin/blob/main/src/contracts/protocol/libraries/types/DataTypes.sol).

| Capital hipotético, USDC | Juros brutos em 84 dias | Após custo total de 2 | Após custo total de 10 | Após custo total de 30 |
|---:|---:|---:|---:|---:|
| 1.000 | 5,673185 | 3,673185 | −4,326815 | −24,326815 |
| 5.000 | 28,365934 | 26,365934 | 18,365934 | −1,634066 |
| 25.000 | 141,829672 | 139,829672 | 131,829672 | 111,829672 |

O cálculo conserva arredondamento para baixo no saldo escalado e no resgate. Liquidez e configuração comportavam esses cenários nos pontos observados. São valores em **USDC**, sem assumir equivalência com USDT/BRL. O capital é hipoteticamente disponível em USDC nativo na Arbitrum; bridge, conversão, impostos e despesas particulares não estão inventados nem embutidos como zero. A evidência é histórica exploratória. Liquidez em fotografias semanais não garante saque, preenchimento ou ausência de pausas entre elas. Os cenários de perda de 1%, 5% e 100% continuam visíveis.

O bloqueio de aquisição D01 foi resolvido. O resultado é inconclusivo para lucro pessoal futuro: com 5.000 USDC, o custo de 30 USDC já supera o juro observado. O ponto de equilíbrio de custos adicionais após o cenário de custo 10 é **18,365934 USDC** no período. O cálculo pronto permite avaliar despesas privadas sem exigir que sejam fornecidas para executar os cenários.

[Histórico](../evidence/dependency_execution_20260910/aave/history.json), [respostas e escopo](../evidence/dependency_execution_20260910/aave/scope.json), [cálculo original](../evidence/dependency_execution_20260910/aave/calculation.json), [sensibilidades de custos](../evidence/dependency_execution_20260910/aave/cost-sensitivity.json) e [manifesto](../evidence/dependency_execution_20260910/manifest.json) estão versionados. O código exato executado foi preservado como `collector_executed.source`; o comando atual acrescenta cálculo offline e análise de custos sem refazer a coleta.

Recalcular offline com custos adicionais totais no período, em destino novo:

```powershell
C:\Cripto\CRIPTO.cmd python -m scripts.recover_aave_history --directory C:\Cripto\operacao\dados\aave-recovered-20260910 --additional-cost-usdc 0 7.25 20 --output C:\Cripto\operacao\relatorios\aave-custos-nova-conta.json
```

O modo padrão é `calculate`, sem rede. `--mode collect` exige diretório novo e consome uma unidade da guarda persistente; não é necessário repetir a aquisição resolvida.

## LLM: executor e avaliador completos, registro manual congelado

`scripts/paired_llm.py` e `scripts/paired_llm_source.py` implementam os dois braços com o mesmo mercado e parâmetros: Gemini `gemini-2.5-flash`, temperatura 0,2, resposta JSON, orçamento de pensamento zero e até 2.048 tokens de saída. O prompt completo está no protocolo congelado. A diferença é a lista de notícias; a ordem dos braços alterna por dia previamente definido. Usa SerpAPI `google_news`, que fornece [data ISO de publicação](https://serpapi.com/google-news-api). Títulos sem data válida ficam fora; ausência de notícias verificáveis invalida o par.

O teste conectado recebeu **200 candles fechados, cinco notícias datadas e duas respostas válidas**, em cinco requisições e sem retries. A primeira tentativa expôs um defeito na remoção de segredos de JSON; a correção passa a remover segredos dos valores já analisados, preservando a estrutura. As duas tentativas ficaram preservadas localmente. O [comprovante público](../evidence/dependency_execution_20260910/llm_connected_check.json) omite os textos das notícias e respostas. Esse teste técnico não conta como observação do piloto.

O executor grava início, entradas, prompts, respostas, falhas e par em diário encadeado com gravação durável. Cada tentativa HTTP tem resposta saneada e referência de integridade. Uma interrupção deixa o horário incompleto; reiniciar não repete o LLM. Não há preenchimento retroativo, resposta inválida convertida em score neutro nem troca automática de modelo. Código, ambiente completo e protocolo são conferidos antes de uso.

As duas respostas precisam estar duráveis dentro da janela. A âncora comum é o **fechamento da primeira barra UTC inteira cujo início seja posterior às duas respostas**; o alvo termina sete dias depois. O avaliador exige oito fechamentos consecutivos da mesma fonte, exclui candle aberto, rejeita fonte ou preço alterado e calcula Spearman com empates. Score constante produz correlação indefinida. Relata dias sobrepostos e a seleção fixa dos offsets 0, 7, …, 77, sem substituir ausências; mostra momentum, contraste primário com/sem notícias, contagens e contribuição zero de mercado do braço sem posição. Custo de infraestrutura desconhecido permanece separado. Nenhuma política de trade é inferida do score.

Registro final: `C:\Cripto\operacao\dados\llm-paired-manual-20260912-v3`. [Protocolo](../evidence/dependency_execution_20260910/llm_protocol.json) e [congelamento atual](llm_audit_registration_v3.json) são cópias exatas. O registro inicial sem sufixo ficou preservado e foi substituído antes de observações para finalizar os contratos de tipos; seus hashes não foram atualizados.

São **84 horários diários, de 12/09 a 04/12/2026, 12:00–13:00 UTC** (09:00–10:00 Brasília), e no máximo 12 blocos semanais. O último alvo pode amadurecer em 13/12/2026, 00:00 UTC. O status inicial contém 84 horários futuros e não cria diário. Não há scheduler, operação financeira, reabertura de H6 ou comprovação de poder estatístico. A implementação está pronta; as observações futuras ainda não existem.

Consultar agora, offline:

```powershell
C:\Cripto\CRIPTO.cmd python C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\work\isolated_python.py -m scripts.paired_llm --directory C:\Cripto\operacao\dados\llm-paired-manual-20260912-v3
```

Executar manualmente dentro de um horário registrado:

```powershell
C:\Cripto\CRIPTO.cmd python C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\work\isolated_python.py -m scripts.paired_llm --directory C:\Cripto\operacao\dados\llm-paired-manual-20260912-v3 --mode tick
```

Após existirem alvos maduros, coletar preços e avaliar usando destinos ainda inexistentes:

```powershell
C:\Cripto\CRIPTO.cmd python C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\work\isolated_python.py -m scripts.paired_llm --directory C:\Cripto\operacao\dados\llm-paired-manual-20260912-v3 --mode collect-outcomes --output C:\Cripto\operacao\relatorios\llm-precos-avaliacao-01.json
C:\Cripto\CRIPTO.cmd python C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\work\isolated_python.py -m scripts.paired_llm --directory C:\Cripto\operacao\dados\llm-paired-manual-20260912-v3 --mode evaluate --prices C:\Cripto\operacao\relatorios\llm-precos-avaliacao-01.json --output C:\Cripto\operacao\relatorios\llm-avaliacao-01.json
```

Guardas compartilhadas: 28 unidades de ingestão, oito tentativas de notícias e seis chamadas lógicas de LLM por provedor/dia UTC. O par usa uma unidade de ingestão, uma tentativa de notícias e duas de LLM; as cinco requisições físicas ficam registradas. Uma aquisição de preços para avaliação usa outra unidade de ingestão. Nenhum comando reseta orçamento.

## Informação histórica e pessoal

Além dos backups e refs já examinados, foi concluída a listagem de **448 artefatos** do repositório. Todos têm o nome do SBOM produzido pelo CI; nenhuma exportação de previsões/inputs foi identificada. [Inventário e limites](../evidence/dependency_execution_20260910/h5_artifacts.json). Não foram baixados todos os ZIPs nem examinadas contas externas ou artefatos já indisponíveis. Preços históricos e um executor novo não recriam respostas antigas de LLM. Os diagnósticos novos têm entradas preservadas; H5 continua sem dados originais suficientes para uma certificação retrospectiva.

Custos pessoais, situação tributária, revogação histórica nos provedores e preenchimentos reais são fatos externos, não bibliotecas ou código por implementar. O cálculo de custos está executável e não depende deles para produzir cenários. A declaração anterior do dono sobre rotação foi preservada; não há novo incidente demonstrado. Os resultados negativos de V3/AR3 e a janela carry original perdida também permanecem como resultados históricos, sem afrouxar regras.

## Validação e escopo

O scanner também foi corrigido: não confunde `ATOKEN` com um nome de credencial e passa a detectar atribuições em JSON e nomes como `accessToken`. A exceção de endereço público é restrita ao campo Aave `a_token`; o mesmo hexadecimal em `api_token` continua sinalizado. Duas regressões verificam essa distinção sem expor valores de segredos.

A nova linha de base sobre `33b0627` passou com 1.358 testes, um skip de symlink no Windows e zero falhas, todos os extras, lint, formato, tipagem, scanner, build e entradas Windows. Os testes novos exercitam causalidade, persistência, interrupção, fontes, resposta inválida, empates, calendário de blocos L2, arredondamento e custos. Os três scripts novos foram incluídos na checagem de tipos do CI. Consulte o registro vivo e os checks do commit integrado para a validação final; a linha de base não é atribuída ao código novo.

As pendências de implementação desta etapa foram executadas. Permanecem condições que exigem passagem do tempo ou informação original/pessoal: observações prospectivas, registros H5 ausentes e validação econômica de uma operação real. Não houve ordem, assinatura, transferência, conta nova, pagamento ou ativação de automação.
