# Guardas antes de chamadas externas

As guardas limitam unidades de trabalho nos pontos que as invocam. Elas não substituem os limites dos provedores nem estabelecem um teto monetário. Neste PC, o perfil privado usa:

```dotenv
API_GUARD_ENABLED=true
API_GUARD_MAX_INGEST_ASSETS=28
API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER=8
API_GUARD_MAX_LLM_CALLS_PER_PROVIDER=6
```

Os valores estão documentados em [CONFIGURACAO_LOCAL.md](CONFIGURACAO_LOCAL.md). Pela semântica do código, limite `0` deixa a respectiva etapa sem teto; não use esse valor para contornar uma quota esgotada.

## Persistência e escopo

O consumo fica em `DATA_DIR/api_guard_budget.db`, neste perfil `C:\Cripto\operacao\dados\api_guard_budget.db`, por dia UTC, etapa e provedor. O incremento usa transação SQLite `BEGIN IMMEDIATE`; processos e reinícios compartilham o mesmo orçamento. A virada normal é às 00:00 UTC. Preservar o banco é parte da continuidade; não apague, zere ou restaure quotas antigas para permitir novas chamadas.

Na Fase 1, a guarda é aplicada antes da ingestão de cada ativo, de cada tentativa de notícias e de cada chamada lógica de LLM. Os executores manuais posteriores usam seus próprios pontos de reserva do orçamento compartilhado; veja [EXECUCAO.md](manual_dependencies_20260910/EXECUCAO.md) e [AUDITORIA_AMPLIADA_20260910.md](AUDITORIA_AMPLIADA_20260910.md). Uma unidade lógica pode envolver várias requisições HTTP ou retries do cliente. A existência desta guarda não comprova cobertura universal de V3, scripts auxiliares ou serviços externos.

## Cache e rastreabilidade

- Fear & Greed é cacheado por processo e limite, evitando a mesma busca por ativo na rodada.
- Notícias bem-sucedidas são cacheadas no processo por fonte, consulta e limite; o router aceita a entrada apenas quando a idade desde o recebimento está entre zero e menos de uma hora.
- Bloqueios no fluxo da Fase 1 emitem `api_guard_skipped`, com etapa, ativo e motivo. Os executores manuais também registram seus estados e recusas nos artefatos definidos pelo protocolo.

Os limites podem alterar a população coletada. Mudanças em provedores, orçamento ou roteamento precisam de protocolo e amostra novos; H5 permanece encerrada. Consulte [fontes de notícias](NEWS_PROVIDERS.md). Nenhum agendamento ou pagamento foi ativado por esta configuração.
