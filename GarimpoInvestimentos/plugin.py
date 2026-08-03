from datetime import UTC, datetime, timedelta
from pathlib import Path

from GarimpoInvestimentos.contracts import HealthStatus, OperationalStatus
from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.feature_store_health import StoreState, inspect_feature_store


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
        """Expose the research-only boundary to the ecosystem gateway."""
        return {
            "domain": self.domain,
            "supports_prediction": False,
            "supports_settlement": False,
            "supports_collection": False,
            "scientific_status": "NO_GO",
            "extra": {
                "mode": "research",
                "secret_rotation_pending": True,
                "trading": False,
            },
        }


PLUGIN = CryptoPredictorPlugin()
