import json
import re
from pathlib import Path

root = Path(__file__).parent / 'cripto-v1.2'

def edit(name, fn):
    p = root / name
    p.write_text(fn(p.read_text(encoding='utf8')), encoding='utf8')

p = root / 'charters/scientific_state.json'
d = json.loads(p.read_text(encoding='utf8'))
d['hypotheses']['H6'] = 'CLOSED_INSUFFICIENT_SAMPLE'
d['hypotheses']['H9'] = 'CLOSED_INSUFFICIENT_SAMPLE'
d['notes'] += (' Errata CRIPTO v1.2, 2026-09-07: H6 e H9 permanecem encerradas, agora '
    'CLOSED_INSUFFICIENT_SAMPLE. H6: INCONCLUSIVE_DUE_TO_POWER (n=84, IC cruza zero, '
    'poder 23% para rho=0.2); H9: INCONCLUSIVE (44/45 folds insuficientes). '
    'A decisão de não promoção de 2026-09-04 é mantida; sua leitura como refutação '
    'científica é retirada. Ver docs/HYPOTHESES.md, errata 2026-09-07. '
    'Isto não reativa hipóteses nem altera coleta, ledger, selos ou frozen_families.')
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

edit('tests/test_scientific_state_charter.py', lambda s: s.replace('state.hypotheses["H6"] == "CLOSED_NO_GO"', 'state.hypotheses["H6"] == "CLOSED_INSUFFICIENT_SAMPLE"').replace('state.hypotheses["H6"] is HypothesisStatus.CLOSED_NO_GO', 'state.hypotheses["H6"] is HypothesisStatus.CLOSED_INSUFFICIENT_SAMPLE'))
edit('README.md', lambda s: '\n'.join(line.replace('**CLOSED_NO_GO**', '**CLOSED_INSUFFICIENT_SAMPLE**') if line.startswith(('| H6 |', '| H9 |')) else line for line in s.split('\n')))

