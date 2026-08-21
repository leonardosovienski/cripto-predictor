# Overview e Roadmap — 2026-08-21

> **Para que serve este documento.** Ele é o ponto de partida frio: escrito para
> que um leitor (ou uma sessão nova) que não acompanhou nada consiga entender o
> projeto inteiro e saber exatamente o que fazer a seguir, sem depender de
> memória de conversa. A fase que começa agora é a **coleta da H6**.
>
> **Estatuto epistêmico.** As seções 1 a 6 são fato verificado por leitura de
> código, execução ou git, na data do título. A seção 7 (roadmap) contém
> planejamento e, portanto, julgamento — está separada de propósito.
>
> **Este documento não autoriza nada.** Nenhum gate deste ecossistema autoriza
> capital, alavancagem ou decisão direta de trading por LLM. Ver §8.

---

## 0. Mapa dos documentos (leia nesta ordem, se for a primeira vez)

| Documento | Para quê | Quando ler |
|---|---|---|
| **este** | overview + roadmap; o estado atual | primeiro |
| `README.md` | como instalar, rodar e a estrutura de pastas | antes de executar qualquer coisa |
| `docs/HYPOTHESES.md` | o pré-registro: todas as hipóteses, critérios e vereditos | antes de propor QUALQUER ideia nova |
| `docs/PANORAMA_2026-08-21.md` | inventário detalhado + avaliação crítica do projeto | para profundidade |
| `docs/ERRATA_2026-08-21.md` | o que os docs datados afirmam de errado, e a correção | ao ler qualquer doc com data no nome |
| `charters/scientific_state.json` | os invariantes, em máquina | é lido por código; não editar à mão |
| `docs/SECURITY_INCIDENT_SERPAPI.md` | incidente de credencial, já rotacionado | contexto |

**Regra de leitura para todo doc datado:** qualquer arquivo com data no nome é um
**instantâneo congelado**, não estado atual. A `ERRATA_2026-08-21.md` é o índice
canônico das divergências. Este documento também vai envelhecer — o que não
envelhece é `charters/scientific_state.json`, porque código o valida.

---

## 1. O que o projeto é

Um **laboratório de pesquisa quantitativa em cripto com governança científica
fail-closed**. A tese central não é "achar um sinal"; é **não se enganar
enquanto procura**. Concretamente, o projeto:

1. **Pré-registra** cada hipótese (critério de sucesso, horizonte, ativos e `n`
   mínimo) em `docs/HYPOTHESES.md` **antes** de olhar o resultado.
2. **Conta as tentativas** em `GarimpoInvestimentos/trials.json`. Esse contador
   é o denominador do **Deflated Sharpe Ratio** — quanto mais coisas você tenta,
   mais alto o Sharpe precisa ser para significar algo.
3. **Trava o capital em código**, não em convenção: `capital_authorized`,
   `leverage_authorized` e `llm_direct_trading_authorized` são `false` em
   `charters/scientific_state.json` e validados por Pydantic; o processo recusa
   subir se alguém mexer.
4. **Exige atestado de poder com validade**: `scripts/attest_harness.py` roda um
   controle positivo (edge plantado + ruído) e grava um atestado que **expira em
   7 dias**. Vencido, o Experiment Registry recusa registrar trial nova.
5. **Preserva o que refutou.** Nenhuma hipótese é reaberta ou reparametrizada em
   silêncio. O validador Pydantic de `ScientificStateCharter` (`governance.py`)
   levanta exceção se H1, H2, H3 ou H5 deixarem de ser `CLOSED_NO_GO`, ou se
   `funding_oi_hmm_v3` sair de `frozen_families`. Separadamente, a **definição da
   H6** está congelada por hash em `charters/h6_definition_frozen.json`.

### O que o projeto explicitamente NÃO é

- Não é um bot de trading. Existe uma camada `trading/`, mas ela foi construída
  sob **override de governança declarado por escrito antes do código**
  (`docs/HYPOTHESES.md`, "Override de governança 2026-08-14"), e o único
  `ExchangeAdapter` implementado é o `SimulatedExchangeAdapter`.
- Não tem edge validado. Nenhum. Ver §5.
- Não usa LLM como decisor de trade. O LLM pontua ativos (H4/H5/H6) e, no
  backlog B9, propõe hipóteses — nunca aperta botão.

---

## 2. Estado científico — o que já foi tentado

