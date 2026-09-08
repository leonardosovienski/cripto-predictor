# Código auxiliar e versões históricas preservadas

O código atual permanece em `GarimpoInvestimentos/`, `scripts/` e `tests/`. Este diretório preserva também os scripts auxiliares, as variantes antigas e os utilitários da primeira migração que existiam nas pastas locais e nos pacotes de pesquisa em 08/09/2026.

O [índice](sources.json) associa cada caminho original a um arquivo em `objects/`, com SHA256, tamanho e extensão original. Conteúdos idênticos ocupam um único objeto; os bytes originais, inclusive finais de linha, foram preservados. `.gitattributes` impede conversões desses arquivos.

Esses objetos são registros históricos, com os defeitos e caminhos da época. Não são módulos ativos nem devem ser executados diretamente. Por esse motivo, estão fora da formatação automática e do lint. Os scripts de operação atuais continuam sujeitos aos checks normais. A varredura de segredos inclui este diretório.

O utilitário atual é [research_migration.py](../../scripts/research_migration.py). Ele restaura o código a partir deste índice e os dados a partir do pacote externo `CRIPTO_DADOS_MIGRACAO_20260908.zip`. O pacote externo não contém arquivos de código, executáveis, bibliotecas Python, bundles Git nem arquivos ZIP mistos: os conteúdos de dados desses ZIPs foram separados, com a origem registrada no manifesto.

Bibliotecas de terceiros e ambientes virtuais são dependências reinstaláveis, não código próprio novo. As versões do ambiente operacional estão em [runtime-requirements.txt](runtime-requirements.txt). A restauração não instala nem ativa automações. Consulte o [guia de migração](../MIGRACAO_WINDOWS.md).