def registry(s):
    s = s.replace('custos reais via CostModel calibrado', 'custos assumidos via CostModel testado')
    s = s.replace('- **Q:** alta (pré-registrado, custos assumidos', '- **Q:** média (pré-registrado, custos assumidos')
    s = s.replace('- **state:** REFUTED (por decisão de escopo do dono, ver docs/HYPOTHESES.md —\n  não há trial numerada dedicada em trials.json com o mesmo rigor de H1-H5)', '- **state:** CLOSED_BY_SCOPE / INCONCLUSIVE — decisão de escopo não é refutação\n  científica; não há trial dedicada com evidência equivalente a H1-H5.')
    a = s.index('## CLAIM-CR-COSTS')
    b = s.index('\n---', a)
    s = s[:a] + '''## CLAIM-CR-COSTS
**Descrição:** O modelo de custos assumido reduz o resultado simulado; a fricção
executável em conta real ainda não foi medida.

- **state:** SUPPORTED_UNDER_ASSUMED_COST_MODEL
- **L:** forte para a identidade contábil; fraco para atribuir a perda real a fees.
- **Q:** baixa para calibração econômica; testes validam aritmética, não execução.
- **classification:** ASSUMED / UNCALIBRATED (fee 10bps e slippage 5bps por perna).
- **evidence:** H1 bruto +0,44bps/sinal, líquido −0,09bps sob o modelo congelado.
  Funding usa a taxa vigente na abertura repetida pelo horizonte; não equivale a
  pagamentos realizados. Sensibilidade e proveniência: `HYPOTHESES.md`, P0-B
  de 2026-09-07. O FAQ público ilustra 2bps maker e 5bps taker; sua própria
  ressalva diz que são taxas hipotéticas. Fee efetiva da conta: UNKNOWN.
- **limitations:** posição média absoluta e decomposição de funding de H1-H3 não
  foram preservadas em um artefato identificado; o agregado não permite calcular
  PSR/MaxDD sob nova fee. Spot segue `UncalibratedCostModel`.
- **new_evidence?:** correção de proveniência, sem reexecução científica.
- **decision:** retirados Q alta e MEASURED/CALIBRATED; valores em `v3/costs.py`
  preservados integralmente. H1-H3 e a família permanecem fechadas.
- **reopen_conditions:** mudar parâmetros exige proposta pré-registrada,
  dossiê e evidência independente; a proposta P0-B não autoriza a execução.
''' + s[b:]
    s = s.replace('`charters/scientific_state.json` continua `COLLECTION_ONLY_IMMATURE`\n  — não alterado, ver decision abaixo.', '`charters/scientific_state.json` era `CLOSED_NO_GO` na base auditada;\n  a afirmação anterior de que continuava COLLECTION_ONLY_IMMATURE era falsa.\n  Errata 2026-09-07: `CLOSED_INSUFFICIENT_SAMPLE`, sem reativação.')
    a = s.index('- **decision:** `CR_PASSIVE_COLLECTION = ENABLED`', s.index('## CLAIM-CR-H6'))
    b = s.index('\n---', a)
    s = s[:a] + '''- **decision:** manter a não promoção operacional registrada em 2026-09-04,
  corrigindo sua causa para `CLOSED_INSUFFICIENT_SAMPLE` / UNDERPOWERED. O
  fechamento existe em `HYPOTHESES.md` e na reconciliação de 2026-09-05; não há
  ali justificativa de poder que permita chamar o IC cruzando zero de refutação.
  A coleta Binance é um plano independente e continua intocada. A disponibilidade
  desse feed não significa que H6 esteja aberta para maturação automática.
- **reopen_conditions:** H6 está encerrada; a afirmação anterior de “N/A, não é
  hipótese fechada” foi retirada. Qualquer nova inferência exige novidade material,
  poder dimensionado, protocolo e evidência independente. Nenhuma reabertura aqui.
''' + s[b:]
    s = s.replace('H5 é o resultado forte (negativo,\n  bem-poderizado)', 'H5 tem evidência negativa na direção testada;\n  n=440, isoladamente, não demonstra poder para todos os efeitos/regimes')
    s = s.replace('n=440, DSR 0.00 vs corte 0.95, acurácia direcional', 'n=440, DSR histórico 0.00 (recalibração exata pendente dos retornos\n  originais; errata P0-A 2026-09-07), acurácia direcional')
    return s
edit('docs/EVIDENCE_REGISTRY.md', registry)

edit('docs/case_studies/CASE-CR-003-multiplas-hipoteses-sem-falso-vencedor.md', lambda s: s.replace('Sete hipóteses', 'Nove hipóteses').replace('sete hipóteses registradas (H1–H7)', 'nove hipóteses registradas (H1–H9)').replace('| H6 | h6-sinal-invertido-d7 | COLLECTION_ONLY_IMMATURE |', '| H6 | h6-sinal-invertido-d7 | CLOSED_INSUFFICIENT_SAMPLE — UNDERPOWERED |').replace('| H7 | (não registrada em trials.json) | REGISTERED_NOT_ACTIVATED |', '| H7 | h7-macro-dxy-hmm-v1 | REGISTERED_NOT_ACTIVATED |\n| H8 | h8-llm-hypothesis-generator | REGISTERED_NOT_ACTIVATED |\n| H9 | h9-oi-volume-ratio-hmm-v1 | CLOSED_INSUFFICIENT_SAMPLE — 1/45 folds avaliável |'))
edit('CR_RESEARCH_FREEZE.md', lambda s: s.replace('core_version_pinned: predictor-core==3.0.0', 'core_version_pinned: predictor-core==3.2.0').replace('passive_observations:\n  - id: H6', 'closed_observations:\n  - id: H6', 1).replace('status: COLLECTION_ONLY_IMMATURE (charters/scientific_state.json — NÃO alterado; ver nota)', 'status: CLOSED_INSUFFICIENT_SAMPLE (errata 2026-09-07; INCONCLUSIVE_DUE_TO_POWER)').replace('    evidence_update_2026-09-03: >', '    errata_2026-09-07: "O texto de 03/09 abaixo é histórico. O charter fechou H6 em 04/09; a causa agora é amostra insuficiente. Não há reabertura nem mudança da coleta."\n    evidence_update_2026-09-03: >', 1).replace('  - id: H6_binance_collection', '\npassive_observations:\n  - id: H6_binance_collection', 1))
edit('CR_FREEZE_INDEX.md', lambda s: s.replace('observações passivas (H6, H6_binance_collection, H7), hipóteses encerradas (H1-H5 + ancestral)', 'observação passiva Binance; H7/H8 registradas sem ativação; hipóteses encerradas (H1-H6, H9 + ancestral)').replace('Atestado real, `core_version: 3.0.0`, reemitido nesta rodada (não editado manualmente)', 'Atestado histórico Core 3.0.0; migração/reemissão Core 3.2.0: errata P0-A em HYPOTHESES.md'))

