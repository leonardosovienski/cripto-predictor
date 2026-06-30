# Dossiê Técnico Consolidado — Plataforma de Experimentação Quantitativa

> Versão final integrando o melhor da análise arquitetural interna e as contribuições
> complementares identificadas, especialmente a adoção do **CCXT**, a separação explícita
> de tabelas brutas/alinhadas na Feature Store, o tratamento da **Variância Zero** e o
> desenho ER.

---

## 1. Visão Geral

**Objetivo do projeto:** construir uma plataforma única de experimentação quantitativa que
atenda múltiplos domínios (futebol, criptomoedas, ações) com uma única fonte canônica de
verdade matemática e de infraestrutura (`predictor_core`), garantindo disciplina
metodológica compartilhada, rastreabilidade de dados e independência de deploy por domínio.

**Problema que estamos tentando resolver:**

- Domínios de modelagem quantitativa estavam duplicando lógica crítica (estatística,
  métricas de avaliação, acesso a dados) sem garantia de consistência.
- As fontes de dados eram acopladas diretamente aos domínios, sem contratos formais,
  impedindo resiliência, reprodutibilidade e auditoria.
- Não havia uma camada que unificasse a ingestão de dados heterogêneos com diferentes
  granularidades e regras de integridade temporal.
- Restrições corporativas (EDR, inspeção TLS) impediam o uso de gerenciadores de pacotes
  tradicionais para compartilhamento de código.

**Princípios arquiteturais atuais:**

- **Hub-and-spoke com fonte canônica** — `predictor_core` é o único repositório de verdade
  matemática e de contratos de dados.
- **Vendoring unidirecional** — cada domínio carrega uma cópia versionada do core
  (`vendor/predictor_core/`) com manifesto de integridade (SHA256).
- **Evolução por demanda** — primitivas sobem dos domínios para o core quando genéricas;
  versões descem do core para os domínios via sync.
- **Separação estrita de responsabilidades** — domínios não importam código uns dos outros;
  o core não conhece os domínios.
- **Disciplina metodológica unificada** — telemetria comum, hipóteses pré-registradas,
  critério GO/NO-GO fixado, dupla lente de validação (PSR + bootstrap).
- **Dados como camada arquitetural explícita** — fontes, conectores e alinhamento temporal
  são responsabilidades do core, não dos domínios.
- **Resiliência e integridade temporal como requisitos de plataforma** — toda ingestão deve
  ser imune a lookahead e capaz de degradar graciosamente.
- **Separação de ingestão e serving** — o domínio nunca dispara chamadas externas; consulta
  apenas um repositório local com dados já alinhados e validados.
- **Tratamento de variância zero delegado ao domínio** — a DPL entrega dados puros com
  forward fill; a engenharia de features (ex.: criação de deltas) é responsabilidade de cada
  domínio.

---

## 2. O que aprendemos

**Aprendizado 1 — Dados e fontes são conceitos distintos.**
A pergunta inicial "dados vêm de APIs, mas as fontes vêm de onde?" revelou que os domínios
estavam acoplados às suas origens de dados, sem distinção entre o dado em si (ex.: OHLCV) e a
fonte física (ex.: Binance). É necessário separar **fonte primária** (verdade canônica),
**mecanismo de obtenção** (API, arquivo) e **consumidor** (domínio). A plataforma deve oferecer
uma camada de provedores de dados (Data Provider Layer — DPL) com contratos padronizados.
*Impacto:* criação do conceito de DPL como parte do core e do manifesto `sources.json` para
registro central das fontes.

**Aprendizado 2 — O core era o elo não testado.**
Toda a confiança vinha dos testes dos domínios (downstream). O `predictor_core` não tinha
suíte própria. O core precisa de suíte de testes própria (32 testes criados) para servir como
base confiável de propagação. *Impacto:* reforço da disciplina de testes no core, com contrato
de versão (`test_version.py`) e smoke tests cross-vendor.

**Aprendizado 3 — A tree do core estava suja.**
Melhorias do ciclo redteam estavam nos vendados mas não commitadas no repositório do core.
Antes de qualquer evolução, é obrigatório consolidar os commits pendentes no core para que a
fonte git reflita a verdade propagada. *Impacto:* priorização de tarefas de limpeza técnica
(Fase 0).

**Aprendizado 4 — O formato do carimbo de versão quebrou um domínio.**
A mudança de `-redteam-` para `-vendored-` quebrou um teste hardcoded no `predictor-stocks`. O
formato do carimbo de versão deve ser um contrato explícito e testado no core
(`test_version.py`). *Impacto:* adoção de regex de versão como parte dos testes do core.