Sete tentativas registradas em `trials.json`; **nenhuma passou**. Este é o fato
mais importante do projeto e o que qualquer leitura otimista precisa atravessar.

| Hipótese | Trial | Veredito | Números que decidiram |
|---|---|---|---|
| **H1** — funding/OI + regime HMM prevê retorno 24h | `v3-hmm-funding-oi-fr90` | **CLOSED_NO_GO** | bruto +0,44bps → **líquido −0,09bps**/sinal; PSR 0,445; n=3958 OOS. Os custos (~0,53bps) comem o edge |
| **H2** — janela curta de funding (fr21) melhora | `v3-hmm-funding-oi-fr21` | **CLOSED_NO_GO** | PSR 0,215; líquido −0,37bps. Janela curta **piora** |
| **H3** — horizonte 48h amortiza a fricção | `v3-hmm-funding-oi-fr90-h48` | **CLOSED_NO_GO** | o edge bruto **vira negativo** (−0,35bps); MaxDD 50,3%. Esticar destrói |
| **H4** — score do LLM prevê D+7 (juiz único) | `v2-dpl-gemini-h7` | **CLOSED_INSUFFICIENT_SAMPLE** | encerrada com n=5, sem veredito |
| **H5** — idem, partição multi-juiz | `v2-dpl-multi-h7` | **CLOSED_NO_GO** | Spearman **−0,166** [−0,266; −0,057], n=440. O IC não cruza zero — **na direção oposta**. Acurácia direcional 45,2%. DSR 0,00 contra corte 0,95 |
| **H6** — **sinal invertido** do LLM prevê D+7 | `h6-sinal-invertido-d7` | **COLLECTION_ONLY_IMMATURE** | último estado versionado: Sharpe auxiliar +0,3479 com **n=6**. Gate exige n≥30 |
| **H7** — calendário macro (FOMC/CPI/PPI) + DXY | não registrada | **REGISTERED_NOT_ACTIVATED** | infra de coleta existe; coleta real não começou |

### O que a H5 ensinou, e por que a H6 existe

Três encarnações da família LLM mostraram correlação **negativa e significativa**
entre score e retorno. A H6 pergunta o óbvio: e se a leitura for invertida (score
alto = queda)? Ela foi pré-registrada em 2026-07-20 com um **risco de
data-snooping admitido por escrito**: a ideia nasceu de olhar resultado anterior.
O pré-registro não apaga esse viés — só impede que o critério seja reescrito
depois. Por isso a trava é dupla:

- `params.fonte = "reserved:h6-inversao-sinal"` nunca casa com o fechamento
  genérico de trial;
- `close_h6_inverted_signal()` e `h6_spearman_verdict()` só aceitam previsões com
  `pred_date` **posterior** ao `registered_at` — nenhuma das 440 previsões da H5
  pode ser reciclada.

Ambas as travas estão congeladas por hash em `charters/h6_definition_frozen.json`.

### Uma ressalva honesta sobre o Sharpe +0,3479

É o único Sharpe positivo do registro inteiro, e **não é veredito nenhum**: com
n=6 não existe IC que decida coisa alguma. Ele também é o que mais infla o `SR0`
do projeto (0,447 com ele; 0,332 sem) — foi verificado, antes de fechar a H5, que
o veredito dela não depende disso.

---

## 3. O que temos — inventário por camada

Suíte executada nesta data: **738 verdes com todos os extras** e **723 verdes + 2
skips** na suíte offline (`--extra test`, sem numpy/hmmlearn). `ruff check` e
`ruff format --check` limpos. CI com 4 jobs (`quality`, `python-314-experimental`,
`all-extras`, `container`), incluindo contract test das wheels instaladas fora do
checkout, SBOM (syft) e Trivy.

**Governança científica** — `analyzers/trials.py` (Experiment Registry, DSR),
`scripts/attest_harness.py` (atestado com validade), `scripts/freeze_h6_definition.py`
(hash da definição da H6), `charters/*.json` (invariantes validados por Pydantic),
`governance.py`.

**Camada de dados (DPL)** — Feature Store **bitemporal**
(`timestamp × published_at × vintage`) com guardas anti-lookahead, 12 migrações
aditivas (numeradas até `_0016`; as primeiras vivem no schema base de `feature_store.py`),
`predictions` **append-only** (migração `_0016`: DELETE bloqueado por trigger;
UPDATE permitido com arquivo `PRE_UPDATE_SNAPSHOT`), hash de proveniência de
conteúdo, backup/restore verificável com runbook, roteador multi-provedor
(binance, kraken, coingecko, bcb, dxy, fear&greed, cotahist), circuit breaker,
calendário macro.

