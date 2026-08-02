# Classificação de cobertura

Nenhum arquivo é omitido do relatório global. A segunda métrica mede o runtime homologado com `coverage-runtime.ini` e falha abaixo de 80% de branch coverage.

| Classe | Namespaces/módulos | Justificativa |
|---|---|---|
| Runtime homologado | `config`, `contracts`, `core`, `dpl`, `analyzers.ai_insights`, `prefilter`, `score_engine`, `feature_store_health`, `jobs`, `persistence`, `plugin`, `providers`, `security`, `services.inference` | Caminho operacional de coleta, inferência, persistência e operação. |
| Pesquisa ativa | `v3` | Hipóteses quantitativas e paper trading; roda no job CI `all-extras`, sem skips. O payload diário é supervisionado pelo entrypoint instalado de `predictor_ops`. |
| Migração | `dpl.migrations`, helpers de importação CSV em `core.history` | Compatibilidade aditiva de stores/exports existentes. |
| Compatibilidade | `scripts/*.py`, `run_garimpo_fase1.bat`, shims pequenos em `dpl` | Adaptadores transitórios; runtime novo usa entrypoints instalados. |
| Legado não executado | Documentos históricos | Não entram no pacote wheel nem no runtime homologado. Os scripts PowerShell restantes são apenas wrappers para o entrypoint instalado. |
| Entrypoints triviais | `cli.py`, módulos `services` que apenas reexportam função canônica | Wiring sem lógica científica; ainda visíveis no relatório global. |

## Skips auditados

Baseline anterior: oito skips — quatro testes de manifesto de vendor, dois de higiene dependentes de Git, um módulo HMM sem NumPy e um módulo paper trader sem hmmlearn. Os seis primeiros foram substituídos por contratos de wheels/higiene que sempre executam. Os dois últimos executam no job `all-extras`, que instala `v3`. Resultado atual com todos os extras: **zero skips**.

O job mínimo pode reportar os dois skips de importação opcional; nenhum teste de extra suportado depende apenas dele, pois `all-extras` é obrigatório e sem `continue-on-error`.
