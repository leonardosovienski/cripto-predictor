# Replay local de falhas

A suite `tests/test_failure_replay.py` reproduz falhas historicas e cenarios de
infraestrutura sem rede, credenciais reais, banco de producao ou capital.

Execute:

```bash
pytest -q tests/test_failure_replay.py
```

## Contrato de aceitacao

Cada replay verifica pelo menos duas dimensoes: a falha/status correto e a
invariante que deve sobreviver. A suite cobre:

1. provider LLM digitado errado, recusado antes da rede;
2. todos os providers de ingestao indisponiveis, sem sucesso vazio;
3. timeout do orquestrador como `FAILED`, sem sobrescrever estado cientifico;
4. regressao de H6 de `n=31` para `n=0`, recusada byte a byte;
5. candle futuro mais proximo, mantido invisivel;
6. adulteracao apos remocao privilegiada dos triggers, detectada pela hash chain;
7. backup consistente enquanto existe escritor SQLite em WAL;
8. prefilter ativo excluindo dado incompleto com razao observavel.

Essa suite e um agregador operacional, nao substitui os testes unitarios mais
detalhados. Novos incidentes devem entrar primeiro como replay minimo que falha,
depois receber a correcao e permanecer aqui como regressao permanente.

## Limites conhecidos

O API guard usa contador SQLite persistente por dia/estagio/chave, com transacao
`BEGIN IMMEDIATE`; reinicio e processos concorrentes compartilham o mesmo teto.
O teste dedicado cobre persistencia e a verificacao operacional multiprocesso
deve permanecer no checklist de release. O replay nao altera retrospectivamente
filtros ou gates de trials congeladas.