**Aprendizado 5 — A integridade temporal exige ancoragem no `published_at`.**
Ao projetar o Alignment Engine, discutiu-se como juntar dados de granularidades diferentes
(ex.: Fear & Greed diário com candles horários). O risco de lookahead bias apareceu como
ameaça central. O alinhamento deve usar o timestamp de publicação da fonte (`published_at`),
não a data do dado. Regra: `candle.timestamp >= signal.published_at`. *Impacto:* todo dado
deve carregar seu instante de disponibilidade pública; o Alignment Engine usa essa informação
no as-of join.

**Aprendizado 6 — Dados obsoletos devem gerar NaN, não valores inventados.**
A DPL não deve imputar dados; após o limite de frescor (`max_staleness`), injeta-se NaN. O
tratamento fica a cargo do domínio. *Impacto:* separação clara entre infraestrutura (entrega
dados brutos íntegros) e modelagem (decide como tratar lacunas).

**Aprendizado 7 — A plataforma deve ter Feature Store local.**
Backtests repetidos não devem consumir APIs externas. O core deve persistir dados alinhados
em um repositório offline (Feature Store local), separando ingestão de serving. *Impacto:*
adição do módulo de persistência e materialização, transformando o Alignment Engine em um
materializador que grava a tabela final para consulta.

**Aprendizado 8 — Agregação de múltiplas fontes aumenta estabilidade.**
RedStone e outras plataformas usam agregação (mediana, TWAP) para imunizar sinais contra
anomalias de uma única exchange. A DPL deve suportar política de agregação configurável
(`fallback | consensus_median | twap`). *Impacto:* Router e conectores precisam operar em
paralelo com fusão de resultados.

**Aprendizado 9 — CCXT como abstração padronizada de conectores cripto.**
O CCXT (CryptoCurrency eXchange Trading Library) é uma biblioteca open-source que unifica o
acesso a mais de 100 exchanges. Não é uma fonte, mas uma camada de SDK que os conectores do
core podem utilizar, padronizando chamadas e reduzindo drasticamente o esforço de
desenvolvimento. *Impacto:* `BinanceProvider`, `CoinbaseProvider` etc. serão implementados
como wrappers finos sobre o CCXT, encapsulando a tradução para `MarketDataPoint`.

**Aprendizado 10 — Variância Zero é um problema do domínio, não da DPL.**
Durante a fusão temporal, o forward fill repete um valor por muitas horas, zerando a variância
intra-período dessa feature. A DPL entrega o dado bruto com preenchimento; cabe ao
`FeatureBuilder` de cada domínio criar features derivadas (ex.: `delta_sentiment`, z-score da
variação) para que o modelo capture o sinal relevante. *Impacto:* reforça a separação de
responsabilidades e orienta a documentação para desenvolvedores de domínio.

---

## 3. Decisões arquiteturais confirmadas

| Decisão | Motivo | Vantagens | Possíveis desvantagens | Status |
|---|---|---|---|---|
| Hub-and-spoke com `predictor_core` como fonte canônica | Evitar duplicação de lógica crítica entre domínios | Consistência matemática, manutenção centralizada | Core precisa ser extremamente estável e bem testado | Confirmada |
| Vendoring unidirecional (não pip) | Restrições corporativas (EDR, inspeção TLS) | Independência de deploy, rastreabilidade exata | Sincronização manual requer disciplina | Confirmada |
| `sync_core.py` com manifesto de SHA256 | Garantir que vendados estão em sincronia com o core | Detecção de drift automatizada, auditoria por hash | Overhead de manutenção do script de sync | Confirmada |
| Evolução por demanda (domínio→core, core→domínios) | Evitar que o core acumule código desnecessário | Core enxuto, primitivas validadas antes da promoção | Risco de assimetria (código nos domínios antes do commit no core) | Confirmada |
| Congelamento por prefixo (PARKED) | Proteger domínios congelados de updates acidentais | Segurança para projetos arquivados | Pode gerar defasagem se reativado | Confirmada |
| Data Provider Layer (DPL) como parte do core | Tratar dados como camada arquitetural explícita, com contratos | Desacoplamento total entre fontes e domínios, resiliência, testabilidade | Complexidade adicional no core | Confirmada |
| Envelope `MarketDataPoint` padronizado | Unificar a representação de dados de mercado | Domínios não precisam conhecer formatos nativos de APIs | Mapeamento pode ser custoso para fontes exóticas | Confirmada |
| Fallback sequencial (não concorrente) como primeiro passo | Respeitar inspeção TLS e possível penalização de paralelismo | Simples, seguro, fácil de depurar | Latência maior se fonte primária falha com frequência | Confirmada |
| Alignment Engine com Forward Fill ancorado em `published_at` | Evitar lookahead bias em dados heterogêneos | Integridade temporal garantida | Requer que todo conector forneça `published_at` | Confirmada |
| `max_staleness` com injeção de NaN após expiração | Não deixar a DPL inventar dados; domínio decide imputação | Honestidade dos sinais, separação de responsabilidades | Modelos precisam lidar com NaN | Confirmada |
| Feature Store local (SQLite/Parquet) | Economizar rate limits, garantir reprodutibilidade de backtests | Backtests rápidos, independentes de rede, rastreáveis | Requer estratégia de atualização e limpeza | Confirmada |
| Circuit Breaker proativo com consulta a status endpoints | Proteger APIs e acelerar diagnóstico de falhas | Resiliência operacional, menos requisições desperdiçadas | Depende da existência de endpoints de status | Confirmada |
| Agregação configurável (`consensus_median`, `twap`) | Imunizar sinal contra anomalias de uma única corretora | Maior estabilidade do dado consolidado | Complexidade de implementação, latência de múltiplas chamadas | Confirmada (evolução futura) |
| Separação entre ingestão e serving | Desacoplar atualização do consumo | Domínios só consultam dados prontos, nunca acessam APIs externas | Necessidade de orquestração da ingestão | Confirmada |
| CCXT como biblioteca base para conectores de exchanges | Padronizar acesso a dezenas de APIs cripto | Manutenção centralizada, atualizações acompanhadas pela comunidade | Dependência externa; é necessário wrappear para não vazar o CCXT ao domínio | Confirmada |

