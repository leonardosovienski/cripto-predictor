"""Package the completed Discovery screen; user-facing outputs only."""
import gzip
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

WORK = Path(__file__).resolve().parent
REPO = WORK / 'cripto-v1.2'
DATA = WORK / 'altcoin-data'
RESULTS = WORK / 'altcoin-results'
OUT = WORK.parent / 'outputs'
CANON = REPO / 'docs/evidence/altcoin_analogs_20260907'
OUT.mkdir(exist_ok=True)
r = json.loads((RESULTS / 'results.json').read_text())
a = json.loads((RESULTS / 'audit.json').read_text())
m = json.loads((DATA / 'acquisition.json').read_text())

def pct(v, decimals=2):
    return f'{v*100:.{decimals}f}%'.replace('.', ',')

def num(v):
    return f'{v:,.0f}'.replace(',', '.')

sources = {
    'access_date': '2026-09-07',
    'documentation': [
        {'url': 'https://github.com/binance/binance-public-data', 'supports': 'Public historical archive, all-symbol files, ms/us timestamp transition and possible archive revisions.'},
        {'url': 'https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market', 'supports': 'Public daily klines with OHLC, base/quote volume and timestamps.'},
        {'url': 'https://www.binance.com/en/support/announcement/detail/aec6fcbc84b749eeab6690e6bcac2f3d', 'supports': 'FTM to S migration 1:1, old spot trading ended 2025-01-13; missing old-symbol bars do not prove total loss.'},
        {'url': 'https://www.binance.com/en/support/announcement/detail/7d5accdcf8f446f3ba3d79f8747a28e2', 'supports': 'BNX to FORM completed 1:1; trading resumed under FORM in March 2025.'}
    ],
    'raw_requests': [json.loads(p.read_text()) for p in sorted((DATA / 'raw').glob('*.json'))],
    'benchmark_reference': 'Existing same-day funding_carry_screen_20260907 protocol/results/sources. No new benchmark claim or operator fee measurement.'
}
ledger = {
    'screen_id': r['screen_id'], 'mode': 'DISCOVERY',
    'scope': 'One-shot research explicitly authorized by the user; independent of live collection and formal H1-H9 trials.',
    'protocol_commit': '444aa02', 'implementation_before_first_outcomes_commit': 'acaa925',
    'model_trials': 1, 'hyperparameter_searches': 0, 'horizons': [7],
    'assets': m['selected'], 'venue': 'Binance spot', 'bar_interval': '1d',
    'features': r['model']['features'], 'model': 'uniform kNN200 with train-only median/IQR and fixed clipping',
    'target': '7-day return >=20% and excess over BTC >=10 percentage points',
    'registered_controls': ['equal eligible basket', 'top5 momentum', 'BTC same weekly exposure', 'zero-yield USDT cash'],
    'registered_cost_scenarios_bps_per_side': [20, 50, 100],
    'after_outcome_diagnostics': ['Decimal raw/accounting reconstruction', 'zero transaction costs', 'flat missing-holding recovery', 'both zero costs and flat recovery', 'official migration source audit'],
    'adaptive_model_changes': [], 'selection_or_training_changes_after_results': [],
    'technical_changes_after_outcomes': ['audit script added, with Decimal typing only; inference implementation unchanged'],
    'first_screen_result': r['decision'], 'final_priority_decision': a['research_priority_decision'],
    'scientific_verdict': a['scientific_verdict'],
    'evidence_consumed': '2021-2023 exploration/training, 2024 and 2025-2026 historical temporal evaluation; not untouched Proof or prospective evidence.',
    'next_iteration_rule': a['future_research_condition'],
    'dsr': 'NOT_ESTIMATED: no compatible independent trial distribution; do not reuse legacy heterogeneous Sharpe values.',
    'formal_hypothesis_activation': False, 'capital_authorized': False, 'production_changed': False,
    'core_attestation': 'Not requested/issued for this separate Discovery screen. Synthetic controls below are not a predictor-core promotion/power attestation.',
}
validation = {
    'synthetic_and_temporal_tests_passed': 11,
    'freeze_gate_tests_passed': 8,
    'ruff': 'PASS on four changed Python files',
    'pyright': 'PASS using actual .venv interpreter on three new scripts',
    'raw_response_hash_checks': a['raw_response_hash_checks'],
    'raw_decimal_return_checks': a['independent_raw_decimal_return_checks'],
    'maximum_raw_return_difference': a['maximum_raw_return_difference'],
    'decimal_portfolio_checks': 6,
    'offline_reproduction_from_extracted_zip': 'PASS; results.json, weekly_portfolios.json, samples.json.gz and audit.json byte-identical to expected outputs',
    'frozen_files_unchanged_since_4cf37a8': ['charters/scientific_state.json', 'GarimpoInvestimentos/trials.json', 'GarimpoInvestimentos/v3/costs.py', 'CR_FREEZE_INDEX.md', 'CR_RESEARCH_FREEZE.md'],
    'full_legacy_suite': '983 passed in the prior infrastructure turn; not rerun for these independent research scripts.',
    'remote_ci_docker_deployment': 'NOT_RUN',
}
for name in ('results.json', 'audit.json'):
    shutil.copy2(RESULTS / name, CANON / name)
