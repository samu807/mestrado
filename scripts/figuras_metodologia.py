"""Gera as figuras do capítulo de metodologia em docs/dissertacao/figuras/.

Uso:  python scripts/figuras_metodologia.py
"""

import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "dissertacao" / "figuras"

TINTA = "#1a1a1a"
TINTA_2 = "#555555"
AZUL = "#256abf"
LARANJA = "#d9731a"
VERDE = "#2a8a57"
CINZA = "#8c8c8c"
FUNDO = {"mercantil": "#eef4fc", "lrcap": "#fdf1e6", "rede": "#f2f2f2"}

plt.rcParams.update({"font.family": "serif", "font.serif": ["DejaVu Serif"], "font.size": 10})


def _caixa(ax, x, y, w, h, texto, cor=TINTA, fundo="#ffffff", peso="normal", tam=11.5):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fundo, ec=cor, lw=1.3))
    ax.text(x, y, texto, ha="center", va="center", color=TINTA, fontsize=tam, fontweight=peso)


def _seta(ax, p0, p1, cor=TINTA_2, estilo="-|>", ls="-", dupla=False, rot=None, rot_pos=0.5, dy=0.12):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="<|-|>" if dupla else estilo, mutation_scale=11,
                                 color=cor, lw=1.2, ls=ls, shrinkA=2, shrinkB=2))
    if rot:
        xm = p0[0] + (p1[0] - p0[0]) * rot_pos
        ym = p0[1] + (p1[1] - p0[1]) * rot_pos
        ax.text(xm, ym + dy, rot, ha="center", va="bottom", fontsize=10, color=TINTA_2)


def topologia():
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.6)
    ax.axis("off")

    # Regiões
    ax.add_patch(FancyBboxPatch((0.2, 2.35), 6.6, 3.05, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=FUNDO["mercantil"], ec="none"))
    ax.text(0.4, 5.15, "Lado mercantil — operado pelo empreendedor", fontsize=11, color=AZUL, fontweight="bold")
    ax.add_patch(FancyBboxPatch((0.2, 0.25), 6.6, 1.75, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=FUNDO["lrcap"], ec="none"))
    ax.text(0.4, 1.75, "Módulo LRCAP — despachado pelo ONS", fontsize=11, color=LARANJA, fontweight="bold")

    _caixa(ax, 1.3, 4.35, 1.6, 0.7, "Usina FV\n$p^{pv}_t \\leq \\bar P^{pv}_t$", cor=AZUL)
    _caixa(ax, 1.3, 3.0, 1.6, 0.7, "BESS mercantil\n$E^{m} = E^{tot} - \\rho P^{cap}$", cor=AZUL)
    _caixa(ax, 3.55, 3.7, 1.3, 1.9, "Barramento\n(balanço de\npotência)", cor=AZUL)
    _caixa(ax, 5.75, 4.35, 1.7, 0.7, "Eletrolisador PEM\n$p^{el}_t,\\ z_t$", cor=VERDE)
    _caixa(ax, 5.75, 3.25, 1.7, 0.7, "Tanque de H$_2$\n$s_t$  →  venda $v_t$", cor=VERDE)
    _caixa(ax, 2.2, 1.0, 2.6, 0.75, "BESS módulo LRCAP\n$p^{dis,lr}_t=\\delta_t P^{cap}$,  $p^{ch,lr}_t=r_t P^{cap}$",
           cor=LARANJA)
    _caixa(ax, 8.35, 2.2, 1.9, 1.2, "Ponto de conexão\ncompartilhado\n$-\\bar P^{imp} \\leq f_t \\leq \\bar P^{exp}$",
           cor=TINTA, fundo=FUNDO["rede"])
    _caixa(ax, 8.35, 4.6, 1.9, 0.75, "SIN\nMCP (PLD $\\lambda_t$)", cor=TINTA, fundo=FUNDO["rede"])

    _seta(ax, (2.1, 4.35), (2.9, 4.2), cor=AZUL)
    _seta(ax, (2.1, 3.0), (2.9, 3.2), cor=AZUL, dupla=True)
    _seta(ax, (4.2, 4.2), (4.9, 4.35), cor=VERDE)
    _seta(ax, (5.75, 4.0), (5.75, 3.6), cor=VERDE)
    ax.text(5.85, 3.8, "$m_t$", fontsize=10, color=TINTA_2, va="center")
    _seta(ax, (4.2, 2.85), (7.4, 2.4), cor=AZUL, dupla=True)
    ax.text(6.3, 2.45, "$p^{exp}_t,\\ p^{imp}_t$", fontsize=10, color=TINTA_2, ha="center", va="top")
    _seta(ax, (3.5, 1.0), (7.4, 1.95), cor=LARANJA, dupla=True, rot="despacho do ONS", rot_pos=0.7, dy=-0.45)
    _seta(ax, (8.35, 2.8), (8.35, 4.22), cor=TINTA, dupla=True)
    ax.text(8.35, 0.95, "Receita fixa $R^{cap}P^{cap}$\n(energia liquidada na CONCAP)", ha="center",
            fontsize=10, color=LARANJA)

    fig.tight_layout()
    fig.savefig(SAIDA / "fig_topologia.png", dpi=200)
    plt.close(fig)


