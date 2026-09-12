# Exportação ResearchBundleV1 — candidato local

Estado corrente 12/09/2026: remediação local, perfil `local-research/2`.
Origem e restrições são definidas por este produtor. `exporter_revision` é o hash
do manifesto `exporter-provenance/1`, recuperável na coleção evidence, que inclui
os bytes efetivos do exportador e dos contratos compartilhados e suas versões.
O receptor exige aprovação administrativa do hash exato antes de importar.
Recibos/E2Es abaixo são históricos; evidência nova fica em
`C:/CRIPTO/operacao/relatorios/bundle-remediation-20260912-real`.
Sem publicação ou instalação operacional nesta remediação. Snapshot e fontes preservados.

Este incremento é aditivo ao exportador ResearchSnapshotV1, que permanece intacto.
O produtor usa somente o pacote independente predictor-research-bundle 1.0.0 do Ecosystem;
não importa CAIN nem executa o runtime científico. Instale o wheel compartilhado em ambiente
auxiliar separado. Não instale o runtime de produção para usar estas ferramentas.

Fontes têm allowlist fixa, SHA256 explícito, limite de 100 KB e precisam estar commitadas.
O exportador verifica novamente os hashes antes de criar saída. O destino é novo, fora do
checkout e dentro da raiz do produtor. Manifest é escrito por último; não há sobrescrita.
O horário --exported-at é explícito para permitir repetição determinística e nunca preenche
os clocks científicos ausentes. Cada entity tem status, eixo, payload, clocks e proveniência.

Entrada: `python -m crypto_research_export.bundle --root ROOT --expected-sha CHARTER_SHA --trials-sha TRIALS_SHA --destination DESTINO_NOVO --exported-at ISO_OFFSET`.
--trials-sha é opcional. O charter admitido é charters/scientific_state.json. O registro
opcional é GarimpoInvestimentos/trials.json; somente entradas com nomes explicitamente
mapeados no charter são selecionadas. O status de hipótese vem literalmente do charter;
trial sem status explícito permanece UNKNOWN. Payload preserva params/sharpe/notes e outros
campos existentes, sem recalcular resultados. registered_at conhecido vira recorded_at.
Charter é preservado byte a byte; cada trial selecionada é um objeto JSON canônico, identificado
como representação serializada e ligado ao hash da fonte e ao seletor name. Não confundir
esta representação com os bytes do arquivo original completo. Ausência de entrada vira referência.
Não são exportados feature store, mercados, caches, segredos ou campanhas completas.
Dados de entrada exatos continuam fora do recorte. Os dois atestados pipeline-power/2
podem ser admitidos explicitamente com --attestation-sha PATH=SHA256. São recibos de
controle plantado, com passed_at/expires_at e veredictos literais preservados; não
certificam validade atual nem são associados a trials por inferência. Instalação opcional:
`crypto-research-export[bundle]`, resolvendo o wheel compartilhado localmente.

E2E local ampliado: C:/CRIPTO/bundle-v1-enriched-e2e. Wheels/recibos em
C:/CRIPTO/operacao/relatorios/bundle-wheels-final e bundle-tests.log.

Validação: 11 testes específicos com fixtures fictícias e fontes commitadas: determinismo,
UNKNOWN/null, leitura sem alteração, fonte inesperada/ausente/alterada, hash incorreto,
destino existente/checkout, entrada malformada e credencial fictícia. Wheels e E2E foram
exercitados separadamente; isso não é validação científica ou econômica.

Nenhum push, release, instalação operacional, modelo, hipótese, trial, holdout, ledger ou
banco científico foi executado/alterado. Rollback desativa esta ferramenta opcional e mantém
as publicações/bundles existentes. Não apagar evidências para retornar ao caminho SnapshotV1.

Na retomada, 11 testes do exportador instalado passaram. O bundle real em
C:/CRIPTO/bundle-v1-completion-e2e contém 20 entidades e 12 objetos, incluindo
os dois atestados. As quatro fontes pinadas ficaram byte a byte inalteradas.
