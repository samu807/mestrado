from pathlib import Path

import numpy as np
import pandas as pd
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


def test_ciclos_ano_seleciona_dias_de_maior_pld():
    from pvbess_h2.dados import despacho_ons, indice_temporal, pld_sintetico
    p = carregar_parametros(CONFIG)
    p.horizonte.dias = 28
    p.lrcap.despacho_ons.modo = "pld"
    p.lrcap.despacho_ons.ciclos_ano = 130          # 130/365 * 28 dias = 10 despachos
    p.validar()
    idx = indice_temporal(p)
    pld = pld_sintetico(p, idx, np.random.default_rng(p.mercado.semente)).to_numpy()
    ons = despacho_ons(p, idx, pld)
    por_dia = ons.descarga_pu.groupby(idx.normalize()).sum() / p.lrcap.duracao_h
    assert por_dia.sum() == pytest.approx(10)
    # dias despachados têm pico noturno de PLD maior que os não despachados
    noite = pd.Series(pld, index=idx)[idx.hour > max(p.lrcap.despacho_ons.janela_recarga)]
    pico = noite.groupby(noite.index.normalize()).apply(lambda x: x.rolling(4).mean().max())
    assert pico[por_dia > 0].min() >= pico[por_dia == 0].max() - 1e-9
    # sem descarga não há recarga: o módulo fica cheio
    sem = por_dia[por_dia == 0].index
    assert ons.recarga_pu[idx.normalize().isin(sem) & (ons.soc_pu.shift().fillna(0) >= ons.soc_pu.max() - 1e-9)].sum() == 0


def test_ciclos_ano_com_arquivo_e_igual_em_blocos():
    # A seleção anual não depende de como o ano é fatiado em blocos.
    from pvbess_h2.dados import montar_series
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml")
    p.lrcap.despacho_ons.ciclos_ano = 100
    p.horizonte.inicio, p.horizonte.dias = "2025-01-01 00:00", 365
    anual = montar_series(p).ons_descarga_pu
    assert anual.sum() / p.lrcap.duracao_h == pytest.approx(100)
    p.horizonte.inicio, p.horizonte.dias = "2025-03-03 00:00", 14
    bloco = montar_series(p).ons_descarga_pu
    assert np.allclose(bloco.values, anual.loc[bloco.index].values)


def test_perfil_ons_em_blocos_igual_ao_anual():
    # O módulo LRCAP não recomeça cheio em cada bloco: o recorte reproduz o perfil do ano
    # inteiro, e a recarga repõe exatamente a energia descarregada (condição cíclica).
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml")
    cols = ["ons_descarga_pu", "ons_recarga_pu", "ons_soc_pu"]
    p.horizonte.inicio, p.horizonte.dias = "2025-01-01 00:00", 365
    anual = montar_series(p)
    rte = p.bess.eficiencia_carga * p.bess.eficiencia_descarga
    assert anual.ons_recarga_pu.sum() == pytest.approx(anual.ons_descarga_pu.sum() / rte)
    for inicio, dias in [("2025-01-01 00:00", 7), ("2025-03-03 00:00", 7), ("2025-12-24 00:00", 8)]:
        p.horizonte.inicio, p.horizonte.dias = inicio, dias
        bloco = montar_series(p)
        assert np.allclose(bloco[cols].values, anual.loc[bloco.index, cols].values)
        assert bloco.ons_recarga_pu.sum() == pytest.approx(bloco.ons_descarga_pu.sum() / rte)


def test_perfil_ons_ciclico_sem_arquivo():
    p = carregar_parametros(CONFIG)
    s = montar_series(p)
    rte = p.bess.eficiencia_carga * p.bess.eficiencia_descarga
    assert s.ons_recarga_pu.sum() == pytest.approx(s.ons_descarga_pu.sum() / rte)