errata = '''
> **Errata CRIPTO v1.2 — 2026-09-07:** H6 não é refutação estatística:
> IC95 cruza zero e o poder em n=84 é 23% para rho=0,2. O estado corrente é
> CLOSED_INSUFFICIENT_SAMPLE; H9 recebe a mesma classe (só 1/45 folds avaliável).
> Ambos continuam encerrados. Referências históricas a CLOSED_NO_GO ou coleta
> H6 aberta ficam superadas por `charters/scientific_state.json` e pela errata
> de `docs/HYPOTHESES.md`. Não houve mudança de coleta, parâmetros ou selos.
'''
for name in ['docs/OVERVIEW_E_ROADMAP_2026-08-21.md', 'docs/H6_REFREEZE_2026-08-27.md']:
    edit(name, lambda s: s.split('\n', 1)[0] + '\n' + errata + '\n' + s.split('\n', 1)[1])

edit('docs/HYPOTHESES.md', lambda s: s.replace('### H6 — Sinal invertido do LLM prevê retorno D+7 (status: **REFUTADA / NO-GO — 2026-09-04**)', '### H6 — Sinal invertido do LLM prevê retorno D+7 (status: **CLOSED_INSUFFICIENT_SAMPLE — errata 2026-09-07**)' + '\n' + errata).replace('### H9 — Razão OI/Volume (crowding especulativo) como covariável exógena do regime (status: **REFUTADA / NO-GO — 2026-09-04**)', '### H9 — Razão OI/Volume (crowding especulativo) como covariável exógena do regime (status: **CLOSED_INSUFFICIENT_SAMPLE — errata 2026-09-07**)\n\n> Um fold avaliável não isola a covariável nem demonstra ausência de efeito.\n> Histórico abaixo preservado; fechamento mantido sem refutação causal.').replace('- Resultado: **REFUTADA — IC cruza zero em n=84**', '- Resultado histórico, superado pela errata 2026-09-07: **REFUTADA — IC cruza zero em n=84**'))

edit('docs/case_studies/CASE-CR-001-custos-comem-sinal.md', lambda s: s.split('\n', 1)[0] + '\n\n> **Errata 2026-09-07:** custos ASSUMED/UNCALIBRATED; teste aritmético não mede\n> fees, slippage ou fills reais. H1 perdeu sob esse cenário, mas a atribuição\n> exclusiva a custos reais não está demonstrada. Ver CLAIM-CR-COSTS e P0-B.\n\n' + s.split('\n', 1)[1])

edit('HANDOFF.md', lambda s: s.split('\n', 1)[0] + '\n\n> **Delta CRIPTO v1.2 — 2026-09-07:** Core 3.2.0 preparado em worktree isolado;\n> seis pins consistentes, DSR estrito e N incluindo Sharpes ausentes. H6/H9\n> encerradas por insuficiência de amostra; custos assumidos reclassificados.\n> Rodada, validação e limitações: `docs/HYPOTHESES.md`, errata 2026-09-07.\n> Produção permanece intacta; as notas de 06/09 abaixo são históricas.\n\n' + s.split('\n', 1)[1])
