> **Ponto de entrada atual:** [publicação, resultado e ordem de leitura](../PUBLICATION_STATUS_20260912.md). A auditoria foi concluída para `9db8e93`; os registros anteriores abaixo mantêm seu contexto e não são instrução para repetir a consolidação.

# Auditoria de engenharia e integração — 12/09/2026

Esta linha parte de `97d60222d14ff211bfd415fff374d0751d5ac235` e preserva o
runtime 1.1.0, o exportador independente 1.0.1 e todas as fontes científicas.
A promoção e a limpeza Git dependem dos recibos do commit final; a existência
deste documento não declara esses gates aprovados.

## Divergências corrigidas na retomada

Os cinco drifts observados foram reconciliados com as versões publicadas e
atestados recuperáveis. Os controles oficiais sintéticos dos julgadores V3 e
Fase 1 passaram com Core 3.2.1, executados pela wheel instalada contra a fonte
limpa Crypto 22219e3db8130bfe81abe95b38ecfbc3cacdb5f9, com saída isolada.
Os quatro braços edge/ruído passaram. Os atestados originais do domínio não
foram modificados; nenhuma hipótese, trial ou permissão de capital foi ativada.

O Ecosystem registra a nova evidência separadamente em
docs/engineering_controls/20260912, verifica seu SHA256 e seus campos, e preserva
os bytes JSON no Git. Os modos offline, remoto e com clones do checker passaram;
76 testes locais do Ecosystem passaram. As atualizações concorrentes já publicadas
na main Ecosystem foram preservadas na combinação.

ALIGNED descreve esses controles sintéticos, não validação econômica ou promoção
dos atestados históricos. O bloqueio anterior e seus recibos são históricos.
A promoção e a limpeza dependem da CI e dos recibos finais desta combinação.

## Combinação reproduzível

- CAIN: `5ba4177a11b9312900e5035517aa5ef25d509859`, versão 0.4.7.
- Ecosystem: `6a998520825292895bcae71e589fa8ac0e02bb85`, versão 0.2.0,
  com Snapshot 1.0.1 e Bundle 1.0.0 construídos de fonte versionada.
- O produtor usa Snapshot 1.0.1. O receptor preserva o leitor Snapshot 1.0.0
  requerido pelo CAIN. O manifesto em `vendor/provenance.json` desse commit
  identifica sua fonte recuperável no Ecosystem.
- Core 3.2.1 e Ops 4.2.0 conservam as URLs e hashes de `uv.lock`.

O workflow `Installed Crypto CAIN integration` registra os SHAs e trees dos três
clones novos, versões, wheels, hashes, comandos, horários, resultados e logs.
O SHA Crypto é o SHA que dispara a execução, incluindo a identidade do merge de
teste quando o evento é um PR. As outras fontes são pinadas no script.

```text
python .ci/integration-audit/validate.py --crypto-sha SHA_EXATO --work DESTINO_NOVO
```

Use o Python do perfil desejado e uv 0.12.1. A CI executa Linux em 3.11–3.14
para contratos, exportador, CAIN e os E2Es. O runtime Crypto e os plugins rodam
em 3.13/3.14, conforme o suporte declarado dos pacotes. A CI original continua
responsável também pelo container restrito, SBOM e Trivy. Nada é marcado como
opcional em razão de falha ou falta de ferramenta local.

## Correções e verificações

A construção do `Builder` no exportador Bundle foi formatada para cumprir o
gate Ruff vigente. Os testes do exportador passaram a usar o temporário do
ambiente, eliminando o caminho Windows fixo. O fingerprint do exportador deve
ser recalculado dos bytes efetivamente instalados; versões nominais iguais não
implicam fingerprints iguais.

No Ecosystem, o checker passou a aceitar um manifesto explícito de wheels
candidatas com hashes obrigatórios, sem substituir o registro de releases.
Um hash incorreto ou a ausência da proveniência do instalador continuam sendo
recusados antes da descoberta dos plugins. A extensão tem regressões próprias.

O E2E usa as quatro fontes Crypto admitidas, com SHA256 e relógio explícitos.
Compara os estados recuperados ao charter, verifica evidence e relações,
aprovação administrativa, importação idempotente, isolamento de escopos,
Snapshot legado, backup/restore/rebuild, materialização offline e revogação.
Produtor e receptor usam ambientes separados e não instalam o runtime científico
para transportar ou consultar relatórios. As políticas são descartáveis.
Durante a recuperação, um audit hook Python recusa aberturas sob a origem e
ambos os caminhos de transporte. Uma tentativa discriminante confirma a recusa;
verify/rebuild/materialização não tentam esses acessos. Essa observação não é
uma prova de isolamento de kernel.

O E2E funcional do runtime usa a demonstração sintética oficial e verifica a
persistência do RunStore. Isso não executa campanha científica, coleta de mercado,
modelo externo, agendamento, ordens reais ou capital. A disponibilidade atual de
provedores externos não é comprovada por esses testes offline.

## Preservação e interpretação dos resultados

O inventário inicial local abrangeu 27 checkouts dos três projetos em raízes
conhecidas. Cinco repositórios Git recuperáveis tiveram bundles verificados,
comparação de refs e ensaio de restauração independente. Um clone interrompido
sem HEAD/refs tinha um pack incompleto, preservado separadamente. Foram copiadas
e verificadas 34 alterações/arquivos de trabalho, incluindo versões em conflito;
índice e estágios do conflito foram conferidos no repositório restaurado.

Recibos privados completos desta execução ficam em
`C:\Cripto\operacao\relatorios\auditoria-main-20260912-01`. O escopo e as
exclusões da descoberta estão no inventário; não foi feita busca indiscriminada
em dados pessoais. Os backups não são publicados automaticamente.

As falhas de preparação também permanecem registradas: a rodada preliminar
interrompida não é PASS; a suíte procurava os artefatos em `dist/` e foi corrigida
a localização, sem alterar testes; uma pasta de testes Snapshot inexistente era
erro do roteiro, enquanto o caminho legado é coberto pelo exportador e E2E.
Contagens de rodadas sobrepostas não representam testes independentes.

Os resultados finais e a autorização individual de cada exclusão pertencem ao
relatório externo e à CI do SHA efetivo. Não eliminar branches por este documento
isoladamente. Consolidar Git não atualiza uma instalação operacional nem altera
estados científicos, econômicos ou permissões de capital.