def test_nivel_inicial_livre():
    p_fixo, m_fixo, _, k_fixo = resolver_caso({"hidrogenio": {"entrega_min_diaria_kg": 2000.0,
                                                              "penalidade_deficit_rs_kg": 35.0}}, dias=4)
    p, m, df, k = resolver_caso({"horizonte": {"nivel_inicial_livre": True},
                                 "hidrogenio": {"entrega_min_diaria_kg": 2000.0,
                                                "penalidade_deficit_rs_kg": 35.0}}, dias=4)
    # Nível livre relaxa o nível inicial fixo
    assert k.lucro_rs >= k_fixo.lucro_rs - 1e-6
    e0, s0 = pyo.value(m.E_0), pyo.value(m.S_0)
    e_merc = pyo.value(m.E_merc)
    assert p.bess.soc_min_frac * e_merc - 1e-6 <= e0 <= p.bess.soc_max_frac * e_merc + 1e-6
    assert df.soc_mwh.iloc[-1] >= e0 - 1e-6
    assert df.tanque_h2_kg.iloc[-1] >= s0 - 1e-6


def test_fronteiras_lp():
    # Estados na fronteira dos blocos tirados da relaxação linear do horizonte inteiro: a
    # concatenação dos blocos é viável (limite inferior) e a relaxação, um limite superior.
    # Requer séries de arquivo: as sintéticas são geradas por horizonte e diferem entre o
    # bloco e o horizonte inteiro.
    from pvbess_h2.decomposicao import fronteiras_lp, operacao_anual
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml")
    p.hidrogenio.entrega_min_diaria_kg, p.hidrogenio.penalidade_deficit_rs_kg = 3000.0, 35.0
    ub, fr = fronteiras_lp(p, "2025-01-06 00:00", 14, 40.0, dias_bloco=7)
    assert len(fr) == 2
    assert fr[0][1] == pytest.approx(fr[1][0]) and fr[0][3] == pytest.approx(fr[1][2])
    _, k = operacao_anual(p, "2025-01-06 00:00", 14, 40.0, dias_bloco=7, processos=2, fronteira="lp")
    lb = k.lucro_rs - k.receita_lrcap_rs
    assert k.limite_superior_lp_rs == pytest.approx(ub, abs=1e-3)
    assert lb <= ub + 1e-6 * abs(ub)
    assert lb >= ub * (1 - 0.02)


def _limite(lim, fator=200.0, janela=24, dias=2):
    return resolver_caso({"rede": {"h2_verde_estrito": False, "fator_emissao_kg_mwh": fator},
                          "hidrogenio": {"limite_emissoes_kg_kg": lim, "janela_emissoes_h": janela}}, dias=dias)


def test_limite_emissoes_zero_equivale_ao_h2_verde_estrito():
    _, m_est, _, _ = resolver_caso({"rede": {"h2_verde_estrito": True}})
    _, m_lim, df, _ = _limite(0.0)
    assert df.p_importacao_mw.max() < 1e-6
    assert pyo.value(m_lim.lucro) == pytest.approx(pyo.value(m_est.lucro), rel=1e-3)


def test_limite_emissoes_respeitado_em_cada_janela():
    # Com 200 kg/MWh e limite de 3 kg/kg, a rede pode suprir até 3 / (0,055 x 200) = 27% da
    # energia do eletrolisador em cada dia; sem limite, a compra seria maior.
    p, m, df, kpi = _limite(3.0)
    _, m_sem, df_sem, _ = resolver_caso({"rede": {"h2_verde_estrito": False}})
    _, m_est, _, _ = resolver_caso({"rede": {"h2_verde_estrito": True}})
    assert (df.p_importacao_mw <= df.p_eletrolisador_mw + 1e-6).all()
    assert 1e-3 < df.p_importacao_mw.sum() < df_sem.p_importacao_mw.sum()
    dia = df.index.normalize()
    emis = (200.0 * df.p_importacao_mw).groupby(dia).sum()
    h2 = df.producao_h2_kg_h.groupby(dia).sum()
    assert (emis <= 3.0 * h2 + 1e-4).all()
    assert kpi.intensidade_h2_kgco2_kg <= 3.0 + 1e-6
    assert pyo.value(m_est.lucro) - 1e-3 <= pyo.value(m.lucro) <= pyo.value(m_sem.lucro) + 1e-3


