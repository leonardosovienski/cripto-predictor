from GarimpoInvestimentos.analyzers.score_engine import calculate_final_score, divergence_flag


def classify_scientific_eligibility(*, llm_fallback: bool, degraded: bool) -> str:
    return "EXCLUDED_DEGRADED" if llm_fallback or degraded else "ELIGIBLE"


__all__ = ["calculate_final_score", "classify_scientific_eligibility", "divergence_flag"]
