# Continuidade — recuperação econômica Nível 2/3 — 19/09/2026

## Comece aqui

Este diretório é o ponto de retomada autocontido da branch `profit-recovery-20260919`. Ele registra a implementação causal, a auditoria econômica sequencial e a verificação `reuse → verify → gap` sem depender do chat.

Branch publicada: `profit-recovery-20260919`. A publicação desta branch **não** implica merge em `main`, release, instalação na operação principal, ativação de scheduler ou autorização de capital.

Depois do push, confirme o corte com:

```powershell
git ls-remote origin refs/heads/profit-recovery-20260919
git show --stat --oneline origin/profit-recovery-20260919
```

## Ordem de leitura

1. [Relatório completo reuse/verify/gap](REUSE_VERIFY_GAP_EXECUTION.md).
2. [Baseline congelado](BASELINE_V1.json).
3. [Resumo econômico estruturado](LEVEL2_SUMMARY.json).
4. [Manifesto de publicação e artefatos locais](MANIFEST.json).
5. [Resultado expandido](LEVEL2_EXECUTION.json) e ledgers causais [BTC](BTC_CAUSAL_LEDGER_V2.json), [ETH](ETH_CAUSAL_LEDGER_V2.json) e [SOL](SOL_CAUSAL_LEDGER_V2.json).
6. Código: [`profit_recovery_v1.py`](../../GarimpoInvestimentos/profit_recovery_v1.py) e [testes](../../tests/test_profit_recovery_v1.py).

## Resultado que deve ser preservado

- `LEVEL_2_VERDICT`: `INCONCLUSIVE`.
- Round A BTC: `INCONCLUSIVE`.
- Round B ETH/SOL: `INCONCLUSIVE`.
- Operação: `RESEARCH_ONLY`.
- Paper trading e microcapital: `NOT_READY`.
- Reservado final: `RESERVED_FINAL_INSUFFICIENT`.
- Capital: `false`.

Não há prova de edge incremental. BTC tem somente um episódio independente na validação; ETH tem três, intervalo cruzando zero e perde para buy-and-hold; SOL tem cinco, intervalo cruzando zero e empata exatamente com momentum de 1 dia.

## Validação local deste corte

- suíte completa: 1.585 passaram, 2 pulados;
- módulo direcionado: 16 passaram;
- Ruff: passou;
- Pyright: 0 erros, 0 avisos;
- sdist e wheel: construídos, com o módulo presente no wheel;
- worktree: limpo após o commit;
- nenhuma credencial, banco operacional ou dado bruto restaurado foi adicionado ao Git.

O primeiro intento da suíte ampla parou na coleta por `numpy` ausente no ambiente novo. Os extras `v3` e `test`, já declarados pelo projeto, foram sincronizados e a suíte completa foi repetida com sucesso. Esse intento inválido permanece documentado no relatório.

## Git versus somente local

O GitHub contém o código, os testes, o relatório completo, o baseline, o resumo, o JSON expandido, os três ledgers causais e este handoff. Os inputs de mercado, o banco operacional, builds e ambientes permanecem locais; seus hashes/procedência necessários estão preservados nos artefatos e no relatório.

Clonar a branch permite revisar e reproduzir a lógica, mas não restaura `C:\Cripto\operacao`, `C:\Cripto\restaurado-20260908`, configuração privada ou ambientes locais. Preserve `C:\Cripto` se esses itens forem necessários.

## Próximo incremento permitido

Somente coleta prospectiva append-only posterior ao freeze, com `event_time`, `received_at`, hash, quotes/depth, acknowledgement e paper fills. Não iniciar automaticamente. Não ajustar PR122 nem adicionar LLM, HMM, notícias, order book ou novas features sem gap causal formal e novo protocolo.