---

## 4. Ideias descartadas

- **Usar pip em vez de vendoring.** Descartado por restrições corporativas (EDR quarentena
  venvs, rede com inspeção TLS). Solução: vendoring unidirecional com `sync_core.py` e
  manifesto de hashes.
- **Começar a DPL pelo eixo de enriquecimento de features (Eixo 2 — micro-variáveis).**
  Descartado como primeiro passo por alta complexidade e por o `wc-predictor-v2` estar
  estacionado. Solução: iniciar com redundância (Eixo 1) no `previsao-cripto`.
- **Começar pelo contexto macro (Eixo 3 — ações com Selic/IPCA).** Descartado por
  complexidade muito alta (frequências heterogêneas, formatos legados governamentais).
  Solução: postergar para após o piloto em cripto.
- **Fallback concorrente (disparar múltiplas fontes ao mesmo tempo).** Descartado como padrão
  inicial; inspeção TLS pode penalizar conexões simultâneas. Solução: fallback sequencial com
  fail-fast, com evolução para paralelo no futuro.
- **Deixar o domínio tratar diretamente o alinhamento temporal.** Descartado por violar o
  princípio de plataforma e aumentar o risco de lookahead acidental. Solução: Alignment Engine
  centralizado no core.
- **Injeção direta do dado de baixa frequência sem tratar frescor.** Descartado porque finais
  de semana e quedas de API tornariam o dado obsoleto sem que o modelo soubesse. Solução:
  `max_staleness` no `sources.json` e injeção de NaN após o limite.

---

## 5. Componentes da arquitetura

### 5.1 `predictor_core` (biblioteca central)
Fornece módulos reutilizáveis de infraestrutura, matemática, telemetria e dados para todos os
domínios. É a fonte canônica de verdade. Comunicação unidirecional — domínios consomem o core;
o core nunca chama domínios. Sem dependências de domínios (apenas bibliotecas padrão e de
terceiros: scipy, CCXT, etc.).

- **Subcomponentes existentes:** `stats` (bootstrap, PSR, Spearman, drawdown), `obs`
  (telemetria JSONL com envelope de 7 chaves), `net` (retry/transitório + download HTTP),
  `replay` (anti-lookahead estrutural), `settings` (trava P0 de credenciais), `infra` (SQLite
  WAL + migração).
- **Subcomponentes novos:** Data Provider Layer (ver abaixo).

### 5.2 `MarketDataPoint` (contrato de dado)
Envelope imutável que todo provedor deve retornar: `symbol`, `timestamp`, `open`, `high`,
`low`, `close`, `volume`, `source`, `interval`, `published_at`. Tipo de retorno de todo
`DataProvider` e tipo de entrada para a Feature Store.

### 5.3 `DataProvider` (interface abstrata)
Define o contrato: `fetch_history(symbol, start, end, interval)` e `health_check()`. Retorna
lista de `MarketDataPoint` e boolean de saúde. Implementada por conectores concretos e usada
pela fachada `CryptoDataProvider` ou pelo Router.

