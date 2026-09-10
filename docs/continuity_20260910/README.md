# Continuidade final dos dados e fontes — 10/09/2026

Este complemento reúne **2685 arquivos em 5 ZIPs**, com corte em **2026-09-10T22:47:29.726272+00:00**. O [manifesto](MANIFEST.json) vincula cada arquivo e cada ZIP por SHA-256. Leia a [conferência de arquivos](../CONFERENCIA_ARQUIVOS_20260910.md) e a [conferência do chat](../CONFERENCIA_CHAT_20260910.md).

Inclui dados operacionais recentes e recibos de fontes (Aave, futuros, spot e registros manuais), saídas de análises, evidências/scripts da revisão, referências do perfil local e um backup consistente do diagnóstico com três previsões, dois snapshots e um input. As versões e tentativas anteriores preservam seus nomes e resultados; não são promovidas a dados válidos apenas por estarem guardadas. Os [24 pacotes anteriores](../continuity_20260909/README.md) continuam necessários para as capturas mais antigas.

## Verificar e recuperar

Use o ambiente atual do projeto:

```powershell
C:\Cripto\CRIPTO.cmd python C:\Cripto\pesquisa-20260909\docs\continuity_20260910\restore_archives.py
C:\Cripto\CRIPTO.cmd python C:\Cripto\pesquisa-20260909\docs\continuity_20260910\restore_archives.py --output C:\Cripto\recuperacao-final-20260910
```

O primeiro comando verifica sem extrair. O segundo exige uma subpasta de recuperação e verifica toda a seleção antes de escrever. Recusa caminhos inseguros, credenciais/quotas, sidecars SQLite, colisões e conteúdo existente diferente. Pode selecionar um ZIP com `--archive nome.zip`.

Arquivos extraídos são cópias de referência. Não execute scripts históricos com caminhos absolutos sem conferir seu protocolo e seus destinos. Não copie a recuperação sobre o banco ativo, quotas, diários ou executores congelados. O banco do diagnóstico fica em `diagnostico-operacional-20260910`, separado da operação.

## O que permanece local e o que ainda falta

Configuração privada, cópia do chat, quotas e ambientes instalados permanecem em `C:\Cripto`; seus locais e backups são indicados no guia local. Um log foi publicado com três valores no formato de credencial ocultados, mantendo o original local. O arquivo propositalmente diferente usado no teste de conflito de restauração ficou local; não é um dado de mercado faltante. Os identificadores públicos de assuntos/publicações das notícias foram mantidos, conforme a [documentação do provedor](https://serpapi.com/google-news-api). Os tratamentos constam no manifesto. Distribuições e ZIPs antigos redundantes continuam nos pacotes anteriores ou nos arquivos locais de auditoria. Nenhum original foi alterado para produzir este complemento.

Esse corte registra o que existe; não cria originais H5 perdidos, versões macro sem comprovação, comparação Aave ainda não executada ou observações futuras. O snapshot v4 vence em 11/09/2026 às 02:00 UTC. Atualizar arquivos no Git não renova dados de mercado nem comprova lucro.

O resultado final da integração e do CI está no [PR #118](https://github.com/leonardosovienski/cripto-predictor/pull/118). O relatório vivo local inclui as etapas posteriores a este corte. Para continuar sem o chat, leia `C:\Cripto\LEIA_PRIMEIRO.md` e os índices acima.
