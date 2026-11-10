"""Testes das rotinas dos scripts que não dependem de resolver o modelo."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from operacao_rolante import previsao_janela  # noqa: E402


def test_persistencia_nao_usa_dado_futuro():
    # pv[i] = i: o valor previsto revela o índice de origem. Em t, só as horas até t são conhecidas.
    pv = np.arange(24.0 * 10)
    for t in (24, 30, 47, 100, 191):
        f = previsao_janela(pv, t, 48, "persistencia")
        assert f[0] == t                                   # a hora t é medida
        assert (f <= t).all()                              # nenhuma previsão usa hora posterior a t
        k = np.arange(len(f))
        assert ((t + k - f) % 24 == 0).all()               # sempre a mesma hora do dia
        assert (f[1:25] == t + k[1:25] - 24).all()         # dia seguinte: a mesma hora da véspera
        assert (f[25:] == t + k[25:] - 48).all()           # segundo dia da janela: o mesmo dia observado


def test_persistencia_primeiro_dia_e_fim_do_ano():
    pv = np.arange(24.0 * 3)
    assert (previsao_janela(pv, 0, 24, "persistencia") == pv[:24]).all()   # sem dia anterior: realizado
    assert len(previsao_janela(pv, 60, 48, "persistencia")) == 12          # a janela termina com as séries
    assert (previsao_janela(pv, 30, 48, "perfeita") == pv[30:72]).all()
    with pytest.raises(ValueError):
        previsao_janela(pv, 0, 24, "outra")