**Análise** — `analyzers/backtest.py` (o juiz oficial: `spearman_block_ci` com
block bootstrap que absorve a sobreposição das janelas D+7), `score_engine.py`,
`indicators.py`, `prefilter.py`, `equivalence.py` (prova DPL ≡ direto).

**Família V3** — HMM de regime, WFA com purge gap de 7 dias, coletores de
funding/OI/spot, paper trader, custos com funding real.

**Camada `trading/`** (construída sob override declarado) — `signal_adapter.py`
(recusa converter sinal de família congelada em `TradeIntent`), `cost_policy.py`
(despacha perp × spot e **recusa** sustentar veredito com modelo não calibrado),
`report.py`, `portfolio.py`, `execution.py`, `store.py` (append-only), 
`microstructure.py`, `binance_spot_collector.py`.

**Ferramentas de aferição (todas de 2026-08-21)** — ver §4.

**Operação** — `jobs.py` com 8 jobs (`phase1`, `backtest`, `watchdog`, `v3-daily`,
`observation-daily`, `observation-live`, `microstructure-live`, `attest-renew`),
watchdog de coleta, `quality_snapshot`, container read-only não-root sem
capabilities.

---

## 4. O que foi feito em 2026-08-21 — 10 PRs, todos na `main`

| PR | O que entregou |
|---|---|
| #37 | Reconcilia o `README` com o repositório real — 13 inconsistências (estado do incidente, nota 5,5→6,0, branches inexistentes, contagem de testes) |
| #38 | Cria `docs/ERRATA_2026-08-21.md` e repara `FINAL_AUDIT_2026-07-20.md` (que nunca teve conteúdo) |
| #39 | Reconcilia as pendências das §5 e §7 do `RELATORIO_FINAL.md` numa §10 nova |
| #40 | `h6_status.json`: ponte produção → git para o `n` da H6 sair da máquina de coleta |
| #41 | Corrige 3 defeitos do próprio artefato do #40, um deles com **perda de dado** — daí `_h6_regride()`, que recusa gravar regressão de `n` ou de veredito |
| #42 | **PBO/CSCV** (`analyzers/pbo.py`), calibração por juiz, **DSL de fatores point-in-time** (whitelist, nunca `eval`) e o **laço de hipóteses** (`hypothesis_loop.py`) |
| #43 | `docs/PANORAMA_2026-08-21.md` |
| #44 | Fecha 4 lacunas do panorama: `signal_adapter`, `report`, `cost_policy`, e renovação condicional do atestado (`--if-expiring-within` + job `attest-renew`) |
| #45 | **Harness de verdade plantada** (`ground_truth_harness.py`) |
| #46 | **Poder do gate** (`gate_power.py`) + B12 com a tabela completa |

### 4.1 As duas medições que mudam como ler tudo

**(a) O pipeline mede certo — aferido contra verdade plantada.** O controle
positivo que existia validava o **juiz** (injetava pares direto no `_report`). O
encanamento onde a **medição** acontece — store → `_load_rows` →
`enrich_with_realized_prices` → par — não era importado por nenhum teste.
Verificado nesta data, plantando um mundo sintético com resposta conhecida por
construção:

| mundo | plantadas | recuperadas | perdidas | erro máx. | Spearman recuperado |
|---|---|---|---|---|---|
| com edge (`edge=0,08`) | 360 | **360** | **0** | 0,004992pp | **+0,9689** |
| nulo (`edge=0,0`) | 360 | 360 | 0 | 0,004995pp | **−0,0733** |

O erro máximo é exatamente o quantum de arredondamento (`round(var, 2)` em
`enrich_with_realized_prices`), documentado como `MEASUREMENT_QUANTUM_PP = 0,01`
com tolerância de meia unidade. A primeira versão do harness usava `1e-6` e
falhou com 0,004992 — foi assim que a granularidade real ficou caracterizada, em
vez de a tolerância ser afrouxada. Um deslocamento de **um dia** produziria erro
de ~0,5pp e seria detectado; existe teste que prova isso.

**Sensibilidade e especificidade juntas:** o pipeline recupera o edge quando ele
existe **e** não fabrica correlação quando não existe. Isso é o que separa "não
temos edge" de "temos um cano furado".

