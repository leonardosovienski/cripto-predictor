# Histórico das execuções

1. `absolute-results-v1`, código 9bfb994: abortou na leitura do catálogo UTF-8 por usar o encoding padrão CP1252 do Windows. Nenhuma variante foi avaliada, nenhuma decisão calculada. Correção explícita de encoding e de anotação de tipo Decimal. Log preservado em `logs/research-first-run.log`. Os 36 controles anteriores passaram; lint apontou apenas importação/formatação, corrigidos antes desta execução. Pyright apontou a tipagem do expoente Decimal, corrigida sem mudar a aritmética.

Nenhuma regra, limiar, período ou custo foi alterado. Execução seguinte usa diretório novo e conserva o primeiro.
