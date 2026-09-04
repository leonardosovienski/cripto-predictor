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

### H6 — Sinal invertido do LLM prevê retorno D+7 (status: **coletando — ver `GarimpoInvestimentos/h6_status.json`**)

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
- Resultado: **imaturo** — última evidência versionada: Sharpe auxiliar +0,3479
  com n=6; o gate pré-registrado exige n>=30 e IC95 positivo. Sem veredito.

### H7 — Calendário macro (FOMC/CPI/PPI) + DXY como contexto exógeno de regime (status: **registrada — infraestrutura de coleta implementada, coleta real não iniciada**)
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
  2. ⬜ Validar `DXYProvider().fetch()` ao vivo, ponta a ponta, contra o FRED —
     precisa rede real, fora deste ambiente.
  3. ⬜ Confirmar `publish_lag_days` real do release H.10 contra o texto oficial
     — idem, fora deste ambiente.
  4. ✅ **Decisão tomada (2026-09-04): integração (a) — covariável exógena do
     HMM em `v3/regime_engine.py`.** Critério de sucesso confirmado: PSR≥0,80 ∧
     IC_CI_lower>0, líquido de custos (mesmo gate de H1-H3).
  5. ✅ `pipeline_fingerprint` coberto pelo atestado do harness já válido
     (expira 2026-09-10; não precisou renovar).
  6. ⬜ Registrar em `trials.json` com `registered_at` ANTES de qualquer previsão
     contar como dado da trial — só falta isso e os itens 2-3.

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

---

## Backlog condicional (ideias — NÃO são tentativas)

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

#### H8 — [RASCUNHO, NÃO REGISTRADA] Promoção de B9 acima a hipótese formal

> Rascunho gerado em 2026-09-04 a pedido do dono, para acelerar a promoção de B9 a
> trial formal quando os itens (3) e (4) da tabela acima forem decididos. **Isto NÃO
> é um registro válido** — falta preencher os placeholders abaixo com dado real
> gerado na máquina do dono e então commitar em `trials.json` com `registered_at`
> ANTES de qualquer previsão contar como dado da trial. Reabrir esta seção só faz
> sentido depois de (1) DSL confirmado ainda íntegro e (2) atestado do harness
> renovado.

- Mecanismo, contramedidas de risco (PBO/DSR/traço append-only) e ressalva de
  honestidade: ver B9 acima na íntegra — não duplicado aqui.
- Família e parentesco: família nova; NÃO reabre H4/H5/H6, que seguem fechadas com
  os vereditos que têm.
- Critério de sucesso (fixar por escrito ANTES de rodar — placeholder):
  ⬜ [PSR ≥ 0.80 ∧ IC_lo > 0, líquido de custos, SE a recipe gerada produzir sinal
  tradeable na V3 — OU métrica equivalente declarada por escrito conforme o tipo de
  fator que a recipe de fato produzir; não decidir isso depois de ver o resultado].
- `metric` a declarar no registro: ⬜ [ex. "psr" ou "sharpe", conforme aplicável].
- `pipeline_fingerprint`: ⬜ [regenerar via `scripts/attest_harness.py`, incluindo
  hash do DSL/prompt usado pelo LLM para propor hipóteses].
- Checklist de ativação:
  1. ⬜ Confirmar que `analyzers/factor_dsl.py` (prova de não-leakage) segue íntegro.
  2. ⬜ Renovar o atestado do harness (`scripts/attest_harness.py`) — o de
     2026-08-21 expirou.
  3. ⬜ Registrar em `trials.json` com `metric` declarado (ato humano deliberado).
  4. ⬜ Só então coletar dado GENUINAMENTE NOVO sob esta configuração.
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