### 5.4 Conectores concretos
Traduzem o formato nativo de uma fonte externa para `MarketDataPoint`. Dependem do módulo
`net`, do CCXT (exchanges) ou de adaptadores específicos (ex.: alternative.me para Fear &
Greed). Instanciados e orquestrados pelo Router. Exemplos: `BinanceProvider` (via CCXT),
`CoinGeckoProvider`, `FearAndGreedProvider`, `AmberdataProvider` (futuro).

### 5.5 `CryptoDataProvider` (fachada composta)
Interface única para o domínio cripto, escondendo múltiplos provedores e a lógica de
fallback/agregação. Internamente delega ao Router; usa `obs` para telemetria.

### 5.6 Router / FallbackRouter
Orquestra tentativas de obtenção, aplicando política de fallback ou agregação conforme
configuração. Lê `sources.json` para prioridades/políticas e usa o Circuit Breaker. Levanta
`DataUnavailableError` em falha total.

### 5.7 Alignment Engine
Funde dados de granularidades diferentes usando Forward Fill ancorado em `published_at`, com
monitoramento de `max_staleness`. Entrega uma única série temporal alinhada (features
preenchidas ou NaN se stale) para a Feature Store (materialização) ou direto para o domínio
(modo online).

### 5.8 Circuit Breaker
Protege o sistema e as APIs contra falhas repetidas, abrindo o circuito e acionando fallback.
Estados: fechado, aberto, meio-aberto. Consultado pelo Router antes de cada tentativa; emite
eventos de telemetria (`obs`).

### 5.9 Feature Store (local)
Persiste dados limpos e alinhados como repositório offline para backtests e consultas dos
domínios. Banco local SQLite (tabelas separadas para dados brutos de cada fonte e features
alinhadas materializadas) ou Parquet particionado. Separa ingestão (escrita) de serving
(leitura). Domínios só leem.

### 5.10 `sources.json` (manifesto de fontes)
Registra centralizadamente todas as fontes, metadados e políticas. Lido pela fábrica de
provedores para instanciar a configuração correta. Ponto único de verdade sobre fontes.

---

## 6. Estado atual do projeto

**O que já está definido:**

- Arquitetura hub-and-spoke, com papéis do `predictor_core` e dos 4 projetos.
- Contrato de vendoring com `CORE_MANIFEST.json` e `sync_core.py`.
- Módulos existentes do core (`stats`, `obs`, `net`, `replay`, `settings`).
- Interface abstrata `DataProvider` e envelope `MarketDataPoint`.
- Desenho da DPL: fachada, Router, conectores (com CCXT), Alignment Engine, Circuit Breaker,
  Feature Store com tabelas brutas e alinhadas.
- Políticas de fallback sequencial, agregação futura e integridade temporal (`published_at`,
  `max_staleness`, NaN).
- Roteiro de evolução em fases (0→limpeza, 1→redundância cripto, 2→Feature Store, 3→agregação,
  4→ações).

**O que já existe em código (inferido do contexto):**

- `predictor_core` v0.8.0-redteam-20260625, com módulos básicos e suíte de testes (32).
- `wc-predictor-v2` — projeto concluído (PARKED), com 159 testes.
- `previsao-cripto` — domínio ativo, atualmente acoplado a APIs de exchange via módulo `net`.
- `predictor-stocks` — estrutura inicial, pendente de integração do COTAHIST.
- `sync_core.py` e `CORE_MANIFEST.json` em operação.

**O que ainda falta implementar:**

- Commits redteam pendentes no repositório git do core.
- Toda a Data Provider Layer — contratos, conectores (CCXT), fachada, Router, Alignment
  Engine, Circuit Breaker, Feature Store.
- Integração da DPL no `previsao-cripto` — substituir chamadas diretas.
- Feature Store local com schema ER definido — tabelas brutas e features alinhadas.
- Conectores concretos — `BinanceProvider` (CCXT), `CoinGeckoProvider`,
  `FearAndGreedProvider`, e potencialmente `AmberdataProvider`.
- Agregação de múltiplas fontes — modo consenso com mediana/TWAP.
- Migração do `predictor-stocks` — `COTAHISTProvider`, `BCBProvider`, Alignment Engine.
- Smoke tests cross-vendor e testes de integração temporal.
- Dashboard de telemetria para eventos de fallback e degradação.

**Riscos conhecidos:**

- Tree do core sujo — commits pendentes podem causar perda de código.
- Carimbo de versão — tratado com `test_version.py`, mas exige propagação.
- Falta de COTAHIST — bloqueia o `predictor-stocks`.
- Complexidade da DPL — risco de overengineering se Feature Store/Alignment Engine forem
  superdimensionados para o piloto.
