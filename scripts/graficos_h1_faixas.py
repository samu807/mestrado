"""Gráficos e tabelas da H1 com a demanda de H2 em faixas (referência) e a comparação com a demanda ilimitada.

Lê resultados/curva_oferta/faixas_ref (curva e operação) e resultados/curva_oferta/base.csv (demanda ilimitada) e
grava em resultados/h1_faixas: curva_oferta_faixas.csv, resumo.csv e as figuras PNG.

Uso:  python scripts/graficos_h1_faixas.py [--receita 600000]
"""

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
REF = RAIZ / "resultados" / "curva_oferta" / "faixas_ref"
ILIM = RAIZ / "resultados" / "curva_oferta" / "base.csv"
SAIDA = RAIZ / "resultados" / "h1_faixas"
ANOS = [2021, 2022, 2023, 2024, 2025]
AZUL, VINHO, CINZA, OURO = "#14223A", "#8A2432", "#B8BEC8", "#C9A227"


def tabela(c: pd.DataFrame, r_ref: float) -> pd.DataFrame:
    c = c.sort_values("p_cap_mw").reset_index(drop=True)
    P, Q = c.p_cap_mw.to_numpy(), c.q_rs.to_numpy()
    t = pd.DataFrame({"p_cap_mw": P, "q_rs": Q, "perda_vs_sem_leilao_rs": Q[0] - Q})
    t["lucro_total_ref_rs"] = r_ref * P + Q
    custo_marg = np.full(len(P), np.nan)
    for i in range(1, len(P)):
        passo = P[i] - P[i - 1]
        if P[i - 1] == 0:            # o primeiro trecho é o bloco mínimo: custo médio por MW
            custo_marg[i] = (Q[0] - Q[i]) / P[i]
        else:
            custo_marg[i] = (Q[i - 1] - Q[i]) / passo
    t["custo_marginal_rs_mw_ano"] = custo_marg
    for a in ANOS:
        t[f"q_{a}"] = c[f"q_{a}"].to_numpy()
    return t


