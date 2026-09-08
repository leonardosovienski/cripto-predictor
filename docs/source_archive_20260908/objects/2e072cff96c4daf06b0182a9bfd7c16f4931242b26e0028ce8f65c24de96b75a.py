from pathlib import Path

root = Path(__file__).parent / 'cripto-v1.2'
old_hash = 'fdc1d3e27b6805a1d125702b6e3bb88f6fa3483791c22ea310bf6c56d5581c4d'
new_hash = '9166dd6bd3be99668c0eb8bd3c59a92061e765186608465c0caf48a2417e3009'
for name in ['pyproject.toml', 'Dockerfile', '.github/workflows/ci.yml', 'scripts/verify_installed_wheels.py', 'tests/test_core_integrity.py']:
    p = root / name
    s = p.read_text(encoding='utf-8').replace('3.0.0', '3.2.0').replace(old_hash, new_hash)
    p.write_text(s, encoding='utf-8')

p = root / 'GarimpoInvestimentos/analyzers/trials.py'
s = p.read_text(encoding='utf-8').replace('from pathlib import Path', 'import json\nfrom pathlib import Path')
s = s.replace('    PowerAttestationMissingError,', '    DeflationNotEstimableError,\n    PowerAttestationMissingError,').replace('    deflated_sharpe_ratio,\n', '')
s = s.replace('from predictor_core.measurement.trials import load_trials as _core_load', 'from predictor_core.measurement.trials import deflated_sharpe_ratio as _core_dsr\nfrom predictor_core.measurement.trials import load_trials as _core_load')
anchor = '\n\ndef load_trials('
helper = '''

def deflated_sharpe_ratio(returns: list, trial_sharpes: list) -> dict:
    """Não publica PSR sob rótulo DSR quando a variância não é estimável."""
    return _core_dsr(returns, trial_sharpes, strict=True)


def _update_attestation(target: Path, name: str, extra: dict) -> dict:
    """Encaminha o atestado da métrica já registrada; o Core valida sua vigência.

    Não emite atestados, não inventa métrica e não libera família fechada.
    Chamadores que fornecem explicitamente o atestado preservam esse contrato.
    """
    if 'power_attestation' in extra or 'pipeline_fingerprint' in extra:
        return extra
    trial = next((t for t in load_trials(target) if t['name'] == name), None)
    if trial is None or not trial.get('metric'):
        return extra
    metric = trial['metric']
    att = (target.with_name(target.stem + '.phase1_harness_attestation.json')
           if metric == 'spearman_ic' else attestation_path_for(target))
    try:
        record = json.loads(att.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        record = {}
    return {**extra, 'power_attestation': att,
            'pipeline_fingerprint': record.get('pipeline_fingerprint')}
'''
s = s.replace(anchor, helper + anchor)
s = s.replace('    return _core_register(name, params=params, sharpe=sharpe, notes=notes, path=target, **extra)', '    if sharpe is not None or "status" in extra:\n        extra = _update_attestation(Path(target), name, extra)\n    return _core_register(name, params=params, sharpe=sharpe, notes=notes, path=target, **extra)')
p.write_text(s, encoding='utf-8')

p = root / 'GarimpoInvestimentos/analyzers/backtest.py'
s = p.read_text(encoding='utf-8').replace('from GarimpoInvestimentos.analyzers.trials import deflated_sharpe_ratio, load_trials, register_trial', 'from GarimpoInvestimentos.analyzers.trials import (\n    DeflationNotEstimableError, deflated_sharpe_ratio, load_trials, register_trial,\n)')
start = s.index('            # Trials abertas têm sharpe=null')
end = s.index('\n    else:\n        print(f"  Hit rate', start)
s = s[:start] + '''            # Tentativas sem Sharpe contam em N, mas não na variância.
            try:
                d = deflated_sharpe_ratio(
                    [x / 100 for x in rets], [t.get("sharpe") for t in trials]
                )
            except DeflationNotEstimableError:
                print("  DSR: UNKNOWN — menos de 2 Sharpes finitos; promoção bloqueada")
            else:
                if not math.isnan(d["dsr"]):
                    print(
                        f"  DSR (N={d['n_trials']} tentativas registradas, "
                        f"{d['n_sharpes']} Sharpes finitos): "
                        f"P(SR > máx-por-sorte) = {d['dsr']:.2f} | SR0 = {d['sr0']:.3f} "
                        f"— {'passa' if d['dsr'] >= 0.95 else 'NÃO passa'} o corte 0.95"
                    )
''' + s[end:]
p.write_text(s, encoding='utf-8')

