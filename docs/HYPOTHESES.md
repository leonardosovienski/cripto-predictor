# Pré-registro de Hipóteses — protocolo anti-data-snooping

> Regra do projeto (complementa o `trials.json`): **hipótese se registra ANTES de rodar.**
> O trials.json conta as tentativas (denominador do DSR); este arquivo registra o que
> cada tentativa esperava encontrar e qual era o critério de sucesso — para que um
> resultado positivo futuro não possa ser reescrito como "era o que sempre buscávamos".

## Formato

```
### H<N> — <nome curto>            (status: registrada | rodando | confirmada | refutada)
- Data do registro:
- Hipótese (mecanismo causal, 1-2 frases):
- Configuração (entra no trials.json como):
- Critério de sucesso (definido ANTES):
- Resultado (preenchido DEPOIS):
```

## Registro

### H1 — Funding/OI + regime HMM prevê retorno 24h (status: **refutada**)
- Data do registro: retroativo (V3, jun/2026 — pré-protocolo)
- Hipótese: desequilíbrio de alavancagem (funding z-score × ΔOI) condicionado ao regime
  do HMM prevê o retorno spot de 24h.
- Configuração: `v3-hmm-funding-oi-fr90`.
- Critério: PSR ≥ 0,80 ∧ IC_lo(Spearman) > 0 ∧ MaxDD < 20% — **líquido de custos**.
- Resultado (2026-07-02): **NO-GO.** Bruto +0,44bps/sinal morre em ~0,53bps de custo
  (BTC líquido −0,09bps, PSR 0,445; ETH PSR 0,051). Kelly-invariante.
- Confirmação independente (2026-07-09, auditoria cruzada): WFA re-rodado na base
  ESTENDIDA (2021→jul/2026) reproduz o NO-GO por caminho diferente — IC_lower do
  Spearman **−0,079 (cruza zero) mesmo com os custos da época da homologação**, e o
  PSR sem sobreposição de janelas (scripts/psr_nonoverlap.py) reprova 0/3 sub-séries.
  Além de os custos comerem o sinal, o edge bruto NÃO se sustentou no forward
  2025-26 — o "GO" de jun/2026 (pré-custos, dados até out/2024) está duplamente
  superado. O juiz tem poder comprovado (controle positivo oficial,
  scripts/attest_harness.py): o NO-GO é veredito, não cegueira. Implicação
  registrada no HANDOFF: **não promover a capital real em 28/07**.

### H2 — Janela curta de funding (fr21) melhora a sensibilidade (status: **refutada**)
- Data do registro: 2026-07-02 (antes do resultado com custos).
- Hipótese: z-score de 7 dias reage mais rápido a squeezes que o de 30 dias.
- Configuração: `v3-hmm-funding-oi-fr21`.
- Critério: idêntico ao H1, líquido de custos.
- Resultado (2026-07-02): **NO-GO.** PSR 0,215; bruto +0,07bps → líquido −0,37bps/sinal;
  MaxDD 25,8%. Janela curta piora vs fr90 — mais ruído, não mais sensibilidade.

### H3 — Horizonte maior amortiza a fricção (status: **refutada**)
- Data do registro: 2026-07-02 (antes do resultado).
- Hipótese: a fricção é fixa por trade (~30bps round-trip em posição cheia); com
  horizonte 48h o edge por sinal dobra de espaço enquanto o custo fica ~constante
  (funding ×2, fee/slip iguais) → o líquido pode cruzar para positivo.
- Configuração: `v3-hmm-funding-oi-fr90-h48` (registrada no trials).
- Critério: idêntico ao H1, líquido de custos.
- Resultado (2026-07-02): **NO-GO — e informativo.** Em 48h o edge bruto VIRA NEGATIVO
  (−0,35bps → líquido −0,75bps/sinal; PSR 0,192; MaxDD 50,3%). O sinal de funding/OI é
  de vida CURTA: esticar o horizonte destrói em vez de amortizar. Aprendizado real:
  qualquer variação futura desta família deve ir na direção OPOSTA (mais convicção e
  menos trades no MESMO horizonte, não horizontes maiores).

### H4 — Score do LLM prevê retorno D+7 (status: **encerrada sem veredicto — coleta interrompida**)
- Data do registro: formalização em 2026-07-02 (hipótese original do projeto).
- Hipótese: LLM sobre indicadores + notícias produz score com correlação positiva com
  o retorno de 7 dias, no universo do discovery (condicional à pré-seleção momentum).
- Configuração: `v2-dpl-gemini-h7`.
- Critério: Spearman IC95 não cruza zero ("validado") com n ≥ 30 previsões maduras,
  estratificado por Fonte; depois disso, Sharpe líquido por trade + DSR ≥ 0,95.
- Resultado: (coleta diária em andamento; n=5 previsões, D+7 imaturo)
- Parcial (2026-07-08, fechamento automático do backtest): primeiro Sharpe por-trade
  maduro da trial 1 = **−0,5734** (n pequeno, estrato único — NÃO é veredicto; o
  critério pede n ≥ 30). Registrado para que a decisão de continuidade da Fase 1
  (prazo 28/07, ver HANDOFF) seja tomada olhando o número, não a memória.
- Encerramento (2026-07-10, decisão do dono): coleta interrompida com **n=5**
  (imaturo — sem veredicto estatístico) para migrar ao modo multi-provedor
  (risco iminente de estouro da cota do Gemini: 22 ativos vs ~20/dia do free
  tier; estourar a cota = dias de coleta perdidos sem querer). Substituída pela
  H5/`v2-dpl-multi-h7`. As 5 previsões coletadas permanecem no histórico,
  carimbadas com o juiz gemini — não se misturam com a série nova.

### H5 — Score do LLM prevê retorno D+7, partição multi-provedor (status: **REFUTADA / NO-GO — 2026-07-28**)

> **VEREDITO, gate executado na data pré-registrada.** Rodado pelo backtest de
> produção, com o critério congelado em 2026-07-10 e sem nenhuma alteração.
>
> ```
> D+7 pooled     Spearman -0.166  [IC95 -0.266; -0.057]  n=440
>                IC NAO cruza zero — na direcao OPOSTA a hipotese
> fonte da trial Spearman -0.161  [IC95 -0.264; -0.050]  n=431
> Sharpe/trade   -0.3120  (n=134)
> DSR            0.00  contra corte 0.95   (SR0 0.447, N=7)
> acuracia dir.  45.2% (199/440) — abaixo de cara-ou-coroa
> estrategia     score>=60 rendeu -6.80%  vs  buy&hold BTC +0.99%
> ```
>
> **Por juiz:** gemini −0,262 [−0,374; −0,140] n=239 (IC fora de zero,
> negativo); groq −0,184 [−0,420; +0,067] n=66 e mistral +0,026 [−0,180;
> +0,238] n=110 (ambos cruzam zero); cerebras −0,483 [−0,765; +0,102] n=22
> (cruza zero e n<30).
>
> **Ressalva registrada por honestidade, que não altera o veredito:**
> separados, nem o estrato de input completo (−0,108 [−0,250; +0,046], n=217)
> nem o de input degradado (+0,099 [−0,093; +0,289], n=123) atingem
> significância. O critério pré-registrado julga o **pooled** com os estratos
> reportados, e o pooled é significativo na direção errada. Escolher estrato
> depois de ver o resultado é exatamente o que o pré-registro existe para
> impedir.
>
> É a **quarta** encarnação desta família a terminar em correlação negativa
> (v1, H4, H5) ou nula. O padrão é consistente e mede-se em centenas de
> observações, não em ruído.
- Data do registro: 2026-07-10 (ANTES de qualquer resultado do modo multi).
- Hipótese: a mesma da H4 (LLM sobre indicadores + notícias produz score com
  correlação positiva com o retorno D+7), agora com os ativos particionados de
  forma FIXA e determinística entre 4 juízes (gemini/groq/cerebras/mistral,
  sha256 do nome mod 4) — cada ativo tem sempre o mesmo juiz, e o carimbo
  `judge` por previsão permite estratificar por juiz na análise.
- Configuração: `v2-dpl-multi-h7`.
- Critério de sucesso (definido ANTES): idêntico ao da H4 — Spearman IC95 não
  cruza zero com n ≥ 30 previsões maduras, estratificado por Fonte (e agora
  também reportado por juiz); depois, Sharpe líquido por trade + DSR ≥ 0,95.
  Um juiz individual só é julgado com n ≥ 30 no SEU estrato.
- Resultado: (coleta iniciada em 2026-07-10)
- Parcial (2026-07-20, leitura do backtest de produção, NÃO é o veredito
  final — decisão fica pra janela de 28/07): D+7 pooled (v1+H4+H5), n=198,
  Spearman −0,255 [IC95% −0,377, −0,120] — **validado, IC não cruza zero,
  na direção OPOSTA à hipótese**. Sharpe por-trade isolado de `v2-dpl-multi-h7`:
  −0,6725 (n=45). DSR 0,00, não passa o corte 0,95. Estratégia (score≥60)
  perde do buy&hold do BTC (−6,87% vs +0,67%). Por juiz com n suficiente:
  gemini −0,330 (n=159, IC fora de zero), groq −0,585 (n=12, IC fora de
  zero), mistral −0,023 (n=20, IC cruza zero = ruído p/ ele). Mesmo padrão
  que encerrou a H4. Motivou o pré-registro da H6 (inversão do sinal).

### H6 — Sinal invertido do LLM prevê retorno D+7 (status: **CLOSED_INSUFFICIENT_SAMPLE — errata 2026-09-07**)

> **Errata CRIPTO v1.2 — 2026-09-07:** H6 não é refutação estatística:
> IC95 cruza zero e o poder em n=84 é 23% para rho=0,2. O estado corrente é
> CLOSED_INSUFFICIENT_SAMPLE; H9 recebe a mesma classe (só 1/45 folds avaliável).
> Ambos continuam encerrados. Referências históricas a CLOSED_NO_GO ou coleta
> H6 aberta ficam superadas por `charters/scientific_state.json` e pela errata
> de `docs/HYPOTHESES.md`. Não houve mudança de coleta, parâmetros ou selos.


> **Veredito 2026-09-04.** Gate atingido (`h6_status.json`): n=84 (≥30 exigido),
> Spearman rho=-0,0567, IC95% [-0,2312, 0,1294] — **o IC CRUZA ZERO**.
> `veredito: "RUIDO (IC cruza 0)"`. O critério pré-registrado (Spearman IC95 sem
> cruzar zero, positivo, n≥30, SOB A CONFIGURAÇÃO INVERTIDA) não foi atingido —
> refutada pelo próprio critério que a trial definiu antes de qualquer dado
> contar. O Sharpe auxiliar de n=6 (+0,3479) citado nas erratas abaixo nunca foi
> o veredito; o veredito sempre foi o IC do Spearman em n≥30, e é isso que
> fechou agora. Não autoriza capital — nenhum gate deste ecossistema autorizaria.

> **Errata de 2026-07-28.** O status abaixo dizia "registrada — não ativada" e
> o item (2) das condições dizia que o código "não existe ainda — nem no
> backtest nem na coleta". **Isso deixou de ser verdade em `556f5ad`
> (2026-07-20)**, que implementou `close_h6_inverted_signal` e a ligou ao ciclo
> noturno. A H6 amadurece sozinha desde então, com a trava anti-data-snooping
> exigida: só entram previsões com `pred_date` POSTERIOR ao `registered_at`
> dela, e o `params.fonte` segue reservado para nunca casar com o mecanismo
> genérico.
>
> Estado real em 2026-07-28: **sharpe +0,3479 com n=6**. É o único Sharpe
> positivo do registro do cripto — e **não é veredito nenhum**: o critério
> pré-registrado exige **n ≥ 30** e IC95 sem cruzar zero. Com n=6 não há IC
> que decida coisa alguma. Citar esse +0,3479 como sinal de que "a inversão
> funciona" seria exatamente o erro que este documento existe para impedir.
>
> Efeito colateral medido, registrado por transparência: esse Sharpe positivo
> é o que mais infla a variância entre tentativas, e portanto o `SR0` do
> projeto — 0,447 com ele, 0,332 sem. **O veredito da H5 não depende disso**:
> o Sharpe dela é −0,312, negativo, e o DSR fica ~0 com qualquer `SR0`
> positivo. Verificado antes de registrar o veredito, justamente para que ele
> não fosse artefato desta contaminação.
>
> **Errata de 2026-08-01 — gap de cálculo fechado.** Até aqui, o `sharpe`
> acima era a ÚNICA estatística automatizada da H6 — o critério de veredito
> pré-registrado (Spearman IC95 sobre a leitura invertida, não o Sharpe) não
> tinha nenhum cálculo automatizado em código; teria que ser feito manualmente
> quando n chegasse a 30. `h6_spearman_verdict()` (`analyzers/backtest.py`),
> ligada ao mesmo ciclo noturno de `close_h6_inverted_signal`, fecha isso:
> aplica a MESMA trava anti-data-snooping (só `pred_date` posterior ao
> `registered_at`, só `fonte==dpl:fallback`) sobre `(100−score, retorno)` e
> roda a mesma regra do juiz da Fase 1 (`spearman_block_ci`, IC não cruzando
> zero). Abaixo de n=30 ela deliberadamente só reporta a contagem, nunca
> rho/IC — evitar repetir com esta métrica o mesmo erro de leitura prematura
> que o Sharpe de n=6 já ilustrou acima. Não roda produção ainda: isto é
> implementação, não resultado — o estado real de n permanece o mesmo até a
> próxima leitura de `logs/operations/GarimpoBacktest.log`.