def test_limite_emissoes_exige_importacao_e_fator():
    p = carregar_parametros(CONFIG)
    p.hidrogenio.limite_emissoes_kg_kg = 7.0
    with pytest.raises(AssertionError):
        p.validar()                       # h2_verde_estrito = true no caso base
    p.rede.h2_verde_estrito = False
    with pytest.raises(AssertionError):
        p.validar()                       # sem fator de emissão da rede
    p.rede.fator_emissao_kg_mwh = 40.0
    p.validar()


def test_correspondencia_temporal():
    # Janela horária: comprar e vender na mesma hora é vedado, logo equivale ao H2 verde estrito.
    _, m_est, _, _ = resolver_caso({"rede": {"h2_verde_estrito": True}})
    _, m_h, df_h, _ = resolver_caso({"rede": {"h2_verde_estrito": False},
                                     "hidrogenio": {"correspondencia_janela_h": 1}})
    assert df_h.p_importacao_mw.max() < 1e-6
    assert pyo.value(m_h.lucro) == pytest.approx(pyo.value(m_est.lucro), rel=1e-3)
    # Janela diária: compra só para o eletrolisador e limitada à exportação do mesmo dia.
    _, m_d, df, _ = resolver_caso({"rede": {"h2_verde_estrito": False},
                                   "hidrogenio": {"correspondencia_janela_h": 24}})
    _, m_sem, _, _ = resolver_caso({"rede": {"h2_verde_estrito": False}})
    assert (df.p_importacao_mw <= df.p_eletrolisador_mw + 1e-6).all()
    dia = df.index.normalize()
    assert (df.p_importacao_mw.groupby(dia).sum() <= df.p_exportacao_mw.groupby(dia).sum() + 1e-6).all()
    assert pyo.value(m_est.lucro) - 1e-3 <= pyo.value(m_d.lucro) <= pyo.value(m_sem.lucro) + 1e-3


def test_faixas_demanda_h2():
    # Uma faixa só, sem limite, ao preço de referência: igual à demanda ilimitada.
    p0, m0, df0, _ = resolver_caso()
    preco = p0.hidrogenio.preco_venda_rs_kg
    _, m1, _, _ = resolver_caso({"hidrogenio": {"faixas_demanda": [[None, preco]]}})
    assert pyo.value(m1.lucro) == pytest.approx(pyo.value(m0.lucro), rel=1e-4)
    # Duas faixas: 500 kg/dia ao preço de referência e o excedente a R$ 1/kg. A receita segue as faixas.
    _, m2, df, _ = resolver_caso({"hidrogenio": {"faixas_demanda": [[500.0, preco], [None, 1.0]]}})
    vendas = df.venda_h2_kg_h.groupby(df.index.normalize()).sum()
    esperado = sum(min(v, 500.0) * preco + max(v - 500.0, 0.0) * 1.0 for v in vendas)
    assert pyo.value(m2.receita_h2) == pytest.approx(esperado, rel=1e-4)
    assert pyo.value(m2.lucro) <= pyo.value(m0.lucro) + 1e-3


def test_precos_faixas_por_ano():
    from pvbess_h2.estocastico import parametros_cenario
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml")
    p.hidrogenio.faixas_demanda = [[2000.0, 35.0], [None, 16.0]]
    p.hidrogenio.precos_faixas_por_ano = {2022: [35.0, 19.0]}
    p.validar()
    c22, c23 = (next(c for c in p.estocastico.cenarios if c.ano == a) for a in (2022, 2023))
    assert parametros_cenario(p, c22).hidrogenio.faixas_demanda == [[2000.0, 35.0], [None, 19.0]]
    assert parametros_cenario(p, c23).hidrogenio.faixas_demanda == [[2000.0, 35.0], [None, 16.0]]
    p.hidrogenio.precos_faixas_por_ano = {2022: [10.0, 19.0]}
    with pytest.raises(AssertionError):
        p.validar()