- Variância zero — modelos podem ignorar features com forward fill; deve ser tratado no
  domínio.
- Dependência de APIs externas — mudanças de formato, depreciações, rate limits.
- Gestão de estado do Circuit Breaker em ambientes multi-instância.

---

## 7. Plano de implementação

### Fase 0 — Limpeza Técnica e Estabilização do Core
*Objetivo:* eliminar débitos técnicos que impedem a evolução segura.
1. Comitar as melhorias redteam no repositório do core.
2. Garantir que `test_version.py` está ativo e cobre regex de sufixo.
3. Adicionar smoke test cross-vendor no CI do core.
*Critérios de conclusão:* core 100% commitado, testes verdes, drift zerado nos vendados.

### Fase 1 — Piloto da DPL: Redundância no `previsao-cripto` com CCXT
*Objetivo:* validar o contrato `DataProvider` e o mecanismo de fallback com duas fontes reais.
1. Implementar `MarketDataPoint`, `DataProvider` e `DataUnavailableError`.
2. Configurar CCXT e implementar `BinanceProvider` (wrapper).
3. Implementar `CoinGeckoProvider` como fallback.
4. Implementar `CryptoDataProvider` com fallback sequencial e telemetria.
5. Criar `sources.json` inicial com as duas fontes.
6. Migrar o `previsao-cripto` para consumir a fachada.
7. Rodar backtest para verificar equivalência.
*Critérios de conclusão:* domínio opera com duas fontes, fallback funciona, telemetria
emitida, backtest equivalente.

### Fase 2 — Feature Store Local e Alignment Engine
*Objetivo:* materializar dados alinhados em repositório offline.
1. Desenhar e aprovar o schema ER do SQLite (tabelas brutas por fonte + features alinhadas).
2. Implementar Feature Store com escrita de dados brutos e materialização de features.
3. Implementar Alignment Engine com Forward Fill, `published_at` e `max_staleness`.
4. Separar camada de ingestão (coleta + alinhamento + gravação) da camada de serving.
5. Adaptar o `previsao-cripto` para consultar Feature Store.
*Critérios de conclusão:* backtest do cripto roda offline, dados sem lookahead, NaN injetado
após `max_staleness`.

### Fase 3 — Agregação e Conectores Adicionais
*Objetivo:* adicionar política de agregação e testar fusão de granularidades.
1. Implementar chamada paralela a múltiplos provedores do mesmo dado.
2. Implementar agregação (mediana, TWAP) ponto a ponto.
3. Adicionar campo `policy` no `sources.json`.
4. Integrar `FearAndGreedProvider` e testar fusão diária + horária.
*Critérios de conclusão:* preço consolidado de duas exchanges; feature de sentimento alinhada.

### Fase 4 — Expansão para `predictor-stocks` (Contexto Macro)
*Objetivo:* aplicar a DPL madura ao domínio de ações.
1. Implementar `COTAHISTProvider` (parser TXT).
2. Implementar `BCBProvider` (SGS/Selic).
3. Configurar `sources.json` para ações e usar Alignment Engine para frequências
   diárias/mensais.
4. Rodar backtest do `predictor-stocks`.
*Critérios de conclusão:* modelo de ações treinado offline com dados macro.

### Fase 5 — (Futuro) Reativação do `wc-predictor-v2` ou Novos Domínios
*Objetivo:* demonstrar a generalidade da plataforma. Tarefas a definir.

---

## 8. Backlog técnico

