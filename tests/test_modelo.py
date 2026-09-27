from pathlib import Path

import numpy as np
import pytest

from pvbess_h2 import (carregar_parametros, construir_modelo, indicadores, montar_series,
                       resolver, serie_resultados)

CONFIG = Path(__file__).resolve().parents[1] / "config" / "caso_base.yaml"


def resolver_caso(ajustes=None, dias=2):
    p = carregar_parametros(CONFIG)
    p.horizonte.dias = dias
    for secao, valores in (ajustes or {}).items():
        for k, v in valores.items():
            setattr(getattr(p, secao), k, v)
    s = montar_series(p)
    m = construir_modelo(p, s)
    resolver(m)
    df = serie_resultados(m, s)
    return p, m, df, indicadores(m, df, p)


def test_balanco_de_potencia():
    _, _, df, _ = resolver_caso()
    oferta = df.p_pv_mw + df.p_descarga_bess_mw + df.p_importacao_mw
    demanda = df.p_carga_bess_mw + df.p_eletrolisador_mw + df.p_exportacao_mw
    assert np.allclose(oferta, demanda, atol=1e-5)


def test_limites_e_exclusividade_bess():
    p, _, df, _ = resolver_caso()
    b = p.bess
    assert (df.soc_mwh >= b.soc_min_frac * b.energia_mwh - 1e-6).all()
    assert (df.soc_mwh <= b.soc_max_frac * b.energia_mwh + 1e-6).all()
    assert ((df.p_carga_bess_mw * df.p_descarga_bess_mw) < 1e-6).all()
    assert df.soc_mwh.iloc[-1] >= b.soc_inicial_frac * b.energia_mwh - 1e-6


def test_carga_minima_eletrolisador():
    p, _, df, _ = resolver_caso()
    e = p.eletrolisador
    ligado = df.p_eletrolisador_mw > 1e-6
    assert (df.p_eletrolisador_mw[ligado] >= e.carga_min_frac * e.potencia_max_mw - 1e-6).all()


def test_h2_verde_estrito_proibe_importacao():
    _, _, df, _ = resolver_caso({"rede": {"h2_verde_estrito": True}})
    assert df.p_importacao_mw.max() < 1e-6


def test_reserva_lrcap_na_janela():
    p, m, df, kpi = resolver_caso()
    b, lr = p.bess, p.lrcap
    reserva = b.soc_min_frac * b.energia_mwh + kpi.potencia_lrcap_mw * lr.duracao_h / b.eficiencia_descarga
    na_janela = df.janela_lrcap == 1
    assert (df.soc_mwh[na_janela] >= reserva - 1e-5).all()


def test_acionamento_lrcap_entregue():
    _, _, df, kpi = resolver_caso({"lrcap": {"acionamentos": [18, 19], "potencia_fixa_mw": 10.0}})
    assert kpi.potencia_lrcap_mw == pytest.approx(10.0)
    assert (df.p_exportacao_mw.iloc[[18, 19]] + df.deficit_lrcap_mw.iloc[[18, 19]] >= 10 - 1e-6).all()
    assert kpi.penalidade_lrcap_rs == pytest.approx(0.0, abs=1e-3)


def test_lrcap_desabilitado_nao_contrata():
    _, _, _, kpi = resolver_caso({"lrcap": {"habilitado": False}})
    assert kpi.potencia_lrcap_mw == pytest.approx(0.0, abs=1e-6)
    assert kpi.receita_lrcap_rs == pytest.approx(0.0, abs=1e-3)


def test_entrega_minima_diaria_h2():
    p, _, df, _ = resolver_caso({"hidrogenio": {"entrega_min_diaria_kg": 3000.0}})
    assert (df.groupby("dia").venda_h2_kg_h.sum() * p.horizonte.dt_h >= 3000 - 1e-4).all()
