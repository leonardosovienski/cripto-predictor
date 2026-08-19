"""H6_DEFINITION_FROZEN: o snapshot deve detectar qualquer mudança na semântica
científica de H6 (código das funções que a maturam, ou a entrada em trials.json).
"""

import json

from scripts.freeze_h6_definition import build_snapshot


def test_snapshot_contem_as_travas_essenciais():
    snap = build_snapshot()
    assert snap["H6_DEFINITION_FROZEN"] is True
    assert snap["trial_id"] == "h6-sinal-invertido-d7"
    assert snap["governing_code"]["constants"]["H6_MIN_N"] == "30"
    assert '"dpl:fallback"' == snap["governing_code"]["constants"]["H6_LIVE_FONTE"]
    assert "registered_at_lock" in snap["rules"]
    assert "min_n_gate" in snap["rules"]


def test_hash_e_deterministico_entre_chamadas():
    a = build_snapshot()
    b = build_snapshot()
    assert a["governing_code_sha256"] == b["governing_code_sha256"]
    assert a["trials_json_entry_sha256"] == b["trials_json_entry_sha256"]


def test_hash_muda_se_a_entrada_do_trial_mudar(tmp_path, monkeypatch):
    import scripts.freeze_h6_definition as mod

    original = json.loads(mod.TRIALS_JSON.read_text(encoding="utf-8"))
    tampered_path = tmp_path / "trials.json"
    tampered = [dict(t) for t in original]
    for t in tampered:
        if t["name"] == "h6-sinal-invertido-d7":
            t["params"]["horizonte_dias"] = 14  # mudanca de definicao simulada
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")

    baseline = mod.build_snapshot()
    monkeypatch.setattr(mod, "TRIALS_JSON", tampered_path)
    tampered_snapshot = mod.build_snapshot()

    assert baseline["trials_json_entry_sha256"] != tampered_snapshot["trials_json_entry_sha256"]


def test_check_falha_quando_snapshot_gravado_diverge(tmp_path, monkeypatch, capsys):
    import scripts.freeze_h6_definition as mod

    out_path = tmp_path / "h6_definition_frozen.json"
    monkeypatch.setattr(mod, "OUT_PATH", out_path)

    stale = mod.build_snapshot()
    stale["governing_code_sha256"] = "0" * 64  # simula divergencia
    out_path.write_text(json.dumps(stale), encoding="utf-8")

    exit_code = mod.main(["--check"])
    assert exit_code == 1
    assert "divergiu" in capsys.readouterr().err


def test_check_passa_quando_snapshot_gravado_confere(tmp_path, monkeypatch):
    import scripts.freeze_h6_definition as mod

    out_path = tmp_path / "h6_definition_frozen.json"
    monkeypatch.setattr(mod, "OUT_PATH", out_path)

    mod.main([])  # gera
    exit_code = mod.main(["--check"])
    assert exit_code == 0
