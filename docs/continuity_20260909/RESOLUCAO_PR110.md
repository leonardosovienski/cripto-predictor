# Correção conjunta dos PRs #110 e #111

O #110 capturou uma revisão ainda em andamento. Sua primeira versão falhava em três testes e a combinação automática com o #111 reintroduzia uma alteração nas funções congeladas H6. Esta atualização incorpora o main `909724e36d23b1683268c9e43d533f553c7dfe5f` e preserva integralmente o código de execução e os testes já corrigidos naquele commit.

As funções científicas H6 permanecem iguais ao congelamento original; o isolamento dos novos diagnósticos ocorre nos consumidores. Foram preservados o contrato de fechamentos futuros, as guardas contra inferência/trials legados, o teste de persistência diante de falha de exportação, a fixture OHLC válida e a correção da asserção de fechamento da store. Nenhum charter, custo ou diário histórico foi redefinido.

Os arquivos api_guard_budget.db-shm e api_guard_budget.db-wal saíram da cópia de publicação. O banco principal continua excluído. A regra agora é verificada pelo recuperador e por testes que também cobrem conflitos entre arquivos, caminhos Windows ambíguos, traversal, hashes incorretos e arquivos existentes do dono. O CI verifica o conteúdo real de todos os ZIPs, além das regressões sintéticas.

O suplemento inclui a validação final e pós-merge do #111 e um backup consistente do diagnóstico final. Os materiais anteriores permanecem datados; o suplemento usa destinos separados para não sobrescrever o passado. As dependências de dados, tempo e condições reais de execução estão em [DEPENDENCIAS.md](DEPENDENCIAS.md).

Validação do commit desta atualização: consulte os quatro jobs em [PR #110](https://github.com/leonardosovienski/cripto-predictor/pull/110) e o workflow do main resultante. O manifesto e PUBLICATION_VALIDATION.json registram a verificação local anterior à publicação; aprovação do #111 não é usada como aprovação automática desta atualização.
