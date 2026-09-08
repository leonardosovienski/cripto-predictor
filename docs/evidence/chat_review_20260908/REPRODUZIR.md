Revisão e correção do planejador de quantidades

Para novos diagnósticos com os dados públicos já preservados, use o ponto de entrada `scripts.plan_btc_hedge_v2`. A versão v1 e os motores históricos permanecem congelados para reproduzir os pacotes anteriores.

No worktree de pesquisa, usando o Python e as dependências já instalados:

```powershell
python -m scripts.plan_btc_hedge_v2 --diagnostic ../btc-execution-diagnostic-v1 --output ../NOVO_PLANO_VALIDADO.json
python -m pytest tests/test_btc_execution_validation.py tests/test_btc_execution_plan.py tests/test_btc_basis.py tests/test_absolute_research.py tests/test_altcoin_payoff.py tests/test_altcoin_retro.py tests/test_altcoin_forward.py -q
```

O arquivo de saída precisa ser novo. A execução usa somente arquivos salvos; não existe envio de ordens. `validation.json` registra as verificações desta revisão. `new_code_freeze.json` registra a nova versão sem substituir os freezes anteriores.

O pacote complementar desta revisão inclui o novo código, seus testes, a versão v1 e os helpers necessários ao diagnóstico, além do relatório e da evidência. Requer Python 3.13, httpx 0.28.1 e pytest para os testes. Os dados públicos de diagnóstico permanecem no pacote anterior `CRIPTO_BASIS_IMPLEMENTACAO.zip`, pasta `execution` após a extração. As validações dos modelos antigos requerem seus módulos do worktree completo.

Para reproduzir apenas a correção no pacote complementar extraído:

```powershell
python -m scripts.plan_btc_hedge_v2 --diagnostic CAMINHO_DO_PACOTE_ANTERIOR/execution --output NOVO_PLANO.json
python -m pytest tests/test_btc_execution_validation.py -q
```

Os campos econômicos dos 12 planos válidos devem ser iguais aos de `execution/net_hedge_plans.json` do pacote anterior. O cabeçalho v2 difere por registrar a correção. Não trocar hashes históricos para forçar aceitação de arquivos modificados.
