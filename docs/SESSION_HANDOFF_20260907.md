# Continuidade da sessão de 07/09/2026

Este documento permite retomar a pesquisa sem ler o chat antigo. O prompt conferido está em `docs/NEXT_CHAT_PROMPT.md`. A tag local `cripto-session-20260907-final` identifica o fechamento completo; a revisão de código e resultados termina em `07794acbc5a3f779eb8d45c932be5070d36251a7`. A documentação e os arquivos de recuperação acrescentados depois não representam novos testes de rentabilidade.

## Objetivo e decisões do usuário

Buscar lucro líquido absoluto, na mesma moeda e após os custos aplicáveis. O usuário delegou a escolha de moedas, corretoras e abordagens de pesquisa. Não existe requisito de superar Selic, BTC, uma cesta ou outro investimento. O uso de BTC como característica estatística do modelo não equivale a exigir um benchmark.

O usuário pediu testes retrospectivos, revisão integral, melhorias e execução das validações. O prompt de continuidade autoriza poucas hipóteses justificadas, registradas antes de avaliar cada variante, com limites de tentativas e preservação dos resultados negativos. Restrições antigas contra novos backtests e comparações externas não devem impedir esses pedidos posteriores. Não reabrir silenciosamente famílias científicas congeladas nem tratar o histórico já consumido como validação independente.

Trabalhar sozinho, sem coordenar agentes. Usar dados públicos e recursos disponíveis. Sem contas autenticadas, ordens, transferências, capital, serviços pagos ou alterações de produção. A referência de 5.000 USDT é hipotética. Resolver escolhas técnicas rotineiras autonomamente. Essas instruções registram o escopo adotado nesta sessão; documentos antigos são evidência histórica quando divergirem dos pedidos posteriores do usuário.

## Resultado que deve acompanhar qualquer continuação

| Linha | Evidência | Limite |
|---|---|---|
| Seletor atual de altcoins | 140 semanas históricas; zero operações; 5.000 → 5.000 USDT | Lucro simulado zero; taxa de acerto e ganhos por operação não estimáveis |
| Carry BTC | +54,84071944 USDT, +1,0968%, entre 07/09/2025 e 07/09/2026 | Custos assumidos; não lucro real comprovado |
| Carry ETH | +34,62367591 USDT, +0,6925%, no mesmo período | Outro cenário de 5.000 USDT; não somar ao BTC na mesma carteira |

Os cenários de carry usam nocional spot inicial de 2.500 USDT e referência de margem de 2.500 USDT, quantidade de hedge fixa, taxas spot de 10 bps e perp de 5 bps por lado e deslizamento de 5 bps por perna. A reconciliação usa oito respostas públicas preservadas e Decimal. Execução, trajetória intradiária de margem/liquidação, custos da conta, conversão, transferências e impostos continuam desconhecidos. A antiga rejeição por benchmark não determina o objetivo atual. Não há lucro líquido real do investidor comprovado.

O adapter implementado cobre Binance spot/USDT. O último preflight tinha 487 pares no catálogo, 472 após exclusões, 44 elegíveis e nenhuma seleção. Esses números são um snapshot, não o estado futuro da corretora.

As 1.045 aprovações de testes, lint, tipos, builds e reproduções são evidência de software nas condições registradas. Docker, caminho POSIX do bloqueio e CI remoto não foram executados. O pacote final teve 4.665 arquivos conferidos, 62 testes selecionados e seis resultados reproduzidos byte a byte, sem consultas públicas durante a reprodução. Não repetir toda a suíte por causa deste fechamento documental; testar mudanças futuras conforme seu impacto.

## Onde está o trabalho

- Worktree original: `C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2`.
- Branch: `codex/cripto-v1-2-execution-20260907`.
- Git comum: `C:\Users\Superleo13\cripto-predictor\.git`, fora da pasta do chat. O checkout `main` não foi modificado por este fechamento; seu `fred_test.csv` preexistente pertence ao usuário.
- Recuperação independente: `C:\Users\Superleo13\Documents\CriptoBackup\2026-09-07\CRIPTO_SESSAO.bundle` e prompt no mesmo diretório.
- Estado econômico/técnico: `docs/PROJECT_STATE_20260907.md` e `docs/evidence/project_review_20260907/`.
- As 41 entregas anteriores e o prompt revisado: `docs/session_archive_20260907/deliverables/`.
- Prompt anterior, configuração da automação, inventário e conferência de coerência: `docs/session_archive_20260907/`.
- Dados originais e auxiliares de trabalho: `docs/session_archive_20260907/WORKSPACE_RESEARCH.zip`. O índice interno lista cada arquivo e SHA256. Ambientes virtuais, caches e cópias de reprodução redundantes são reconstruíveis e foram excluídos; a lista exata consta no inventário.

O pacote `deliverables/CRIPTO_REVISAO_FINAL_REPRODUCAO.zip` permanece com SHA256 `99d2063d33b9e517b58c1c35e5fec2c16cd29b3f1f6b1a34ce15879c3439fbb3` e fonte `51c5a88084c9cf77c36731c5a26eb1e6574a3d8f`. Seus manifests antigos mantêm os checkpoints originais. Não atualizá-los para fingir que foram gerados no novo commit.

O anexo original `C:\Users\Superleo13\Downloads\CRIPTO_V1.2.md` já não estava disponível na revisão nem neste fechamento. Seu hash anteriormente registrado era `e0e2d24e54130571448eb0dcf770e1b2990ea52b1b1a387b6c1b55808a69bc4c`. Não alegar preservação ou releitura de um arquivo ausente. As decisões adotadas e suas alterações posteriores estão consolidadas aqui e no histórico de hipóteses.

