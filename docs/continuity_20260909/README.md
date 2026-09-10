# Pacote de continuidade corrigido

Esta versão reúne **24 ZIPs e 9.817 arquivos internos**. O [manifesto](MANIFEST.json) registra cada tamanho, hash, origem, transformação e horário. Há sobreposição entre aquisições; a contagem não representa ativos distintos. Veja [resolução das falhas](RESOLUCAO_PR110.md) e [dependências](DEPENDENCIAS.md).

- Os pacotes históricos preservam seus bytes e datas. data-operacao-v2.zip exclui exclusivamente os dois sidecars transitórios do orçamento; todos os demais conteúdos são iguais. O original permanece no commit 4ae9e3d e na cópia local preservada.
- reports-final-review-20260910.zip acrescenta 105 arquivos: validações finais e pós-merge do #111, auditorias, diagnóstico real, scripts e revisão do #110. Recupera para operacao/relatorios/REVISAO_FINAL_PUBLICADA_20260910, separado da captura anterior. A revisão do #110 contida nele antecede as correções descritas em RESOLUCAO_PR110.md.
- operational-diagnostic-final-20260910.zip contém um backup SQLite consistente com três previsões, um snapshot e um input. Recupera para operacao/diagnosticos-preservados/20260910/feature_store.db. Não restaura sobre o banco operacional.
- operational-diagnostics.zip é a captura anterior, com duas previsões. As diferenças temporais são esperadas; as versões não são combinadas nem retrodatadas.
- Os demais data-* e reports-* contêm aquisições públicas e referências históricas. local-root guarda cópias de referência dos atalhos e instruções anteriores.

## Verificação e recuperação

Na instalação atual, depois de atualizar o checkout, execute no PowerShell:

    C:\Cripto\CRIPTO.cmd python C:\Cripto\pesquisa-20260909\docs\continuity_20260909\restore_archives.py

Esse comando verifica todos os arquivos sem extrair. Para recuperar em um diretório novo:

    C:\Cripto\CRIPTO.cmd python C:\Cripto\pesquisa-20260909\docs\continuity_20260909\restore_archives.py --output C:\Cripto\recuperacao-continuidade-20260910

Pode selecionar pacotes com --archive nome.zip, repetindo a opção. Os caminhos recuperados são relativos à pasta de recuperação; use-os como referências isoladas. Scripts históricos com caminhos absolutos exigem ajustar o destino operacional antes de executar.

O recuperador verifica a seleção inteira antes de criar arquivos, recusa configurações privadas, bancos de orçamento, WAL/SHM/journals, caminhos externos ou ambíguos, arquivos conflitantes entre ZIPs e destinos existentes diferentes. Arquivos existentes idênticos permitem repetir uma recuperação concluída. Hashes e extração usam blocos de memória limitados. Não há escrita em credenciais, quotas ou diários ativos.

Em outra instalação, reconstrua Python/uv e as dependências fixadas pelo uv.lock conforme [MIGRACAO_WINDOWS.md](../MIGRACAO_WINDOWS.md) e [CONFIGURACAO_LOCAL.md](../CONFIGURACAO_LOCAL.md); os ambientes instalados não estão no pacote. Apagar o chat nesta máquina não exige reinstalar nada.

## Limites da publicação

Credenciais, configurações privadas, o pacote original completo de migração, ambientes instalados e orçamento de APIs permanecem locais. O scanner de segredos conhecidos não certifica ausência de toda credencial desconhecida. A publicação é uma continuidade versionada, não uma imagem completa da máquina, uma prova de lucro ou uma recuperação dos inputs H5 ausentes. Os resultados do CI final ficam no GitHub; não são presumidos por um relatório capturado antes desse CI.