**(b) O gate `n≥30` é cego — poder medido.** Provar que o juiz funciona não prova
que, com o `n` que a coleta vai ter, ele **consegue ver**. Medido com o critério
real — `spearman_block_ci` (de `predictor_core.stats`, o mesmo juiz da Fase 1) com
`block_length = overlap_block_length(7)`, sobre amostras que reproduzem a
sobreposição das janelas D+7 (`n_sim=150`, `n_boot=400`; a linha `n=30` reproduz,
dentro do ruído de simulação, a medição canônica com `n_boot=10.000` e 400
simulações, que deu 14,2%):

| n | rho=0,0 | rho=0,1 | rho=0,2 | rho=0,3 | rho=0,5 |
|---|---|---|---|---|---|
| **30** | 6,7% | 11,3% | **14,7%** | 29,3% | 62,0% |
| 60 | 6,0% | 11,3% | 23,3% | 47,3% | 93,3% |
| 120 | 7,3% | 24,7% | 59,3% | **82,7%** | 100% |
| 250 | 6,0% | 34,7% | **81,3%** | 100% | 100% |
| 500 | 8,0% | 65,3% | 97,3% | 100% | 100% |

Em `n=30`, um efeito real de rho=0,2 passa despercebido em **~85% das vezes**. O
poder chega a 80% em `n≈120` (rho=0,3) e `n≈250` (rho=0,2); rho=0,1 não chega nem
com `n=500`. Falso positivo estável em 6–8%.

> **A consequência operacional, e ela é o coração do roadmap:** o critério
> pré-registrado diz *"n ≥ 30 antes de calcular veredito"*. Ele **não** diz
> *"pare em 30"*. `h6_spearman_verdict()` recalcula a cada ciclo. Logo o primeiro
> veredito impresso, por volta de n=30, é **subdimensionado e não é final**; o
> **mesmo** critério, sem nenhuma alteração, fica bem dimensionado por volta de
> n=250. Nada precisa ser mudado — apenas lido corretamente.
>
> Mudar o `30` agora, **depois** de calcular poder, seria ajuste post-hoc de
> critério: exatamente o que o pré-registro existe para impedir. A H6 está
> congelada por hash. **Não toque no gate.**

---

## 5. O que NÃO temos (fato)

- **Edge.** É o item que importa; tudo acima serve a um sinal que ainda não existe.
- **Reprodutibilidade histórica.** `HISTORICAL_REPRODUCIBILITY = LIMITED`: os
  dados brutos das 440 previsões da H5 foram perdidos. **Permanente.**
- **Venue real.** Só `SimulatedExchangeAdapter`. Bloqueado neste ambiente (sem
  credencial, egress restrito) e adjacente a capital — decisão humana.
- **Consenso validado ao vivo (C-03).** A agregação por mediana nunca fundiu dado real.
- **Equivalência ETH/SOL.** Provada para bitcoin/kaspa/aave; ETH/SOL pendentes (429).
- **CPI/PPI no calendário macro.** `macro_calendar.json` tem 8 eventos, todos
  FOMC; `bls.gov` é bloqueado neste ambiente e a convenção do projeto proíbe
  adivinhar datas.
- **`services/`** — 6 arquivos, 21 linhas: fachada de re-exports quase vazia. Não
  é bug, é arquitetura inacabada; vale decidir entre completar e remover.

---

## 6. O caminho crítico, em uma frase

> **Coletar.** A H6 é a única hipótese viva, a coleta é o único insumo que ela
> aceita, e agora sabemos que o alvo útil não é n=30 — é da ordem de n≈250.

Na taxa observada da H5 (n=440 em ~18 dias ≈ **24 previsões elegíveis/dia**),
n=30 chega em ~1,5 dia e n=250 em **~10 dias de coleta ininterrupta**, mais os 7
dias de maturação do D+7 para as últimas previsões.

---

## 7. Roadmap

> Esta seção é planejamento — contém julgamento sobre prioridade e sequência. As
> anteriores sobrevivem a discordância sobre ela.

### Fase 0 — Destravar (esta semana, tem prazo)

