from pathlib import Path

import numpy as np
import pyomo.environ as pyo
import pytest

from pvbess_h2 import (carregar_parametros, construir_modelo, indicadores, montar_series,
                       resolver, serie_resultados)

CONFIG = Path(__file__).resolve().parents[1] / "config" / "caso_base.yaml"


def resolver_caso(ajustes=None, dias=2, despacho=None):
    p = carregar_parametros(CONFIG)
    p.horizonte.dias = dias
    for secao, valores in (ajustes or {}).items():
        for k, v in valores.items():
            setattr(getattr(p, secao), k, v)
    for k, v in (despacho or {}).items():
        setattr(p.lrcap.despacho_ons, k, v)
    p.validar()
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


def test_limites_e_exclusividade_bess_mercantil():
    p, m, df, _ = resolver_caso()
    b = p.bess
    e_merc = pyo.value(m.E_merc)
    assert (df.soc_mwh >= b.soc_min_frac * e_merc - 1e-6).all()
    assert (df.soc_mwh <= b.soc_max_frac * e_merc + 1e-6).all()
    assert ((df.p_carga_bess_mw * df.p_descarga_bess_mw) < 1e-6).all()
    assert df.soc_mwh.iloc[-1] >= b.soc_inicial_frac * e_merc - 1e-6


def test_carga_minima_eletrolisador():
    p, _, df, _ = resolver_caso()
    e = p.eletrolisador
    ligado = df.p_eletrolisador_mw > 1e-6
    assert (df.p_eletrolisador_mw[ligado] >= e.carga_min_frac * e.potencia_max_mw - 1e-6).all()


def test_h2_verde_estrito_proibe_importacao():
    _, _, df, _ = resolver_caso({"rede": {"h2_verde_estrito": True}})
    assert df.p_importacao_mw.max() < 1e-6


def test_divisao_do_bess_entre_modulos():
    p, _, df, kpi = resolver_caso()
    b, lr = p.bess, p.lrcap
    pcap = kpi.potencia_lrcap_mw
    assert kpi.energia_modulo_lrcap_mwh == pytest.approx(lr.energia_por_mw_h * pcap, abs=1e-2)
    assert (df.p_descarga_bess_mw + df.p_descarga_lrcap_mw <= b.potencia_descarga_mw + 1e-6).all()
    assert (df.p_carga_bess_mw + df.p_recarga_lrcap_mw <= b.potencia_carga_mw + 1e-6).all()


def test_potencia_minima_lrcap_30mw():
    _, _, _, kpi = resolver_caso()
    assert kpi.potencia_lrcap_mw < 1e-6 or kpi.potencia_lrcap_mw >= 30 - 1e-6
    # BESS pequeno demais para o mínimo de 30 MW: não participa do LRCAP
    _, _, _, kpi = resolver_caso({"bess": {"potencia_carga_mw": 20.0, "potencia_descarga_mw": 20.0}})
    assert kpi.potencia_lrcap_mw == pytest.approx(0.0, abs=1e-6)


def test_modulo_lrcap_segue_despacho_ons():
    p, _, df, kpi = resolver_caso({"lrcap": {"potencia_fixa_mw": 40.0}})
    assert kpi.potencia_lrcap_mw == pytest.approx(40.0)
    em_despacho = df.index.hour.isin(p.lrcap.despacho_ons.horas_descarga)
    assert np.allclose(df.p_descarga_lrcap_mw[em_despacho], 40.0)
    assert np.allclose(df.p_descarga_lrcap_mw[~em_despacho], 0.0)
    # SOC do módulo nunca sai da faixa permitida
    e_lr = p.lrcap.energia_por_mw_h * 40.0
    assert (df.soc_lrcap_mwh >= p.bess.soc_min_frac * e_lr - 1e-6).all()
    # Receita no MCP vem só do lado mercantil (energia do módulo LRCAP vai para a CONCAP)
    assert kpi.receita_mcp_rs == pytest.approx((df.pld_rs_mwh * df.p_exportacao_mw).sum(), rel=1e-6)


def test_conexao_compartilhada():
    p, _, df, _ = resolver_caso({"rede": {"exportacao_max_mw": 45.0, "importacao_max_mw": 45.0},
                                 "lrcap": {"potencia_fixa_mw": 40.0}})
    assert (df.fluxo_conexao_mw <= 45.0 + 1e-6).all()
    assert (df.fluxo_conexao_mw >= -45.0 - 1e-6).all()


def test_despacho_ons_inviavel_e_detectado():
    with pytest.raises(ValueError, match="inviável"):
        resolver_caso(despacho={"horas_descarga": list(range(12, 20)), "horas_recarga": [2, 3]})


def test_lrcap_desabilitado_nao_contrata():
    _, _, _, kpi = resolver_caso({"lrcap": {"habilitado": False}})
    assert kpi.potencia_lrcap_mw == pytest.approx(0.0, abs=1e-6)
    assert kpi.receita_lrcap_rs == pytest.approx(0.0, abs=1e-3)


def test_entrega_minima_diaria_h2():
    p, _, df, _ = resolver_caso({"hidrogenio": {"entrega_min_diaria_kg": 3000.0}})
    assert (df.groupby("dia").venda_h2_kg_h.sum() * p.horizonte.dt_h >= 3000 - 1e-4).all()


def test_contrato_h2_teto_diario():
    p, _, df, _ = resolver_caso({"hidrogenio": {"entrega_max_diaria_kg": 1500.0}})
    vendas = df.venda_h2_kg_h.groupby(df.index.date).sum() * p.horizonte.dt_h
    assert (vendas <= 1500.0 + 1e-6).all()


def test_contrato_h2_deficit_multado():
    # Entrega mínima inalcançável: sem multa seria inviável; com multa, o déficit é pago.
    ajuste = {"entrega_min_diaria_kg": 50000.0, "entrega_max_diaria_kg": 50000.0,
              "penalidade_deficit_rs_kg": 10.0}
    p, m, df, kpi = resolver_caso({"hidrogenio": ajuste})
    vendas = df.venda_h2_kg_h.groupby(df.index.date).sum() * p.horizonte.dt_h
    assert kpi.deficit_h2_kg == pytest.approx((50000.0 - vendas).sum(), rel=1e-4)
    assert kpi.custo_h2_rs >= 10.0 * kpi.deficit_h2_kg - 1e-3
