# Capacidades implementadas e evidência

## Contratos e critérios

| Capacidade | Hipótese técnica / incerteza | Controle / falsificação | Sucesso e resultado | Limite e próximo uso |
|---|---|---|---|---|
| Painel de fatores | Uma API por data/grupo elimina montagem manual sem mudar Spearman | SciPy em 8 combinações de grupos/ties; resíduos contra solução fechada; duplicatas e não finitos rejeitados | Testes aprovados; IC, quantis, médias de labels e turnover disponíveis | Não é retorno líquido; grupos/labels fornecidos. Próximo: estudo residual com universo admissível |
| Universo | Regras ordenadas e cutoff não deixam versão futura alterar seleção | Versões fora do cutoff, inativo recente, campo ausente, moeda incompatível, empate | Testes aprovados; seleção e razões reproduzíveis | known_at é contrato de entrada, não prova histórica. Próximo: dados F03 quando admissíveis |
| Validação | Intervalos e disponibilidade impedem treino com label não conhecido | Oracle independente de interseção em intervalos irregulares/aleatórios; bordas fechadas | Testes aprovados; exclusões rastreáveis | Forward-only, não CPCV; não valida cobertura estatística nem retuna F05 |
| Caixa de cenário | Reserva por bolsa/moeda impede uso duplicado de capital e fill precoce | Fractions como oracle de saldo; vendas, cancelamento, duplicatas, capital fragmentado; lifecycle nativo | Testes aprovados; reservas liberadas parcialmente ou no cancelamento | Spot sintético; sem lotes, margem, fila ou impacto. Próximo: otimização do uso de caixa em cenários |
| RunStore/CLI | Mesmo input gera mesmos resultados e adulteração de artefato é detectada | Reexecução idêntica; tentativa de sobrescrita, path traversal e alteração de métricas | Demo integrado e reproduzido; hashes verificados | Manifesto não é assinatura; sem servidor, dashboard ou registro científico substituído |

Dados e contrato temporal: apenas fixtures sintéticas/entradas explícitas. Não houve nova coleta de preços, funding, books, contas ou transações. Custos no cenário: taxa decimal na moeda de cotação, reserva ao limite e preço de fill fornecido; nenhuma conversão de moeda implícita. Métricas do painel não deduzem custos nem representam PnL.

Rejeição técnica: desigualdade ao oracle, vazamento de label/versão, uso duplo de saldo, mutação de run concluído ou regressão atribuível ao código. Inconclusão econômica: sempre que faltar identidade, dados PIT, execução empírica ou custos; essas ausências não são falha técnica do protótipo nem rejeição científica da hipótese.

## Resultados verificáveis

Regressão completa: `{'tests': 1529, 'failures': 0, 'errors': 0, 'skipped': 1}`. Bateria final das capacidades: `{'tests': 24, 'failures': 0, 'errors': 0, 'skipped': 0}`. As contagens não devem ser somadas como testes únicos: a regressão completa já incluiu os primeiros 23 testes novos; o teste diferencial nativo adicional foi executado na bateria final de 24.

Primeira bateria: um erro de roundtrip JSON dos índices excluídos pelo splitter; corrigido usando chaves string. Primeiro ensaio do teste nativo: chamada de argumento keyword-only como posicional; corrigida no teste, sem mudança de regra de execução. Ambos os recibos de falha foram mantidos. Nenhuma dessas falhas é evidência econômica.

Checks de lint/formatação/tipos e scanner aprovados em CHECKS.json e FINAL_CHECKS.json. O build sem isolamento falhou por backend hatchling indisponível; o build isolado via uv foi concluído e o demo importado diretamente do wheel fora do checkout passou, conforme WHEEL_CHECK.json. Benchmark de cinco repetições aquecidas: painel de 20 mil linhas ~0,197 s; universo de 10 mil registros ~0,063 s; splitter de 10 mil labels e dez janelas ~0,039 s. São tempos locais, sem baseline de desempenho externo ou medição de produtividade humana. Repetições deram resultados iguais; BENCHMARK.json contém medidas brutas.

Preservação: 229 arquivos protegidos comparados por SHA-256; divergências: 0. HEAD igual ao baseline. Alterações de Python preexistente: ['C:\\Cripto\\pesquisa-20260909\\GarimpoInvestimentos\\cli.py']. `docs/NEXT_CHAT_PROMPT.md` conserva a alteração que já existia antes da rodada.

## Uso imediato

```powershell
C:\Cripto\CRIPTO.cmd python -m GarimpoInvestimentos.research demo --store C:\Cripto\operacao\relatorios\research-runs
C:\Cripto\CRIPTO.cmd python -m GarimpoInvestimentos.research run --input C:\Cripto\input.json --store C:\Cripto\operacao\relatorios\research-runs
```

O README do pacote documenta o contrato JSON. `demo_config.json` na entrega é uma entrada executável. `list`, `verify` e `compare` tornam o workflow inspecionável. O código já está aplicado no checkout local, sem commit, push ou alteração de protocolo congelado.