## Recuperação sem depender da pasta do chat

Clone o bundle em um diretório novo, sem sobrescrever arquivos existentes. Exemplo em PowerShell:

```powershell
git clone --branch cripto-session-20260907-final 'C:\Users\Superleo13\Documents\CriptoBackup\2026-09-07\CRIPTO_SESSAO.bundle' 'C:\Users\Superleo13\Documents\Codex\cripto-retomada-20260907'
```

O checkout da tag fica destacado. Crie uma branch nova antes de pesquisar. Se esse diretório já existir, escolha outro. Não fazer reset, checkout ou merge sobre a `main` do repositório original. O bundle contém o histórico alcançável pela branch desta pesquisa e pela tag, não todos os projetos do usuário.

Para reproduzir, extraia o pacote final em outro diretório novo, confira `FILES_SHA256.json` e siga seu README. A instalação requer acesso às dependências; a reprodução usa os dados guardados. Python 3.13.14, Core 3.2.0 e Ops 4.1.0 foram os componentes validados. Prefira `uv sync --locked --all-extras --no-cache --link-mode copy` e verifique a integridade do runtime conforme o projeto. As wheels exatas de Core e das dependências reparadas também foram guardadas no snapshot de trabalho; isso não é um mirror completo de todas as dependências.

O snapshot `WORKSPACE_RESEARCH.zip` está dividido nas partes `.001` e `.002`, para manter os arquivos individuais abaixo de 100 MiB. O script `docs/session_archive_20260907/restore_workspace.py` verifica os arquivos preservados, reúne as partes em memória e confere os 7.136 arquivos de trabalho. Sem argumentos, apenas verifica. Com `--destination CAMINHO_NOVO`, restaura os diretórios com seus nomes originais; recusa um destino já existente. Requer somente a biblioteca padrão do Python 3.11 ou posterior.

Extraia em uma pasta nova e use caminhos absolutos. Não sobrescreva o ledger atual com um snapshot antigo. Os scripts auxiliares preservados documentam a execução passada: alguns não são idempotentes e não devem ser executados em lote.

Os hashes científicos podem depender de bytes e finais de linha. Um checkout Git com outra política de CRLF pode diferir da cópia congelada em disco. Os pacotes preservam os bytes originais. Para execução sob freeze, conferir os hashes antes de seguir, usando a cópia exata do pacote se necessário; nunca recalcular hashes para aceitar uma mudança involuntária.

## Acompanhamento vinculado ao chat antigo

No fechamento, a automação `observar-altcoins-semanalmente`, nome “Observar altcoins semanalmente”, estava ACTIVE, tipo heartbeat, vinculada à tarefa `01a07d06-406f-7781-adad-0d0ea3ae9424`. O horário é domingo às 21h em America/Sao_Paulo. Primeira entrada: 13/09/2026; última saída: 06/12/2026. São 12 janelas de 60 minutos. O perfil ativo é `docs/evidence/altcoin_reviewed_20260907`, com freeze SHA256 `2bc8f67c704780acff78973404c7a8f5915d05d90f8b05bba72d16aa360a25f6`.

O estado preservado tem duas linhas de preflight no ledger, nenhuma decisão prospectiva e nenhum resultado maturado. Lucro prospectivo é desconhecido, não zero. A qualidade está `AWAITING_NEW_OBSERVATIONS`. Confira o estado atual antes de retomar; arquivos futuros podem ser mais recentes que este snapshot.

O Git salva a configuração e os registros; não transfere o agendamento entre conversas. O prompt novo pede que a tarefa sucessora atualize o destino da automação existente, preservando os demais campos. Se ela tiver sido removida, recriar uma única heartbeat com a configuração guardada e conferir o resultado. Não presumir que apagar o chat preserva uma automação vinculada a ele. Não duplicar nem substituir silenciosamente por cron independente. Este fechamento não criou outra tarefa, não alterou o agendamento e não apagou o chat.

Para manter continuidade sem interrupção, abrir a nova tarefa com o prompt salvo, concluir a transferência da automação e então apagar a antiga. Se o chat antigo já tiver sido apagado, o projeto e o estado guardado continuam recuperáveis; o agendamento precisa ser restabelecido antes da próxima janela. Não registrar retrospectivamente janelas perdidas.

O computador e o aplicativo precisam estar ativos para trabalho agendado com arquivos locais, conforme a [documentação oficial](https://learn.chatgpt.com/docs/automations?surface=app). A [documentação de worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees) descreve limpeza de worktrees geridos pelo aplicativo; não usamos isso como garantia de preservação da pasta desta tarefa. A cópia independente existe para que a continuidade não dependa desse comportamento.

## Próximo trabalho

Confirmar a integridade e a transferência do acompanhamento; depois pesquisar poucas hipóteses registradas, executando mudanças e testes necessários em isolamento. Explicar em português simples o que mudou, quanto ganhou ou perdeu nas condições declaradas, a sensibilidade a custos e o que ainda não está demonstrado. Preservar todos os resultados. Não transformar ausência de operações, controles sintéticos, testes aprovados ou um único período adaptativo em prova de rentabilidade.

Os commits deste fechamento são locais; nenhum push foi solicitado ou executado. A cópia em outro diretório protege contra perda da pasta do chat, não contra perda do computador inteiro.
