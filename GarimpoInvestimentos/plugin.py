from datetime import UTC, datetime, timedelta
from pathlib import Path

from GarimpoInvestimentos.contracts import HealthStatus, OperationalStatus
from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.feature_store_health import StoreState, inspect_feature_store
from GarimpoInvestimentos.governance import load_scientific_state


class CryptoPredictorPlugin:
    name = "cripto-predictor"
    domain = "crypto"

    def __init__(self, store_path: Path = FEATURE_STORE_DB) -> None:
        self._store_path = store_path

    def health(self) -> HealthStatus:
        store = inspect_feature_store(
            self._store_path, now=datetime.now(UTC), max_age=timedelta(days=2)
        )
        status = {
            StoreState.READY: OperationalStatus.SUCCEEDED,
            StoreState.STALE: OperationalStatus.DEGRADED,
            StoreState.EMPTY: OperationalStatus.WAITING,
            StoreState.MISSING: OperationalStatus.SOURCE_UNAVAILABLE,
            StoreState.CORRUPT: OperationalStatus.FAILED,
        }[store.state]
        return HealthStatus(
            domain=self.domain,
            status=status,
            details={"mode": "research", "feature_store": store.state},
        )

    def capabilities(self) -> dict[str, object]:
        """Expose the current research boundary without promoting capital."""
        state = load_scientific_state()
        active = sorted(
            name
            for name, status in state.hypotheses.items()
            if str(status) == "COLLECTION_ONLY_IMMATURE"
        )
        return {
            "domain": self.domain,
            "supports_prediction": False,
            "supports_settlement": False,
            "supports_collection": False,
            "scientific_status": "ACTIVE_HYPOTHESIS" if active else "NO_ACTIVE_HYPOTHESIS",
            "predictive_status": "INCONCLUSIVE",
            "economic_status": "HISTORICAL_NO_GO",
            "capital_permission": "FORBIDDEN",
            "extra": {
                "mode": "RESEARCH_ONLY",
                "active_hypothesis": active[0] if len(active) == 1 else None,
                "hypotheses": {name: str(status) for name, status in state.hypotheses.items()},
                "security_status": "ROTATED_CONFIRMED_BY_OWNER_2026-08-19",
                "old_key_revocation_external_check_pending": True,
                "trading": False,
                "source_of_scientific_truth": "charters/scientific_state.json",
            },
        }


PLUGIN = CryptoPredictorPlugin()