for name, obj in [('sources.json', sources), ('search_log.json', ledger), ('validation.json', validation)]:
    (CANON / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

e1, e2 = r['evaluation']['evaluation_1'], r['evaluation']['evaluation_2']
table = ['| Regra simulada | 2024, 52 semanas | 2025–2026, 87 semanas |', '|---|---:|---:|']
for key, label in [('analogs','5 moedas por padrões semelhantes'), ('equal_basket','Cesta das moedas elegíveis'), ('momentum','5 moedas por momentum'), ('btc','BTC, mesmas semanas de exposição')]:
    table.append(f"| {label} | {pct(e1['cost_scenarios']['20']['methods'][key]['compounded_return'])} | {pct(e2['cost_scenarios']['20']['methods'][key]['compounded_return'])} |")
ci = e2['cost_scenarios']['20']['paired_contrasts']['equal_basket']
report = f'''# Seleção de altcoins por padrões anteriores às altas

Executado em 07/09/2026. **Decisão: não promover esta regra para operação.**

O protótipo foi construído, testado e aplicado a dados públicos. A seleção encontrou maior frequência de altas fortes, mas o resultado da carteira foi negativo e inferior à cesta simples. Isso rejeita a especificação na triagem de pesquisa; não demonstra que toda seleção de altcoins seja impossível.

**O P&L abaixo é uma simulação com premissas de custo e recuperação, não perda realizada nem estimativa confiável de execução.** A auditoria encontrou migrações de tokens entre os dados ausentes. O veredito científico sobre P&L executável permanece `INCONCLUSIVE_DATA_FIDELITY`; a decisão de pesquisa é `DO_NOT_PROMOTE_THIS_SELECTOR`.

O treinamento usou 5.204 observações de 121 símbolos em 156 semanas de 2021–2023: 504 episódios-alvo e 4.700 controles. “Alta forte” significa pelo menos 20% em sete dias e vantagem de pelo menos 10 pontos percentuais sobre BTC. Preço, força relativa, volume e volatilidade foram calculados antes da entrada, com atraso de um dia. Os controles incluem altas menores, lateralização, quedas e casos sem saída observável.

O modelo procura os 200 vizinhos históricos mais próximos, estima a frequência do alvo nesse grupo e escolhe cinco moedas com pesos iguais. As regras, os custos e as datas foram fixados antes da coleta em lote, no commit `444aa02`; implementação e controles sintéticos ficaram registrados em `acaa925` antes do primeiro resultado. Não houve ajuste de modelo, janela ou ativos depois dos resultados.

{chr(10).join(table)}

Retornos compostos em USDT, reinvestindo o saldo semanal. Entrada na abertura de segunda e saída no fechamento de domingo, preços de referência diários. Custo assumido de 10 bps de taxa mais 10 bps de slippage em cada ponta; inclusive posições mantidas são encerradas e reabertas. Com menos de dez moedas elegíveis, todos os métodos ficam em caixa sem rendimento. Isso ocorreu em nove semanas de julho/agosto de 2026; a linha BTC também segue essa regra e **não é buy-and-hold de BTC**. A semana de 30/12/2024 foi purgada por atravessar os segmentos. A última posição avaliada entrou em 31/08/2026 e terminou em 06/09/2026.

A diferença média semanal de log-retorno contra a cesta, no segundo segmento, foi {pct(ci['mean_weekly_log_difference'])}; intervalo de 95% por bootstrap de blocos de quatro semanas: [{pct(ci['ci95_block4'][0])}; {pct(ci['ci95_block4'][1])}]. A conta agrupa as moedas por semana, respeitando dependência temporal e de mercado. É inferência condicional a esta busca exploratória, sem ajuste por todo o histórico de pesquisa do projeto. O planejamento conservador tinha poder apenas para efeitos grandes: cerca de 0,61 desvio padrão semanal no segundo segmento. Não se declara ausência de efeitos pequenos.

O achado que responde à ideia original é concreto: no segundo segmento, a seleção acertou o alvo em **7,18%** das posições (28/390), contra **5,27%** na média semanal da cesta — aumento relativo descritivo de 36%. Em 2024 foram 13,08% contra 8,82%. Essa concentração de altas não gerou vantagem econômica. No segundo segmento somente 133 de 390 posições tiveram retorno bruto positivo; o ganho médio das positivas foi 13,75%, e a perda média das demais foi 13,69%, sob o tratamento de lacunas descrito abaixo. O alvo binário não remunera a gravidade das perdas que o acompanham. Isso é uma explicação compatível com a contabilidade, não uma identificação causal definitiva.

## Conferência das perdas e dos dados

A amostra foi sorteada por hash fixo entre os símbolos do arquivo, sem ranking por retorno ou capitalização atual: 240 pares entre 735 pares USDT catalogados. Foram coletadas 251.930 velas, incluindo BTC de referência. 77 históricos terminam antes do último dia da amostra; não se afirmou que todos sejam deslistagens, pois migrações e pausas também encerram um símbolo. BCHABC e BCHSV não tinham observações dentro do intervalo, confirmado na API e no catálogo de arquivos. Não foram substituídos por vencedores.

Houve sete desfechos ausentes entre todas as moedas elegíveis na avaliação, quatro deles na carteira por analogia: CVP, FTM, BNX e VIDT. A regra pré-fixada atribui perda total a esses desfechos, como stress de recuperação. Isso não pode ser confundido com o valor econômico dos tokens. FTM migrou para S e BNX para FORM, ambos 1:1, conforme [comunicado FTM/S](https://www.binance.com/en/support/announcement/detail/aec6fcbc84b749eeab6690e6bcac2f3d) e [comunicado BNX/FORM](https://www.binance.com/en/support/announcement/detail/7d5accdcf8f446f3ba3d79f8747a28e2), consultados em 07/09/2026.

Para medir a dependência da decisão dessas premissas, fiz diagnósticos **após o resultado**, preservando posições, sinais e treinamento. Não são novos testes independentes:

| Diagnóstico da carteira por analogia | 2024 | 2025–2026 |
|---|---:|---:|
| Lacunas com retorno zero, demais custos mantidos | {pct(a['diagnostics']['evaluation_1']['analogs']['post_hoc_missing_holdings_flat_return'])} | {pct(a['diagnostics']['evaluation_2']['analogs']['post_hoc_missing_holdings_flat_return'])} |
| Todos os custos de negociação zerados, stress de lacunas mantido | {pct(a['diagnostics']['evaluation_1']['analogs']['post_hoc_zero_cost_return'])} | {pct(a['diagnostics']['evaluation_2']['analogs']['post_hoc_zero_cost_return'])} |
| Custos zerados e lacunas com retorno zero | {pct(a['diagnostics']['evaluation_1']['analogs']['post_hoc_missing_flat_and_zero_cost_return'])} | {pct(a['diagnostics']['evaluation_2']['analogs']['post_hoc_missing_flat_and_zero_cost_return'])} |

Mesmo o último cenário fica abaixo da cesta equivalente nos dois segmentos. Retorno zero nas migrações é uma hipótese diagnóstica; não é avaliação real da troca nem limite superior universal. Não se corrigiu o histórico de rótulos ou se reexecutou o treinamento para favorecer a conclusão. O cálculo independente a partir dos preços brutos confirmou 9.430 retornos individuais, com diferença máxima de 4,45×10⁻¹⁶, e seis carteiras usando Decimal.

Os arquivos públicos permitem incluir símbolos antigos, mas não garantem inventário histórico completo ou ausência de revisões. A hora em que observamos os dados foi 18:50–18:51 UTC de 07/09/2026; disponibilidade histórica após o fechamento é uma premissa de simulação. O arquivo da Binance pode ser revisado, como informa a [documentação oficial](https://github.com/binance/binance-public-data). A exclusão textual de sufixos UP/DOWN/BULL/BEAR também retirou JUP e SYRUP: limitação de cobertura registrada, sem trocar a amostra após ver os resultados.

## Ranking disponível e decisão

Há 14 moedas elegíveis na fotografia de 07/09/2026 00:00 UTC, usando informações até a vela de 05/09. A lista completa e exemplos de vizinhos vencedores e não vencedores estão em `ALTCOINS_RANKING_PESQUISA.md` e no JSON. O horizonte é sete dias, não previsão intradiária. A frequência entre vizinhos não é uma probabilidade futura calibrada. O ranking permanece **resultado de pesquisa de um modelo reprovado**, sem ativação de sinais ou ordens.

Para o objetivo de lucro, encontrar mais episódios de alta não basta. A próxima pesquisa só se justifica com rótulos e identidade de tokens corrigidos, regra de saída e universo historicamente negociável definidos, novo protocolo e evidência nova. Trocar o alvo para retorno líquido esperado seria outra hipótese adaptativa; os períodos já vistos não voltam a ser teste intocado. A família funding/OI/HMM continua congelada.

USDT é a moeda de P&L; conversão USDT/USD 1:1 é apenas premissa. O reporte econômico é em BRL. Com FX constante 5,1253, a ilustração sobre US$5.000 produz perdas de aproximadamente R$14.120 no primeiro segmento e R$25.285 no segundo, sob o stress original. Isso não é previsão de perda nem comparação sincronizada com Tesouro. O benchmark condicional apurado na rodada anterior era R$2.900–2.907/ano sobre R$25.626,50, antes de prêmio de risco e atenção; acessibilidade, imposto aplicável ao operador, FX e fricção real seguem desconhecidos. Não há retorno esperado futuro demonstrado para comparar honestamente com esse hurdle. Exposição cambial também existe nas semanas em caixa USDT.

Validação: 11 testes novos de temporalidade, custos, amostragem e controles sintéticos; oito testes do gate de freeze; 395 respostas brutas com hash conferido; Ruff e Pyright passaram. A reprodução a partir do ZIP extraído gerou resultados, carteiras, amostras e auditoria idênticos byte a byte. Não foram alterados produção, coleta, capital, ledger formal H1–H9, custos congelados ou selos. A pesquisa tem registro próprio em `docs/evidence/altcoin_analogs_20260907/search_log.json`. O pacote inclui dados e scripts para reprodução offline.
'''
(OUT / 'ALTCOINS_RESULTADO.md').write_text(report, encoding='utf-8')

ranking = ['# Ranking de pesquisa — 07/09/2026', '', '**Modelo reprovado na triagem econômica. Esta lista não é recomendação de compra.**', '', 'Fotografia simulada: 07/09/2026 00:00 UTC. Última vela usada: 05/09/2026; horizonte: sete dias. Consulta dos dados: 07/09 às 18:50–18:51 UTC. Apenas 14 moedas da amostra de 240 passaram os filtros de 90 dias de histórico e mediana de volume financeiro diário ≥5 milhões USDT.', '', 'A frequência do alvo entre 200 vizinhos de 2021–2023 mede semelhança histórica; não é probabilidade futura calibrada. Os vizinhos da mesma semana não são 200 eventos independentes. A maioria dos vizinhos de cada moeda não atingiu o alvo.', '', '| Posição | Par | Vizinhos que atingiram o alvo | Frequência histórica | Mediana de volume diário, USDT |', '|---:|---|---:|---:|---:|']
for i, s in enumerate(r['current_signal']['ranking'], 1):
    ranking.append(f"| {i} | {s['symbol']} | {s['positive_neighbors']}/200 | {pct(s['score'],1)} | {num(s['median_quote_volume_30d'])} |")
ranking += ['', 'O alvo exige alta ≥20% em sete dias e vantagem ≥10 pontos percentuais sobre BTC. A ordenação desempata pelo símbolo. Para cada uma das cinco primeiras posições, seguem os três vizinhos mais próximos de cada classe que existem no grupo de 200, incluindo os casos negativos. Não são exemplos escolhidos manualmente.']
for s in r['current_signal']['ranking'][:5]:
    ranking += ['', f"## {s['symbol']}", '', '| Classe | Par histórico | Entrada | Retorno bruto em 7 dias | Distância padronizada |', '|---|---|---|---:|---:|']
    for key, label in [('nearest_winners','Atingiu o alvo'), ('nearest_non_winners','Não atingiu')]:
        for n in s[key]:
            ranking.append(f"| {label} | {n['symbol']} | {n['entry_date']} | {pct(n['gross_return_7d'])} | {n['distance']:.3f} |")
(OUT / 'ALTCOINS_RANKING_PESQUISA.md').write_text('\n'.join(ranking)+'\n', encoding='utf-8')
combined_results = {'screen': r, 'audit': a, 'search_log': ledger, 'validation': validation}
(OUT / 'ALTCOINS_RESULTADOS.json').write_text(json.dumps(combined_results, ensure_ascii=False, indent=2), encoding='utf-8')

requirements = 'httpx==0.28.1\nnumpy==2.5.1\nscikit-learn==1.9.0\nscipy==1.18.0\njoblib==1.5.3\nthreadpoolctl==3.6.0\npytest==8.4.2\n'
readme = '''# Reprodução offline da triagem de altcoins

Pesquisa Discovery, não sistema de ordens. Python 3.13 usado na execução original.
O protocolo, a amostra e o primeiro resultado são preservados; audit.json é
um diagnóstico posterior explicitamente separado. Não transforme retorno de
simulação com perda total nas lacunas em retorno realizado.

Extraia o ZIP em uma pasta própria, abra o terminal nessa pasta e instale as
dependências gratuitas, se ainda não existirem, em ambiente isolado:

    python -m venv .venv
    .venv\\Scripts\\python.exe -m pip install -r requirements.txt
    .venv\\Scripts\\python.exe -m pytest tests/test_altcoin_analogs.py -q
    .venv\\Scripts\\python.exe -m scripts.research_altcoin_analogs --data-dir data --output-dir reproduction
    .venv\\Scripts\\python.exe -m scripts.audit_altcoin_analogs --data-dir data --results-dir reproduction

A análise e a auditoria acima não fazem chamadas de rede. A instalação inicial
de dependências usa rede; uma máquina com essas dependências já instaladas não
precisa dela. Compare reproduction/results.json e audit.json com expected/.
O arquivo acquisition.json preserva a seleção, cobertura e timestamps reais.
data/raw contém bytes originais comprimidos e metadados de cada resposta.
MANIFEST.json contém SHA256 de todos os membros, exceto ele próprio.

collect_altcoin_analogs.py é o coletor público utilizado e pode reconstruir o
cache com rede, mas reconsultar o provedor não equivale a reproduzir a versão
histórica congelada: o provedor pode revisar arquivos. Use os dados deste ZIP.
Nada neste pacote ativa a coleta de produção ou envia ordens.
'''
members = {}
for p in sorted(DATA.rglob('*')):
    if p.is_file():members['data/'+p.relative_to(DATA).as_posix()] = p.read_bytes()
for p in sorted(CANON.glob('*.json')):
    members['docs/evidence/altcoin_analogs_20260907/'+p.name] = p.read_bytes()
for name in ('collect_altcoin_analogs.py','research_altcoin_analogs.py','audit_altcoin_analogs.py'):
    members['scripts/'+name] = (REPO / 'scripts' / name).read_bytes()
members['scripts/__init__.py'] = b''
members['tests/test_altcoin_analogs.py'] = (REPO / 'tests/test_altcoin_analogs.py').read_bytes()
for p in sorted(RESULTS.iterdir()):
    if p.is_file():members['expected/'+p.name] = p.read_bytes()
for name in ('protocol.json','results.json','sources.json'):
    members['benchmark_reference/'+name] = (REPO / 'docs/evidence/funding_carry_screen_20260907' / name).read_bytes()
members['requirements.txt'] = requirements.encode()
members['README_REPRODUCAO.md'] = readme.encode()
manifest = {name: {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)} for name, content in members.items()}
members['MANIFEST.json'] = json.dumps(manifest, indent=2).encode()
zip_path = OUT / 'ALTCOINS_REPRODUCAO.zip'
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for name, content in members.items():archive.writestr(name, content)
with zipfile.ZipFile(zip_path) as archive:
    assert archive.testzip() is None
    for name, item in manifest.items():assert hashlib.sha256(archive.read(name)).hexdigest() == item['sha256']
print(json.dumps({'outputs':[p.name for p in OUT.glob('ALTCOINS*')],'zip_bytes':zip_path.stat().st_size,'zip_members':len(members),'sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest()}, indent=2))