- [ ] Limpeza do core — commits redteam no repositório git
- [ ] Teste de versão — `test_version.py` com regex
- [ ] Smoke tests cross-vendor — CI do core validando contratos com domínios
- [x] Contrato `MarketDataPoint` — definição da classe/dataclass *(Fase 1)*
- [x] Interface `DataProvider` — classe abstrata *(Fase 1)*
- [x] Erro `DataUnavailableError` — exceção padronizada *(Fase 1)*
- [x] Integração CCXT — instalado como dependência do domínio (piloto) *(Fase 1)*
- [x] `BinanceProvider` — wrapper CCXT para OHLCV + `published_at` *(Fase 1)*
- [x] `CoinGeckoProvider` — conector REST (fallback) *(Fase 1)*
- [x] `FearAndGreedProvider` — conector para alternative.me *(Fase 2)*
- [ ] `AmberdataProvider` (futuro) — fonte de alta frequência
- [x] `CryptoDataProvider` — fachada composta com fallback *(Fase 1)*
- [x] Router / FallbackRouter — orquestrador de tentativas e políticas *(Fase 1)*
- [x] `sources.json` — manifesto central de fontes *(Fase 1)*
- [x] Fábrica de provedores — leitura de `sources.json` e instanciação *(Fase 1)*
- [x] Desenho ER do SQLite — `raw_market_data` / `raw_signals` / `features_aligned` *(Fase 2)*
- [x] Feature Store (SQLite) — implementação de escrita e leitura *(Fase 2)*
- [x] Alignment Engine — Forward Fill + `published_at` + `max_staleness` *(Fase 2)*
- [ ] Circuit Breaker — disjuntor proativo com telemetria
- [x] Camada de ingestão — pipeline coleta → alinhamento → gravação *(Fase 2)*
- [x] Camada de serving — consulta offline à Feature Store *(Fase 2)*
- [ ] Migração do `previsao-cripto` — substituir acesso direto (DPL pronta; wiring no `main.py` pendente)
- [x] Testes de contrato — provedores retornam `MarketDataPoint` *(Fase 1)*
- [x] Testes de fallback — simular falha e verificar secundária *(Fase 1)*
- [x] Testes de integridade temporal — zero lookahead + injeção de NaN por staleness *(Fase 1/2)*
- [x] Telemetria de dados — eventos `data.fallback`, `data.unavailable` *(Fase 1; `data.stale` na Fase 2)*
- [ ] Política de agregação — chamada paralela + mediana/TWAP
- [ ] `COTAHISTProvider` — parser de arquivo B3
- [ ] `BCBProvider` — conector para Selic/IPCA
- [ ] Migração do `predictor-stocks` — DPL + Feature Store
- [ ] Dashboard de telemetria — consumo de eventos de saúde das fontes
- [ ] Documentação do arquiteto — guia de como adicionar domínios e fontes

---

## 9. ADRs (Architecture Decision Records)

### ADR-001 — Arquitetura Hub-and-Spoke com Vendoring
**Status:** Confirmada.
**Contexto:** múltiplos projetos quantitativos precisam compartilhar lógica, mas restrições
corporativas impedem pacotes tradicionais.
**Decisão:** topologia hub-and-spoke com `predictor_core` como fonte canônica; cada domínio
carrega uma cópia versionada via vendoring, com manifesto de integridade e script de sincronia.
**Consequências:** independência de deploy, mas exige disciplina de commit e sync.
**Alternativas:** pip (descartado por restrições de rede); monorepo (descartado por acoplamento
excessivo).

### ADR-002 — Data Provider Layer (DPL) como Parte do Core
**Status:** Confirmada.
**Contexto:** domínios estavam acoplados diretamente a APIs externas, sem contratos formais.
**Decisão:** criar camada de provedores dentro do core, com interface `DataProvider`, envelope
`MarketDataPoint` e manifesto `sources.json`.
**Consequências:** desacoplamento total; qualquer domínio pode consumir qualquer fonte
plugável. Aumenta a complexidade do core.
**Alternativas:** cada domínio implementar seu próprio acesso (descartado por duplicação).

### ADR-003 — Alignment Engine com Forward Fill e `published_at`
**Status:** Confirmada.
**Contexto:** dados de diferentes granularidades precisam ser fundidos sem vazamento de futuro.
**Decisão:** Alignment Engine que aplica Forward Fill ancorado no timestamp de publicação.
Regra: `candle.timestamp >= signal.published_at`.
**Consequências:** integridade temporal certificada; requer que conectores capturem
`published_at`.
**Alternativas:** interpolação (lookahead), forward fill por data base (falso frescor).

### ADR-004 — Circuit Breaker Proativo
**Status:** Confirmada.
**Contexto:** APIs externas podem falhar ou ficar lentas.
**Decisão:** Circuit Breaker que monitora falhas consecutivas, abre o circuito e testa
recuperação; opcionalmente consulta endpoints de status.
**Consequências:** maior resiliência; telemetria de degradação.
**Alternativas:** retry simples com backoff (insuficiente para falhas persistentes).

### ADR-005 — Feature Store Local como Repositório Offline
**Status:** Confirmada.
**Contexto:** backtests repetidos não devem consumir APIs, e a reprodutibilidade exige dados
imutáveis.
**Decisão:** Feature Store local (SQLite) com tabelas separadas para dados brutos e features
alinhadas. A ingestão materializa; o serving consulta apenas localmente.
**Consequências:** backtests offline, economia de rate limits, reprodutibilidade total.
**Alternativas:** cache em memória (volátil), acesso direto sempre (caro e instável).