def oferta(c: pd.DataFrame, receitas: np.ndarray) -> np.ndarray:
    P, Q = c.p_cap_mw.to_numpy(), c.q_rs.to_numpy()
    return np.array([P[int(np.argmax(r * P + Q))] for r in receitas])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receita", type=float, default=600000.0)
    args = ap.parse_args()
    R = args.receita
    SAIDA.mkdir(parents=True, exist_ok=True)
    cf = pd.read_csv(REF / "base.csv")
    ci = pd.read_csv(ILIM)
    tf, ti = tabela(cf, R), tabela(ci, R)
    tf.to_csv(SAIDA / "curva_oferta_faixas.csv", index=False)
    ti.to_csv(SAIDA / "curva_oferta_ilimitada.csv", index=False)

    # 1. Lucro anual com a receita fixa, por ano e esperado
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for a in ANOS:
        ax.plot(cf.p_cap_mw[1:], (R * cf.p_cap_mw + cf[f"q_{a}"])[1:] / 1e6, color=CINZA, lw=1.5)
        ax.annotate(str(a), (60, (R * 60 + cf[f"q_{a}"].iloc[-1]) / 1e6), xytext=(4, -3), textcoords="offset points",
                    fontsize=8, color="#555D6B")
    e = (R * cf.p_cap_mw + cf.q_rs) / 1e6
    ax.plot(cf.p_cap_mw[1:], e[1:], color=VINHO, lw=2.6, label="esperado (demanda em faixas)")
    ax.plot([0, 30], [e[0], e[1]], color=VINHO, lw=1.5, ls="--")
    ax.scatter([0, 30, 60], [e[0], e[1], e.iloc[-1]], color=VINHO, zorder=3)
    ei = (R * ci.p_cap_mw + ci.q_rs) / 1e6
    ax.plot(ci.p_cap_mw[1:], ei[1:], color=AZUL, lw=1.8, ls=":", label="esperado (demanda ilimitada)")
    ax.axvspan(0, 30, color="#EFEDE7", zorder=0)
    ax.set_xlabel("Potência contratada no LRCAP [MW]")
    ax.set_ylabel("Lucro anual com receita fixa [R$ milhões]")
    ax.set_title(f"Lucro esperado com receita fixa de R$ {R / 1e3:.0f} mil/(MW·ano)", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(SAIDA / "lucro_x_potencia.png", dpi=150); plt.close(fig)

    # 2. Custo marginal (escada) e curva de oferta
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    for t, cor, rot, ls in ((tf, VINHO, "demanda em faixas", "-"), (ti, AZUL, "demanda ilimitada", ":")):
        v = t[(t.p_cap_mw >= 30)].copy()
        ax[0].step(v.p_cap_mw, v.custo_marginal_rs_mw_ano / 1e3, where="pre", color=cor, lw=2, ls=ls, label=rot)
    ax[0].axhline(R / 1e3, color="#9a9a9a", lw=0.8, ls="--")
    ax[0].annotate(f"R = R$ {R / 1e3:.0f} mil", (31, R / 1e3), xytext=(0, 4), textcoords="offset points", fontsize=8)
    ax[0].set_xlabel("Potência contratada [MW]"); ax[0].set_ylabel("Custo marginal [R$ mil/(MW·ano)]")
    ax[0].set_title("Custo marginal de contratar mais um degrau de 2,5 MW", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8)
    rec = np.arange(0, 1_000_001, 5_000)
    for c, cor, rot, ls in ((cf, VINHO, "demanda em faixas", "-"), (ci, AZUL, "demanda ilimitada", ":")):
        ax[1].step(rec / 1e3, oferta(c, rec), where="post", color=cor, lw=2, ls=ls, label=rot)
    ax[1].axvline(R / 1e3, color="#9a9a9a", lw=0.8, ls="--")
    ax[1].set_xlabel("Receita fixa [R$ mil/(MW·ano)]"); ax[1].set_ylabel("Potência ótima a ofertar [MW]")
    ax[1].set_title("Curva de oferta", fontsize=10)
    ax[1].legend(frameon=False, fontsize=8, loc="lower right")
    for a in ax:
        a.grid(alpha=0.25); a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(SAIDA / "custo_marginal_e_oferta.png", dpi=150); plt.close(fig)

    # 3. Operação: dia 06/08/2025 sem leilão e com 60 MW
    fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for a, p in zip(ax, (0, 60)):
        arq = REF / f"op_{p}MW_2025.csv"
        if not arq.exists():
            a.set_title(f"{p} MW: operação ainda não calculada"); continue
        d = pd.read_csv(arq, parse_dates=["timestamp"], index_col="timestamp").loc["2025-08-06"]
        h = d.index.hour
        el_b = d.p_descarga_bess_mw.clip(upper=d.p_eletrolisador_mw)
        el_pv = (d.p_eletrolisador_mw - el_b).clip(lower=0)
        base = np.zeros(len(d))
        for serie, cor, rot in ((el_pv, AZUL, "eletrolisador, direto da FV"), (el_b, VINHO, "eletrolisador, pela bateria"),
                                (d.p_carga_bess_mw, OURO, "carga da bateria mercantil"),
                                (d.p_exportacao_mw.clip(lower=0), "#8C95A3", "exportação ao MCP")):
            a.bar(h, serie, bottom=base, color=cor, label=rot, width=0.85); base = base + serie.to_numpy()
        if p:
            for col, cor, rot in (("p_recarga_lrcap_mw", "#4A5D7E", "recarga LRCAP (ONS)"),
                                  ("p_descarga_lrcap_mw", "#D9A8A0", "descarga LRCAP (ONS)")):
                a.plot(h, d[col], color=cor, lw=2, drawstyle="steps-mid", label=rot)
        a.set_title(("Sem leilão" if p == 0 else f"{p} MW no leilão") + " — 06/08/2025", fontsize=10)
        a.set_ylabel("MW"); a.set_ylim(0, 88); a.grid(alpha=0.25)
        a.legend(frameon=False, fontsize=7, ncol=3, loc="upper left")
    ax[1].set_xlabel("Hora do dia")
    fig.tight_layout(); fig.savefig(SAIDA / "operacao_dia_2025_08_06.png", dpi=150); plt.close(fig)

    # 4. Resumo numérico
    linhas = []
    for nome, c, t in (("faixas", cf, tf), ("ilimitada", ci, ti)):
        P, Q = c.sort_values("p_cap_mw").p_cap_mw.to_numpy(), c.sort_values("p_cap_mw").q_rs.to_numpy()
        v = t[t.p_cap_mw > 0]
        linhas.append({"demanda": nome, "q0_sem_leilao_rs": Q[0],
                       "entrada_rs_mw_ano": float(((Q[0] - Q[1:]) / P[1:]).min()),
                       "otimo_ref_mw": float(oferta(c, np.array([R]))[0]),
                       "lucro_ref_rs": float((R * P + Q).max()),
                       "ganho_liquido_ref_rs": float((R * P + Q).max() - Q[0]),
                       "custo_marginal_ultimo_mw_rs_mw_ano": float((Q[-2] - Q[-1]) / (P[-1] - P[-2])),
                       "receita_para_ofertar_tudo_rs_mw_ano": float(((Q[:-1] - Q[-1]) / (P[-1] - P[:-1])).max())})
    pd.DataFrame(linhas).to_csv(SAIDA / "resumo.csv", index=False)
    for p in (0, 60):
        arq = REF / f"resumo_op_{p}MW.csv"
        if arq.exists():
            d = pd.read_csv(arq).astype({"ano": object})
            media = d.drop(columns="ano").mean().to_frame().T.assign(ano="média")
            pd.concat([d, media], ignore_index=True).to_csv(SAIDA / f"operacao_{p}MW_por_ano.csv", index=False)
    print(pd.DataFrame(linhas).T.to_string())


if __name__ == "__main__":
    main()
