import hashlib
import json
import re
import subprocess
from pathlib import Path

work = Path(__file__).parent
root = work / 'cripto-v1.2'
out = work.parent / 'outputs'
out.mkdir(exist_ok=True)
base = subprocess.check_output(['git', 'rev-parse', '3c104ce'], cwd=root, text=True).strip()
v3 = json.loads((root / 'GarimpoInvestimentos/trials.harness_attestation.json').read_text(encoding='utf8'))
p1 = json.loads((root / 'GarimpoInvestimentos/trials.phase1_harness_attestation.json').read_text(encoding='utf8'))
p = root / 'CR_RESEARCH_FREEZE.md'
s = p.read_text(encoding='utf8')
for name, rec in [('v3_judge', v3), ('phase1_judge', p1)]:
    start = s.index('  ' + name + ':')
    end = s.find('\n  ', start + len(name) + 4)
    # Update exact historical triples once, without rewriting other dated history.
    old = ('    core_version: "3.0.0"\n'
           + ('    passed_at: "2026-09-03T00:45:53Z"\n    expires_at: "2026-09-10T00:45:53Z"' if name == 'v3_judge'
              else '    passed_at: "2026-09-03T00:45:43Z"\n    expires_at: "2026-09-10T00:45:43Z"'))
    new = f'    core_version: "3.2.0"\n    passed_at: "{rec["passed_at"]}"\n    expires_at: "{rec["expires_at"]}"'
    assert old in s
    s = s.replace(old, new, 1)
s = s.replace('  test_suite: "853 passed, 0 failed (uv run pytest tests/, all-extras, 2026-09-03)"', '  test_suite: "983 passed, 0 failed (pytest all-extras, Core 3.2.0, 2026-09-07)"')
s = s.replace('harness_attestation:\n', f'harness_attestation:\n  # Reemissão real 2026-09-07, árvore limpa: {v3["code_version"]}\n', 1)
p.write_text(s, encoding='utf8')
p = root / 'CR_FREEZE_INDEX.md'
s = p.read_text(encoding='utf8').replace('Atestado histórico Core 3.0.0; migração/reemissão Core 3.2.0: errata P0-A em HYPOTHESES.md', 'Atestado real Core 3.2.0, reemitido 2026-09-07 em árvore limpa; errata P0-A em HYPOTHESES.md')
p.write_text(s, encoding='utf8')
p = root / 'docs/HYPOTHESES.md'
s = p.read_text(encoding='utf8') + f'''

### Validação da entrega — 2026-09-07

983 testes passaram (all-extras, Python 3.13.14, Core 3.2.0). Ruff check e
format, Pyright, scan de segredos (0 achados), build wheel/sdist e instalação
da wheel em ambiente novo fora do checkout: PASS. Snapshot H6 confere; costs,
trials, h6_status e selos permanecem byte-idênticos à base. Docker e CI remoto
não foram executados. A primeira execução de testes teve 979 passes e uma
falha do path de isolamento escolhido dentro do checkout; mudado apenas o
DATA_DIR de teste para pasta externa, a suíte final passou sem essa falha.

Atestados realmente reemitidos: Fase 1 {p1['passed_at']}, V3 {v3['passed_at']},
Core 3.2.0, ambos contra `{v3['code_version']}`. Expiração: 2026-09-14;
nenhuma validade permanente inferida. Os arquivos novos não foram instalados
na produção. Antes de qualquer implantação, é necessária revisão concreta
do diff científico e uma decisão de deployment que preserve a coleta.

Limites que continuam abertos: tarifa atual por tier/conta e fills não
medidos; benchmark do operador e FX não confirmados; séries originais dos
DSRs e posições de H1-H3 não identificadas. Resultado honesto nesses campos
é UNKNOWN, com as condições de desbloqueio descritas acima.
'''
p.write_text(s, encoding='utf8')

protected = ['GarimpoInvestimentos/v3/costs.py', 'GarimpoInvestimentos/trials.json',
             'charters/h6_definition_frozen.json', 'GarimpoInvestimentos/h6_status.json']