### ADR-006 — Uso do CCXT como Biblioteca de Abstração de Exchanges
**Status:** Confirmada.
**Contexto:** o domínio cripto precisa acessar múltiplas exchanges de forma padronizada.
**Decisão:** adotar o CCXT como camada de SDK interna dos conectores do core; os conectores
wrappeiam o CCXT e convertem sua saída para `MarketDataPoint`.
**Consequências:** manutenção drasticamente reduzida; o core não expõe o CCXT ao domínio.
**Alternativas:** conectores manuais para cada exchange (descartado pelo custo de manutenção).

---

## 10. Glossário

- **Predictor Core:** biblioteca central com módulos de infraestrutura, matemática e dados.
- **Domínio:** um projeto de modelagem específico (ex.: `previsao-cripto`, `predictor-stocks`).
- **Vendoring:** cópia versionada do core dentro de cada domínio, em vez de gerenciador de
  pacotes.
- **`CORE_MANIFEST.json`:** arquivo com SHA256 de cada arquivo do core, para verificar
  sincronia.
- **Sync unidirecional:** fluxo core → domínios, via `sync_core.py`.
- **Evolução por demanda:** primitivas criadas no domínio e promovidas ao core quando
  genéricas.
- **PARKED:** prefixo que congela um domínio, impedindo recebimento de sync.
- **DPL (Data Provider Layer):** camada de abstração de fontes de dados, parte do core.
- **`MarketDataPoint`:** envelope padronizado de um ponto de mercado (OHLCV + metadados).
- **`DataProvider`:** interface abstrata que todo provedor de dados implementa.
- **Router / FallbackRouter:** componente que decide qual fonte usar e gerencia tentativas.
- **Alignment Engine:** motor que funde séries temporais de granularidades diferentes via
  Forward Fill.
- **Forward Fill:** técnica que repete o último valor conhecido até a próxima atualização.
- **Published At:** timestamp em que um dado se tornou publicamente disponível.
- **Max Staleness:** tempo máximo que um dado é considerado fresco; após isso, vira NaN.
- **Feature Store:** repositório de dados limpos e alinhados, com tabelas brutas e features
  materializadas.
- **Circuit Breaker:** padrão que interrompe chamadas a uma fonte após falhas consecutivas.
- **Obs:** módulo de telemetria do core (eventos JSONL com envelope de 7 chaves).
- **CCXT:** biblioteca open-source que unifica o acesso a mais de 100 exchanges de cripto.
- **Shin:** método de purificação de odds.
- **CLV:** Closing Line Value — medida de edge em apostas.
- **PSR:** Probabilistic Sharpe Ratio.
- **Lookahead Bias:** vazamento de informação futura no treinamento.
- **Variância Zero:** feature preenchida por forward fill que não varia dentro do período,
  exigindo engenharia de features (ex.: delta) no domínio.

---

## 11. Próximos passos

1. Executar Fase 0 — commits redteam, `test_version.py`, smoke tests cross-vendor.
2. Implementar o contrato `MarketDataPoint` e `DataProvider` no core.
3. Configurar CCXT e construir `BinanceProvider` (wrapper) com testes unitários.
4. Construir `CoinGeckoProvider` e a fachada `CryptoDataProvider` com fallback sequencial.
5. Migrar o `previsao-cripto` para a fachada — validar equivalência.
6. Desenhar e aprovar o schema ER da Feature Store (tabelas brutas + alinhadas).
7. Implementar a Feature Store (SQLite) e a separação ingestão/serving.
8. Implementar o Alignment Engine com Forward Fill, `published_at` e `max_staleness`.
9. Adaptar o `previsao-cripto` para consultar a Feature Store offline.
10. Adicionar `FearAndGreedProvider` e testar fusão de granularidades.
11. Implementar Circuit Breaker proativo com telemetria.
12. Adicionar política de agregação (consenso) ao Router.
13. Migrar o `predictor-stocks` — `COTAHISTProvider`, `BCBProvider`, Feature Store.
14. Documentar o guia do arquiteto para extensão da plataforma.

---

## 12. Auditoria da conversa

**Inconsistências identificadas:**

- Módulos `obs` e `net` no `wc-predictor-v2`: na visão de arquitetura o wc consome apenas
  `obs` e `stats` do core, mas listagens do projeto sugerem implementações locais. Débito
  conhecido, mitigado pelo status PARKED.
- Transição de fallback em runtime para Feature Store offline: o design inicial pensava em
  roteamento sob demanda; a arquitetura evoluiu para ingestão separada do serving — coerente,
  não é inconsistência.

**Mudanças de direção:**