def test_config_deterministica_igual_ao_cenario_2025():
    # config/referencia_2025.yaml é a versão determinística do caso de referência: os mesmos
    # parâmetros do cenário de 2025 de config/estocastico_unifei.yaml (o mapa de sensibilidade
    # roda nela) e, portanto, as mesmas séries horárias.
    from dataclasses import asdict
    from pvbess_h2.estocastico import parametros_cenario
    raiz = Path(__file__).resolve().parents[1]
    det = carregar_parametros(raiz / "config" / "referencia_2025.yaml")
    est = carregar_parametros(raiz / "config" / "estocastico_unifei.yaml")
    ref = parametros_cenario(est, next(c for c in est.estocastico.cenarios if c.ano == 2025))
    for secao in ("pv", "bess", "eletrolisador", "hidrogenio", "rede", "mercado", "lrcap"):
        assert asdict(getattr(det, secao)) == asdict(getattr(ref, secao)), secao
    for p in (det, ref):
        p.horizonte.inicio, p.horizonte.dias = "2025-06-02 00:00", 7
    assert np.allclose(montar_series(det).values, montar_series(ref).values)


def test_recarga_excedente_apurada_no_ano():
    # Com poucos despachos, a recarga de um despacho pode cair no bloco semanal vizinho ao da
    # descarga. O excedente sobre a recarga custeada pela CONCAP é apurado no ano civil: a soma do
    # custo dos blocos é igual ao custo do ano inteiro, e um bloco sem descarga não paga excedente.
    from pvbess_h2.decomposicao import dividir_em_blocos
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml")
    p.lrcap.despacho_ons.ciclos_ano = 50
    dt = p.horizonte.dt_h

    def custo(s):
        return float((s.ons_recarga_excedente_frac * s.pld_rs_mwh * s.ons_recarga_pu * dt).sum())

    p.horizonte.inicio, p.horizonte.dias = "2025-01-01 00:00", 365
    ano = montar_series(p)
    assert ano.ons_recarga_excedente_frac.nunique() == 1
    rte = p.bess.eficiencia_carga * p.bess.eficiencia_descarga
    assert ano.ons_recarga_pu.sum() == pytest.approx(ano.ons_descarga_pu.sum() / rte)
    assert custo(ano) == pytest.approx(0.0, abs=1e-6)       # RTE do BESS acima da de referência
    total, desbalanceados = 0.0, 0
    for inicio, dias in dividir_em_blocos("2025-01-01", 365, 7):
        p.horizonte.inicio, p.horizonte.dias = inicio, dias
        bloco = montar_series(p)
        total += custo(bloco)
        desbalanceados += bloco.ons_recarga_pu.sum() > bloco.ons_descarga_pu.sum() / p.lrcap.rte_referencia + 1e-9
    assert desbalanceados > 0                                # a apuração por bloco cobraria excedente
    assert total == pytest.approx(custo(ano), abs=1e-6)
    # O modelo usa a fração das séries: sem excedente no ano, o custo é nulo em qualquer bloco
    p.horizonte.inicio, p.horizonte.dias = "2025-01-01 00:00", 7
    p.lrcap.potencia_fixa_mw = 30.0
    m = construir_modelo(p, montar_series(p))
    assert pyo.value(m.custo_recarga_lrcap) == pytest.approx(0.0, abs=1e-6)


def test_recarga_excedente_de_arquivo_de_despacho(tmp_path):
    # Perfil de despacho lido de arquivo que cobre o ano: a fração excedente é a do ano, igual em
    # todos os blocos; com RTE de referência acima da do perfil, há excedente e ele é cobrado.
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml")
    idx = pd.date_range("2025-01-01", "2026-01-01", freq="h", inclusive="left")
    desc = np.zeros(len(idx))
    rec = np.zeros(len(idx))
    dias = np.arange(0, 365, 9)                               # um despacho a cada 9 dias, às 18 h
    for d in dias:
        desc[d * 24 + 18:d * 24 + 22] = 1.0
        rec[d * 24 + 34:d * 24 + 39] = [1.0, 1.0, 1.0, 1.0, 4 / 0.9025 - 4]   # recarga na manhã seguinte
    arq = tmp_path / "despacho.csv"
    pd.DataFrame({"timestamp": idx, "descarga_pu": desc, "recarga_pu": rec}).to_csv(arq, index=False)
    p.lrcap.despacho_ons.arquivo = str(arq)
    p.lrcap.rte_referencia = 0.95                             # acima da RTE do perfil (0,9025): há excedente
    p.bess.eficiencia_carga = p.bess.eficiencia_descarga = 0.95
    esperado = 1 - (desc.sum() / 0.95) / rec.sum()
    fracoes = set()
    for inicio in ("2025-01-01 00:00", "2025-01-08 00:00", "2025-03-05 00:00"):
        p.horizonte.inicio, p.horizonte.dias = inicio, 7
        fracoes.add(round(float(montar_series(p).ons_recarga_excedente_frac.iloc[0]), 12))
    assert fracoes == {round(esperado, 12)}


