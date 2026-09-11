# Implementação arquitetural — 2026-09-11

Exportador integrado à linha de pesquisa atual copiando apenas `packages/research-export`; os módulos existentes em `GarimpoInvestimentos/research` foram preservados. O wheel do exportador 1.0.1 requer o contrato stdlib >=1.0.1,<2 e não importa o predictor.

`cripto-predictor history --database PATH` lê SQLite em modo somente leitura, sem configuração privada, coleta ou migração. `_load_rows` do backtest também não migra schema/CSV. A importação antiga passa a ser uma ação explícita: `cripto-predictor migrate-history --database PATH --csv PATH`. A análise continua escrevendo suas previsões, mas não absorve mais CSV implicitamente.

`FeatureStore(..., read_only=True)` não cria bancos nem executa migrações. As ferramentas de backup e harness estão dentro do pacote instalável, em `GarimpoInvestimentos.operational`; scripts antigos são entradas de compatibilidade. O harness exige checkout de fonte explícito e limpo para atestar; o wheel sozinho não ganha autorização de escrever atestados.

A ingestão emite recibo com etapas efetivamente persistidas. As gravações continuam em commits separados: falha posterior não é descrita como rollback. A análise registra resultado por ativo e distingue falha de fonte, filtragem, cache, degradação e orçamento. Falha total é erro; execução parcial retorna 2.

Validação: 59 testes de DPL/história/falhas/fronteiras; 33 testes de migração, backup e jobs; 12 do exportador. Há sobreposição entre conjuntos, portanto não somar como casos únicos. Ruff aprovado nos arquivos alterados. Wheels do predictor e exportador gerados separadamente. Nada foi coletado, agendado ou reavaliado em coortes reais.

Rollback preserva dados e publicações; não reinstalar a árvore inteira do branch antigo do exportador sobre esta linha de pesquisa. Os pins publicados de Core/Ops permanecem até homologação da combinação candidata.
