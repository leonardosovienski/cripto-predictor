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

### H6 — Sinal invertido do LLM prevê retorno D+7 (status: **REFUTADA / NO-GO — 2026-09-04**)

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
- Resultado: **REFUTADA — IC cruza zero em n=84** (ver veredito 2026-09-04 no
  topo desta seção). Histórico intermediário preservado acima por transparência
  (n=6, Sharpe auxiliar +0,3479) — nunca foi o veredito, só uma leitura
  imatura de passagem.

### H7 — Calendário macro (FOMC/CPI/PPI) + DXY como contexto exógeno de regime (status: **registrada em `trials.json` 2026-09-04, coleta prospectiva ainda não iniciada**)
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

### H9 — Razão OI/Volume (crowding especulativo) como covariável exógena do regime (status: **REFUTADA / NO-GO — 2026-09-04**)

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

- **EM ABERTO, para decisão do dono — Sharpes divergentes de hipóteses
  FECHADAS.** O registro local traz valores diferentes dos versionados:

  | trial | versionado | local |
  |---|---|---|
  | `v2-dpl-multi-h7` (H5) | -0,312 | **-0,4186** |
  | `h6-sinal-invertido-d7` (H6) | 0,3479 | **0,4766** |

  Ambas as hipóteses estão `CLOSED_NO_GO`, e `register_trial` proíbe reescrever
  trial de hipótese fechada. Os valores locais são provavelmente mais maduros
  (mais previsões acumuladas), mas sobrescrever resultado de hipótese fechada é
  precisamente o que a imutabilidade existe para impedir — e fazê-lo por
  iniciativa de quem audita seria pior do que a divergência. Fica REGISTRADO
  aqui e NÃO aplicado: cabe ao dono decidir, e a decisão deve ser documentada
  junto do motivo.

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
