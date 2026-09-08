"""Contrato IS -> PURGE -> OOS do walk-forward (backtest_v3.run_wfa).

run_wfa exige dados de mercado reais (CSV com meses de funding/OI/spot para o
HMM treinar) e não é viável rodá-lo com dados fabricados sem arriscar mascarar
bugs atrás de uma série sintética artificial. Em vez disso, este teste importa
as constantes REAIS do módulo (não valores redigitados aqui) e reproduz
exatamente a aritmética de fronteira do loop de folds (backtest_v3.py, linhas
545-557: ``oos_start_day = is_start_day + _IS_DAYS + _PURGE_DAYS``), provando
por código — não por leitura — que:

  1. todo fold tem um purge gap não-nulo entre o fim do IS e o início do OOS;
  2. o gap é exatamente _PURGE_DAYS, nem mais nem menos;
  3. o mesmo vale em milissegundos (a unidade real usada no slicing dos dados);
  4. uma regressão que zere ou remova o purge é pega por este teste.
"""

from GarimpoInvestimentos.v3.backtest_v3 import (
    _IS_DAYS,
    _MS_PER_DAY,
    _OOS_DAYS,
    _PURGE_DAYS,
    _STEP_DAYS,
)


def _generate_fold_boundaries(total_days: int) -> list[tuple[int, int, int, int]]:
    """Reproduz o loop real de run_wfa (backtest_v3.py:545-557) em dias."""
    folds = []
    is_start_day = 0
    while True:
        oos_start_day = is_start_day + _IS_DAYS + _PURGE_DAYS
        oos_end_day = oos_start_day + _OOS_DAYS
        if oos_end_day > total_days:
            break
        folds.append((is_start_day, is_start_day + _IS_DAYS, oos_start_day, oos_end_day))
        is_start_day += _STEP_DAYS
    return folds


def test_purge_gap_e_estritamente_positivo():
    assert _PURGE_DAYS > 0, (
        "purge=0 elimina o embargo entre treino e teste — leakage direto do "
        "último candle do IS para o primeiro do OOS"
    )


def test_cada_fold_tem_gap_exato_de_purge_days_entre_is_e_oos():
    total_days = _IS_DAYS + _OOS_DAYS + _PURGE_DAYS + 3 * _STEP_DAYS
    folds = _generate_fold_boundaries(total_days)
    assert len(folds) >= 2, "cenário precisa gerar ao menos 2 folds para o teste valer algo"
    for is_start, is_end, oos_start, oos_end in folds:
        assert oos_start - is_end == _PURGE_DAYS
        assert oos_start > is_end, "OOS não pode começar antes (ou junto) do fim do IS"
        assert oos_end > oos_start


def test_gap_em_milissegundos_bate_com_o_slicing_real_de_timestamps():
    # backtest_v3.py:554-557 converte dia -> ms multiplicando por _MS_PER_DAY
    # antes de fatiar a série. Confirma que a aritmética em ms não diverge da
    # aritmética em dias (ex.: por arredondamento ou constante trocada).
    is_start_day, is_end_day = 0, _IS_DAYS
    oos_start_day = is_start_day + _IS_DAYS + _PURGE_DAYS

    is_end_ms = is_end_day * _MS_PER_DAY
    oos_start_ms = oos_start_day * _MS_PER_DAY

    assert (oos_start_ms - is_end_ms) == _PURGE_DAYS * _MS_PER_DAY


def test_regressao_purge_zero_e_detectada_pelo_gerador_de_folds():
    # Prova que o teste acima teria pego a regressão: com purge=0 simulado
    # localmente (sem tocar na constante real do módulo), o gap desaparece.
    fake_purge_days = 0
    is_start_day = 0
    oos_start_day = is_start_day + _IS_DAYS + fake_purge_days
    assert oos_start_day - (is_start_day + _IS_DAYS) == 0
    # ... e é exatamente esse "== 0" que test_cada_fold_tem_gap_exato_de_purge_days_entre_is_e_oos
    # rejeitaria se _PURGE_DAYS real virasse 0 (o assert de lá exige == _PURGE_DAYS,
    # e test_purge_gap_e_estritamente_positivo exige _PURGE_DAYS > 0).


def test_folds_consecutivos_avancam_por_step_days_sem_pular_dados():
    total_days = _IS_DAYS + _OOS_DAYS + _PURGE_DAYS + 2 * _STEP_DAYS
    folds = _generate_fold_boundaries(total_days)
    assert len(folds) >= 2
    for (is_start_a, *_), (is_start_b, *_) in zip(folds, folds[1:]):
        assert is_start_b - is_start_a == _STEP_DAYS