- De "analisar fontes" para "construir DPL completa".
- De "começar com micro-variáveis" para "começar com redundância (Eixo 1)".
- De "fallback simples" para "agregação + Feature Store + Circuit Breaker + CCXT".

**Decisões contraditórias:** nenhuma. As evoluções foram aditivas e planejadas.

**Pontos ainda indefinidos:**

- Formato exato da Feature Store — SQLite vs. Parquet (decisão dependerá de testes de
  performance).
- Mecanismo de atualização da Feature Store — cron, gatilho por demanda, ou ambos.
- Governança de promoção de código — critérios formais para uma primitiva subir ao core.
- Tratamento de NaN — cada domínio definirá sua estratégia de imputação.
- Testes do Alignment Engine — como automatizar a verificação de integridade temporal.
- Estado do Circuit Breaker em multi-instância.

**Riscos técnicos:** sobrecarga do core com muitas responsabilidades; manutenção de conectores
mesmo com CCXT (APIs mudam); ambiente restritivo pode dificultar a ingestão inicial;
complexidade de testes de fallback e alinhamento.

**Possíveis melhorias:** dashboard de saúde das fontes com dados do `obs`; versionamento
semântico do core com contratos explícitos; ferramenta de validação de `sources.json`.

**Inferências:** o estado exato do código atual é inferido a partir das discussões; a
implementação real pode divergir. A referência a Amberdata é ilustrativa de uma possível fonte
futura, não uma decisão tomada.

---

## 13. Inventário de APIs / Fontes por fase

### 13.1 Em uso (Fase 1 — piloto)

| API / Fonte | Papel | Status |
|---|---|---|
| **Binance** (via CCXT) | Preço OHLCV (fonte primária) | Em uso |
| **CoinGecko** | Preço/mercado (fallback) | Em uso |
| **SerpAPI** | Notícias (insumo qualitativo) | Em uso |
| **Gemini** (Google) | LLM / juiz da análise | Em uso |

### 13.2 Planejadas para as fases seguintes (Fase 2/3 — Agregação e Sentimento)

| API / Fonte | Papel | Fase | Motivo |
|---|---|---|---|
| **Kraken** | Agregação (preço) | Fase 3 | Segunda exchange de alta confiabilidade para o modo consenso (mediana/TWAP). O CCXT já abstrai a Kraken, então o custo de adicionar é baixo. |
| **Fear & Greed Index** (alternative.me) | Sentimento diário | Fase 2/3 | Validar o Alignment Engine com fusão de granularidades (diário + horário). É a fonte de baixa frequência usada como prova de conceito da fusão temporal. |

### 13.3 Mencionadas como possibilidades futuras (Eixo 2 — Micro-variáveis)

Estas fontes **não estão no plano imediato**, mas foram citadas como exemplos de como o Eixo 2
(enriquecimento de features) poderia ser atacado depois que a DPL estiver madura. Não há decisão
de implementá-las — apenas registro de que são compatíveis com a arquitetura.

| API / Fonte | Tipo de dado | Exemplo de uso |
|---|---|---|
| **Amberdata** | Alta frequência (tick data, velas de 1 minuto) | Treinar modelos intraday com mais resolução. |
| **Glassnode** | On-chain (volume de baleias, taxas de mineradores, fluxo para exchanges) | Features de comportamento da rede que podem anteceder movimentos de preço. |
| **mempool.space** | On-chain (taxas de transação, congestionamento) | Indicadores de atividade da rede Bitcoin em tempo real. |
| **CoinMarketCap** | Agregador (preço, volume, market cap) | Alternativa ao CoinGecko como segundo fallback, se necessário. |

### 13.4 O papel do CCXT

O CCXT **não é uma fonte**, mas uma biblioteca que unifica o acesso a mais de 100 exchanges.
Será usado **dentro dos conectores** para exchanges como Binance e Kraken. O domínio nunca vê o
CCXT; ele é encapsulado nos provedores concretos.

### 13.5 Resumo por fase

| Fase | APIs adicionadas | Propósito |
|---|---|---|
| Fase 1 (piloto) | Binance + CoinGecko | Redundância de preço |
| Fase 2/3 (sentimento + agregação) | Fear & Greed, Kraken | Fusão temporal e consenso |
| Futuro (Eixo 2) | Amberdata, Glassnode, etc. | Micro-variáveis on-chain e alta frequência |

---

> **Conclusão:** este dossiê reflete o estado da arte da arquitetura da plataforma,
> incorporando todo o aprendizado, decisões e componentes discutidos, enriquecido com a adoção
> do CCXT, a separação explícita das tabelas da Feature Store e o tratamento da Variância Zero.
> Serve como documentação canônica para os próximos passos de implementação.
