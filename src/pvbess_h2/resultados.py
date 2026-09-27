"""Extração de resultados, indicadores e gráficos."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyomo.environ as pyo

from .parametros import Parametros


def serie_resultados(m: pyo.ConcreteModel, series: pd.DataFrame) -> pd.DataFrame:
    v = lambda var: [pyo.value(var[t]) for t in m.T]  # noqa: E731
    df = series.copy()
    df["p_pv_mw"] = v(m.p_pv)
    df["curtailment_mw"] = df["pv_disp_mw"] - df["p_pv_mw"]
    df["p_carga_bess_mw"] = v(m.p_ch)
    df["p_descarga_bess_mw"] = v(m.p_dis)
    df["soc_mwh"] = v(m.soc)
    df["p_eletrolisador_mw"] = v(m.p_el)
    df["producao_h2_kg_h"] = v(m.m_h2)
    df["venda_h2_kg_h"] = v(m.v_h2)
    df["tanque_h2_kg"] = v(m.s_h2)
    df["p_exportacao_mw"] = v(m.p_exp)
    df["p_importacao_mw"] = v(m.p_imp)
    df["p_descarga_lrcap_mw"] = [pyo.value(m.p_dis_lr[t]) for t in m.T]
    df["p_recarga_lrcap_mw"] = [pyo.value(m.p_ch_lr[t]) for t in m.T]
    df["soc_lrcap_mwh"] = df["ons_soc_pu"] * pyo.value(m.P_cap)
    df["fluxo_conexao_mw"] = [pyo.value(m.fluxo_conexao[t]) for t in m.T]
    return df.round(6)


def indicadores(m: pyo.ConcreteModel, df: pd.DataFrame, p: Parametros) -> pd.Series:
    e = lambda col: df[col].sum() * p.horizonte.dt_h  # noqa: E731
    k = {
        "lucro_rs": pyo.value(m.lucro),
        "receita_mcp_rs": pyo.value(m.receita_mcp),
        "receita_h2_rs": pyo.value(m.receita_h2),
        "receita_lrcap_rs": pyo.value(m.receita_lrcap),
        "custo_importacao_rs": pyo.value(m.custo_importacao),
        "custo_h2_rs": pyo.value(m.custo_h2),
        "custo_degradacao_rs": pyo.value(m.custo_degradacao),
        "custo_recarga_lrcap_rs": pyo.value(m.custo_recarga_lrcap),
        "potencia_lrcap_mw": pyo.value(m.P_cap),
        "energia_modulo_lrcap_mwh": p.bess.energia_mwh - pyo.value(m.E_merc),
        "energia_modulo_mercantil_mwh": pyo.value(m.E_merc),
        "energia_injetada_lrcap_mwh": e("p_descarga_lrcap_mw"),
        "ciclos_completos_lrcap": df["ons_descarga_pu"].sum() * p.horizonte.dt_h / p.lrcap.duracao_h,
        "energia_pv_disponivel_mwh": e("pv_disp_mw"),
        "energia_pv_utilizada_mwh": e("p_pv_mw"),
        "curtailment_mwh": e("curtailment_mw"),
        "energia_exportada_mwh": e("p_exportacao_mw"),
        "energia_importada_mwh": e("p_importacao_mw"),
        "energia_eletrolisador_mwh": e("p_eletrolisador_mw"),
        "h2_produzido_kg": e("producao_h2_kg_h"),
        "ciclos_equivalentes_mercantil": e("p_descarga_bess_mw") / max(pyo.value(m.E_merc), 1e-9),
        "fator_capacidade_eletrolisador": df["p_eletrolisador_mw"].mean() / p.eletrolisador.potencia_max_mw,
        "preco_medio_exportacao_rs_mwh": (df["pld_rs_mwh"] * df["p_exportacao_mw"]).sum()
        / max(df["p_exportacao_mw"].sum(), 1e-9),
    }
    return pd.Series(k).round(4)


def grafico_operacao(df: pd.DataFrame, arquivo: str | Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    ax[0].plot(df.index, df["pv_disp_mw"], color="#999999", lw=1, ls="--", label="PV disponível")
    ax[0].plot(df.index, df["p_pv_mw"], color="#e6a100", lw=1.5, label="PV utilizado")
    ax[0].plot(df.index, df["p_exportacao_mw"], color="#1f5fbf", lw=1.5, label="Exportação (MCP)")
    ax[0].plot(df.index, df["p_eletrolisador_mw"], color="#2a9d5c", lw=1.5, label="Eletrolisador")
    ax[0].set_ylabel("MW")
    ax[0].legend(loc="upper right", ncol=4, fontsize=8)

    ax[1].bar(df.index, df["p_carga_bess_mw"], width=0.04, color="#2a9d5c", label="Carga mercantil")
    ax[1].bar(df.index, -df["p_descarga_bess_mw"], width=0.04, color="#c0392b", label="Descarga mercantil")
    ax[1].step(df.index, df["p_recarga_lrcap_mw"] - df["p_descarga_lrcap_mw"], where="post",
               color="#1f5fbf", lw=1.2, label="Módulo LRCAP (ONS)")
    ax1b = ax[1].twinx()
    ax1b.plot(df.index, df["soc_mwh"], color="#333333", lw=1.2, label="SOC mercantil")
    ax1b.plot(df.index, df["soc_lrcap_mwh"], color="#1f5fbf", lw=1, ls="--", label="SOC LRCAP")
    ax1b.set_ylabel("SOC [MWh]")
    ax1b.legend(loc="upper right", fontsize=8)
    ax[1].set_ylabel("BESS [MW]")
    ax[1].legend(loc="upper left", fontsize=8)

    ax[2].plot(df.index, df["tanque_h2_kg"], color="#2a9d5c", lw=1.5, label="Estoque H2")
    ax[2].set_ylabel("kg")
    ax[2].legend(loc="upper right", fontsize=8)

    ax[3].plot(df.index, df["pld_rs_mwh"], color="#333333", lw=1.2, label="PLD")
    despacho = df["ons_descarga_pu"] > 0
    ax[3].fill_between(df.index, 0, df["pld_rs_mwh"].max(), where=despacho, color="#1f5fbf",
                       alpha=0.12, step="post", label="Descarga ONS (LRCAP)")
    ax[3].set_ylabel("R$/MWh")
    ax[3].legend(loc="upper right", fontsize=8)

    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)
