# Exportação ResearchBundleV1

> **Continuidade:** [CONTINUAR_AQUI.md](../CONTINUAR_AQUI.md). O código do exportador está integrado à fonte publicada; os relatos de “candidato local”, “sem push” e de E2Es de 12/09 abaixo são históricos. Publicação da fonte não comprova instalação no ambiente operacional.
>
> **Interpretação das fontes:** leia a [errata de evidências](ERRATA_AUDITORIA_20260915.md), inclusive a distinção H6 n observado=84 versus poder tabelado para n de referência=60. O Bundle preserva os textos e estados admitidos; não aplica nem inclui automaticamente essa errata.

## Uso e configuração conferidos em 17/09/2026

O pacote independente é `crypto-research-export` `1.0.1`, Python `>=3.11`, com Snapshot `>=1.0.1,<2` e extra `bundle` exigindo `predictor-research-bundle==1.0.0`. Consulte o [manifesto](../packages/research-export/pyproject.toml) e o [guia de instalação](../packages/research-export/README.md). Use ambiente auxiliar separado do runtime científico e do receptor CAIN.

O caminho Bundle é aditivo ao Snapshot. A [integração instalada](FINAL_INTEGRATION_AUDIT.md) identifica fontes, contratos e a diferença entre produtor e leitor legado. A aprovação de uma execução pertence ao SHA, aos bytes instalados e ao escopo dos testes registrados; não renova atestados científicos nem prova que o CAIN principal esteja implantado.

Entrada documentada:

```text
python -m crypto_research_export.bundle --root ROOT --expected-sha CHARTER_SHA --trials-sha TRIALS_SHA --destination DESTINO_NOVO --exported-at ISO_OFFSET
```

`--trials-sha` é opcional. O charter é `charters/scientific_state.json`; o registro opcional é `GarimpoInvestimentos/trials.json`. Somente trials explicitamente mapeadas no charter são selecionadas. Os dois atestados `pipeline-power/2` podem ser admitidos com `--attestation-sha PATH=SHA256`. Não invente hashes, revisão ou horários para executar o exemplo.

As fontes têm allowlist fixa, hashes explícitos, limite de 100 KB e precisam estar commitadas. O destino é novo, fora do checkout e dentro da raiz autorizada do produtor. Manifest é escrito por último, sem sobrescrita. O horário de exportação não preenche clocks científicos ausentes. `exporter_revision` é o hash do manifesto `exporter-provenance/1`, com bytes e versões do exportador e dos contratos; o receptor exige aprovação administrativa do hash exato.

O status de hipótese vem literalmente do charter; trial sem status explícito permanece `UNKNOWN`. Parâmetros, Sharpe e notes são preservados sem recálculo. Charter é preservado byte a byte; cada trial selecionada é uma representação JSON canônica ligada à fonte e ao seletor `name`, não os bytes do arquivo original inteiro. Atestados conservam `passed_at` e `expires_at`; transportá-los não certifica validade corrente nem os associa a trials por inferência.

Feature store, mercados, caches, segredos, campanhas completas e inputs exatos permanecem fora desse recorte. Não altere as quatro fontes admitidas, suas autorizações ou hashes para acomodar uma correção documental. Rollback desativa a ferramenta opcional e preserva publicações anteriores.

## Registro histórico da implementação e remediação de 12/09

Os caminhos, contagens e estados deste registro pertencem àquela execução, não ao HEAD ou à instalação atual. O [texto integral anterior](https://github.com/leonardosovienski/cripto-predictor/blob/e5997104f9c72f31764acdbdd4d26ec176791b68/docs/RESEARCH_BUNDLE_V1.md) permanece recuperável no Git.

A remediação local usou perfil `local-research/2`, com recibos em `C:/CRIPTO/operacao/relatorios/bundle-remediation-20260912-real`. Os E2Es anteriores ficaram em `C:/CRIPTO/bundle-v1-enriched-e2e`; wheels e recibos em `C:/CRIPTO/operacao/relatorios/bundle-wheels-final` e `bundle-tests.log`.

O registro reportou 11 testes específicos com fixtures fictícias e fontes commitadas, cobrindo determinismo, UNKNOWN/null, leitura sem alteração, fontes inesperadas/ausentes/alteradas, hashes incorretos, destino existente/checkout, entrada malformada e credencial fictícia. Na retomada, 11 testes do exportador instalado passaram; o bundle em `C:/CRIPTO/bundle-v1-completion-e2e` tinha 20 entidades e 12 objetos, incluindo os dois atestados, com as quatro fontes byte a byte inalteradas. Não somar rodadas sobrepostas como casos independentes.

A declaração “sem publicação ou instalação operacional” descrevia aquela remediação local. A consolidação posterior da fonte está documentada na continuidade e na integração; isso não converte os E2Es em validação científica ou econômica. Esta atualização não executa modelo, hipótese, trial, holdout, ledger ou banco científico.
