from datetime import UTC, date, datetime

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.governance import load_observation_plan
from GarimpoInvestimentos.observation_quality import evaluate_daily_metric
from GarimpoInvestimentos.observation_reporting import maturity_report, weekly_report


def test_weekly_and_maturity_reports_fail_closed_without_evidence(tmp_path):
    db_path = tmp_path / "features.db"
    plan = load_observation_plan()
    with FeatureStore(db_path) as store:
        evaluate_daily_metric(
            store,
            plan=plan,
            metric_name="funding_rate",
            day=date(2026, 8, 8),
            audit_path=tmp_path / "audit.jsonl",
            calculated_at=datetime(2026, 8, 9, tzinfo=UTC),
        )
        weekly = weekly_report(
            store, plan=plan, week_start=date(2026, 8, 8), output_dir=tmp_path / "reports"
        )
        maturity = maturity_report(
            store,
            plan=plan,
            as_of=datetime(2026, 9, 8, tzinfo=UTC),
            desired=False,
            output_dir=tmp_path / "reports",
            db_path=db_path,
        )
    assert weekly["metrics"]["funding_rate"]["daily_scorecards"] == 1
    assert maturity["passed"] is False
    assert maturity["capital_authorized"] is False
    assert maturity["resources"]["cost_within_charter"] is False
