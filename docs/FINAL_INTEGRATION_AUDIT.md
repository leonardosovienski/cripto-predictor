# Auditoria de engenharia e integração — 12/09/2026

Esta linha parte de `97d60222d14ff211bfd415fff374d0751d5ac235` e preserva o
runtime 1.1.0, o exportador independente 1.0.1 e todas as fontes científicas.
A promoção e a limpeza Git dependem dos recibos do commit final; a existência
deste documento não declara esses gates aprovados.

## Bloqueio obrigatório encontrado na conferência ao vivo

O checker Ecosystem em `821c7d7411ee983ef2c7ac03fa11083944826321`
passa suas invariantes offline, mas a leitura ao vivo e o modo `--from-clones`
detectaram cinco divergências em 12/09/2026: Core anunciado 3.2.0 versus
3.2.1 publicado; Ops 4.1.0 versus 4.2.0; release Core antiga no registry de
harnesses; versão e expiração Crypto diferentes do atestado original.

Uma prova controlada em memória, sem editar registries, confirmou que trocar
apenas a versão corrente para 3.2.1 faz o gate offline recusar a ausência de
harness `ALIGNED` dessa versão. Não foi emitido atestado, alterado resultado
científico nem enfraquecido o checker. Resolver exige evidência de alinhamento
admitida pela governança, ou uma decisão explícita sobre o contrato desse gate.
As fontes consultadas não fornecem essa evidência. O PASS da CI de engenharia
não elimina o FAIL dessa conferência obrigatória.

Portanto, a candidata permanece em `integration/final-audit-20260912`;
`main` não foi promovida e nenhuma branch foi excluída. O relatório privado
`RELATORIO_FINAL.md` na área indicada abaixo contém a matriz e a retomada.

## Combinação reproduzível

- CAIN: `5ba4177a11b9312900e5035517aa5ef25d509859`, versão 0.4.7.
- Ecosystem: `821c7d7411ee983ef2c7ac03fa11083944826321`, versão 0.2.0,
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
