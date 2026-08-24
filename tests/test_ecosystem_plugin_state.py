from GarimpoInvestimentos.plugin import PLUGIN


def test_ecosystem_plugin_exposes_current_governance_state():
    caps = PLUGIN.capabilities()
    assert caps["domain"] == "crypto"
    assert caps["scientific_status"] == "ACTIVE_HYPOTHESIS"
    assert caps["predictive_status"] == "INCONCLUSIVE"
    assert caps["economic_status"] == "HISTORICAL_NO_GO"
    assert caps["capital_permission"] == "FORBIDDEN"
    assert caps["extra"]["active_hypothesis"] == "H6"
    assert caps["extra"]["security_status"] == "ROTATED_CONFIRMED_BY_OWNER_2026-08-19"