| # | Ação | Prazo | Se não fizer |
|---|---|---|---|
| 0.1 | **Renovar o atestado de poder.** `uv run cripto-predictor-job attest-renew` (ou `python -m scripts.attest_harness`). Expira em **2026-08-28T10:44Z** nos dois arquivos (`trials.harness_attestation.json` e `trials.phase1_harness_attestation.json`) | **2026-08-28** | Nenhuma trial nova pode ser registrada; o registry fecha |
| 0.2 | **Agendar** o `attest-renew` diariamente (`--if-expiring-within 2` já embutido: só grava perto do vencimento) | junto com 0.1 | O prazo volta a ser manual e vai vencer de novo |
| 0.3 | **Colar o novo prompt do cron** de acompanhamento na UI | disparo em **seg 2026-08-24 12:00 UTC** | O cron roda com o prompt velho |
| 0.4 | Verificar a revogação das chaves antigas do SerpAPI | sem prazo | `EXTERNAL_BLOCKER` segue aberto na auditoria formal |

### Fase 1 — A coleta (o trabalho principal)

**1.1 Rodar o ciclo diário, ininterrupto.** É `phase1` + `backtest`; em produção,
`run_sinal_diario.bat` / `run_garimpo_fase1.bat` encapsulam o fluxo (inclusive o
`uv sync` com os **três** extras juntos — sincronizar só `llm+excel` desinstala
numpy/hmmlearn/ccxt e quebra a família V3).

**1.2 Vigiar a continuidade, não só o `n`.** Interrupção de coleta é o modo de
falha que já matou a H4 (encerrada com n=5). O `watchdog` e o `observation-daily`
existem para isso; use-os. Um gap de dias não só atrasa — muda a composição da
amostra.

**1.3 Publicar o `n` para fora da máquina de coleta.** O `feature_store.db` é
gitignored, então **a única via** pela qual o estado da H6 sai é
`GarimpoInvestimentos/h6_status.json`, gravado por `quality_snapshot` **apenas
quando o estado muda** (para não gerar commit de ruído diário). **Commite esse
arquivo quando ele mudar** — é o que o cron semanal e qualquer acompanhamento
externo leem. Sem esse commit, o `n` real é invisível fora dali.

**1.4 Não olhar o resultado antes da hora.** Abaixo de n=30,
`h6_spearman_verdict()` deliberadamente reporta só a contagem, nunca rho/IC.
Isso é proposital: o Sharpe de n=6 já é o exemplo do erro que essa trava evita.

### Fase 2 — Ler o veredito (quando n≥30 e depois)

1. **Em n≈30:** o veredito sai, e deve ser registrado **qualificado pelo poder**.
   Se der "RUÍDO", a leitura correta é *ausência de evidência*, não *evidência de
   ausência* — 14,7% de detecção em rho=0,2. Registre a leitura, **continue
   coletando**.
2. **Em n≈120 e n≈250:** o mesmo critério, sem alteração, passa a ter 80% de
   poder para rho=0,3 e rho=0,2 respectivamente. É aí que um "RUÍDO" começa a
   significar algo.
3. **Se der VALIDADO:** o Spearman é só o primeiro portão. Vem **Sharpe líquido
   por trade** (com `cost_policy.py`, e o modelo calibrado para o instrumento
   certo) e **DSR ≥ 0,95** contra o `N` de tentativas do `trials.json` — que hoje
   é 7 e sobe a cada coisa nova que for registrada. **Nada disso autoriza capital.**
4. **Rodar o PBO** (`analyzers/pbo.py`) sobre o conjunto de configurações
   consideradas, antes de acreditar em qualquer resultado positivo.

### Fase 3 — Ramos condicionais (só depois da Fase 2)

- **Se a H6 for refutada:** a linha do LLM terá acumulado **quatro encarnações sem
  resultado positivo** — `v1-direct-gemini-h7` (ancestral pré-protocolo), H4
  (encerrada por amostra insuficiente), H5 (NO-GO formal) e H6 —, das quais duas
  com veredito formal. O caminho honesto é o **B4** (meta-análise: o que as
  refutadas têm em comum?) antes de gastar a próxima tentativa — que seria a 8ª do
  registro, e o DSR desconta por ela —, e/ou promover a **H7** (macro/DXY), cuja
  infraestrutura já existe e cuja coleta nunca começou.
- **Se a H6 for validada:** `signal_adapter.py` já existe e já recusa família
  congelada; o gargalo passa a ser venue real — **decisão humana, adjacente a
  capital**, não tarefa técnica.
