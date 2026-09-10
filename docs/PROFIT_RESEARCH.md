# Pesquisa de lucro multiestratégia — entrega de engenharia de 08/09/2026

A rodada de 10/09 está em [Aave: validação histórica, custos e execução](AAVE_VALIDACAO_20260910.md). Ela apresenta resultados positivos condicionais com o capital integralmente reconciliado, sem declarar lucro pessoal ou futuro comprovado.

Neste PC, execute e salve toda pesquisa somente dentro de `C:\Cripto`, seguindo [CONFIGURACAO_LOCAL.md](CONFIGURACAO_LOCAL.md). Código atual em `C:\Cripto\pesquisa-20260909`; dados originais em `C:\Cripto\restaurado-20260908`; novas entregas em `C:\Cripto\operacao\relatorios`.

A rodada econômica posterior está em [RESULTADOS — 09/09/2026](evidence/economic_round_20260909/RESULTADOS.md): acesso histórico ao Aave bloqueado e economia de renovação AR2 insuficiente para resolver as perdas dos cenários adversos registrados. Esta página preserva o contexto da entrega de engenharia anterior.

## Objetivo e estado

O objetivo é lucro líquido absoluto em cripto, com quaisquer ativos e estratégias
que tenham justificativa econômica. Não é obrigatório usar BTC, carry, LLM ou
prever preços. A autorização do dono nesta conversa permite alterar o projeto;
não permite ordens reais, contas autenticadas, serviços pagos ou movimentar fundos.

Foi acrescentado `GarimpoInvestimentos.profit_research`, instalado no mesmo pacote
Python existente. Ele não importa nem altera motores/observadores congelados,
charters, diários, thresholds ou agendamentos. O coletor antigo de momentum e sua
política de custos permanecem para reprodução; esta é uma entrada adicional.

**Esta entrega não encontrou nem validou uma estratégia lucrativa.** Implementa
contas verificáveis, descoberta mais ampla e um comparador de giro. Testes usam
cenários sintéticos e uma reconciliação de valores históricos já publicados,
arredondados. Não foi reexecutado o backtest AR2, nem reduzida sua perda histórica.

## O que funciona

### Conta econômica e comparação

`evaluate` recebe uma lista JSON de oportunidades. Família, ativo e local são
livres. Cada caso declara capital total (incluindo margem/caixa), moeda, período,
cenário, tipo/referência da evidência e fluxos com sinal. Custos obrigatórios:
`execution`, `financing`, `infrastructure`, `tax`, `conversion`, `other`.

Cada custo precisa de justificativa em `cost_notes`. Zero significa uma hipótese
explicitamente justificada; `null` significa desconhecido e bloqueia o lucro
líquido calculado. Custos agregados devem cobrir todas as pernas, entrada/saída,
gas, bridges, spread e deslizamento aplicáveis, sem dupla contagem. Juros/funding
já contabilizados nos fluxos não devem ser repetidos em `financing`.

A saída distingue `known_net_ceiling_not_profit` (receitas conhecidas menos custos
conhecidos) de `net` após todos os custos declarados. Se falta uma receita, ambos
ficam desconhecidos. Uma receita pode ser negativa; custos negativos são recusados.

O ranking exige mesma moeda, capital, início/fim, cenário e tipo de evidência;
não mistura base/adverso, janelas diferentes ou projeção com histórico. Casos não
são uma carteira: o capital e lucros de alternativas não são somados. Bloqueios
ficam visíveis e contados, inclusive falta de evidência de execução/risco e perda
no estresse acima do orçamento declarado. Não é exigido lucro em todo estresse.

`CANDIDATE_FOR_VALIDATION` significa apenas que as hipóteses declaradas passam
nessas contas. Referências e estimativas não são certificadas por este comparador.
Não substitui backtest temporal, protocolo, teste fora da amostra ou validação de
execução. `capital_permission` é sempre `false`, mesmo em exemplos positivos.

Reproduzir a conta adversa publicada sem inventar tributos/conversão:

