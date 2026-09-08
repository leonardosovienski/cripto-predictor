# Execução CRIPTO v1.2 — 7 de setembro de 2026

As correções foram implementadas na branch local
`codex/cripto-v1-2-execution-20260907`, baseada em `3c104ce`.
Repositório de trabalho: `C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2`.
Produção, coleta, capital, parâmetros de custos e ledger congelado foram preservados.

| Prioridade | Entrega | Limite restante |
|---|---|---|
| P0-D | H6 reconciliada como encerrada por amostra insuficiente; corrigidos charter, registry, case e erratas | Não reaberta; IC cruzando zero não é refutação |
| P0-B | Claims de custos rebaixados para ASSUMED/UNCALIBRATED; sensibilidade algébrica H1-H3; proposta de pré-registro | Fee real, fills e posições originais desconhecidos; não inventado novo PSR |
| P0-A | Core 3.2.0 nos seis pins, DSR estrito, contagem de todas as tentativas, bloqueio de unidades incompatíveis, cinco caminhos de atestado corrigidos | DSR histórico exato não é reconstruível sem séries e ledger originais |
| P0-C | Reclassificação causal H1-H9 aplicada; H9 encerrada por amostra insuficiente | Só 1/45 folds avaliável não identifica o efeito de OI/volume |
| Economia | Fontes públicas, benchmark candidato em BRL, exposição cambial, cenários e dossiê de carry | Hurdle efetivo UNKNOWN; carry bloqueado em G1 por falta de estrutura de execução |

**Validação:** 983 testes passaram; Ruff, formatação, Pyright, build e instalação
da wheel fora do checkout passaram; scan de segredos com zero achados.
Dois atestados reais emitidos em árvore limpa, válidos até 14/09/2026.
Docker/CI remoto não executados; nenhum merge, push ou deployment realizado.

O achado adicional mais relevante foi a mistura de Sharpes por operação com
`mean/std × sqrt(n)` no ledger. A nova implementação recusa esse DSR até que
a base de comparação seja comprovada, preservando os resultados históricos.

US$5.000 equivalem contabilmente a R$25.626,50 na [PTAX de 04/09](https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do).
O cenário de benchmark, condicionado à elegibilidade no [Tesouro Reserva](https://www.tesourodireto.com.br/tesouro-reserva),
taxa constante, tributação PF e demais premissas explicitadas, gera cerca de
R$2.900–R$2.907/ano. Isso não é o retorno contratado nem o hurdle final do operador.
Na estrutura ilustrativa com metade do capital gerando carry, corresponde a
22,64%–22,69% sobre o nocional, antes de prêmio de risco, FX e atenção.

O [FAQ Binance](https://www.binance.com/en/support/faq/detail/360033544231) ilustra
2bps maker e 5bps taker, mas não comprova a tarifa atual de uma conta. Essa
diferença de proveniência impede chamar a análise de calibração real.

Para revisar a implementação, use o patch entregue, relativo à base `3c104ce`.
O relatório detalhado está no patch em `docs/HYPOTHESES.md`, seção
“Errata e decisões CRIPTO v1.2 — 2026-09-07”. Evidências de fontes e inventário
de 48 menções numéricas DSR/SR0 ficam em `docs/evidence/`. A branch local já
contém os arquivos, testes e atestados; a aplicação em produção não foi feita.

Pendências concretas: dados da tarifa/execução, benchmark acessível e rota FX
do operador, prêmio de risco/custo de atenção e inputs históricos dos DSRs.
Não há estratégia liberada para capital real.
