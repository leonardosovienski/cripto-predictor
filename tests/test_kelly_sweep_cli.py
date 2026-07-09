"""Regressão C1 (auditoria 2026-07-09): o CLI do Kelly sweep quebrou quando o
--taker-fee-bps entrou (Risco 4) — _main passava taker_fee_bps a
run_kelly_sweep, que não aceitava o parâmetro (TypeError na hora da chamada,
antes de qualquer dado ser lido). O sweep é a ferramenta de re-homologação da
fração de Kelly; nenhum teste cobria o cabeamento CLI → run_kelly_sweep →
run_wfa. Estes testes fecham a lacuna sem precisar de dados reais (run_wfa é
substituído por um stub que só grava os kwargs recebidos).
"""
from unittest import mock

from GarimpoInvestimentos.v3 import backtest_v3


def _fake_wfa_result(kelly_fraction: float) -> backtest_v3.WFAResult:
    return backtest_v3.WFAResult(
        symbol="STUBUSDT", n_folds=0, folds=[],
        aggregate_psr=0.0, aggregate_ic=0.0, aggregate_ic_ci_lower=0.0,
        aggregate_max_dd=0.0, aggregate_sharpe=0.0,
        final_verdict="NO-GO", verdict_reason="stub",
        kelly_fraction=kelly_fraction,
    )


def test_run_kelly_sweep_accepts_and_forwards_taker_fee_bps():
    """A regressão original: taker_fee_bps precisa ser aceito E repassado ao
    run_wfa de cada fração (sem o repasse, o sweep re-homologaria com o fee
    default silenciosamente — inconsistente com o que o operador pediu)."""
    calls = []

    def stub_run_wfa(**kwargs):
        calls.append(kwargs)
        return _fake_wfa_result(kwargs["kelly_fraction"])

    with mock.patch.object(backtest_v3, "run_wfa", side_effect=stub_run_wfa), \
            mock.patch.object(backtest_v3, "emit_event"):
        sweep = backtest_v3.run_kelly_sweep(
            symbol="STUBUSDT",
            kelly_fractions=[1.0, 0.5],
            slippage_bps=7.0,
            taker_fee_bps=12.5,     # <- o kwarg que causava TypeError
            horizon_hours=24,
            fr_window=90,
        )

    assert len(calls) == 2
    for kw in calls:
        assert kw["taker_fee_bps"] == 12.5
        assert kw["slippage_bps"] == 7.0
    assert [r.kelly_fraction for r in sweep.results] == [1.0, 0.5]


def test_cli_wiring_matches_run_kelly_sweep_signature():
    """Guarda estrutural: todo kwarg que o _main passa a run_kelly_sweep tem
    que existir na assinatura — é exatamente a classe de quebra do C1 (o CLI
    divergiu da função e nenhum teste olhava)."""
    import inspect
    params = set(inspect.signature(backtest_v3.run_kelly_sweep).parameters)
    cli_kwargs = {"symbol", "kelly_fractions", "slippage_bps",
                  "taker_fee_bps", "horizon_hours", "fr_window"}
    faltando = cli_kwargs - params
    assert not faltando, f"CLI passa kwargs fora da assinatura: {faltando}"
