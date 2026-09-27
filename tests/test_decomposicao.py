import warnings
from pathlib import Path

import numpy as np
import pytest

from pvbess_h2 import carregar_parametros
from pvbess_h2.decomposicao import avaliar_bloco, dividir_em_blocos, resolver_benders

CONFIG = Path(__file__).resolve().parents[1] / "config" / "caso_base.yaml"
warnings.filterwarnings("ignore", category=UserWarning)


def test_divisao_em_blocos():
    bl = dividir_em_blocos("2025-01-01", 365, 7)
    assert len(bl) == 52 and sum(d for _, d in bl) == 365 and bl[-1][1] == 8


def test_corte_reforcado_e_valido():
    """O corte deve limitar superiormente o lucro do bloco em qualquer P_cap."""
    p = carregar_parametros(CONFIG)
    r30 = avaliar_bloco((p, "2025-01-06", 2, 30.0, 1e-6))
    for x in [0.0, 40.0, 60.0]:
        q = avaliar_bloco((p, "2025-01-06", 2, x, 1e-6)).q
        assert r30.c + r30.lam * x >= q - 1e-3 * abs(q)
    assert r30.c + r30.lam * 30.0 == pytest.approx(r30.q, rel=1e-3)


def test_benders_certifica_otimo():
    p = carregar_parametros(CONFIG)
    x, lucro, hist, _ = resolver_benders(p, "2025-01-06", 4, dias_bloco=2, tol=1e-3,
                                         processos=2, verbose=False)
    tab = hist.tabela()
    assert tab.limite_superior_rs.iloc[-1] >= lucro - 1e-6
    assert (tab.limite_superior_rs.iloc[-1] - lucro) / lucro <= 1e-3 + 1e-9
    assert x == 0 or x >= p.lrcap.potencia_min_mw - 1e-6
    # Nenhum ponto de uma grade pode superar o limite superior certificado
    r_cap = p.lrcap.receita_fixa_rs_mw_ano * 4 * 24 / 8760
    for xg in np.linspace(30, 60, 4):
        v = r_cap * xg + sum(avaliar_bloco((p, i, d, xg, 1e-6)).q
                             for i, d in dividir_em_blocos("2025-01-06", 4, 2))
        assert v <= tab.limite_superior_rs.iloc[-1] + 1e-3 * abs(v)
