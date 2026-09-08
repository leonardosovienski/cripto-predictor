# Observador público de carry BTC

Protocolo: `carry-btc-forward-20260908-v1`. Trabalhar sozinho. Somente dados públicos e marcas hipotéticas; sem contas, ordens, capital, serviços pagos ou alteração de produção.

O diretório operacional é `work/cripto-research` nesta tarefa; os novos dados ficam em `work/carry-forward-data`, fora do repositório. Não substituir a pasta nem o diário por cópias do pacote. O pacote é uma fotografia para reprodução.

Use o Python 3.13.14 já validado em `C:/Users/Superleo13/Documents/Codex/2026-09-07/files-mentioned-by-the-user-cripto/work/cripto-v1.2/.venv/Scripts/python.exe`, com httpx 0.28.1. Primeiro execute `-m scripts.verify_research_runtime` no repositório original. Uma divergência interrompe a rodada; não altere hashes para aceitá-la.

No diretório desta pesquisa, execute com esse Python:

```text
-m scripts.observe_carry_forward --data ../carry-forward-data --mode tick
```

O próprio observador confere o congelamento de código, o encadeamento do diário e os arquivos brutos referenciados. `--mode status` consulta o estado; `--mode preflight` faz uma coleta diagnóstica e nunca abre a posição prospectiva. Pré-testes não são semanas ou operações lucrativas. Não substituir o relógio real na operação; os relógios simulados existem somente nos testes.

Confira o código de saída e `last_run.json` antes de usar `status.json`: falha de integridade pode deixar o último status desatualizado. Preserve `ledger.jsonl` e `raw/`, incluindo falhas. O arquivo `observer.lock` pode permanecer em disco; o bloqueio é do sistema operacional. Não o apague para contornar uma execução concorrente.

Horário registrado: diariamente às 21h15 de Brasília, primeira observação em 08/09/2026 e saída prevista em 01/12/2026. A criação da automação foi recusada pelo limite de uma por tarefa; aguarda autorização para uma tarefa separada. Ver `scheduling.json`; não presumir execução automática enquanto seu estado indicar que a automação não foi criada. Entrada/saída perdidas ou interrompidas são terminais e desconhecidas. Uma coleta diária ausente permanece visível, mesmo quando dados de funding publicados são relidos depois. Nunca recriar o livro ausente por candles ou por uma oferta posterior. Não escolher outra entrada nem mudar parâmetros nesta rodada.

Notificar somente primeira entrada, falha, mudança relevante da qualidade, quebra de margem, término ou necessidade de informação. Usar `notification_signature` como auxílio; variações rotineiras de preço não justificam notificação. Ao `observation_finished=true`, relatar resultado observado e lacunas e pausar somente a nova automação de carry, preservando seus demais campos. Não alterar a automação de altcoins.

O computador deve estar ligado e o aplicativo em execução para acessar os arquivos locais no horário agendado, conforme a [documentação oficial de tarefas agendadas](https://learn.chatgpt.com/pt-BR/docs/automations). Se o agendamento não executar dentro da janela, o código preserva a ausência em vez de retrodatá-la.

Reprodução offline do suplemento:

```text
python -m pytest -q tests/test_research_corrections.py tests/test_carry_forward.py tests/test_carry_public.py
python -m scripts.plan_btc_hedge_v3 --diagnostic saved-quotes --output novo-plano.json
python -m scripts.audit_basis_sources --data CAMINHO_BASIS_RESEARCH_DATA --output nova-auditoria.json
```

Os 532 arquivos históricos estão no pacote `CRIPTO_BASIS_IMPLEMENTACAO.zip` anterior. A normalização separada precisa desse conjunto completo; o suplemento inclui o resultado da conferência. A validação sintética não necessita rede. Um ambiente diferente do runtime congelado pode rodar os testes, mas não deve continuar o diário operacional sem um protocolo novo e declarado.
