> Continuidade sem o chat antigo: `docs/SESSION_HANDOFF_20260907.md`; prompt conferido: `docs/NEXT_CHAT_PROMPT.md`; tag do fechamento: `cripto-session-20260907-final`.

# Estado consolidado após a revisão de 07/09/2026

**Há cenários históricos de carry positivos após custos assumidos. Não há lucro real nem lucro líquido do investidor comprovado. O seletor atual de altcoins não operou nas 140 semanas históricas.**

Este é o ponto de entrada corrente desta linha de trabalho. Os relatórios, hipóteses e freezes anteriores permanecem registros das suas respectivas datas. O objetivo adotado pelo usuário é lucro líquido absoluto; nenhuma comparação com outro investimento é exigida.

## Resultado econômico revisado

| Linha | Evidência que existe | Conclusão permitida |
|---|---|---|
| Seletor original de grandes altas | Resultados negativos nas análises anteriores, incluindo correções de migrações; três desfechos ainda desconhecidos | Não promovido; contar grandes altas não demonstrou carteira lucrativa |
| Seletor atual de payoff | 140 semanas, 13.996 ocorrências elegíveis, nenhuma posição; 5.000 → 5.000 USDT | Lucro simulado zero, sem taxa de acerto de operações estimável |
| Carry BTC, 07/09/2025–07/09/2026 | +54,84071944 USDT, +1,0968% sobre 5.000 USDT hipotéticos | Cenário histórico positivo após taxas/deslizamento assumidos; não lucro real validado |
| Carry ETH, mesmo período | +34,62367591 USDT, +0,6925% sobre 5.000 USDT hipotéticos | Mesma limitação; é outro cenário de 5.000 USDT, não ganho adicional na mesma carteira |
| H1–H9 e famílias antigas | Estados e resultados anteriores preservados | Nenhuma nova aprovação, reabertura ou alegação de lucro |

A rejeição antiga do carry dependia de uma referência externa que o usuário depois retirou. Ela não equivale a retorno absoluto negativo. A revisão recompõe os mesmos fluxos dos dois ativos a partir de oito respostas brutas, com Decimal, sem buscar outro período ou ajustar parâmetros. O ganho BTC suporta apenas 54,84 USDT de custos adicionais antes de zerar; no ETH, 34,62 USDT. Conversão, transferências, tarifas reais, impostos e a viabilidade efetiva da margem não estão certificados. Uma margem de referência de 2.500 USDT não comprova ausência de liquidação.

## Alterações implementadas

1. O observador usa bloqueio do sistema operacional, liberado quando o processo termina. Um arquivo `observer.lock` remanescente já não impede todas as execuções posteriores; concorrência continua bloqueada.
2. O status contabiliza as 12 janelas, semanas conhecidas, ausentes, com posições e em caixa. Sem observações, lucro é desconhecido. Semana ausente não vira zero. Calendário encerrado não vira evidência de lucro.
3. Falhas de aquisição atualizam o status com o erro, preservando os registros anteriores.
4. O CI de qualidade e o perfil experimental instalam a dependência científica necessária aos testes novos. O perfil mínimo equivalente foi instalado e executado separadamente.
5. Arquivos inconsistentes de `distlib` e `virtualenv` no ambiente local foram restaurados das versões exatas do lockfile, por wheels com SHA256 conferido e cópia sem vínculos ao cache compartilhado. `verify_research_runtime.py` detecta novas divergências; não atribuímos uma causa sem evidência.
6. As conclusões de lucro foram reunidas, incluindo os cenários positivos que a resposta anterior centrada no seletor omitiu.

O modelo, treinamento, penalidade de incerteza, limiar, tamanho por candidato e custos declarados do seletor não foram alterados para produzir um resultado favorável. A geometria identifica sinais sintéticos fortes, mas sua penalidade continua heurística; isso não calibra probabilidade de sucesso no mercado. A versão atual permanece como observação de pesquisa.

## Operação corrente

Perfil: `docs/evidence/altcoin_reviewed_20260907/`; dados: `work/altcoin-reviewed-data`. A v4 anterior permanece intacta e reproduzível usando sua versão preservada. O novo perfil incorpora somente correções operacionais antes das primeiras decisões prospectivas.

O preflight repetiu a busca: 487 pares spot/USDT ativos no catálogo, 472 após exclusões, 44 elegíveis, nenhum selecionado. Foram conferidas 616 respostas, 44 contas de compra hipotética e a reprodução offline do snapshot. O universo implementado continua Binance spot/USDT, sem alegar cobertura de qualquer cripto ou corretora.

O horário do acompanhamento permanece domingo às 21h de Brasília: primeira entrada possível 13/09, última saída 06/12. Cada janela tem 60 minutos. A checagem do runtime precede o registrador. O computador e o app precisam estar ativos para a automação local; [documentação oficial de tarefas agendadas](https://learn.chatgpt.com/docs/automations?surface=app).

Cada semana usa 5.000 USDT como referência fixa de tamanho. A soma dos resultados semanais conhecidos não é saldo de uma conta capitalizada, pois o tamanho não foi recalculado segundo uma conta real. O total do piloto fica desconhecido até todas as janelas serem observadas. A simulação de um ciclo completo nos testes é controle de software, não observação dos meses futuros.

## Limites da validação

Testes, controles de interrupção, lint, formatação, tipos, build por uv e por `python -m build`, instalação da wheel fora do checkout, integridade das bibliotecas e reproduções históricas têm registros na pasta `project_review_20260907`. Os seis pacotes antigos e os arquivos científicos protegidos permanecem íntegros. Contagens finais e hashes constam em `validation.json`.

O Docker local não ficou disponível; iniciar seu serviço foi negado pelo Windows. Container, branch POSIX do bloqueio e CI remoto não foram executados nesta máquina. Esses limites não são transformados em PASS. Produção, banco de dados real, ordens, contas e capital permanecem fora desta execução.

**Qualidade final:** infraestrutura de pesquisa e simulação validada nos controles locais descritos; seletor sem lucro demonstrado; carry com cenários positivos ainda não convertidos em execução e lucro líquido comprovados. Não existe uma nota numérica objetiva ou um selo de rentabilidade decorrente da contagem de testes.