> **Errata de 2026-08-24 — o cabeçalho acima ficou desatualizado, e a
> correção é estrutural, não pontual.** O cabeçalho desta seção chegou a
> afirmar "n=6 de 30" muito depois de o `n` real já ter mudado — o número
> só é atualizado quando alguém edita este arquivo, e ninguém tem obrigação
> de lembrar disso a cada execução do ciclo noturno. É o mesmo defeito, em
> forma de prosa, que `GarimpoInvestimentos/h6_status.json` (PR #40) existe
> para resolver em forma de dado: uma única fonte, publicada por commit
> humano, em vez de um número copiado à mão em documentos que divergem.
>
> O cabeçalho não cita mais um `n` — cita o arquivo. **Última leitura
> commitada, 2026-08-22T14:14:51Z: n=0** (legítimo: zero previsões haviam
> maturado em D+7 até aquele momento; não é banco vazio). Para o número
> atual, leia `h6_status.json`, nunca este parágrafo.
>
> A referência ao log em `logs/operations/GarimpoBacktest.log`, no
> parágrafo acima, também ficou obsoleta — esse caminho é de uma era
> pré-`predictor_ops`; o heartbeat real do backtest vive em
> `<state_root>/cripto-backtest/heartbeat.json` (corrigido em `watchdog.py`
> no mesmo commit desta errata, junto com o mesmo defeito no caminho do
> banco que o watchdog lia).
- Data do registro: 2026-07-20 (ANTES de qualquer resultado dedicado a esta
  configuração).
- Hipótese: as 3 encarnações anteriores da mesma família (H4/`v2-dpl-gemini-h7`,
  `v1-direct-gemini-h7`, H5/`v2-dpl-multi-h7`) mostraram correlação NEGATIVA e
  estatisticamente significativa entre score do LLM e retorno D+7 (relatório de
  produção 2026-07-20: Spearman −0,255, IC95% [−0,377, −0,120], n=198 pooled —
  IC não cruza zero, mas na direção oposta à hipótese original). Inverter a
  leitura (score alto = sinal de QUEDA, score baixo = sinal de ALTA) pode
  capturar esse padrão em vez de ser derrotado por ele.
- Configuração: `h6-sinal-invertido-d7` — `params.fonte` deliberadamente
  `reserved:h6-inversao-sinal` (nunca aparece em `predictions.fonte` real), pra
  `close_trial_sharpes()` do backtest NUNCA amadurecer esta trial sozinha com
  dado da coleta atual (não-invertida). A maturação dedicada foi implementada
  em `close_h6_inverted_signal()` e só aceita previsões posteriores ao registro,
  como documentado na errata acima. H6 continua sendo pesquisa de correlação:
  não produz `TradeIntent`, não autoriza shadow e não permite decisão direta de
  trading por LLM.
- ⚠️ **Risco de data-snooping explícito, registrado por honestidade**: a ideia
  nasceu observando o resultado negativo das trials anteriores — pré-registrar
  agora não elimina esse viés de origem, só impede que o CRITÉRIO de sucesso
  seja reescrito depois de ver o resultado. O veredito desta trial só é válido
  com amostra coletada DEPOIS do registro, nunca reaproveitando as previsões
  já vistas (v1/H4/H5).
- Critério de sucesso (definido ANTES): idêntico ao da H4/H5 — Spearman IC95
  não cruza zero (positivo desta vez) com n ≥ 30 previsões maduras SOB A
  CONFIGURAÇÃO INVERTIDA; depois, Sharpe líquido por trade + DSR ≥ 0,95.
- Resultado histórico, superado pela errata 2026-09-07: **REFUTADA — IC cruza zero em n=84** (ver veredito 2026-09-04 no
  topo desta seção). Histórico intermediário preservado acima por transparência
  (n=6, Sharpe auxiliar +0,3479) — nunca foi o veredito, só uma leitura
  imatura de passagem.

### H7 — Calendário macro (FOMC/CPI/PPI) + DXY como contexto exógeno de regime (status: **registrada em `trials.json` 2026-09-04; backtest TENTADO e abortado por bug de infraestrutura em 2026-09-04, sem veredito válido — `REGISTERED_NOT_ACTIVATED`**)
- Data do registro: 2026-08-14 (ANTES de qualquer coleta ou resultado). Promove o
  item B1 do backlog condicional (abaixo) — ativação estava liberada desde o
  veredito da H4 (2026-07-10), formalizada agora.
- Hipótese (mecanismo causal): eventos macro conhecidos com antecedência (reunião
  do FOMC, divulgação de CPI/PPI) e o nível/variação do DXY carregam informação
  sobre o regime de risco do mercado cripto — mercado tende a reduzir
  alavancagem/exposição na véspera de eventos de alta incerteza macro, e um DXY
  em alta/queda forte é contexto de fluxo para ativos de risco. Isso é ORTOGONAL
  a tudo já testado (H1-H6): nenhuma trial anterior olhou agenda macro ou câmbio.
- Configuração (entra no trials.json quando ativada): dummy de janela de evento
  (±N dias, N a definir no in-sample) por tipo de evento (FOMC/CPI/PPI) +
  nível/retorno do DXY, como feature adicional — não como sinal isolado. Duas
  integrações possíveis, a decidir com dado real em mãos antes de qualquer
  backtest: (a) covariável exógena do HMM do V3 (`v3/regime_engine.py`), ou (b)
  contexto adicional no prompt do juiz LLM (Fase 1). Qualquer uma das duas conta
  como trial NOVA própria — não é reaproveitamento de H1-H6.
- Estado de governança: ainda não é uma trial ativa e, por isso, não entra no
  denominador antes da escolha prévia de uma das integrações. Dados observados
  para completar/calibrar a formulação não podem depois ser reutilizados como
  OOS. A ativação exige atestado de poder válido e registro em `trials.json`.
- Critério de sucesso (definido ANTES): idêntico em espécie ao das famílias
  anteriores — líquido de custos quando aplicável ao V3 (PSR ≥ 0,80, IC_lo > 0),
  ou Spearman IC95 não cruzando zero com n ≥ 30 quando aplicável à Fase 1 —
  critério exato a fixar por escrito no momento da ativação (antes de rodar),
  igual às demais.
- O que foi implementado nesta sessão (infraestrutura, não resultado):
  `GarimpoInvestimentos/dpl/providers/dxy.py` (DXYProvider, stooq.com, CSV
  público sem chave — endpoint não verificado ao vivo, ambiente de
  desenvolvimento sem rede externa liberada) e
  `GarimpoInvestimentos/dpl/macro_calendar.py` (loader do calendário +
  `macro_event_signal_points`, dummy de janela por tipo de evento).
- Atualização 2026-08-14 (mesmo dia, sessão seguinte): `WebFetch` continua
  bloqueado pelo egress proxy do ambiente para qualquer host externo (inclusive
  `federalreserve.gov`, `bls.gov` e `stooq.com` — testado e confirmado); só
  `WebSearch` (busca com resumo, sem acesso direto à página) funciona. Com isso,
  `GarimpoInvestimentos/macro_calendar.json` (renomeado de `.example.json`) foi
  preenchido com as 8 datas do FOMC 2026 — corroboradas por múltiplas fontes
  independentes no WebSearch, ver `source_note` no próprio arquivo para a
  proveniência completa. **CPI/PPI continuam vazios**: a busca só devolveu
  calendário parcial (faltaram meses inteiros) — sem fonte primária confiável
  disponível nesta sessão, nenhuma data foi adivinhada para preencher o buraco.
- Atualização 2026-08-14 (dono testou ao vivo, na própria máquina): o endpoint
  de CSV do stooq.com passou a exigir um desafio anti-bot em JavaScript
  (resposta HTTP 200 com página "verify your browser", não CSV) — confirmado
  contra os 3 símbolos candidatos (`usd_i`, `dx.f`, `dx.c`). Não é algo pra
  contornar (seria burlar um mecanismo anti-scraping de propósito). O
  `DXYProvider` foi trocado para o **FRED** (`fredgraph.csv`, série
  `DTWEXBGS` — Nominal Broad U.S. Dollar Index, dado oficial do Federal
  Reserve, sem chave, sem desafio anti-bot). `publish_lag_days=1` é
  conservador (o release H.10 sai com defasagem de ~1 dia útil; o valor exato
  não foi confirmado contra o texto oficial do release).
- Atualização 2026-08-14 (mesmo dia, validação ao vivo pelo dono): primeira
  tentativa contra o FRED rodou (sem erro de rede/HTTP) mas devolveu "nenhuma
  linha válida" — o `curl -v` mostrou por quê: o CSV do FRED usa
  `observation_date` como nome da primeira coluna, não `DATE` como o código
  assumia. Corrigido; teste de regressão com os bytes reais devolvidos
  (`observation_date,DTWEXBGS\n2006-01-02,101.4155...`) adicionado em
  `tests/test_dpl_dxy.py` pra travar contra reintroduzir esse erro. Nota à
  parte: `Invoke-WebRequest` do PowerShell deu timeout contra esse mesmo
  endpoint enquanto `curl.exe` respondeu rápido — possível inspeção de TLS do
  proxy corporativo afetando um cliente especificamente; sem efeito no
  `httpx` que o provider usa, mas vale observar se aparecer timeout em
  produção. **Ainda pendente:** confirmar que a correção da coluna funciona
  de ponta a ponta rodando `DXYProvider().fetch()` ao vivo de novo (só o
  `curl` cru foi validado até aqui, não o parsing do provider contra a
  resposta real).
- Resultado (preenchido DEPOIS): não iniciado (calendário FOMC pronto, DXY
  reapontado para o FRED com o bug de coluna corrigido, mas o `fetch()` do
  provider ainda não foi confirmado ao vivo de ponta a ponta; nenhum dado
  coletado). Pendências antes de qualquer dado: (1) preencher CPI/PPI a
  partir da fonte oficial (requer acesso direto a bls.gov, indisponível nesta
  sessão), (2) validar ao vivo o `DXYProvider` contra o FRED e confirmar o
  `publish_lag_days` real do H.10, (3) `--ingest`, `--summary` e a coleta
  `observation-daily` do Binance têm a mesma limitação de rede (e, para a
  Fase 1, precisam de chaves reais de LLM/notícias), (4) decidir e
  implementar a integração V3 vs. Fase 1, (5) só então começar a coletar
  dado GENUINAMENTE NOVO sob esta configuração.
- **Checklist de ativação consolidado (2026-09-04, revisão de status — não altera
  critério nem mecanismo acima, só reafirma o que falta em formato acionável):**
  1. ✅ CPI/PPI preenchido em `macro_calendar.json` (verificado em fontes
     primárias 2026-08-31; 33 eventos carregam sem erro via `load_macro_calendar()`).
  2. ✅ **Validação ao vivo já registrada no docstring de `dxy.py`**: endpoint
     revalidado em 2026-08-31, retornou observações válidas de 2026-08-24 a
     2026-08-28 com `source=fred`, sem interpolar feriados (achado ao revisar
     o código em 2026-09-04 — o checklist anterior não tinha conferido isso).
  3. ✅ **`publish_lag_days` corrigido para dias ÚTEIS em 2026-09-04**
     (`_add_business_days`, `GarimpoInvestimentos/dpl/providers/dxy.py`),
     depois de pesquisa via WebSearch (fetch direto de federalreserve.gov/
     fred.stlouisfed.org segue bloqueado neste ambiente — não é fonte
     primária lida diretamente, é achado de busca): a tabela semanal oficial
     do H.10 sai segunda-feira 16h15, e a série `DTWEXBGS` específica mostrou
     um exemplo concreto de dado de sexta publicado na segunda seguinte — lag
     em dias úteis, não corridos. A versão anterior (dias corridos) podia
     declarar um dado disponível cedo demais perto de fim de semana (sexta+1
     dia corrido = sábado, quando o dado real só sai na segunda) — era risco
     de look-ahead, não só imprecisão. 4 testes novos cobrem sexta→segunda,
     lag=2 dias úteis, e os casos de borda (`n<0`, `n=0`).
  4. ✅ **Decisão tomada (2026-09-04): integração (a) — covariável exógena do
     HMM em `v3/regime_engine.py`.** Critério de sucesso confirmado: PSR≥0,80 ∧
     IC_CI_lower>0, líquido de custos (mesmo gate de H1-H3).
  5. ✅ `pipeline_fingerprint` coberto pelo atestado do harness já válido
     (expira 2026-09-10; não precisou renovar).
  6. ✅ **Registrada em `trials.json` em 2026-09-04T08:36:02Z** (nome:
     `h7-macro-dxy-hmm-v1`), `metric="psr"`, `pipeline_fingerprint` conferido
     pelo próprio `register_trial()` contra o atestado do V3 válido (expira
     2026-09-10). `charters/scientific_state.json` atualizado:
     `hypotheses.H7="REGISTERED_NOT_ACTIVATED"`,
     `hypothesis_trials.H7="h7-macro-dxy-hmm-v1"`.

  **Ressalva sobre os itens 2-3, que persiste mesmo registrada**: nenhum dos
  dois foi confirmado por leitura direta da fonte primária NESTA sessão (rede
  segue bloqueada aqui) — o item 2 é evidência já existente no repo (sessão
  anterior, na máquina do dono), e o item 3 é achado de busca (WebSearch), não
  fetch direto da página oficial do Fed. O registro em `trials.json` é válido
  (o mecanismo de proteção do core não exige isso), mas ambos ficam mais
  fortes se o dono confirmar diretamente
  https://www.federalreserve.gov/releases/h10/ na própria máquina antes de
  tratar qualquer resultado futuro como definitivo.

  **Infraestrutura do item 4 implementada e testada em 2026-09-04** (código +
  40 testes novos, suíte inteira 892/892 verde, `ruff check` limpo):
  - `v3/regime_engine.py`: `RegimeEngine(extra_features=...)` — covariáveis
    extras opcionais no HMM (`macro_event_dummy`, `dxy_return_1d`). Default
    `()` preserva EXATAMENTE o comportamento de H1-H3 (mesmo fingerprint, testado
    bit-a-bit); com `extra_features`, o fingerprint muda e um modelo H7 nunca
    carrega como se fosse H1-H3 (`StaleRegimeModelError`). Invariância
    anti-lookahead reconfirmada com a covariável extra ativa.
  - `v3/macro_features.py` (novo): `build_macro_event_dummy` (dummy de janela
    ±N dias, reusa `dpl.macro_calendar` puro, sem rede) e `build_dxy_return`
    (retorno 1d do DXY, respeitando `publish_lag_days`, lido de um CSV local
    via `load_dxy_daily_closes` — não busca nada na rede; o CSV é gerado
    offline pelo `DXYProvider` na máquina do dono).
  - `v3/backtest_v3.py`: `--use-macro-dxy` (+ `--macro-window-days`,
    `--dxy-closes`). Desligado por padrão, comportamento idêntico ao
    congelado. Testado ponta a ponta com dado sintético
    (`tests/test_v3_macro_dxy_integration.py`): roda o WFA completo com a
    flag ligada e confirma que o resultado sem a flag não muda.
  - Testes novos: `tests/test_v3_regime_engine_extra_covariates.py` (8),
    `tests/test_v3_macro_features.py` (12), `tests/test_v3_macro_dxy_integration.py` (3).

  **O que ainda falta antes de registrar de verdade**: rodar os itens 2-3
  (rede real) na máquina do dono, e coletar o CSV de DXY histórico
  (`load_dxy_daily_closes`) via `DXYProvider` para alimentar `--dxy-closes` em
  produção. Só então `registered_at` pode ser cravado e a coleta prospectiva
  começar.

  **Correção de infraestrutura 2026-09-04 — instabilidade numérica do HMM,
  ANTES de qualquer leitura OOS válida.** Primeira execução real do backtest
  H7 (`--use-macro-dxy`, dado de produção do dono) quebrou: `covariance_type=
  "full"` com as 4 dimensões (2 originais + 2 do H7) e estados raros (às
  vezes <1% da amostra num fold IS de ~180d) convergiu, via EM, para
  covariância quase singular — `'covars' must be symmetric,
  positive-definite'`. TODOS os 15 folds do run dispararam `Model is not
  converging`; nenhum produziu veredito válido (a maioria `INSUFFICIENT_DATA`
  ou "sem sinais ativos no OOS"). Duas correções, nesta ordem:
  1. Retry de `random_state` alternativo (42→46) antes de desistir — ajudou
     em 2/15 folds, mas 1 fold esgotou o orçamento mesmo assim. Sintoma
     tratado, não causa.
  2. Causa raiz: `covariance_type` agora é **por instância**
     (`_covariance_type_for()`), não mais uma constante global — `"full"`
     continua fixo para H1-H3 (sem `extra_features`, comportamento congelado
     bit-a-bit, nunca muda), `"diag"` para qualquer modelo com
     `extra_features` (H7+). "diag" estima variância por feature sem
     covariância cruzada entre elas, o que remove estruturalmente a
     superfície onde a matriz pode ficar não-positiva-definida. O
     fingerprint do modelo passou a incluir `covariance_type`, então H1-H3 e
     H7 continuam mutuamente incarregáveis por dois motivos independentes
     (features E tipo de covariância).
  Esta é uma decisão de infraestrutura, tomada porque NENHUM fold do run
  anterior tinha produzido leitura válida — não é reação a um resultado
  científico do H7, que continua sem nenhum veredito.

---

### H9 — Razão OI/Volume (crowding especulativo) como covariável exógena do regime (status: **CLOSED_INSUFFICIENT_SAMPLE — errata 2026-09-07**)

> Um fold avaliável não isola a covariável nem demonstra ausência de efeito.
> Histórico abaixo preservado; fechamento mantido sem refutação causal.

> **Veredito 2026-09-04.** Primeiro WFA completo rodado em produção
> (`backtest_v3.py --use-oi-volume-ratio`, BTCUSDT, dado real, sem crash —
> a correção `covariance_type="diag"` do H7 funcionou aqui de primeira,
> nenhum retry de seed necessário). Gate pré-registrado:
> ```
> PSR agregado : 0.1621  (exige >= 0.80)
> IC Spearman  : 0.0283  IC_CI_lower: -0.1476  (exige CI_lower > 0 — CRUZA ZERO)
> MaxDD        : 11.49%  (dentro do limite — irrelevante, os dois acima já reprovam)
> Sharpe       : -1.0041
> ```
> **VEREDITO: NO-GO.** PSR muito abaixo do corte e o IC cruza zero — nem PSR
> nem IC atingem o critério pré-registrado. Refutada pelo próprio critério
> que a trial definiu antes de qualquer dado contar. Não autoriza capital —
> nenhum gate deste ecossistema autorizaria.
- Data do registro: 2026-09-04 (ANTES de qualquer backtest rodar). Promove o item B2
  do backlog condicional (abaixo) — ativação exigia "mecanismo causal novo por
  escrito", escrito agora.
- Mecanismo causal (por que seria diferente de H1-H3, mesma família de dado):
  H1-H3 usam o NÍVEL/z-score do funding rate — pressão de carregamento entre
  longs e shorts. H9 usa a razão OI notional / volume spot — mede algo
  ORTOGONAL: o quanto do interesse aberto é sustentado por volume real de
  negociação, vs. posição alavancada acumulada sem giro correspondente
  ("crowding" especulativo). Um funding rate neutro pode coexistir com OI/volume
  extremo (muita alavancagem parada, pouco giro) — cenário que H1-H3 não vê.
  Mecanismo: OI/volume extremo historicamente precede desalavancagem forçada
  (unwind de posição crowded), o que H1-H3 não captura porque olha só o CUSTO
  de carregar a posição (funding), não a FRAGILIDADE estrutural dela (OI vs.
  giro real).
- Por que isso NÃO é reparametrizar H1-H3 (a família congelada `funding_oi_hmm_v3`
  não pode ser reaberta): a feature em si é nova (razão, não nível/z-score de
  funding) e entra como covariável EXÓGENA do HMM (mesmo mecanismo de
  `extra_features` que o H7 já usa), não como substituição de nenhuma feature
  congelada. H1-H3 continuam intocados, byte-idênticos.
- Fonte do dado: 100% já coletado — `KlineRecord.volume` (spot 1h) já existe no
  provider (`ccxt_base.py`, `spot_collector.py`) e já está no disco de qualquer
  ativo com histórico de H1-H3, só nunca foi usado (o builder descartava o campo).
  `oi_notional_usd` já é consumido pelo H1-H3. Zero coleta prospectiva nova
  necessária — pode ser testado contra dado histórico já em mãos, igual H1-H3
  (a integridade anti-lookahead vem do próprio método WFA IS/OOS, não da
  novidade do dado).
- Critério de sucesso (definido ANTES de rodar): idêntico ao gate de H1-H3/H7 —
  PSR ≥ 0,80 E IC_CI_lower(Spearman) > 0 E MaxDD < 20%, líquido de custos,
  via `backtest_v3.py --use-oi-volume-ratio`.
- Risco de p-hacking a vigiar: esta é a família de dado mais próxima da já
  refutada (mesmo funding/OI). Se o resultado vier marginal como H1
  (-0,09bps vs -0,53bps de custo, ver B4 acima), não há espaço para
  "ajustar" parâmetro algum — vira NO-GO e fecha, igual H1-H3.
- Resultado: **REFUTADA — PSR=0,162 (<0,80) e IC cruza zero** (ver veredito
  2026-09-04 no topo desta seção). Terceira família de dado independente
  (funding/OI-nível, LLM-score, agora OI/volume-crowding) a não passar do
  gate — reforça o padrão do B4: nenhum sinal testado até aqui tem magnitude
  suficiente pra sobreviver ao gate estatístico, não só ao custo.


> Registrado em 2026-07-07 (triagem de propostas externas). Nada daqui entra no
> `trials.json` nem consome tentativa: são candidatos a hipótese futura, com
> critério de ATIVAÇÃO explícito. Promover um item = escrever um H<N> completo
> acima (com critério de sucesso ANTES de rodar) + registrar no trials.json.
> Ordenados por relação benefício/custo estimada na triagem.

### B1 — Calendário macro + DXY como features exógenas — **PROMOVIDO a H7 (2026-08-14)**
- Sinal: dummies de evento (FOMC, CPI/PPI — datas conhecidas com antecedência) e
  série do DXY/juros como contexto de regime.
- Fonte: CSV estático de calendário (custo ~zero) + `BCBProvider` já existente como
  precedente de sinal macro com `published_at` correto; DXY via fonte gratuita.
- Ortogonalidade: choque exógeno — nenhum sinal atual quantifica agenda macro.
- Ativação: após veredicto da H4 (não misturar mudança de input com trial em curso).
- Ver H7 acima para o registro completo (mecanismo, critério e o que já foi
  implementado vs. o que ainda falta antes de qualquer coleta real).

### B2 — Derivativos derivados do que JÁ se coleta (OI/volume, funding contínuo)
- Sinal: razão OI/volume spot (especulação vs demanda real) e funding como custo de
  carregamento contínuo (não só extremos); funding consenso multi-exchange via ccxt.
- Fonte: dados de funding/OI da V3 já ingeridos — só recombinação.
- Ortogonalidade: parcial (mesma família da H1-H3 refutada) — o aprendizado da H3
  (sinal de vida curta) LIMITA o desenho: mesma janela, mais convicção, menos trades.
- Ativação: só com mecanismo causal novo por escrito (recombinar features da família
  refutada sem tese nova é convite a p-hacking).
- RESSALVA FACTUAL da triagem: liquidações históricas da Binance NÃO são endpoint
  público simples (forceOrders exige auth; histórico agregado é de provedores pagos)
  — o custo de coleta de liquidações é MAIOR que o proposto originalmente.

### B3 — Feature engineering sobre dados existentes (espectro de momentum/vol)
- Sinal: momentum 3/14/30d, vol EWMA, z-score de volume, correlação rolante com BTC.
- Fonte: OHLCV já na Feature Store; `feature_version` (migração 0007) permite
  backfill de versões novas SEM sobrescrever o que experimentos passados leram.
- Ortogonalidade: baixa-média (deriva de preço/volume) — o ganho é dar espectro ao
  modelo, não fenômeno novo.
- Ativação: após veredicto da H4; CADA conjunto de features testado = trial nova
  (features_used no registro — o schema já suporta).

### B4 — Meta-análise dos NO-GO ("o que as refutadas têm em comum?")
- Sinal: nenhum — é meta-pesquisa sobre trials.json/HYPOTHESES (não conta tentativa).
- Custo ~zero; pode rodar a qualquer momento, MAS com n=3 refutadas da MESMA família
  a resposta hoje é trivial ("custos comem sinais de microestrutura de 24h").
- Ativação: quando houver ≥2 famílias distintas fechadas (ex.: após veredicto da H4).

**Executada 2026-09-04** (condição de ativação atendida: 2 famílias fechadas —
`funding_oi_hmm_v3` e a linha LLM-score/H4-H6). Achados, lendo os vereditos já
registrados em `trials.json`/acima, sem rodar nada novo:

1. **`funding_oi_hmm_v3` (H1-H3): edge existia, mas era minúsculo — morreu no
   custo, não na direção.** Sharpe entre -0.0022 e -0.0132 nas 3 variantes —
   perto de zero, não fortemente negativo. H1 especificamente perdeu por
   margem estreita (líquido -0.09bps vs custo -0.53bps, `costs.py`). Isto é
   diferente do padrão da linha LLM abaixo.
2. **Linha LLM-score (H4→H5→H6): o sinal muda de SENTIDO entre tentativas,
   nunca estabiliza.** H5 (pooled, pré-inversão): Spearman -0.166 [IC95%
   -0.266, -0.057] — significativo, mas na direção OPOSTA à hipótese
   original (score alto devia prever alta, previu queda). H6 inverteu a
   leitura pra capturar exatamente esse padrão oposto — e o resultado, com
   n=84 real, foi rho=-0.057 [IC95% -0.231, +0.129]: **cruza zero, e ainda
   por cima o sinal da correlação voltou a ser levemente NEGATIVO**, não
   positivo como a inversão previa. Ou seja: nem a leitura original nem a
   invertida têm direção estável — o mais provável é que não haja
   correlação real nenhuma entre score do LLM e retorno D+7, só ruído que
   parece ter direção diferente a cada amostra.
3. **Implicação prática pras próximas hipóteses (H7 em diante):** um
   candidato só vale a pena testar se o efeito esperado for GRANDE o
   suficiente pra sobreviver tanto ao custo de transação (H1-H3 mostraram
   que -0.5bps já mata um edge de -0.09bps) quanto à instabilidade de sinal
   pequeno (H4-H6 mostraram que |rho|<0.2 numa família não é confiável nem
   no SINAL, quanto mais na magnitude). Isso não é uma regra formal nova —
   é contexto pra calibrar expectativa, não pra mudar nenhum gate já
   definido.

**Atualização 2026-09-05 — terceira família fechada (H9) muda a leitura.**
O B4 acima rodou com 2 famílias. Desde então o H9 fechou
(`oi-volume-crowding-hmm-covariate`), e ele NÃO segue o padrão descrito no
achado 1. Meta-pesquisa sobre vereditos já registrados — não roda nada novo,
não consome tentativa, não reabre nem reparametriza nada.

4. **O modo de falha do H9 é DIFERENTE, não mais do mesmo.** O achado 1 dizia
   que o edge "morria no custo": Sharpe perto de zero (-0,0022 e -0,0132 em
   H1/H3). O H9 deu **Sharpe = -1,0041** — cerca de 76x mais negativo que a
   pior variante de H1-H3. Isso não é um edge minúsculo comido pelo custo; é
   desempenho ativamente ruim. Acrescentar a covariável exógena não deixou de
   ajudar: coincidiu com uma piora de ordem de magnitude.

5. **O veredito do H9 mistura TRÊS mudanças simultâneas.** Indo de H1-H3 para
   H9, variaram ao mesmo tempo:
   - (a) entrou uma covariável exógena — a hipótese sob teste;
   - (b) `covariance_type` mudou de `"full"` para `"diag"`, forçado pelo próprio
     caminho de código de `extra_features` (ver `_covariance_type_for`);
   - (c) passou a existir imputação silenciosa de `0.0` em pontos sem join,
     valor que não é neutro depois do `StandardScaler` (ver `dxy_coverage`,
     auditoria 2026-09-05).

   O critério pré-registrado testava (a). O experimento variou (a)+(b)+(c).

   **O veredito NO-GO continua válido e não está em discussão:** o critério foi
   definido antes do dado, o resultado reprovou nos dois eixos, a hipótese está
   fechada e não autoriza capital. O que NÃO se sustenta é a atribuição causal
   — "crowding OI/volume não tem sinal" não é conclusão suportada, porque (b) e
   (c) são confundidores não controlados. H9 refutou uma ESTRATÉGIA, não uma
   feature.

6. **O H7 herda exatamente o mesmo confundidor.** Ele usa o mesmo caminho de
   `extra_features`, logo carrega (b) e (c) por construção. Se a degradação vem
   do MECANISMO e não da covariável, o H7 produzirá um NO-GO que não diz nada
   sobre DXY — gastando coleta prospectiva para medir um artefato de
   infraestrutura.

7. **Falta o controle — e ele nunca foi rodado.** Não há, em lugar nenhum do
   repositório, um run de `backtest_v3.py` com `extra_features=()` no mesmo
   símbolo, período e harness do H9. Sem isso, `-1,0041` não tem referência: os
   `-0,0022` de H1 vêm de outro período e outro caminho de código, não são
   comparáveis. O número existe, mas está solto.

   Um controle assim separaria as duas explicações:
   - baseline também ≈ -1,0 → a covariável é inocente; o que mudou foi
     período/harness, e o H9 mediu isso, não crowding;
   - baseline ≈ 0 → acrescentar covariável exógena degrada de verdade, e o H7
     tende ao mesmo destino por razão mecânica, não científica.

   Custo ~zero (dado já coletado, nenhuma coleta prospectiva). **Não executado
   aqui de propósito:** roda a configuração da família congelada `funding_oi_hmm_v3`,
   e mesmo sendo medição de diagnóstico — não altera parâmetro, não registra
   trial, não reabre hipótese — encostar nela é decisão do dono, não de quem
   audita.

**Recomendação de sequência:** rodar esse controle ANTES de iniciar a coleta do
H7. É a diferença entre o H7 testar DXY e o H7 testar o próprio `extra_features`.

### B5 — Sentimento textual como série temporal (separar texto do viés do LLM)
- Sinal: série diária de sentimento das notícias (léxico/contagem), alinhada por
  `published_at`, testável como feature independente do score consolidado do LLM.
- Ortogonalidade: média — permite atribuir o (eventual) alpha da H4 ao texto ou ao LLM.
- Ativação: só se a H4 validar (se o score consolidado não prevê, decompor ele não
  tem urgência).

### B6 — Microestrutura de liquidez (spread, profundidade do book)
- Sinal: spread % médio e profundidade top-10 por snapshot horário → média diária.
- CORREÇÃO da triagem: o custo NÃO é baixo — exige coletor de alta frequência novo,
  storage e operação contínua; e sinais de prazo mais curto enfrentam custos de
  transação PIORES que os que já mataram o sinal de 24h (lição H1-H3).
- Ativação: só com tese explícita de uso em horizonte ≥ D+1 e orçamento de operação.

### B7 — On-chain (net flow p/ exchanges, Coin Days Destroyed)
- Ortogonalidade: alta (comportamento de rede, não deriva de preço).
- Custo: API paga (Glassnode/CoinMetrics) — decisão de ORÇAMENTO, não técnica.
- Ativação: decisão explícita do dono sobre custo recorrente + hipótese isolada.

### B8 — Modelagem de sobrevivência (tempo até evento de risco, não direção)
- Sinal: P(drawdown ≥ X% em ≤ T dias) para sizing/gestão de risco.
- Ativação: SOMENTE se existir edge direcional validado para proteger — gestão de
  risco de um sinal que não existe é polimento de motor desligado (mesma razão da
  rejeição do Regime Shift Detector na triagem de jul/2026).

### B9 — Inverter o papel do LLM: gerador de HIPÓTESES, não preditor

> Registrado em 2026-08-21, a partir de triagem de literatura externa. **Ressalva de
> proveniência:** `arxiv.org` está bloqueado pelo proxy de egress deste ambiente, então
> os papers abaixo foram lidos apenas por RESUMO de busca, não na fonte primária.
> Confirmar antes de promover.

- Mecanismo: a família H4/H5/H6 usa o LLM como PREDITOR — o `opportunity_score` É a
  previsão, e o backtest testa esse número. H4 encerrou sem amostra, H5 foi refutada
  (Spearman −0,166, IC fora de zero na direção OPOSTA) e H6 testa a leitura invertida.
  A literatura recente sugere um desenho diferente para o mesmo insumo: o LLM propõe
  HIPÓTESES falsificáveis, mapeadas para recipes executáveis num DSL point-in-time, e
  um motor determinístico impõe splits, gates, custos e testes. O princípio declarado
  é a separação de papéis — o agente controla a direção do raciocínio, nunca o
  protocolo empírico.
- Referência: Huang, Fan, Hu & Ye, "From Hypotheses to Factors: Constrained LLM Agents
  in Cryptocurrency Markets" (arXiv 2604.26747, abr/2026). Regularizações contra alpha
  decay (controle de complexidade, alinhamento semântico hipótese↔fator, imposição de
  novidade) em Wang et al., "AlphaAgent" (arXiv 2502.16789, KDD 2025).
- Por que este projeto está bem posicionado: o desenho exige trace append-only de
  experimentos (`trials.json` + `predictions_archive`/migração 0016), gates
  determinísticos (DSR, IC95 por block bootstrap, custos) e dados point-in-time
  (Feature Store bitemporal com guard de `published_at`). Tudo isso JÁ existe. A peça
  ausente é o DSL de fatores e o laço hipótese→recipe→avaliação.
- **NÃO reabre H4/H5/H6.** Aquelas seguem fechadas com os vereditos que têm. Esta é
  uma família nova, com trial nova, e nasce sujeita às mesmas regras.
- Ativação: (1) DSL implementado e testado, com garantia de que uma recipe não
  consegue ler dado futuro (teste de leakage, não só revisão); (2) atestado do harness
  válido; (3) registro em `trials.json` com `metric` declarado; (4) dado coletado
  DEPOIS do registro. Sem os quatro, é infraestrutura — não hipótese.

- **Estado da infraestrutura (2026-08-21).** Construída a pedido explícito do dono,
  depois de eu registrar a objeção de que o laço não deveria existir antes do
  pré-registro; ele reafirmou. Registrado aqui como decisão, no mesmo espírito do
  override de 2026-08-14.

  | Requisito | Estado |
  |---|---|
  | (1) DSL com prova de não-leakage | ✅ `analyzers/factor_dsl.py` — invariância sob mutilação do futuro para CADA operação, **com contraprova** |
  | (2) atestado do harness válido | ✅ renovado 2026-08-21, expira 2026-08-28 |
  | (3) registro em `trials.json` com `metric` | ❌ **ato humano, deliberadamente não automatizado** |
  | (4) dado coletado depois do registro | ❌ depende de (3) |

  `analyzers/hypothesis_loop.py` implementa o laço propõe→valida→avalia→registra
  no traço. Ele **não** escreve em `trials.json`, **não** emite veredito e **não**
  descarta proposta em silêncio (rejeitada entra no denominador com o motivo).
  Enquanto (3) e (4) não acontecerem, rodar o laço produz observação exploratória,
  não hipótese — e nada do que sair dele pode ser citado como resultado.

- **RISCO NOVO que este laço cria, declarado antes de qualquer uso.** Propor
  hipóteses fica barato e escalável. Gerar 500 fatores e escolher o melhor é
  data-snooping industrializado — mais rápido que à mão, não mais válido. As
  contramedidas embutidas: traço append-only contando TODAS as propostas (inclusive
  rejeitadas) como denominador honesto, e `analyzers/pbo.py` (B10) medindo se a
  seleção entre elas distingue sinal de sorte. PBO alto sobre as propostas significa
  parar de propor, não propor mais.
- RESSALVA de honestidade: o resultado positivo citado na referência (Sharpe OOS
  líquido) é DELES, com o universo e o período DELES. Não é evidência sobre este
  pipeline e não pode ser citado como expectativa.

#### H8 — Promoção de B9 a hipótese formal (status: **registrada**, coleta não iniciada)

> Registrada em `trials.json` em 2026-09-04T08:20:59Z (`registered_at`), com
> `metric="spearman_ic"` e `pipeline_fingerprint` conferido pelo próprio
> `predictor_core.measurement.trials.register_trial` contra o atestado válido da
> Fase 1 (`trials.phase1_harness_attestation.json`, expira 2026-09-10). Isto É um
> registro válido — não um rascunho. Qualquer previsão que conte como dado desta
> trial precisa ser posterior a esse timestamp.

- Mecanismo, contramedidas de risco (PBO/DSR/traço append-only) e ressalva de
  honestidade: ver B9 acima na íntegra — não duplicado aqui.
- Família e parentesco: família nova (`llm-hypothesis-generator`); NÃO reabre
  H4/H5/H6, que seguem fechadas com os vereditos que têm.
- Critério de sucesso (fixado por escrito ANTES de qualquer dado, confirmado
  pelo dono em 2026-09-04): **Spearman IC95% (block bootstrap, overlap-aware —
  mesmo mecanismo de H4-H6, via `spearman_block_ci` já usado em
  `hypothesis_loop.evaluate_proposal`) NÃO cruzando zero, `n≥30` pré-registrado.**
  Leitura de poder da B12 aplicada antes de tratar qualquer veredito com `n`
  próximo do piso como final — mesma disciplina da H6.
- `metric`: `spearman_ic` (já era o que `evaluate_proposal` calculava; a
  decisão só formalizou o gate que o código já implementava).
- `pipeline_fingerprint`: `69a096c9d86b9fcdc49cad22d43e76a675554b494a7969fbe222065a014c59db`
  (atestado da Fase 1, mesmo usado por H4-H6).
- Checklist de ativação:
  1. ✅ `analyzers/factor_dsl.py` (prova de não-leakage) confirmado íntegro
     (27/27 testes, 2026-09-04).
  2. ✅ Atestado do harness válido (expira 2026-09-10 — não precisou renovar).
  3. ✅ Registrado em `trials.json` com `metric` declarado (2026-09-04).
  4. ⬜ Coletar dado GENUINAMENTE NOVO sob esta configuração — só a partir de
     agora conta.

  **Lacuna de infraestrutura fechada em 2026-09-04**: `hypothesis_loop.py` já
  tinha o motor completo (`run_round`: propõe→valida→registra) e 19 testes,
  mas nada chamava `evaluate_proposal` sobre as propostas aceitas, e nada
  agendava o laço pra rodar — item 4 nunca teria como sair de ⬜ sem isso.
  `analyzers/hypothesis_loop_runner.py` (novo) fecha: carrega FeatureVector já
  coletados (zero dado novo de mercado), monta `dados`/`retornos`, roda
  `run_round`, avalia as propostas ACEITAS e anexa a
  `hypothesis_evaluations.json` (traço append-only, mesmo princípio de
  `hypothesis_proposals.json`). `--dry-run` existe só pra smoke-test do
  wiring — grava em arquivos `.dryrun.json` SEPARADOS, nunca no traço real
  (misturar entrada sintética com proposta real corromperia o denominador
  honesto que PBO/DSR dependem). Disponibilizado como job
  (`jobs.py:h8-hypothesis-loop`), **NÃO agendado automaticamente** — decisão
  do dono, mesma regra de todo outro job. Item 4 continua ⬜ até o dono
  decidir rodar (cada execução chama o LLM de verdade e gasta cota).
- `capital_authorized`: false até veredicto prospectivo líquido de custos, com PBO
  medido e reportado ao lado do DSR.

### B10 — Probabilidade de Overfitting do Backtest (PBO) via CSCV

- Mecanismo: o projeto já desconta múltiplas tentativas com **Deflated Sharpe Ratio**
  (`analyzers/trials.py` → core), que responde "este Sharpe sobrevive ao máximo
  esperado por sorte dado N tentativas?". O PBO responde outra pergunta, complementar:
  "qual a PROBABILIDADE de que a configuração escolhida como melhor seja, de fato,
  overfit?" — estimada por Combinatorially Symmetric Cross-Validation, particionando a
  série em S blocos e comparando o ranking IS vs OOS em todas as combinações.
- Referência: Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest
  Overfitting" (SSRN 2326253).
- Custo: ZERO coleta nova — aplica-se retroativamente ao registro que já existe.
- Ortogonalidade: alta. Nenhum gate atual mede isto; `grep` confirma que não há
  `pbo`/`cscv` no código.
- Ativação: é FERRAMENTA de avaliação, não hipótese — não consome tentativa e não
  precisa de pré-registro. Entra como métrica relatada ao lado do DSR.

### B12 — Poder do gate: 'RUÍDO' com poder baixo não é evidência de ausência

- Mecanismo: o projeto prova que o JUIZ funciona (`scripts/attest_harness.py`, controle
  positivo com n=120 sintético). Não prova que, com o `n` que a coleta vai ter, o juiz
  CONSEGUE ver. São perguntas diferentes, e a segunda decide como LER um veredito
  negativo: poder alto + "RUÍDO" é evidência de ausência de efeito; poder baixo +
  "RUÍDO" é ausência de evidência, e não diz nada.
- Agravante estrutural: a coleta é diária e o horizonte é D+7, então previsões
  consecutivas do mesmo ativo compartilham 6 dos 7 dias de retorno. O `n` efetivo é bem
  menor que o nominal. O `block_length` do bootstrap já absorve isso na estimativa do
  IC, mas ninguém tinha medido o que SOBRA de poder depois de absorver.
- Medido em 2026-08-21 com o critério real (`spearman_block_ci` + `overlap_block_length`,
  n_boot canônico de 10.000, 400 simulações), no gate pré-registrado `n=30`:

  | rho verdadeiro | 0,0 (falso positivo) | 0,1 | 0,2 | 0,3 | 0,5 |
  |---|---|---|---|---|---|
  | detecção | 7,5% | 8,2% | **14,2%** | **27,5%** | 60,0% |

- Leitura: em `n=30`, um efeito de rho=0,2 passa despercebido em ~86% das vezes.
- Tabela estendida (mesmo critério, `n_sim=150`, `n_boot=400` — reproduz a linha
  `n=30` acima dentro do ruído de simulação, o que valida a redução do `n_boot`):

  | n | rho=0,0 | rho=0,1 | rho=0,2 | rho=0,3 | rho=0,5 |
  |---|---|---|---|---|---|
  | 30 | 6,7% | 11,3% | 14,7% | 29,3% | 62,0% |
  | 60 | 6,0% | 11,3% | 23,3% | 47,3% | 93,3% |
  | 120 | 7,3% | 24,7% | 59,3% | **82,7%** | 100% |
  | 250 | 6,0% | 34,7% | **81,3%** | 100% | 100% |
  | 500 | 8,0% | 65,3% | 97,3% | 100% | 100% |

- **Onde o poder chega a 80%:** rho=0,3 exige `n ≈ 120`; rho=0,2 exige `n ≈ 250`;
  rho=0,1 não chega nem com `n=500` (65%). A taxa de falso positivo fica em 6-8% em
  todos os `n` — levemente acima do nominal de 5%, mas estável, sem inflar com o `n`.
- **Tradução operacional.** A H5 acumulou n=440 em ~18 dias (2026-07-10 a 07-28), ou
  seja ~24 previsões elegíveis por dia. Nessa taxa, `n=30` chega em ~1,5 dia e `n=250`
  em ~10 dias de coleta ininterrupta.
- **O que fazer com isso SEM tocar no gate.** O critério diz "n >= 30 antes de calcular
  veredito"; ele NÃO diz "pare em 30". A `h6_spearman_verdict` recalcula a cada
  execução do ciclo. Logo: o primeiro veredito impresso, por volta de n=30, é
  subdimensionado e não deve ser tratado como final; o mesmo critério, sem nenhuma
  alteração, fica bem dimensionado por volta de n=250. Nada precisa ser mudado —
  apenas lido corretamente.
- **NÃO altera o gate.** A H6 está congelada por hash com `n >= 30` pré-registrado;
  trocar esse número DEPOIS de calcular poder seria ajuste post-hoc de critério —
  exatamente o que o pré-registro existe para impedir. O uso correto é QUALIFICAR a
  leitura do veredito, nunca reescrever a regra que o produz.
- Ativação: é FERRAMENTA de avaliação, não hipótese. Não consome tentativa e não
  precisa de pré-registro.

### B11 — Concordância entre os juízes LLM (diversificação real da partição multi-juiz)

> **Errata de 2026-08-21, no mesmo dia do registro.** Este item nasceu propondo medir
> a CORRELAÇÃO entre os juízes. Ao implementar, verifiquei em código que isso é
> **não-computável a partir do dado existente**: `provider_for_asset()` é uma partição
> FIXA por sha256 do nome do ativo, então cada ativo é sempre pontuado pelo MESMO
> juiz. Não existe nenhuma observação pareada (dois juízes, mesmo ativo, mesma data)
> em toda a coorte da H5 — e a ausência é por desenho, não por falta de dados. O item
> foi dividido no que é medível agora e no que exigiria desenho novo.

- Mecanismo: a H5 usa partição fixa por sha256 entre 4 provedores (gemini, groq,
  cerebras, mistral), sob a premissa implícita de que juízes distintos trazem
  diversificação. Essa premissa nunca foi medida.
- **B11a — medível hoje, custo zero: CALIBRAÇÃO.** Se as distribuições de score
  diferem materialmente entre juízes (nível médio, dispersão, fração acima do
  limiar), o pooled da H5 mistura estimadores com réguas diferentes. Isso não
  invalida o veredito já emitido — o critério pré-registrado julgava o pooled e foi
  executado como estava —, mas QUALIFICA a leitura, do mesmo modo que a limitação
  do block bootstrap foi qualificada e não reescrita.
- **B11b — exige desenho novo: CONCORDÂNCIA.** Medir se dois juízes concordam sobre
  o MESMO ativo exige atribuição sobreposta (ex.: uma fração dos ativos pontuada em
  duplicata). Isso muda a coleta, logo é hipótese/trial nova, com pré-registro — não
  se faz retroativamente.
- Relevância dupla: (a) qualifica retroativamente a leitura da H5; (b) a literatura de
  alpha decay (B9) aponta homogeneidade entre saídas de LLM como causa de crowding —
  medir concordância é o primeiro diagnóstico dessa família.
- Ativação: é MEDIÇÃO descritiva sobre dado existente, não hipótese preditiva. Não
  consome tentativa. Não altera nenhum veredito já emitido — a H5 continua refutada
  pelo critério pré-registrado que foi executado na data pré-registrada.

---

### B13 — Ciclicidade multi-escala (ciclos dentro de ciclos)

- Mecanismo proposto: cripto historicamente mostra estrutura cíclica em múltiplas
  escalas simultâneas — o ciclo de halving do BTC (~4 anos), regimes de
  acumulação/distribuição de meses, e microestrutura intradiária — e essas escalas
  podem interagir (um ciclo maior modulando a amplitude/direção dos menores), não
  só coexistir. Nenhuma trial até agora (H1-H8) testou estrutura EXPLICITAMENTE
  multi-escala — H1-H3/H7 usam janelas de features fixas (fr_window), não uma
  decomposição de ciclos por construção.
- Por que é backlog e não trial: "ciclos dentro de ciclos" como está descrito é uma
  intuição, não uma feature operacionalizável. Precisa de decisão de desenho ANTES
  de qualquer dado contar, exatamente como toda outra trial: qual método de
  decomposição (ex.: wavelets, decomposição espectral, indicador de fase de
  halving), qual horizonte por escala, qual métrica de sucesso — e então
  pré-registro formal com `pipeline_fingerprint`, como H7/H8.
- Risco de p-hacking específico deste item: ciclos de mercado são um dos alvos
  mais clássicos de overfitting em finanças (é fácil "ver" um ciclo em qualquer
  série depois do fato). Qualquer trial nascida daqui precisa do mesmo gate WFA
  (PSR≥0.80, IC_CI_lower>0, MaxDD<20%) e, dado o risco extra de olhar pra trás
  pra "achar" o ciclo, provavelmente precisa de um controle adicional de
  multiplicidade (ex.: PBO via CSCV, como B10) antes de qualquer leitura contar.
- Ativação: nenhuma. Ideia registrada por pedido do dono (2026-09-04), não
  operacionalizada. Não consome tentativa, não é trial, não tem
  `pipeline_fingerprint`, não afeta H1-H8.

---

## Override de governança 2026-08-14 — infraestrutura de execução antes de edge validado

**Decisão explícita do dono, registrada por honestidade**: construir contrato
econômico, execução (order lifecycle), microestrutura (book/impacto) e
portfólio (risco agregado) **agora**, apesar de nenhuma hipótese ter validado
edge até esta data (H1-H6: NO-GO/refutadas; H7: infraestrutura de coleta
pronta, coleta real não iniciada). Isto **contradiz deliberadamente** a regra
do B8 acima ("gestão de risco de um sinal que não existe é polimento de motor
desligado") — o dono foi avisado da contradição antes de decidir e escolheu
prosseguir mesmo assim.

**O que isso é e o que não é:**
- É infraestrutura de engenharia (contratos, máquina de estados, matemática de
  portfólio/microestrutura) — testável e testada offline, sem depender de
  nenhum sinal ter poder preditivo.
- **NÃO é autorização de capital.** Nenhum gate do ecossistema (trials.json,
  DSR, atestado do harness) muda por causa disso. `scientific_state` dos dados
  que essa camada eventualmente consumir continua `COLLECTION_ONLY` até uma
  hipótese validar pelos critérios já estabelecidos.
- **NÃO é validação de que a execução simulada aqui é fidedigna.** Os modelos
  de impacto/fill em `trading/microstructure.py` são fórmulas-texto-padrão
  (walk-the-book, impacto raiz-quadrada) — não foram calibrados contra
  execução real, e não devem ser tratados como mais confiáveis do que o
  modelo de custo fixo (`v3/costs.py`) já usado nos vereditos H1-H3 até
  passarem por calibração.
- Módulos novos vivem em `GarimpoInvestimentos/trading/` (app layer) — não
  promovidos a `predictor_core` ainda; promoção é decisão futura, só depois
  do padrão provar estável em uso (mesmo caminho que `analyzers/trials.py`
  percorreu antes de virar `predictor_core.measurement.trials`, ADR-015).

## Auditoria externa 2026-09-05 — três achados corrigidos

Pedido explícito do dono: abrir um chat novo e auditar o projeto do zero
(hipóteses, matemática, infraestrutura, protocolo) de forma cética, sem
confiar no que já tinha sido dito. Três achados reais, corrigidos nesta
mesma leva:

1. **Cobertura zero no fix de `covariance_type="diag"` (H7).** A auditoria
   provou por mutação: revertendo `_covariance_type_for()` pra sempre
   devolver `"full"` (exatamente a regressão que o squash-merge do GitHub já
   causou duas vezes nesta sessão, PRs #86 e #90), a suíte inteira continuava
   verde — nenhum teste percebia. Corrigido: `test_v3_regime_engine_extra_covariates.py`
   ganhou `test_covariance_type_e_diag_com_extra_features_full_sem`, que
   falha imediatamente sob a mesma mutação (confirmado manualmente antes de
   commitar). Sem isso, o fix podia se perder uma terceira vez sem ninguém
   notar.

2. **Lookahead real em `build_dxy_return` (H7).** A função usava
   `day - timedelta(days=publish_lag_days)` — dias CORRIDOS — enquanto
   `DXYProvider.publish_lag_days` já tinha sido corrigido para dias ÚTEIS
   (2026-09-04, ver correção acima na seção H7). Cripto negocia fim de
   semana: um close de sexta só é publicado na segunda seguinte, mas o
   cutoff em dias corridos permitia usá-lo num ponto de sábado ou domingo —
   até ~2 dias de informação futura. Uma primeira tentativa de correção
   (subtrair dias úteis do dia do ponto) ainda dava resultado errado pra
   pontos de fim de semana, por uma armadilha de inversão (ver
   `_add_business_days` em `macro_features.py`); a correção final usa
   checagem direta por observação (`data de publicação <= dia do ponto`),
   não um cutoff único subtraído. Nenhum veredito do H7 foi contaminado —
   a coleta prospectiva nunca chegou a começar — mas o bug era real e teria
   afetado qualquer leitura feita antes desta correção. Testes novos:
   `test_fim_de_semana_nao_usa_close_de_sexta_ainda_nao_publicado` e
   `test_segunda_ja_pode_usar_close_de_sexta`.

3. **Congelamento de família (H1-H3) aplicado só por NOME, não por
   família.** `register_trial` (core) valida colisão de nome e imutabilidade
   de `params`/`metric`, mas nunca inspeciona `params["family"]` nem
   `frozen_families` — registrar uma trial NOVA (nome nunca visto) com
   `family: "funding_oi_hmm_v3"` passava sem barreira alguma; o único
   guardião real era `scripts/check_reopen_dossier.py`, manual e nunca
   chamado pelo CI. Corrigido no wrapper local
   (`GarimpoInvestimentos/analyzers/trials.py::register_trial`): trial nova
   declarando uma `family` presente em `frozen_families` é barrada ANTES de
   chegar no core. Ressalva honesta: isso fecha o caso de quem declara a
   família corretamente (por engano ou não) — não substitui o dossiê manual
   contra alguém que omita ou renomeie a família deliberadamente para
   escapar do guard.

Duas hipóteses novas foram **propostas** pela auditoria (mecanismo +
critério escritos ANTES de qualquer código), mas **não registradas** —
ficam para decisão do dono, e herdam o mesmo aviso: a arquitetura
HMM+covariável exógena já deu um NO-GO real (H9) e um pendente (H7); um
terceiro NO-GO na mesma arquitetura seria evidência sobre o método, não
azar.

- **B14 (proposta, não registrada)** — Assimetria de basis perpétuo↔spot
  como preditor de reversão: o basis mede quanto alavancado paga por
  exposição; a ASSIMETRIA entre expansões e contrações captura
  desalavancagem forçada (direcional), diferente do nível de funding
  (H1-H3, simétrico, já refutado). Família nova (`basis-asymmetry-hmm-covariate`).
- **B15 (proposta, não registrada)** — Dispersão de funding entre exchanges
  como proxy de estresse de liquidez: desvio-padrão do funding entre venues
  mede fragmentação; picos precedem cascatas de liquidação. Distinto de H9
  (crowding numa venue só) e H1-H3 (nível agregado).

Ambas usariam o mesmo gate de H1-H3/H7/H9 (PSR≥0,80 E IC_CI_lower>0 E
MaxDD<20%, líquido de custos) se e quando ativadas.


## Auditoria externa 2026-09-05 — quatro achados corrigidos

Pedido explícito do dono: abrir um chat novo e auditar o projeto do zero
(hipóteses, matemática, infraestrutura, protocolo) de forma cética, sem confiar
no que já tinha sido dito — inclusive por ele. Duas auditorias independentes
rodaram em paralelo (PRs #92 e #93) e convergiram nos três primeiros achados,
o que é confirmação cruzada de que são reais. Consolidados aqui:

1. **Cobertura zero no fix de `covariance_type="diag"` (H7).** Provado por
   MUTAÇÃO: revertendo `_covariance_type_for()` para sempre devolver `"full"`
   — exatamente a regressão que o squash-merge do GitHub já causou duas vezes
   (PRs #86 e #90) — a suíte inteira continuava VERDE, 915 testes passando.
   Nenhum teste percebia. Era por isso que o fix sumia em silêncio e precisou
   ser reaplicado. Corrigido: `test_v3_regime_engine_extra_covariates.py` ganhou
   travas de contrato (`_covariance_type_for`, fingerprint) e uma trava
   COMPORTAMENTAL que confere que a matriz de covariância treinada é de fato
   diagonal. Sob a mesma mutação, 3 testes agora falham.

2. **Lookahead real em `build_dxy_return` (H7).** A função usava
   `day - timedelta(days=publish_lag_days)` — dias CORRIDOS — enquanto o
   `DXYProvider` já tinha sido corrigido para dias ÚTEIS no PR #83. Duas cópias
   da mesma regra que divergiram. Cripto negocia fim de semana: o close de sexta
   só é publicado na segunda, mas o cutoff em dias corridos permitia usá-lo num
   ponto de sábado ou domingo — até ~2 dias de informação futura, em ~2/7 dos
   pontos. Contradizia o parâmetro pré-registrado do H7
   (`dxy_publish_lag_business_days: 1`).

   Nenhum veredito foi contaminado — a coleta prospectiva do H7 nunca começou —
   mas qualquer leitura feita antes desta correção teria sido.

   A correção ataca a CAUSA RAIZ, não só o sintoma: a regra passou a viver num
   módulo único (`dpl/business_days.py`), consumido pelo provider e pelas
   features. Uma armadilha registrada para quem mexer nisso: subtrair dias úteis
   do dia do ponto NÃO é o inverso de somar dias úteis à observação (a soma pula
   o fim de semana adiante; a subtração recua para o dia útil mais próximo sem
   saber disso). Por isso a disponibilidade é testada pelo predicado direto
   `published_at(observação) <= dia do ponto`, nunca por um cutoff subtraído.

3. **Congelamento de família (H1-H3) aplicado só por NOME.** `register_trial`
   valida colisão de nome e imutabilidade de `params`/`metric`, mas nunca
   inspecionava `params["family"]` nem `frozen_families` — verificado no wheel
   3.0.0 pinado, não só no `main` do core. Registrar uma trial NOVA com
   `family: "funding_oi_hmm_v3"` passava sem barreira; o único guardião era
   `scripts/check_reopen_dossier.py`, manual e nunca chamado pelo CI. Corrigido
   no wrapper local: trial nova declarando família congelada é barrada ANTES de
   chegar ao core (`FrozenFamilyError`).

   Duas ressalvas honestas: (a) o guard só vale para trial NOVA — atualizar uma
   já existente é como um veredito é gravado (foi assim que o H9 foi fechado), e
   bloquear isso impediria FECHAR uma hipótese; (b) fecha o caso de quem declara
   a família corretamente, mas não substitui o dossiê manual contra quem omita
   ou renomeie a `family` de propósito.

4. **`predict_last` quebrado para H7/H9** (achado só no PR #93). O wrapper não
   repassava `extra_covariates`, então qualquer engine com `extra_features`
   estourava `ValueError` de wiring no caminho de tempo real que o próprio
   método documenta. Latente (sem chamadores hoje), corrigido e coberto.

Também adicionado `dxy_coverage()`: o `0.0` que `build_dxy_return` devolve em
lacuna NÃO é neutro — entra no `StandardScaler` ajustado no IS e vira uma
posição concreta da distribuição, então cobertura ruim ensina o HMM um "estado
de dado faltante" disfarçado de regime. A função é separada de propósito, para
não alterar nenhum valor que `build_dxy_return` já produz: o veredito fechado do
H9 e o pré-registro do H7 têm que continuar reproduzíveis.

Um falso positivo, registrado para memória: a primeira auditoria reportou um bug
numérico no `sharpe` do PBO (variância zero devolvendo valor finito enorme em vez
de `-inf`). Era artefato de rodar em Python 3.11 — o `sum()` compensado do 3.12+
zera a variância corretamente, e o projeto exige >=3.13. Não havia bug. Fica como
lembrete de conferir o ambiente antes de acreditar numa falha de teste.

**Correção 2026-09-05 (mesma data, algumas horas depois) — o achado 4 acima
estava incompleto.** Ao inspecionar o log real do run do H9
(`h9_backtest_result.log`, máquina de produção), apareceu o que faltava:

```
Folds: 45 | GO: 0 | NO-GO: 1
```

**44 dos 45 folds saíram `INSUFFICIENT_DATA`.** A condição, em
`backtest_v3.py`, é `len(fold_ic_pairs) < 10`: em 44 de 45 janelas OOS a
estratégia gerou MENOS DE 10 sinais avaliáveis. Não é dado ausente — é sinal
que quase nunca dispara.

Ou seja: o `PSR=0,1621` e o `Sharpe=-1,0041` registrados como veredito do H9
não são um agregado sobre 45 janelas independentes. São, na prática, o
resultado de UMA janela. O achado 4 acima atribuía a "piora de 76x" a um modo
de falha diferente; a explicação real é mais simples e mais séria — não há
agregado robusto ali para comparar com H1-H3.

**O NO-GO segue válido e a hipótese segue fechada:** o critério pré-registrado
reprovou, e nada disto reabre H9. Mas a FORÇA EVIDENCIAL do veredito é muito
menor do que o número "45 folds" sugere, e isso não estava documentado.

**Consequência direta para o H7:** ele usa o mesmo gerador de sinal e a mesma
cadência. Vai encontrar a mesma escassez. A pergunta que importa deixou de ser
"DXY tem sinal?" e passou a ser "este gerador dispara o suficiente para medir
qualquer coisa?". Rodar a coleta prospectiva do H7 antes de responder isso é
gastar tempo de calendário para reencontrar `INSUFFICIENT_DATA`.

**O H7 já foi tentado, e abortou.** `h7_backtest_result.log` (2026-09-04
17:35) termina em `ERRO - transmat_ rows must sum to 1 (got row sums of
[1. 1. 0.])` - exatamente a falha que o PR #91 corrigiu ao mover `predict()`
para dentro do laço de retry, mergeado às 21:51 do mesmo dia. O status
`REGISTERED_NOT_ACTIVATED` no charter está correto (nenhum veredito válido
saiu), mas "coleta não iniciada" é impreciso: foi tentada e quebrou por bug de
infraestrutura, já corrigido.

### Reconciliação do registro — 2026-09-05

Auditoria do estado local de produção contra o `main` revelou que o registro
público estava **incompleto**, o que enfraquecia um controle anti-p-hacking:

- **16 tentativas da varredura de threshold** (`v3-grid-btcusdt-fr{1.5,2,2.5,3}
  -conf{0.55,0.6,0.65,0.7}`), registradas em produção em 2026-09-04T02:32:31Z
  por `run_threshold_grid`, existiam APENAS na máquina local. O `trials.json`
  versionado tinha 10 trials; o local tinha 26.

  Isto importa porque o **Deflated Sharpe desconta pelo número de tentativas**.
  A nota da H5 registra `DSR 0.00 (SR0 0.447, N=7 tentativas)`. Com a grade, N
  passa de 7 para 23+. O registro público subestimava a multiplicidade em 16
  tentativas — exatamente a grandeza que o controle existe para medir.

  As 16 entradas foram restauradas no `trials.json` versionado, com os Sharpes
  medidos no run original. Nenhuma foi re-executada e nenhuma é veredito: todas
  carregam `selection_family: threshold_grid` e a nota
  `candidate-only, never direct GO`. A melhor delas atingiu PSR 0,664 — abaixo
  do corte de 0,80.

- **Causa raiz, em cadeia.** O `scripts/safe_pull.ps1` (PR #84) foi criado
  justamente para eliminar o stash/pull/pop manual sobre o `trials.json`. Ele
  nunca rodou: estava salvo em UTF-8 sem BOM com travessões dentro de strings,
  e o Windows PowerShell 5.1 lê `.ps1` sem BOM como ANSI/cp1252, onde os bytes
  do travessão viram uma ASPA DUPLA que fecha a string e quebra o parser. Sem o
  script, os conflitos foram resolvidos à mão; uma dessas resoluções leu o
  `trials.json` com codepage OEM (cp850) e regravou em UTF-8, corrompendo os
  travessões das notas para `ÔÇö` — mojibake dentro do registro científico.

  Corrigido: `safe_pull.ps1` agora é ASCII puro com BOM UTF-8, e
  `tests/test_registry_e_scripts_encoding.py` trava as duas pontas (todo `.ps1`
  ASCII-puro-ou-com-BOM; `trials.json` sem mojibake, sem nomes duplicados e com
  as 16 tentativas da grade presentes). Validado por mutação: reverter qualquer
  uma das três condições faz um teste falhar.

- **RESOLVIDO 2026-09-05 (mesmo dia) — Sharpes divergentes de hipóteses FECHADAS
  foram reconciliados, por decisão explícita do dono.**

  | trial | antes | depois |
  |---|---|---|
  | `v2-dpl-multi-h7` (H5) | -0,312 | **-0,4186** |
  | `h6-sinal-invertido-d7` (H6) | 0,3479 | **0,4766** |

  Ambos são valores medidos pelos jobs de produção, presentes no `trials.json`
  local que nunca havia sido publicado. A objeção foi levantada — `register_trial`
  PROÍBE reescrever trial de hipótese fechada — e o dono a reafirmou. A escrita foi
  feita direto no arquivo, por PR revisado: o guard existe para impedir reescrita
  automática/acidental, não decisão humana documentada. Cada registro recebeu nota
  de proveniência com o valor anterior, a decisão e o motivo.

  **NENHUM VEREDITO MUDOU.** H5 e H6 seguem `CLOSED_NO_GO`. O gate da H5 é o
  Spearman IC95 pooled (-0,166 [-0,266; -0,057], direção oposta à hipótese); o da
  H6 é o Spearman IC95 (rho -0,057 [-0,231; +0,129], n=84, cruza zero). O Sharpe
  sempre foi auxiliar em ambas, nunca critério de decisão.

  **A H6 exigiu quebrar um selo criptográfico — registrado aqui em destaque.**
  `charters/h6_definition_frozen.json` congela por SHA256 duas coisas: (a) o código
  de `close_h6_inverted_signal`/`h6_spearman_verdict`, e (b) a entrada do H6 no
  `trials.json` — incluindo o campo `sharpe` e o texto das notas. A suíte pegou a
  divergência (`test_h6_spearman_verdict_continua_confere_com_o_snapshot_congelado`),
  que é exatamente o que essa trava existe para fazer.

  O snapshot foi regenerado. O que justifica isso, na regra do próprio
  `scripts/freeze_h6_definition.py` ("ou foi mudança inofensiva e o snapshot deve
  ser regenerado com justificativa no commit, ou a definição mudou e H6 precisaria
  virar trial NOVA"):

  - divergiu **somente** `trials_json_entry_sha256`;
  - `governing_code_sha256` permaneceu **byte-idêntico**
    (`5582ec23...b99b9f0a` antes e depois) — a semântica científica do H6 não se
    moveu;
  - `params` (fonte, horizonte_dias) e `registered_at` intocados — o que está sendo
    testado não mudou;
  - a regra `no_silent_change` do selo enumera "threshold, horizonte, ativos,
    provider, score transformation ou filtro"; um resultado registrado não é
    nenhum deles;
  - o `note` do selo o vincula à janela em que "H6 estiver ACTIVE_PROSPECTIVE", e a
    H6 está fechada desde 2026-09-04 — a coleta que o selo protegia terminou.

  **RESSALVA DE PROVENIÊNCIA, em aberto:** o valor antigo da H6 vinha carimbado com
  `n=6, IMATURO`. O `n` por trás de `+0,4766` **não está documentado em lugar nenhum
  do repositório** e não foi possível recuperá-lo nesta auditoria. O número é o que
  os jobs mediram; sua maturidade é DESCONHECIDA. Não o trate como evidência antes
  de recuperar o `n` — e se ele vier a ser recuperado, registre-o aqui.

  **PISTA CONCRETA, encontrada em 2026-09-06.** Ao revisar as branches antes de
  apagá-las, apareceram cinco scripts que existiam **só** numa branch de backup
  (`claude/entender-3-projetos-cfvrck-backup-2026-09-03`) e em nenhum outro lugar
  do repositório. Eles registram que a máquina de produção guarda um snapshot do
  Feature Store **anterior a uma limpeza**:

  ```
  C:\predictor\data\output\feature_store_backup_antes_limpeza.db
  C:\predictor\data\failed-runs\feature_store-*-2026-08-09.db   (3 arquivos)
  ```

  Um deles, `check_backup.py`, faz exatamente a consulta que responde esta
  ressalva — total de `predictions`, quebra por fonte e intervalo de `ts`. Os
  cinco foram preservados em `scripts/forense/` antes de as branches serem
  apagadas; o mapa completo da máquina está em `docs/MAQUINA_DE_PRODUCAO.md`.

  Rodar na máquina de produção:

  ```powershell
  cd C:\predictor\prod
  python scripts\forense\check_backup.py
  ```

  **Não testado** — os bancos não existem fora da máquina, então não há como
  verificar daqui se o `n` está mesmo lá. É a pista mais concreta que existe,
  não uma resposta.


### Lacunas conhecidas e NÃO corrigidas — 2026-09-06

Achados da auditoria de 2026-09-05 que ficaram **documentados mas não
implementados**, porque corrigi-los muda a régua de uma hipótese ou depende de
decisão do dono. Registrados aqui para não serem redescobertos do zero.

1. **O dedup do H8 subestima a multiplicidade.**
   `analyzers/hypothesis_loop.parse_proposals` deduplica propostas por
   `recipe_fingerprint` — hash da receita EXATA. Duas propostas semanticamente
   equivalentes (operandos comutativos em ordem diferente, z-score de uma feature
   já escalada) produzem fingerprints diferentes e contam como tentativas
   distintas.

   Isso importa porque o traço append-only de propostas é o denominador que o
   PBO/DSR usa para descontar seleção. Fingerprint exato **infla** o número de
   tentativas aparentes e, ao mesmo tempo, **deixa passar** duplicatas reais como
   se fossem exploração nova — nas duas direções, o controle mede errado.

   NÃO corrigido: o H8 já está registrado (`h8-llm-hypothesis-generator`) com
   `multiplicity_control` declarado. Mudar como a multiplicidade é contada é
   mudar a régua de uma hipótese registrada — decisão científica do dono, não
   correção de bug. Relevante ANTES de a coleta do H8 começar, não depois.

2. **`build_macro_event_dummy` usa janela ±N — antes E depois do evento.**
   Marcar 1.0 no dia seguinte a um FOMC é trivialmente causal; marcar 1.0 no dia
   ANTERIOR só é legítimo porque FOMC/CPI/PPI têm data **anunciada com
   antecedência**. A função é causal por uma propriedade do CALENDÁRIO, não do
   código.

   Consequência: se `macro_calendar.json` algum dia for preenchido
   retroativamente — com datas de divulgação real em vez de datas agendadas
   ex-ante — a mesma função vira look-ahead sem que nada no código mude. Não há
   teste que detecte isso, porque o dado é que muda, não a lógica.

   NÃO corrigido: hoje o calendário é agendado e a suposição vale. Fica como
   pré-condição a conferir se a origem do calendário mudar.

3. **O controle do H7/H9 (`extra_features=()`) continua não rodado.**
   Ver o item 7 do B4 acima. Tentativa de rodá-lo em 2026-09-05 falhou por dois
   motivos independentes, ambos externos ao código: a série histórica de OI não
   existe fora da máquina de produção (o endpoint REST da Binance só serve ~30
   dias — ver `v3/collectors/oi_collector.py`), e o arquivo público que a
   reconstruiria (`data.binance.vision`) está bloqueado pela política de rede do
   ambiente de auditoria.

   O runbook para rodá-lo na máquina de produção (dois braços, baseline e
   `--use-oi-volume-ratio`, na MESMA janela) está em
   `docs/MAQUINA_DE_PRODUCAO.md`, seção "O controle do H7/H9, quando for rodar".
   Enquanto não rodar, o `Sharpe=-1,0041` do H9 permanece sem referência.

4. **Duas flags do backtest registram trials sem confirmação.**
   `--fr-thresholds` e `--confidence-thresholds` desviam para
   `run_threshold_grid`, que chama `register_trial` para TODA a grade **antes**
   de rodar o WFA (`v3/backtest_v3.py:1179`). Uma grade 4×4 gasta 16 tentativas
   do denominador do DSR no instante em que o comando roda.

   O comportamento está **certo** — registrar antes de ver o resultado é o que
   impede escolher o vencedor depois. O problema é que nada avisa, e
   `docs/RISK_MGMT_E_CALIBRACAO_2026-08-27.md` apresenta exatamente esse comando
   na seção "Como rodar" **sem mencionar o efeito colateral**. Foi assim que as
   16 trials `v3-grid-btcusdt-*` nasceram em 2026-09-04 e ficaram um dia inteiro
   só na máquina de produção, subestimando o N do DSR no registro público.

   Não corrigido: aquele documento é um retrato datado e a convenção do projeto
   é não reescrever registro histórico. O aviso foi para
   `docs/MAQUINA_DE_PRODUCAO.md`, que é documento vivo. Se algum dia a
   convenção admitir errata em doc datado, este é um caso claro.

5. **O atestado de poder é chaveado pela versão do core, não só pelo prazo.**
   `trials.harness_attestation.json` carrega `core_version: "3.0.0"`, enquanto
   o `pyproject.toml` permite `predictor-core>=3.0.0,<4`. Qualquer bump de minor
   dentro do intervalo permitido invalida o atestado e **bloqueia todo registro
   de trial** até nova aferição.

   Fail-closed é o comportamento correto — harness não aferido não deve registrar
   hipótese. Não corrigido porque não é defeito: é expectativa não documentada.
   A falha se apresenta como recusa de registro, não como "sua dependência subiu
   de versão", e isso custa tempo de diagnóstico. Descoberto por acidente na
   auditoria de 2026-09-05.

### B14 — Assimetria de basis perpétuo↔spot (proposta, NÃO registrada)

**Mecanismo (escrito antes de qualquer código):** o basis (perp − spot) mede
quanto o alavancado paga por exposição. A ASSIMETRIA entre expansões e
contrações captura desalavancagem forçada, que é direcional — diferente do
NÍVEL de funding que H1-H3 usam, que é simétrico e já foi refutado. Família
nova: `basis-asymmetry-hmm-covariate`. Dado já coletado.

**Critério de sucesso (definido antes de ver dado):** PSR ≥ 0,80 E
IC_CI_lower(Spearman) > 0 E MaxDD < 20%, líquido de custos — mesmo gate de
H1-H3/H7/H9.

### B15 — Dispersão de funding entre exchanges (proposta, NÃO registrada)

**Mecanismo (escrito antes de qualquer código):** o desvio-padrão do funding
entre venues mede fragmentação de liquidez; picos precedem cascatas de
liquidação. Distinto de H9 (crowding numa venue só) e de H1-H3 (nível
agregado). Dado já coletado.

**Critério de sucesso:** idem B14.

**Aviso que ambas herdam:** a arquitetura HMM + covariável exógena já produziu
um NO-GO real (H9) e tem um pendente (H7). Um terceiro NO-GO na mesma
arquitetura não é azar — é evidência sobre a arquitetura, e o B4 (meta-análise
dos NO-GO) merece prioridade sobre promover B14/B15. Nenhuma das duas foi
registrada em `trials.json`: registro exige `decided_by: owner`.

## Errata e decisões CRIPTO v1.2 — 2026-09-07

Base auditada: `3c104ce` (origin/main). Trabalho isolado da produção. Esta seção
substitui interpretações causais conflitantes acima, sem reescrever observações
históricas, parâmetros, trials ou hashes congelados.

### P0-D / P0-C — causa científica versus encerramento operacional

O fechamento de H6 EXISTE: foi publicado em 2026-09-04, reafirmado pela
reconciliação de 05/09. Sua justificativa confundiu “não passou o gate de
validação” com “refutada”. O protocolo de 27/08 exige IC inteiramente negativo
para refutação direcional; o IC observado cruza zero. Não há teste de
equivalência/futilidade com poder adequado sustentando ausência de efeito.
Corrigido o charter para `CLOSED_INSUFFICIENT_SAMPLE`: mantém a decisão de
não promover e o bloqueio de reescrita, mas retira a inferência de refutação.
H9 recebe a mesma classe operacional, por apenas um fold avaliável. Nenhuma
das duas foi reaberta, nem qualquer job de coleta foi alterado.

| Hipótese | Diagnóstico causal sustentado | Decisão / limitação |
|---|---|---|
| H1 | COST_FAILURE_UNDER_ASSUMED_MODEL; bruto histórico positivo pequeno | CLOSED_NO_GO; causalidade exclusiva de fee real não demonstrada; reanálise forward também negativa |
| H2 | INCONCLUSIVE quanto à atribuição causal; edge insuficiente no cenário testado | CLOSED_NO_GO; +0,07 → −0,37bps; PSR 0,215; poder não documentado |
| H3 | NO_GROSS_EDGE_IN_TESTED_CONFIGURATION | CLOSED_NO_GO; bruto −0,35bps, PSR 0,192, MaxDD 50,3%; fee não explica a origem do bruto negativo |
| H4 | LOW_POWER / coleta interrompida | CLOSED_INSUFFICIENT_SAMPLE, n=5; não refuta feature/LLM |
| H5 | OPPOSITE_DIRECTION_EVIDENCE na amostra prospectiva especificada | CLOSED_NO_GO; rho −0,166, IC95 [−0,266; −0,057], n=440. Não prova ausência universal de alpha; DSR histórico não é confirmação atual |
| H6 | INCONCLUSIVE_DUE_TO_POWER / UNDERPOWERED | CLOSED_INSUFFICIENT_SAMPLE; n=84, IC95 [−0,231; +0,129], poder 23% para rho=0,2 |
| H7 | HARNESS_FAILURE_NO_VALID_RESULT | REGISTERED_NOT_ACTIVATED; tentativa abortou por matriz de transição; correção do bug não é evidência sobre DXY |
| H8 | NOT_TESTED | REGISTERED_NOT_ACTIVATED; pipeline implementado não demonstra valor de hipóteses geradas |
| H9 | INCONCLUSIVE / LOW_EFFECTIVE_SAMPLE | CLOSED_INSUFFICIENT_SAMPLE; 44/45 folds insuficientes, sem ablação que isole OI/volume |

`CONFIRMED_NO_EDGE` irrestrito não é sustentado para nenhuma feature isolada
por esta rodada. A decisão de manter `funding_oi_hmm_v3` congelada é preservada
pelos múltiplos resultados negativos existentes. O claim TREND foi corrigido:
decisão de escopo sem trial não é refutação estatística.

### P0-B — fees, unidades e sensibilidade sem reexecutar H1-H3

Fontes públicas consultadas em **2026-09-07**:

| Insumo | Observado / fonte | Classificação |
|---|---|---|
| USDⓈ-M maker 0,02% = 2bps; taker 0,05% = 5bps por perna | [FAQ Binance](https://www.binance.com/en/support/faq/detail/360033544231), atualizado 2026-05-01 | Exemplos públicos explicitamente hipotéticos, NÃO fee confirmada de conta |
| Desconto BNB de 10% em USDⓈ-M | mesmo FAQ | Regra condicionada a BNB suficiente; cenário 1,8/4,5bps, sem assumir elegibilidade |
| Tabela atual por tier | [Fee Rate Table](https://www.binance.com/en/fee/futureFee) retornou “No records found”; sonda pública auxiliar retornou 404 | UNKNOWN; não substituir por exemplo do FAQ |
| Fee específica do operador | [User Commission Rate](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/User-Commission-Rate), endpoint USER_DATA assinado | UNKNOWN sem conta/consulta autorizada; exemplo JSON de API não é tabela comercial |
| Modelo V3 | 10bps fee + 5bps slippage/perna; funding corrente repetido | ASSUMED/UNCALIBRATED; arquivo byte-idêntico ao freeze |

**Correção de unidade:** os números H1/H2/H3 em bps/sinal são retornos sobre
capital ponderados pela posição. A fee é bps de nocional POR PERNA. Não se
subtrai 5bps diretamente de −0,09bps/sinal. Denote `a_i = média(|position|)`
sobre exatamente os mesmos sinais do agregado original. Mantendo posições,
funding e slippage fixos, a identidade exata é:

`net_i(f) [bps/sinal] = net_i(10) + 2 × (10 − f) × a_i`.

| Fee f, bps/perna | H1 líquido, bps/sinal | H2 | H3 |
|---|---|---|---|
| 10 (congelada) | −0,09 | −0,37 | −0,75 |
| 5 (exemplo público) | −0,09 + 10a₁ | −0,37 + 10a₂ | −0,75 + 10a₃ |
| 2 (cenário, NÃO fill maker assumido) | −0,09 + 16a₁ | −0,37 + 16a₂ | −0,75 + 16a₃ |
| 0 (limite matemático) | −0,09 + 20a₁ | −0,37 + 20a₂ | −0,75 + 20a₃ |

No cenário de 5bps, o líquido cruza zero somente se `a₁>0,009`, `a₂>0,037`
ou `a₃>0,075`, respectivamente. Isto NÃO diz que cruza PSR/IC/MaxDD ou o
hurdle econômico. `a_i`, retornos por sinal e funding realizado por sinal
das três execuções originais: UNKNOWN. Não é possível separá-los do custo
total agregado porque funding é assinado. O `wfa_returns.json` atualmente
presente em produção não identifica H1/H2/H3 e não contém posições: recusado
como substituto silencioso da amostra original. A busca cobriu artefatos
versionados e os arquivos de resultados locais identificáveis, sem rodar WFA.

**Decisão:** Q de CLAIM-CR-COSTS rebaixada; H1 é sensível a uma premissa
não calibrada, mas a hipótese/família segue encerrada. PSR sob nova fee é
UNKNOWN; nenhum GO foi inferido da sensibilidade algébrica.

**Proposta de pré-registro `cost-provenance-v1` — DRAFT_NOT_REGISTERED:**
pergunta exclusiva: qual a fricção de uma estrutura especificada? Universo
BTCUSDT/ETHUSDT USDⓈ-M, sem escolha posterior por performance; código de
estratégia/posição e dados de H1-H3 não serão reexecutados. Fixar antes da
coleta independente: venue/conta/tier, tamanho nocional, tipo de ordem, horários,
known_at, endpoint de fee e protocolo de mensuração. Comparar a referência
congelada 10bps com a tarifa efetivamente observada, sem selecionar fee que
resgate resultado. Orçamentos separados: análise contábil DISCOVERY sem capital;
fills realizados só após autorização própria. Missing fee/fill → UNKNOWN;
sem fee autenticada e sem fills não existe MEASURED_EXPECTED_FRICTION.
Pré-definir precisão/IC e tamanho amostral após a estrutura ser conhecida,
antes de observar seus resultados. Desfechos: erro de proveniência, amplitude
de custo e decisão de envelope; nunca reabertura de `funding_oi_hmm_v3`.

### P0-A — DSR instalado, migração e retificação dos números

Core 3.0.0 encontrado em `C:/predictor/prod/.venv`; checkout antigo do usuário
tinha Core 2.2.0. O ambiente isolado reproduziu o lock 3.0.0 e a degeneração:
retornos `[0.01, -0.02, 0.03, 0.01]`, Sharpes `[None, 0.3]` → N=2,
SR0=0, DSR=0,7450734876819202 (PSR puro). A release vigente verificada foi
[Core 3.2.0](https://github.com/leonardosovienski/core-predictor/releases/tag/v3.2.0).
Sua função permanece permissiva por padrão: apenas trocar a wheel NÃO basta.
O domínio agora chama `strict=True`, tratando não estimável como UNKNOWN.

Migrados os seis arquivos: pyproject, uv.lock, Dockerfile, CI,
verify_installed_wheels e test_core_integrity. SHA256 da wheel:
`9166dd6bd3be99668c0eb8bd3c59a92061e765186608465c0caf48a2417e3009`.
Os cinco caminhos de update listados no HANDOFF agora executam controles
sintéticos reais e encaminham o atestado correspondente à métrica gravada;
validade, versão e fingerprint continuam verificados pelo Core. A emissão dos
dois atestados usa staging externo para que o primeiro arquivo não suje a
árvore antes do segundo controle. Não há `allow_dirty=True` na emissão canônica.

**Achado adicional material:** `run_wfa` calcula `aggregate_sharpe` como
`mean/population_std × sqrt(n)`, e `run_threshold_grid` grava esse número no
campo `sharpe` do ledger. O registro também contém Sharpes por trade e outras
frequências. Assim, sua variância conjunta NÃO está em uma unidade comum.
Não corrigimos esses resultados congelados sem n e séries originais.
O relatório agora exige `params.sharpe_basis` compatível com seu horizonte
para cada Sharpe finito; metadado desconhecido ou incompatível → DSR UNKNOWN.
Nenhum metadado foi inventado retroativamente para liberar o cálculo.

| Número publicado / diagnóstico | Resultado desta auditoria |
|---|---|
| SR0 com N filtrado (23 Sharpes finitos) | 0,9524130493332158, reprodução aritmética do ledger atual |
| SR0 contando todas as 26 tentativas | 0,9777608299827842, reprodução aritmética corrigida de N |
| Validade dos dois SR0 acima | INVALID_FOR_INFERENCE: unidades/períodos incompatíveis; números de diagnóstico, não benchmarks científicos |
| DSR H5 histórico 0,00, SR0 0,447, N=7 | Revalidação exata UNKNOWN: não foram localizados retornos congelados + snapshot de ledger usados naquela publicação |
| H1/ETH, DSR histórico ≤ PSR | São limites publicados, não uma série DSR reconstruível; não promovem alpha |
| DSRs em HANDOFF e relatórios históricos de outras datas | NOT_RECOMPUTABLE_FROM_SUMMARY: Sharpe/n agregado não determina assimetria/curtose exigidas pelo PSR/DSR |

O inventário de ocorrências numéricas publicadas está em
`docs/evidence/cripto_v12_dsr_inventory.json`. Tentativas com Sharpe null
continuam em N. Converter t-like para Sharpe requer n e convenção original;
normalizar períodos distintos exige protocolo próprio. Nem usar a série WFA
atual sem identidade, nem criar retornos sintéticos com o mesmo Sharpe,
recalcula legitimamente uma publicação passada. Portanto não alegamos ter
recalculado DSRs irrecuperáveis. Todos ficam retirados de uso como evidência
atual até recuperação dos inputs; o NO-GO direcional da H5 permanece sustentado
pelo Spearman prospectivo, independentemente de DSR.

### §8–§10 — moedas e custo de oportunidade, as of 2026-09-07

Fontes consultadas em 2026-09-07. OBSERVADO: [PTAX fechamento
04/09](https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do),
USD compra 5,1247 / venda 5,1253 BRL. Reporting currency fixada para esta
rodada: BRL. US$5.000 = R$25.626,50 usando PTAX venda como marca contábil,
nunca como cotação executável. P&L de carry em USDT, com referência USD e risco
de descolamento USDT/USD explícito. Benchmark em BRL. Hedge: NENHUM modelado.
Exposição cambial: aproximadamente US$5.000 de principal + P&L líquido, sem
hedge; ±10% de USD/BRL representa ±R$2.562,65 sobre o principal, sem alpha.

| Campo obrigatório | Valor / ressalva |
|---|---|
| BENCHMARK_SOURCE | Candidato concreto: [Tesouro Reserva via BB](https://www.tesourodireto.com.br/tesouro-reserva), 100% Selic. Conta BB e escolha efetiva pelo operador: UNKNOWN. Não foi aberta conta. |
| BENCHMARK_GROSS_RATE | Selic efetiva anualizada 13,90% em 04/09, [BCB SGS 1178](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados/ultimos/1?formato=json). Meta 14,00% é referência macro separada. Projeção de 365 dias a taxa constante é cenário, não retorno contratado. |
| BENCHMARK_TAX | Cenário PF, resgate após 365 dias: IR 17,5% do rendimento; IOF zero após 30 dias ([B3](https://www.b3.com.br/pt_br/produtos-e-servicos/tesouro-direto/tesouro-direto/perguntas-frequentes/)). Perfil tributário efetivo: UNKNOWN. |
| BENCHMARK_FEES | Custódia B3 0,20% a.a., isenção até R$10.000. Taxa adicional do intermediário e isenção já consumida pelo CPF: UNKNOWN. |
| BENCHMARK_NET_RETURN | Efetivamente acessível ao operador: UNKNOWN. Cenário descrito abaixo, com taxa do intermediário zero e isenção integral disponível, produz 11,318%–11,346% em um ano. |
| AS_OF_DATE | 2026-09-07; câmbio e Selic efetiva com data do último dia útil disponível, 2026-09-04. |

Controle temporal: SGS432 `/ultimos/1` devolveu data 16/09/2026 (futura no
momento da consulta), logo foi rejeitada. Consulta delimitada 04–07/09 confirmou
meta 14,00%. A indicação da constituição “desde 06/08” não foi promovida a dado
histórico confirmado. O endpoint antigo de preços do Tesouro retornou 410;
a página corrente de títulos não expôs cotação de Tesouro Selic. Não se
inventou spread para completar o benchmark.

FX_CONVERSION_COST: **UNKNOWN** para entrada e saída (spread, taxa, tributos,
rede e rota não escolhidos). PTAX não mede esse custo; a marcação não assume
conversão gratuita. Prêmio de risco exigido por venue/colateral/stablecoin:
UNKNOWN, decisão do operador. Custo fixo operacional e atenção reais: UNKNOWN.
Estimar 2h/mês a R$50/h produz R$1.200/ano apenas como sensibilidade explícita.

**Cálculo reproduzível do cenário**, sem misturar taxa com moeda:

- Capital marcado C=5.000×5,1253=R$25.626,50.
- Rendimento bruto, taxa constante 13,9%: R$3.562,0835/ano.
- IR do cenário: 17,5% do rendimento. Custódia entre R$31,253 e R$38,377167,
  limitando a base entre saldo inicial e saldo final bruto; não é simulação
  exata de apropriação diária/tributação de cada fluxo.
- Ganho líquido ilustrativo: R$2.900,34–R$2.907,47/ano.
- ANNUAL_REQUIRED_VALUE real = BENCHMARK_NET_RETURN×C + prêmio de risco +
  custo fixo + atenção: **UNKNOWN**. No cenário, sem os três acréscimos,
  a referência é R$2.900,34–R$2.907,47; com a atenção ilustrativa,
  R$4.100,34–R$4.107,47, antes de prêmio de risco, FX e custos fixos.
- Estrutura ilustrativa spot integralmente pago + margem integral separada:
  C=N_spot+M, M=N_spot; logo C/N=2 por construção desta estrutura, não por lei.
  N=R$12.813,25; hurdle ilustrativo 22,635%–22,691% sobre esse nocional antes
  dos acréscimos. Colateral eficiente só muda o fator quando venue e regras
  forem conhecidos. Não há leverage autorizada nem medida.

O valor real exigido não virou um número preciso com campos faltantes. O
cenário é referência condicional; não é limite inferior universal, pois o
benchmark futuro e a elegibilidade do operador também não estão fixados.
MIN_GROSS_EDGE_WORTH_PURSUING permanece UNKNOWN por fricção não medida.
FX_CONVERSION_COST será incluído uma única vez nos custos fixos e não também
como desconto duplicado no retorno do benchmark.

### Funding carry, gates, oportunidades e ranking

Novidade material proposta: captar pagamentos de funding mantendo spot comprado
e perp vendido, alvo FINANCING_PREMIUM / STRUCTURAL_CONSTRAINT. H1-H3 testaram
funding/OI como preditor de direção; isso não mede essa transferência de valor.
Distinção causal aceita para preparar dossiê, não para autorizar reabertura.
`docs/reopen_dossiers/funding_carry_structural_v1.json` contém os seis campos
do gate vigente e protocolo preliminar. Passar no validador só comprova
completude documental. Não modifica `frozen_families`, não registra trial e
não autoriza execução econômica antes dos insumos acima serem conhecidos.

**G1 — FAIL para executar hoje:** sem venue/adapter real, nenhuma estrutura
de colateral verificável ou autorização de capital. Veredito:
`KILL_UNDER_CURRENT_ENVELOPE` para deployment; `BACKLOG` para a tese. G2–G7
**NOT_RUN**, obedecendo à regra do primeiro gate que reprova. Além disso, G2
estaria UNKNOWN sem benchmark efetivo e fricção; não tratá-lo como aprovado.
A tese de dez perguntas não foi aprofundada antes de fechar esses insumos.

Apenas disponibilidade pública foi sondada: [funding BTCUSDT gratuito](https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=3)
respondeu HTTP 200 em 07/09 às 18:07 UTC. Três settlements não estimam
estabilidade, APY futuro ou P&L capturável; não foram usados para um backtest.
`known_at` é a hora da consulta, distinto de `fundingTime`. A sonda independente
não substitui nem redireciona o coletor prospectivo existente.

| Família | Fidelidade, concorrência e half-life | Lacuna / primeiro gate |
|---|---|---|
| Structural/carry | Funding 8h pesquisa pagamentos; sem fills/book/margem, execução UNKNOWN. Competição profissional em basis/carry; vantagem própria não demonstrada. Half-life econômica UNKNOWN (settlement 8h não é half-life). | Venue, colateral e custos reais; G1 bloqueia deployment; G2 não computável |
| Predictive | OHLCV diário/OI1h/funding8h permitem apenas mecanismos lentos; competição sistemática, sem vantagem demonstrada. Half-life deve ser medida por alvo; 24/48h de forecast não prova duração do edge. | Família HMM congelada; H7/H8 sem evidência; não priorizar mais busca adaptativa |
| Execution/MM | Sem L2/tape/queue, latência e fill model: INCONCLUSIVE_DATA_FIDELITY. Competidores com infraestrutura mais rápida. | G1 KILL_UNDER_CURRENT_ENVELOPE; feed+venue+host apropriado destravam |
| Cross-venue | Sem execução simultânea e capital pré-posicionado; concorrência automatizada; half-life UNKNOWN com dado atual. | G1 KILL_UNDER_CURRENT_ENVELOPE; duas venues+capital+execução destravam |
| Options/on-chain | known_at defensável e histórico equivalente ainda UNKNOWN; APY divulgado não mede edge. | HOLD_ON_DATA; futura comparação depende de proveniência gratuita e estrutura |

**FREE_ALPHA_CANDIDATE — lending de stablecoin sem alavancagem:**
classe FINANCING_PREMIUM; tomadores pagam juros, potencialmente por segmentação
de crédito/colateral. Protocolo e cadeia não escolhidos, concorrência de
depositantes e fundos; contrato/oráculo, supply/borrow, utilização, custos de
rede e known_at são dados necessários. Feed live específico, capital mínimo,
edge bruto/líquido, half-life e capacidade: UNKNOWN. Pesquisa pública inicial
gratuita; falsificação mais barata é demonstrar um caminho autorizado para
custódia/execução e depois comparar juros líquidos com o hurdle em BRL.
Confiança baixa; tempo até veredito de envelope: esta rodada; até evidência
deployable: UNKNOWN. **BACKLOG, G1 KILL_UNDER_CURRENT_ENVELOPE** (nenhuma wallet,
venue ou infraestrutura de contrato autorizada). Não se examinou APY para
escolher um vencedor; G2–G7 não foram rodados. Candidato registrado e morto
barato sob o envelope, sem afirmar que não existe alpha na classe.

**Expected Value of Research — ranking qualitativo, não EV financeiro inventado:**
1. Correção DSR/causal já executada: impede conclusões ilegítimas a custo limitado.
2. Structural/carry: próxima frente exploratória apenas quando estrutura e
   benchmark forem conhecidos; mecanismo de pagamento mais direto, mas nenhuma
   vantagem ou expectativa líquida demonstrada hoje.
3. Predictive H7/H8: BACKLOG, abaixo de carry; dado/gerador precisa sustentar
   identificação e poder antes de qualquer novo resultado. HMM congelado.
4. Lending FREE_ALPHA_CANDIDATE: BACKLOG sob G1. Nenhum candidato novo passou
   G1–G7, portanto nenhum qualifica para Proof.

CURRENT_NEXT_IRREVERSIBLE_DECISION: **NONE_AUTHORIZED**. Próxima decisão
externa necessária para deployment é escolher/autorizar estrutura de venue,
custódia e capital depois da evidência de execução requerida. Para concluir o
hurdle, dependem do operador: alternativa efetivamente acessível, rota/custo FX,
prêmio de risco e custo de atenção. Esta rodada não gasta, transfere, abre
conta, altera coleta, aprova ou mergeia em nome de terceiros.


### Validação da entrega — 2026-09-07

983 testes passaram (all-extras, Python 3.13.14, Core 3.2.0). Ruff check e
format, Pyright, scan de segredos (0 achados), build wheel/sdist e instalação
da wheel em ambiente novo fora do checkout: PASS. Snapshot H6 confere; costs,
trials, h6_status e selos permanecem byte-idênticos à base. Docker e CI remoto
não foram executados. A primeira execução de testes teve 979 passes e uma
falha do path de isolamento escolhido dentro do checkout; mudado apenas o
DATA_DIR de teste para pasta externa, a suíte final passou sem essa falha.

Atestados realmente reemitidos: Fase 1 2026-09-07T18:19:19Z, V3 2026-09-07T18:19:27Z,
Core 3.2.0, ambos contra `package:3.2.0;git:b765948f5f7b48986dcbb00533193669d1202b41`. Expiração: 2026-09-14;
nenhuma validade permanente inferida. Os arquivos novos não foram instalados
na produção. Antes de qualquer implantação, é necessária revisão concreta
do diff científico e uma decisão de deployment que preserve a coleta.

Limites que continuam abertos: tarifa atual por tier/conta e fills não
medidos; benchmark do operador e FX não confirmados; séries originais dos
DSRs e posições de H1-H3 não identificadas. Resultado honesto nesses campos
é UNKNOWN, com as condições de desbloqueio descritas acima.


### Funding carry — triagem econômica autorizada em 2026-09-07

O usuário pediu explicitamente para fechar a conta econômica e decidir se
vale aprofundar. Isso autoriza a falsificação barata em Discovery apesar de
G1 deployment permanecer bloqueado; não altera coleta, capital ou freeze.
Protocolo antes do download: commit `d85d75b`, em
`docs/evidence/funding_carry_screen_20260907/protocol.json`.

**Decisão: REJECT nesta triagem; carry passivo BTC/ETH sai da prioridade de
pesquisa sob a estrutura C=US$5.000, N=US$2.500 e benchmark de referência BRL.**
As taxas de funding de 365 dias somaram 3,352476% BTC e 2,487086% ETH. Mesmo a
comparação otimista N=C, custo zero, fica em R$859/R$637 contra referência
condicional de R$2.900–2.907. Não é refutação universal da classe.

Reconstrução contábil por quantidade fixa, incluindo basis por mark price e
custos ilustrativos: US$54,84 BTC / US$34,62 ETH, ou R$281,08/R$177,46 com
FX constante 5,1253. Antes de imposto, FX e atenção; não são fills realizados.
O primeiro settlement foi excluído para não atribuir recebimento antes de
manter a posição. A referência do benchmark usa taxa corrente constante;
essa comparação com cripto retrospectivo prioriza pesquisa, não é retorno
histórico sincronizado do Tesouro nem previsão de funding.

Taxa anual requerida na estrutura padronizada: 23,14% sobre nocional, ou 32,50%
com R$1.200/ano de atenção ilustrativa. BTC/ETH ficam abaixo também nas
janelas de 30/90 dias pré-fixadas. Reduzir fee a zero não resgata a conta.
FX favorável não conta como alpha: seria necessária alta do USD/BRL de
10,11%/10,55% para igualar a referência antes de imposto.

Validação: 2.190 registros públicos, sem duplicações/lacunas de 8h; somas
Decimal, corte temporal, hashes e identidade spot+short conferidos. Campos
da vela final posteriores ao corte foram descartados. Reabertura só com
mudança material em remuneração, benchmark ou estrutura mensurável.
Resultados, cenários e fontes canônicos: `docs/evidence/funding_carry_screen_20260907/`.
Nenhuma migração adicional de runtime ou reexecução de H1-H9 foi feita.

### Altcoins por analogias anteriores às altas — Discovery, 2026-09-07

O usuário autorizou construir e executar a comparação de padrões anteriores
às altas com controles e avaliação temporal. Nova família exploratória:
`cross_sectional_spot_pre_rally_analogs_v1`; não usa funding/OI/HMM/LLM e não
reabre H1-H9. G1 de deployment continua bloqueado. Nenhum gate de capital ou
promoção foi aprovado. Esta falsificação barata tem ledger de Discovery em
`docs/evidence/altcoin_analogs_20260907/search_log.json`, sem ativação formal
de hipótese ou uso de atestado de outro harness.

Protocolo `444aa02`, antes da coleta em lote; código/controles sintéticos
`acaa925`, antes do primeiro resultado. Um kNN200 fixo, oito features diárias,
alvo de alta >=20% em sete dias e excesso >=10pp sobre BTC. Universo de 240
pares amostrados por hash do catálogo histórico, incluindo símbolos antigos;
elegibilidade por histórico e volume conhecidos antes de cada decisão.
Treinamento 2021–2023: 5.204 observações, 504 alvos, 4.700 controles. Avaliações
de 52 semanas em 2024 e 87 semanas em 2025–2026, com um dia de atraso e sem
retuning. Arquivos brutos: 251.930 velas, 395 respostas com proveniência.

**Decisão de prioridade: DO_NOT_PROMOTE_THIS_SELECTOR.** A especificação de
stress pré-fixada recebeu `REJECT_FOR_THIS_SPECIFICATION`: retornos simulados
-55,10% e -98,67%, contra -37,21% e -93,24% da cesta equivalente. Encontrar
mais episódios-alvo (7,18% versus 5,27% no segundo segmento) não compensou as
perdas. Diferença média semanal de log-retorno contra a cesta: -0,01866;
IC95% por blocos de quatro semanas [-0,03426; -0,00453], condicional a esta
busca e sem alegação de Proof ou refutação universal de efeitos pequenos.

**Fidelidade de P&L executável: INCONCLUSIVE_DATA_FIDELITY.** A regra atribuiu
-100% a desfechos sem velas completas, como stress. Entre eles há migrações
FTM/S e BNX/FORM 1:1 comprovadas em anúncios oficiais; ausência do símbolo
antigo não mede perda total. Auditoria posterior separada, mantendo sinais,
posições e treinamento: custos zerados e retorno zero nas lacunas ainda dão
-26,88% e -96,49%, abaixo da cesta equivalente. Esses diagnósticos não são
novas trials independentes nem avaliação real dos tokens migrados. As cifras
do stress original não podem ser anunciadas como perdas reais. O filtro por
sufixo também excluiu JUP/SYRUP: limitação registrada, sem troca adaptativa
da amostra. Retenção do arquivo e known_at histórico seguem limitações.

O ranking de 07/09/2026 existe como artefato de pesquisa, com 14 elegíveis,
frequência não calibrada e exemplos de vizinhos que atingiram/não atingiram
o alvo; não é sinal promovido. Para nova rodada: corrigir identidade e
rótulos de migração, definir universo negociável e saída, registrar nova
hipótese e reservar evidência nova. Trocar o alvo para payoff líquido é
pesquisa adaptativa nova; os períodos consumidos não voltam a ser intocados.
Sem DSR estimável com uma única tentativa compatível, nenhum DSR foi emitido.

Validação: 11 controles/testes novos e oito testes do gate de freeze passaram;
9.430 retornos conferidos contra strings de preços brutos usando Decimal,
seis carteiras reconstruídas independentemente; Ruff/Pyright passaram.
Produção, coleta, ledger H1-H9, scientific_state, costs e selos preservados.
Resultados originais e diagnóstico permanecem separados em `results.json`
e `audit.json` no diretório de evidência. Nenhuma ordem ou capital ativado.

### Continuação: identidade e payoff líquido — 2026-09-07

O usuário pediu continuar a partir da infraestrutura existente. Protocolo de
preparação `bbe7a8b`; implementação e controles antes da consulta de novos
preços `34b599a`. Escopo: resolver os 13 desfechos censurados já identificados,
preservar a evidência anterior e preparar um scorer que considere payoff
líquido e permita abstenção. **Zero novas trials de performance histórica.**

Dez casos receberam marcação de preço com identidade/quantidade corrigida:
NPXS/PUNDIX, BZRX/OOKI, COCOS/COMBO, OCEAN/FET, MATIC/POL, FTM/S, BNX/FORM,
EOS/A e os pares HNT/BUSD e FTT/BUSD convertidos pelo fechamento BUSD/USDT
observado. Preços são referências diárias, não fills sincronizados. BTT,
CVP e VIDT permanecem censurados: a saída no horizonte original não foi
verificada; novo ticker de BTT só negocia depois desse horizonte. Nenhum
preço futuro é usado para preencher a lacuna. `gross_return=null` substitui
o stress -100% apenas no dataset derivado; original, controles e ledger
permanecem preservados. Todas as 5.204 observações de treino são mantidas,
incluindo a única censurada remanescente nessa janela.

Sensibilidade contábil das mesmas escolhas V1, agora com migrações conhecidas:
2025–2026 permanece aproximadamente -97,83% com perda total na VIDT
censurada ou -97,33% com retorno zero nessa posição. São cenários para o
resíduo desconhecido, não resultado executável. Não mudam a decisão de
não promoção da V1 nem tornam qualquer modelo novo lucrativo.

Protótipo adaptativo V2: mesmos vizinhos/features/universo; usa log-payoff
após custos assumidos de 20 bps por perna, agrupa vizinhos por semana e
exige margem positiva após penalidade heurística de incerteza. Observação
censurada entre vizinhos força abstenção, em vez de desaparecer do treino.
Até cinco alocações de 20%; vagas vazias ficam em caixa. A fotografia já
consumida de 07/09 teve **0 de 14 candidatos aprovados, 100% caixa simulado**.
Isso testa funcionamento, não rentabilidade ou evidência prospectiva.

Status: `IMPLEMENTED_DRY_RUN_ONLY_NOT_PROMOTED`. Antes da comparação
prospectiva: universo e feed de eventos/suspensões com known_at completo,
equivalência live, preços/fills de paper, benchmark/FX/fricção e atestado
específico/poder adequado. A amostra legada ainda não é taxonomia completa
de altcoins: inclui RLUSD entre os elegíveis atuais; não há claim de universo
sem stablecoins. O helper para uso futuro corrige JUP/SYRUP como falsos
positivos de produto alavancado, sem trocar silenciosamente a amostra V1.
Primeira semana futura possível após este protocolo: 14/09; não há scheduler
ou coleta nova ativados. Evidência já vista não volta a ser intocada.

30 testes direcionados passaram (11 V1, 11 novos de payoff/identidade e oito
do gate). Ruff/Pyright passaram. Modo offline reproduziu resultados e dataset
derivado byte a byte. Detalhes: `docs/evidence/altcoin_payoff_20260907/`.