def test_receita_fixa_em_ano_bissexto():
    # A receita fixa é rateada pelas horas do ano civil: os blocos de um ano bissexto somam a receita
    # anual, e não 366/365 dela; num ano comum, uma semana vale 168/8760.
    from pvbess_h2.dados import fracao_do_ano_periodo
    from pvbess_h2.decomposicao import dividir_em_blocos
    assert fracao_do_ano_periodo("2024-01-01", 366) == pytest.approx(1.0)
    assert fracao_do_ano_periodo("2025-01-01", 365) == pytest.approx(1.0)
    assert sum(fracao_do_ano_periodo(i, d) for i, d in dividir_em_blocos("2024-01-01", 366, 7)) == pytest.approx(1.0)
    assert fracao_do_ano_periodo("2025-06-02", 7) == pytest.approx(168 / 8760)
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml")
    p.mercado.arquivo, p.pv.arquivo = "data/pld_se_2024.csv", "data/pv_itajuba_sarah3_2024.csv"
    p.rede.fator_emissao_arquivo = "data/fator_emissao_sin_2024.csv"
    p.horizonte.inicio, p.horizonte.dias = "2024-02-26 00:00", 7      # semana com o dia 29/02
    p.lrcap.potencia_fixa_mw = 40.0
    m = construir_modelo(p, montar_series(p))
    assert pyo.value(m.receita_lrcap) == pytest.approx(p.lrcap.receita_fixa_rs_mw_ano * 40.0 * 168 / 8784)


def test_corte_do_ons_reduz_a_geracao_disponivel(tmp_path):
    # O perfil de corte do ONS reduz a geração FV disponível (e não é o curtailment voluntário do modelo):
    # a série traz a potencial e a disponível, e o modelo nunca usa mais do que a disponível.
    p = carregar_parametros(CONFIG)
    sem = montar_series(p)
    idx = sem.index
    frac = np.where(idx.hour == 12, 0.4, 0.0)
    arq = tmp_path / "corte.csv"
    pd.DataFrame({"timestamp": idx, "fracao_corte": frac}).to_csv(arq, index=False)
    p.pv.corte_arquivo = str(arq)
    com = montar_series(p)
    assert np.allclose(com.pv_potencial_mw, sem.pv_disp_mw)
    assert np.allclose(com.pv_disp_mw, sem.pv_disp_mw * (1 - frac))
    p.pv.corte_fator = 3.0                          # fração limitada a 1: 3 x 0,4 -> corte total ao meio-dia
    assert np.allclose(montar_series(p).pv_disp_mw[idx.hour == 12], 0.0)
    p.pv.corte_fator = 1.0
    m = construir_modelo(p, com)
    resolver(m)
    df = serie_resultados(m, com)
    assert (df.p_pv_mw <= com.pv_disp_mw + 1e-6).all()
    assert indicadores(m, df, p)["energia_pv_cortada_ons_mwh"] == pytest.approx(
        (com.pv_potencial_mw - com.pv_disp_mw).sum() * p.horizonte.dt_h)


def test_corte_do_ons_por_cenario():
    # "{ano}" no nome do arquivo escolhe o perfil de cada cenário
    from pvbess_h2.estocastico import parametros_cenario
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml")
    p.pv.corte_arquivo = "data/ons_corte_fv_recente_{ano}.csv"
    for c in p.estocastico.cenarios:
        assert parametros_cenario(p, c).pv.corte_arquivo == f"data/ons_corte_fv_recente_{c.ano}.csv"