def perfis_entrada():
    pld = pd.read_csv(RAIZ / "data" / "pld_se_2025.csv", parse_dates=["timestamp"]).set_index("timestamp").pld
    pv = pd.read_csv(RAIZ / "data" / "pv_itajuba_2025.csv", parse_dates=["timestamp"]).set_index(
        "timestamp").fator_capacidade
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    umido = pld[pld.index.month.isin([1, 2, 3, 4, 12])]
    seco = pld[pld.index.month.isin([5, 6, 7, 8, 9, 10, 11])]
    ax[0].plot(range(24), umido.groupby(umido.index.hour).mean(), color=AZUL, lw=2, label="Dez–abr (úmido)")
    ax[0].plot(range(24), seco.groupby(seco.index.hour).mean(), color=LARANJA, lw=2, label="Mai–nov (seco)")
    ax[0].set_xlabel("Hora do dia")
    ax[0].set_ylabel("PLD médio [R$/MWh]")
    ax[0].set_title("(a) PLD horário médio — SE/CO, 2025", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8)
    ax[1].plot(range(24), pv.groupby(pv.index.hour).mean(), color=AZUL, lw=2)
    ax[1].set_xlabel("Hora do dia")
    ax[1].set_ylabel("Fator de capacidade médio [–]")
    ax[1].set_title("(b) Geração FV por kWp — Itajubá", fontsize=10)
    for a in ax:
        a.set_xticks(range(0, 24, 3))
        a.grid(alpha=0.25, lw=0.6)
        a.spines[["top", "right"]].set_visible(False)
        a.set_xlim(0, 23)
    ax[1].set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(SAIDA / "fig_perfis_entrada.png", dpi=200)
    plt.close(fig)


def fluxograma_benders():
    fig, ax = plt.subplots(figsize=(8.5, 8.4))
    ax.set_xlim(-1.3, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    w = 8.6
    passos = [
        (9.3, "Início: pontos iniciais  $\\hat x \\in \\{0,\\ \\underline{P}^{cap},\\ \\bar P^{cap}\\}$", "#ffffff"),
        (7.75, "Subproblemas (em paralelo, para cada bloco $w$):\n"
               "1) MILP com $P^{cap}=\\hat x$  →  $Q_w(\\hat x)$  (solução viável)\n"
               "2) LP relaxado  →  dual $\\lambda_w$ da restrição de cópia\n"
               "3) MILP lagrangiano  →  limite dual $C_w(\\lambda_w)$", FUNDO["mercantil"]),
        (6.05, "Limite inferior:  $LB = \\max\\{LB,\\ R^{cap}(H/8760)\\hat x + \\sum_w Q_w(\\hat x)\\}$\n"
               "Novos cortes:  $\\theta_w \\leq C_w(\\lambda_w) + \\lambda_w P$", "#ffffff"),
        (4.5, "Problema mestre (MILP pequeno):\n"
              "$\\max\\ R^{cap}(H/8760)P + \\sum_w \\theta_w$  s.a. cortes,  "
              "$\\underline{P}^{cap}w \\leq P \\leq \\bar P^{cap}w$\n→  novo $\\hat x$ e limite superior $UB$",
        FUNDO["lrcap"]),
    ]
    for y, t, f in passos:
        _caixa(ax, 5.3, y, w, 1.25 if "\n" in t else 0.6, t, fundo=f, tam=12)
    for y0, y1 in [(9.0, 8.4), (7.1, 6.7), (5.4, 5.15)]:
        _seta(ax, (5.3, y0), (5.3, y1))
    # Decisão
    ax.add_patch(plt.Polygon([(5.3, 3.4), (7.5, 2.7), (5.3, 2.0), (3.1, 2.7)], fc="#ffffff", ec=TINTA, lw=1.3))
    ax.text(5.3, 2.7, "$(UB-LB)/LB \\leq \\varepsilon$ ?", ha="center", va="center", fontsize=12.5)
    _seta(ax, (5.3, 3.85), (5.3, 3.42))
    _caixa(ax, 5.3, 0.9, 5.6, 0.7, "Fim: $P^{cap}$ ótimo com certificado de gap", fundo=FUNDO["rede"], tam=12)
    _seta(ax, (5.3, 2.0), (5.3, 1.27))
    ax.text(5.45, 1.63, "sim", fontsize=11, color=TINTA_2, va="center")
    ax.plot([3.1, 0.55, 0.55], [2.7, 2.7, 7.75], color=TINTA_2, lw=1.2)
    _seta(ax, (0.55, 7.75), (0.98, 7.75))
    ax.text(0.45, 5.2, "não: avaliar\no novo $\\hat x$", ha="right", va="center", fontsize=11, color=TINTA_2)
    fig.tight_layout()
    fig.savefig(SAIDA / "fig_fluxograma_benders.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    topologia()
    perfis_entrada()
    fluxograma_benders()
    print("Figuras em", SAIDA, file=sys.stderr)
