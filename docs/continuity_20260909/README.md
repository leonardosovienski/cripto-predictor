# Pacote de continuidade — 09/09/2026

O dono pediu que código, prompt, contexto e dados necessários à continuidade fossem publicados antes de apagar o chat. Este pacote preserva **22 arquivos ZIP, contendo 9.713 arquivos**, aproximadamente 128 MB, além dos documentos legíveis no repositório. Há sobreposição entre aquisições; essas quantidades não representam ativos distintos.

## Conteúdo

- Código e testes: na árvore normal do repositório, com alterações da revisão capturadas sem modificar o checkout onde ela continua.
- [Prompt final](../NEXT_CHAT_PROMPT.md): mandato de revisão, estado anterior e instruções de continuidade.
- [Arquivos locais de entrada](local-root/LEIA_PRIMEIRO.md), [instruções da raiz](local-root/AGENTS.md) e [atalho original](local-root/CRIPTO.cmd): cópias de referência, sem alteração da instalação.
- `reports-root.zip`: relatórios gerais, mandato econômico original, resultados, configuração documentada sem valores secretos e textos ao investidor.
- `reports-fechamento_pendencias_20260909.zip`: validação anterior, scripts de recuperação/verificação e evidências.
- `reports-revisao_completa_20260909.zip`: registro vivo, testes e evidências da revisão em andamento na data da captura. O estado ainda é de revisão.
- Demais `reports-*.zip`: preparação dos dados e versões anteriores do repasse.
- `data-operacao.zip`: aquisições novas, incluindo futuros recuperados e tentativas de recuperar altcoins.
- `data-20260907-*.zip`: bases públicas preservadas de carry, futuros, altcoins e suas fontes, incluindo arquivos brutos comprimidos.
- `operational-diagnostics.zip`: saídas do pipeline, marcador de diagnóstico e cópia consistente de `feature_store.db` criada pela API de backup SQLite em leitura. WAL/SHM não foram copiados como se fossem bancos independentes.

O [MANIFEST.json](MANIFEST.json) lista cada arquivo interno, tamanho e SHA-256, o arquivo ZIP correspondente e seu hash. As fontes de dados foram preservadas byte a byte. Relatórios com dados de autenticação conhecidos ou endereços de email receberam remoção desses valores na cópia exportada, identificada no manifesto; originais locais não foram modificados. Os bytes descomprimidos das fontes gzip também foram examinados para correspondências com as credenciais configuradas. Isso não substitui uma auditoria universal de segredos desconhecidos.

## Verificar ou recuperar

Com o Python do projeto, para verificar todos os hashes sem extrair:

```powershell
C:\Cripto\CRIPTO.cmd python C:\Cripto\publicacao-chat-20260909\docs\continuity_20260909\restore_archives.py
```

Se o checkout estiver em outro caminho, ajuste apenas o caminho do script. Para recuperar em uma pasta nova dentro de C:\Cripto:

```powershell
C:\Cripto\CRIPTO.cmd python C:\Cripto\publicacao-chat-20260909\docs\continuity_20260909\restore_archives.py --output C:\Cripto\recuperacao-github-20260909
```

O script verifica os arquivos antes de escrever, recusa caminhos que escapem da pasta e não sobrescreve arquivos diferentes. Pode selecionar um ZIP com `--archive nome.zip`. A recuperação não configura provedores, restaura credenciais, ativa observadores ou envia ordens. Confira os caminhos e as instruções antes de usar qualquer script histórico extraído.

Na máquina atual, os originais continuam em seus caminhos de C:\Cripto. Não é necessário extrair ou substituir esses originais para continuar a tarefa.

## O que permanece apenas local

Chaves/API keys e configurações privadas, o ZIP original de migração de aproximadamente 1,57 GB, ambientes/dependências instalados, pastas duplicadas de verificação, estado transitório e banco de cotas não foram publicados. Alguns binários de build/cobertura e saídas anteriores estão excluídos e enumerados no manifesto; os respectivos logs e comprovantes textuais estão incluídos.

Esta é uma publicação de continuidade do projeto, não uma imagem completa do computador. O banco antigo de previsões que não foi encontrado não passou a existir nesta cópia; permanecem as lacunas históricas e econômicas descritas no repasse. Mudanças da revisão ativa após a captura precisam de publicação própria.