p = root / 'tests/test_trials.py'
s = p.read_text(encoding='utf-8').replace('import math\n', '').replace('    FrozenFamilyError,', '    DeflationNotEstimableError,\n    FrozenFamilyError,')
start = s.index('def test_uma_tentativa_dsr_equivale_ao_psr():')
end = s.index('# ---------- registro versionado', start)
s = s[:start] + '''@pytest.mark.parametrize("sharpes", [[], [0.3], [None, float("inf"), 0.3]])
def test_dsr_sem_variancia_estimavel_bloqueia_em_vez_de_publicar_psr(sharpes):
    with pytest.raises(DeflationNotEstimableError):
        deflated_sharpe_ratio(_returns(), sharpes)


def test_mais_tentativas_so_reduzem_o_dsr():
    rets = _returns()
    psr = probabilistic_sharpe_ratio(rets, benchmark_sharpe=0.0)
    dez = deflated_sharpe_ratio(rets, [0.3, -0.1, 0.2, 0.05, -0.3, 0.4, 0.1, -0.2, 0.25, 0.0])
    assert dez["sr0"] > 0
    assert dez["dsr"] < psr


def test_sharpes_ausentes_contam_no_n_sem_entrar_na_variancia():
    rets = _returns()
    complete = deflated_sharpe_ratio(rets, [0.3, -0.1])
    missing = deflated_sharpe_ratio(rets, [0.3, -0.1, None, float("inf")])
    assert missing["n_trials"] == 4 and missing["n_sharpes"] == 2
    assert missing["sr0"] > complete["sr0"]
    assert missing["dsr"] < complete["dsr"]


''' + s[end:]
s = s.replace('def test_registro_roundtrip_e_dedup_por_nome(tmp_path):', 'def test_registro_roundtrip_e_dedup_por_nome(tmp_path, registry_attestation):')
s = s.replace('register_trial("cfg-a", params={"h": 7}, sharpe=0.1, path=p, power_attestation=False)', 'register_trial("cfg-a", params={"h": 7}, sharpe=0.1, path=p, **registry_attestation(p))')
p.write_text(s, encoding='utf-8')

p = root / 'tests/test_experiment_registry.py'
s = p.read_text(encoding='utf-8')
for name in ['test_reexecucao_mesma_config_atualiza_sharpe_preservando_registro', 'test_backtest_fecha_sharpe_da_trial_casada', 'test_backtest_divide_eras_entre_trial_encerrada_e_sucessora', 'test_h6_matura_com_dado_posterior_ao_registro_e_score_baixo']:
    start = s.index('def ' + name + '(')
    end = s.find('\ndef ', start + 4)
    if end < 0: end = len(s)
    block = s[start:end].replace('(tmp_path):', '(tmp_path, registry_attestation):').replace('**_NOGATE', '**registry_attestation(p)').replace('# update: sem trava', '# update: atestado validado pelo Core')
    s = s[:start] + block + s[end:]
s = s.replace('H6 fechou REFUTADA/NO-GO em 2026-09-04 (docs/HYPOTHESES.md, veredito real:\n    IC cruza zero, n=84).', 'H6 permanece encerrada por amostra insuficiente (errata 2026-09-07):\n    IC cruza zero, n=84; o rótulo causal não libera reescrita.')
p.write_text(s, encoding='utf-8')

p = root / 'tests/conftest.py'
s = p.read_text(encoding='utf-8') + '''

import pytest


@pytest.fixture
def registry_attestation(tmp_path):
    """Executa o juiz real sobre controles sintéticos; só escreve no tmp do teste."""
    from predictor_core.testing.harness import attest_pipeline_power
    from scripts.attest_harness import judge_phase1, phase1_edge_series, phase1_noise_series

    def emit(path):
        att = path.with_name(path.stem + ".phase1_harness_attestation.json")
        record = attest_pipeline_power(
            judge_phase1, phase1_edge_series, phase1_noise_series,
            attestation_path=att, edge_verdict="VALIDADO", null_verdict="RUIDO",
            metric="spearman_ic", repo=tmp_path,
            note="Controle real do juiz em fixture sintética; não autoriza registro canônico.",
        )
        return {"metric": "spearman_ic", "power_attestation": att,
                "pipeline_fingerprint": record["pipeline_fingerprint"]}

    return emit
'''
p.write_text(s, encoding='utf-8')