- **B9 (LLM propõe hipóteses):** implementado, mas **não ativado**. Faltam
  deliberadamente duas coisas fora do código: (3) registrar a trial com `metric`
  declarado e (4) coletar dado **depois** disso. Os pré-requisitos (1) DSL com
  prova de não-leakage e (2) atestado válido já estão cumpridos. **Risco a
  respeitar:** propor fica barato e escalável; gerar centenas de fatores e
  escolher o melhor é data-snooping industrializado — mais rápido, não mais
  válido. Por isso o PBO entrou no mesmo PR. **PBO alto significa parar de
  propor, não propor mais.**

### Fase 4 — Engenharia sem prazo (não bloqueia nada)

Bloqueado por rede neste ambiente: C-03 (consenso ao vivo), equivalência ETH/SOL
(429), CPI/PPI no calendário (`bls.gov`). Disponível a qualquer momento: decidir
o destino de `services/`.

---

## 8. Invariantes — o checklist que não se negocia

Antes de qualquer mudança, confira que continua tudo verdadeiro:

1. `capital_authorized`, `leverage_authorized`, `llm_direct_trading_authorized`
   permanecem **`false`**.
2. H1, H2, H3, H5 permanecem **`CLOSED_NO_GO`**; H4 permanece
   `CLOSED_INSUFFICIENT_SAMPLE`. Nenhuma é reaberta ou reparametrizada.
3. `funding_oi_hmm_v3` permanece em `frozen_families`.
4. A definição da H6 (gate `n≥30`, trava `registered_at`, fonte reservada)
   permanece com o hash de `charters/h6_definition_frozen.json`. Rode
   `python -m scripts.freeze_h6_definition --check` a cada deploy; **hash
   divergente é bloqueante até investigação humana**.
5. `trials.json` **só é escrito por decisão humana explícita** — nunca por
   automação, nunca por um assistente por conta própria. Ele é o denominador do
   DSR: inflá-lo em silêncio corrompe todos os vereditos passados e futuros.
6. Ideia nova entra como **item B do backlog**, não como trial. Vira trial só com
   pré-registro, `metric` declarado e atestado válido.
7. Ferramenta de avaliação (`pbo`, `gate_power`, `ground_truth_harness`,
   `judge_calibration`) **não emite veredito** e não consome tentativa.
8. Nunca abrir os 5 logs históricos do incidente SerpAPI em texto bruto.

---

## 9. Comandos

```bash
# suíte offline, sem chaves (723 verdes + 2 skips; com --all-extras sao 738)
uv sync --locked --extra test
uv build                      # test_distribution_security.py inspeciona dist/
uv run pytest -q

# ciclo de coleta
uv run python -m GarimpoInvestimentos.main --ingest --discover 10   # máx 20 (cota free tier)
uv run python -m GarimpoInvestimentos.main --summary                # gera previsões carimbadas
uv run python -m GarimpoInvestimentos.analyzers.backtest            # juiz + DSR + H6

# publicar o estado da H6 para fora da máquina de coleta
uv run python -m GarimpoInvestimentos.quality_snapshot              # grava h6_status.json SE mudou
git add GarimpoInvestimentos/h6_status.json && git commit           # <- o passo que falta sempre

# governança
uv run cripto-predictor-job attest-renew                            # renova se faltar <2 dias
uv run python -m scripts.freeze_h6_definition --check               # hash da definição da H6

# jobs operacionais (lock, heartbeat, artefato esperado)
uv run cripto-predictor-job phase1 | backtest | watchdog | v3-daily
                                   | observation-daily | observation-live | microstructure-live
```

---

## 10. O padrão que vale levar para a próxima sessão

Ao longo da revisão de 2026-08-21, os defeitos encontrados quase nunca foram
código quebrado. Foram **afirmações desatualizadas ou vazias**: documentação
descrevendo estado já superado, testes sintaticamente corretos e semanticamente
nulos (uma asserção que não podia falhar; um teste de arquivo corrompido que
usava entrada não-corrompida), e um artefato de auditoria que nunca teve
conteúdo.

Num projeto que audita a si mesmo com este rigor, **o que ninguém testa é
justamente o que se afirma sobre ele** — e a contagem de testes verdes mede
consistência interna, não correção. Foi exatamente essa a crítica que a auditoria
da DPL registrou em jul/2026 sobre este mesmo projeto. Vale relê-la antes de
confiar em qualquer número deste documento sem reexecutá-lo.
