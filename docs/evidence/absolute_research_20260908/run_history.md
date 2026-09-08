# Histórico das execuções

1. `absolute-results-v1`, código 9bfb994: abortou na leitura do catálogo UTF-8 por usar o encoding padrão CP1252 do Windows. Nenhuma variante foi avaliada, nenhuma decisão calculada. Correção explícita de encoding e de anotação de tipo Decimal. Log preservado em `logs/research-first-run.log`. Os 36 controles anteriores passaram; lint apontou apenas importação/formatação, corrigidos antes desta execução. Pyright apontou a tipagem do expoente Decimal, corrigida sem mudar a aritmética.

Nenhuma regra, limiar, período ou custo foi alterado. Execução seguinte usa diretório novo e conserva o primeiro.

2. `absolute-results-v2`, código dc27268: primeira avaliação econômica completa das cinco séries; todos os resultados preservados. Passaram 57 controles direcionados e Pyright. O auditor inicialmente exigiu barras de BNX depois da migração que o próprio modelo já havia tratado pelo registro BNX→FORM. Corrigido o auditor para rastrear a quantidade e a cotação do sucessor; nenhuma conta da estratégia mudou. A auditoria completa passou.

3. Correção de causalidade registrada em 3ceef8f, aplicada no código 9048c61: filtros atuais não participam mais do dimensionamento histórico. A grade matemática permanece em 0,001 unidade. `absolute-results-v3` conserva exatamente todos os ledgers econômicos e as decisões anteriores. Apenas metadados de proveniência/diagnóstico mudaram. A fonte dos scores passou de caminho absoluto para identificador e hash para permitir reprodução em outra pasta; o leitor de dados interpreta separadores de caminho portavelmente. Passaram 58 controles, incluindo tornar os filtros presentes impossíveis sem mudar a simulação.

4. O helper de documentação inicial leu tanto o snapshot antigo quanto o arquivo de automação em CP1252; só a cópia textual salva no Git ficou com acentos incorretos. A automação efetiva sempre esteve em UTF-8 correto. A cópia documental foi relida explicitamente em UTF-8 e comparada ao prompt original, mantendo toda a configuração efetiva intacta. A falha da comparação e a correção não causaram alteração na automação.

5. A entrega inclui restauração em pasta nova, conferência dos hashes, auditoria independente e replay integral em caminhos diferentes. Não há novo teste econômico nem uso de outro período; essa execução verifica reprodução e preservação.