```bash
python -m GarimpoInvestimentos.profit_research evaluate docs/evidence/profit_research_20260908/carry_adverse_rounded.json
```

Resultado esperado: teto parcial **-6,97 USDT**, `net: null`, pesquisa bloqueada.
É o mesmo resultado histórico arredondado antes dos custos desconhecidos, não uma
nova amostra. Na hipótese contábil que desconsiderasse todos esses custos, o teto
para execução seria 11,35 USDT; gastar exatamente isso só empata, não produz lucro.
Não usar esse número como uma tarifa alcançável ou como justificativa para zerar custos.

### Descoberta de rendimentos, sem filtrar stablecoins ou wrapped tokens

```bash
python -m GarimpoInvestimentos.profit_research capture-yields snapshot-novo.json
python -m GarimpoInvestimentos.profit_research discover-yields snapshot-novo.json
```

A coleta é um único GET público no endpoint fixo da DefiLlama, sem credenciais,
redirecionamentos ou tarefa recorrente. O arquivo novo preserva bytes JSON,
SHA256 e horário de recebimento; não sobrescreve snapshots. Falha HTTP/dados
inválidos não são interpretados como mercado sem oportunidades.

Todos os ativos válidos são mantidos. `apyBase` e `apyReward` são campos separados;
base ausente nunca vira APY total. Nenhuma recompensa desconhecida vira zero.
Pools duplicados são todos rejeitados, não se escolhe a primeira versão. Cada
rejeição é reportada. TVL não certifica liquidez de retirada. Recebimento agora não
certifica frescor do dado de origem: `source_freshness_verified` permanece falso.

Referência de esquema/metodologia consultada em 08/09/2026:
https://github.com/DefiLlama/yield-server#apy-methodology

O parser não recomenda protocolos e não converte APY instantâneo em lucro futuro.
`yield_return` é apenas uma conta de cenário com taxa constante e convenção APR
ou APY explícita; a reinversão implícita em APY também precisa ser viável.

### Ajuste de posição em vez de fechamento/reabertura

`transition` recebe JSON com identidade anterior e alvo, quantidades com sinal,
preço, grade de quantidade e custos em pontos-base declarados. As identidades
precisam representar exatamente a mesma venue/contrato/moeda de liquidação.
Nunca compensar spot com perpétuo ou posições de corretoras distintas.

```bash
python -m GarimpoInvestimentos.profit_research transition docs/evidence/profit_research_20260908/transition_synthetic.json
```

No exemplo artificial, manter -1 unidade custa zero de giro em vez de negociar
2 unidades para fechar/reabrir. Isso é economia matemática sob preços/custos
fixados; não é lucro histórico adicional. Mudanças de quantidade negociam a
diferença; inversão de lado não recebe economia fictícia. Grid inválido bloqueia.
Mínimo nocional, preenchimentos, funding na fronteira, tributação, margem e risco
da execução devem ser reavaliados antes de usar essa alternativa em outra pesquisa.
O observador e a AR2 originais continuam inalterados.

## Próxima decisão econômica, não outra reescrita

Comparar primeiro rendimentos sem alavancagem, carry/diferenciais multiativos e
uma hipótese direcional simples apenas se não reabrir uma família encerrada sem
dossiê. A escolha entre elas depende de dados e custos verificáveis, não da maior
APY ou de um resultado sintético. Instrumentos com vencimento e arbitragem também
são elegíveis, mas adaptadores de preços/execução para eles ainda não foram feitos.

Antes de qualquer avaliação nova, registrar fonte, especificação, intervalo,
orçamento de tentativas, custos, risco e regra de parada. Os gates de reabertura
existentes continuam aplicáveis. Não forçar entradas para eliminar NO_OPPORTUNITY.
Não registrar como prospectiva uma decisão tomada após olhar o resultado.

O registro desta entrega está em `evidence/profit_research_20260908/scope.json`.
O acompanhamento carry/altcoins e os arquivos locais do dono não foram acessados
ou modificados. Não há novo scheduler nem resolução da pendência de agendamento.