manifest = {
    'base_commit': base, 'code_commit': v3['code_version'],
    'branch': 'codex/cripto-v1-2-execution-20260907',
    'tests': {'passed': 983, 'failed': 0, 'python': '3.13.14', 'core': '3.2.0'},
    'input_sha256': hashlib.sha256(Path('C:/Users/Superleo13/Downloads/CRIPTO_V1.2.md').read_bytes()).hexdigest(),
    'protected_artifacts': {},
}
for name in protected:
    before = subprocess.check_output(['git', 'show', f'{base}:{name}'], cwd=root)
    now = (root / name).read_bytes()
    # Git checkout line endings can differ; compare content normalized to LF.
    assert before.replace(b'\r\n', b'\n') == now.replace(b'\r\n', b'\n'), name
    manifest['protected_artifacts'][name] = {'git_content_unchanged': True, 'sha256_on_disk': hashlib.sha256(now).hexdigest()}
(out / 'validacao.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
report = f'''# Execução CRIPTO v1.2 — 7 de setembro de 2026

As correções foram implementadas na branch local
`codex/cripto-v1-2-execution-20260907`, baseada em `{base[:7]}`.
Repositório de trabalho: `{root}`.
Produção, coleta, capital, parâmetros de custos e ledger congelado foram preservados.

| Prioridade | Entrega | Limite restante |
|---|---|---|
| P0-D | H6 reconciliada como encerrada por amostra insuficiente; corrigidos charter, registry, case e erratas | Não reaberta; IC cruzando zero não é refutação |
| P0-B | Claims de custos rebaixados para ASSUMED/UNCALIBRATED; sensibilidade algébrica H1-H3; proposta de pré-registro | Fee real, fills e posições originais desconhecidos; não inventado novo PSR |
| P0-A | Core 3.2.0 nos seis pins, DSR estrito, contagem de todas as tentativas, bloqueio de unidades incompatíveis, cinco caminhos de atestado corrigidos | DSR histórico exato não é reconstruível sem séries e ledger originais |
| P0-C | Reclassificação causal H1-H9 aplicada; H9 encerrada por amostra insuficiente | Só 1/45 folds avaliável não identifica o efeito de OI/volume |
| Economia | Fontes públicas, benchmark candidato em BRL, exposição cambial, cenários e dossiê de carry | Hurdle efetivo UNKNOWN; carry bloqueado em G1 por falta de estrutura de execução |

**Validação:** 983 testes passaram; Ruff, formatação, Pyright, build e instalação
da wheel fora do checkout passaram; scan de segredos com zero achados.
Dois atestados reais emitidos em árvore limpa, válidos até 14/09/2026.
Docker/CI remoto não executados; nenhum merge, push ou deployment realizado.

O achado adicional mais relevante foi a mistura de Sharpes por operação com
`mean/std × sqrt(n)` no ledger. A nova implementação recusa esse DSR até que
a base de comparação seja comprovada, preservando os resultados históricos.

US$5.000 equivalem contabilmente a R$25.626,50 na [PTAX de 04/09](https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do).
O cenário de benchmark, condicionado à elegibilidade no [Tesouro Reserva](https://www.tesourodireto.com.br/tesouro-reserva),
taxa constante, tributação PF e demais premissas explicitadas, gera cerca de
R$2.900–R$2.907/ano. Isso não é o retorno contratado nem o hurdle final do operador.
Na estrutura ilustrativa com metade do capital gerando carry, corresponde a
22,64%–22,69% sobre o nocional, antes de prêmio de risco, FX e atenção.

O [FAQ Binance](https://www.binance.com/en/support/faq/detail/360033544231) ilustra
2bps maker e 5bps taker, mas não comprova a tarifa atual de uma conta. Essa
diferença de proveniência impede chamar a análise de calibração real.

Para revisar a implementação, use o patch entregue, relativo à base `{base[:7]}`.
O relatório detalhado está no patch em `docs/HYPOTHESES.md`, seção
“Errata e decisões CRIPTO v1.2 — 2026-09-07”. Evidências de fontes e inventário
de 48 menções numéricas DSR/SR0 ficam em `docs/evidence/`. A branch local já
contém os arquivos, testes e atestados; a aplicação em produção não foi feita.

Pendências concretas: dados da tarifa/execução, benchmark acessível e rota FX
do operador, prêmio de risco/custo de atenção e inputs históricos dos DSRs.
Não há estratégia liberada para capital real.
'''
(out / 'EXECUCAO_CRIPTO_V1.2.md').write_text(report, encoding='utf8')
print('Report and validation manifest generated.')
