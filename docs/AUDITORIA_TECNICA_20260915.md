# Auditoria e correcoes locais — 15/09/2026

Base do codigo: `4eb96e141389b8390536716af3c4a0cb46edab23`.
Publicacao autorizada pelo dono; nenhum arquivo local deve ser apagado.

## Correcoes

- Saude do feature store compara instantes UTC em vez de MAX textual e recusa timestamps invalidos.
- Testes de subprocessos separam redaction de timeout e sincronizam a disputa de lock.
- Tipos explicitos e verificacoes de None nos fatores, propostas, snapshots, jobs, HMM e verificadores.
- Validacao da estrutura de coverage do exportador; configuracao Pyright cobre todo runtime e scripts.

## Evidencias executadas

- Suite completa apos as correcoes: 1542 aprovados, zero falhas, um skip, 322,31 s.
- Teste de symlink: usuario apresentou execucao separada como administrador, PASSED, 1,71 s. Nao integra o XML da suite acima.
- Exportador: 23 aprovados, zero falhas, 14,37 s.
- Pyright ampliado: 232 arquivos, zero erros/avisos; inclui exportador com Bundle em QA e exclui copia gerada pelo build.
- Ruff aprovado, 513 arquivos formatados; integridade local de 3783 arquivos de dependencias aprovada.
- Builds offline; 160 arquivos Python do wheel principal e dois do exportador conferidos com instalacao QA e fontes.
- Exportacao local: quatro fontes, 20 entidades, 29 relacoes, contrato valido.

Recibos completos locais: `C:/Cripto/operacao/relatorios/AUDITORIA_COMPLETA_20260915/fechamento`.
O relatorio anterior e suas tentativas permanecem preservados; seus 52 diagnosticos abertos foram tratados nesta continuacao, incluindo imports opcionais e duplicatas de build. A dependencia correta revelou tres diagnosticos adicionais de coverage, tambem corrigidos.

## Limites

Os replays historicos ja executados de carry/basis, AR, altcoins, Aave e renovacao confirmam resultados sob suas convencoes, sem constituir validacao prospectiva.
Originais historicos ausentes impedem algumas reproducoes. CAIN principal nao foi certificado; o endpoint local nao respondeu nesta verificacao.
Dados operacionais antigos continuam STALE. Nao houve coleta, nova previsao, ordem, alteracao de protocolos ou autorizacao de capital.

Os hashes de charter, trials, H6 e HYPOTHESES permanecem iguais aos da auditoria inicial. Publicar codigo nao publica bancos, credenciais, ambientes ou todos os recibos privados, e nao atualiza a instalacao principal.
