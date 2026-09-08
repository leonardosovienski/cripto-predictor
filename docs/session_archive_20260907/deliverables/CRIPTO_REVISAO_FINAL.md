# Revisão final do projeto de cripto — 07/09/2026

**A revisão foi executada, as correções foram aplicadas e os testes locais passaram. Ainda não há lucro real comprovado. Há dois cenários históricos de carry positivos após custos de negociação assumidos.**

| Estudo | Capital hipotético | Resultado |
|---|---:|---:|
| Seletor atual de altcoins, 140 semanas de 2024 a setembro/2026 | 5.000 USDT | **0 USDT / 0%**, nenhuma operação |
| Carry BTC, setembro/2025 a setembro/2026 | 5.000 USDT | **+54,84 USDT / +1,10%** |
| Carry ETH, mesmo ano | 5.000 USDT | **+34,62 USDT / +0,69%** |

Cada linha é um cenário separado; os ganhos não devem ser somados como se usassem os mesmos 5.000 USDT. Carry, aqui, combina uma posição na moeda com uma posição vendida equivalente em contrato perpétuo. Os números usam preços de referência, taxas e deslizamento assumidos; não foram operações realizadas.

## A conclusão que precisava mudar

O carry havia sido descartado por não superar uma comparação externa. Você depois retirou essa exigência. **Eu deveria ter trazido os seus saldos positivos de volta à conclusão geral. Corrigi essa omissão e refiz a conta a partir dos dados brutos.** O objetivo agora é somente lucro absoluto.

Isso ainda não confirma lucro líquido real: faltam custos efetivos da conta, conversões/transferências, impostos e comprovação da execução e da margem ao longo do caminho. No BTC, apenas 54,84 USDT de custos adicionais eliminariam o ganho do cenário; no ETH, 34,62 USDT. Os dados já foram consultados na pesquisa, portanto são diagnóstico histórico, não validação independente nem promessa futura.

## O que foi corrigido e validado

- Recuperação do observador após encerramento brusco, mantendo a proteção contra duas execuções simultâneas.
- Balanço que distingue semanas conhecidas, perdidas, com posições e em caixa. Falta de observação não vira lucro zero; término do calendário não vira aprovação.
- Registro atualizado quando a coleta falha. A soma de experimentos semanais de tamanho fixo não é apresentada como saldo de uma conta capitalizada.
- Dependências científicas do CI e arquivos inconsistentes de duas ferramentas de empacotamento. As versões fixadas foram restauradas e receberam checagem permanente de integridade.
- Acompanhamento existente atualizado para a versão corrigida, mantendo datas e preferências de aviso. O novo preflight encontrou 44 candidatos elegíveis e nenhuma seleção.

**Validação final: 1.045 testes passaram, sem falhas ou pulos.** Também passaram lint, formatação, checagem de tipos, geração do pacote, instalação fora da pasta de código, verificação de 3.785 arquivos do ambiente e reprodução dos cálculos. Um ambiente mínimo separado passou em 1.011 testes, com quatro pulos por dependências opcionais. Os seis pacotes históricos anteriores foram preservados.

Docker e CI remoto não foram validados: o serviço local do Docker não ficou acessível e o Windows negou sua inicialização. Não considero essas verificações aprovadas.

## Qualidade final e lucro

**A infraestrutura funciona como ferramenta de pesquisa e simulação nos controles locais executados. A rentabilidade do projeto ainda não está comprovada.** O seletor atual não mostrou capacidade de lucrar; eu não afrouxei seus filtros para fabricar entradas. O carry apresentou saldos históricos positivos pequenos, ainda dependentes de hipóteses de custo e execução.

O acompanhamento futuro permanece agendado para domingo às 21h de Brasília, primeira janela em 13/09 e última saída em 06/12. Não há observações futuras ainda. Testar o ciclo inteiro com dados sintéticos valida o software, não antecipa esses resultados. O computador e o app precisam estar ativos para a automação local. [Documentação oficial](https://learn.chatgpt.com/docs/automations?surface=app).

Nenhuma ordem, conta, transferência ou capital foi ativado. A conclusão é: **simulação positiva de carry existe; lucro real comprovado ainda não.**
