"""Figura e tabelas da sensibilidade ao preço do H2 (demanda em faixas, H1).

Custo marginal do último MW em cada trecho da curva Q(P) (grade comum de 0, 30, 40, 50, 55, 57,5 e 60 MW),
potência ótima para diferentes receitas fixas e limiar do preço do excedente. Lê
resultados/curva_oferta/{sensibilidade_preco_h2,sensibilidade_limiar_h2,faixas_2t.csv}.
"""
import glob
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GRADE = [0.0, 30.0, 40.0, 50.0, 55.0, 57.5, 60.0]
RECEITAS = (200e3, 300e3, 400e3, 500e3, 600e3)
casos = {}
for sub in ("sensibilidade_preco_h2", "sensibilidade_limiar_h2"):
    for f in glob.glob(f"resultados/curva_oferta/{sub}/*.csv"):
        if "resumo" in f:
            continue
        casos[os.path.basename(f)[:-4]] = pd.read_csv(f)
casos["ref"] = pd.read_csv("resultados/curva_oferta/faixas_2t.csv")
q = {}
for k, d in casos.items():
    d = d.set_index("p_cap_mw").q_rs
    q[k] = np.array([d.loc[p] for p in GRADE])  # exige que todo ponto da grade exista

def marg(k):  # custo marginal médio de cada trecho, R$ mil/(MW·ano)
    Q = q[k]; P = np.array(GRADE)
    return (Q[:-1] - Q[1:]) / np.diff(P) / 1e3

def p_otimo(k, R):
    return GRADE[int(np.argmax(R * np.array(GRADE) + q[k]))]

rot = {"preco_11_5": "11 / 5", "preco_35_5": "35 / 5", "preco_35_11": "35 / 11", "ref": "35 / 16 (referência)",
       "preco_35_24": "35 / 24", "preco_35_26": "35 / 26", "preco_35_28": "35 / 28", "preco_18_16": "18 / 16",
       "preco_27_16": "27 / 16", "preco_54_16": "54 / 16", "faixas_3t": "35 / 16, até 3 t/dia"}
ordem = ["preco_11_5", "preco_35_5", "preco_35_11", "preco_18_16", "preco_27_16", "ref", "preco_54_16",
         "preco_35_24", "preco_35_26", "preco_35_28", "faixas_3t"]
ordem = [k for k in ordem if k in q]

print("| Preço cheio / excedente (R$/kg) | " + " | ".join(f"R$ {int(R/1e3)} mil" for R in RECEITAS) + " |")
print("|---|" + "---|" * len(RECEITAS))
for k in ordem:
    print(f"| {rot[k]} | " + " | ".join(str(p_otimo(k, R)).replace(".", ",") for R in RECEITAS) + " |")
print()
for k in ordem:
    print(f"{rot[k]:22s} trechos:", [round(x) for x in marg(k)], " último:", round(marg(k)[-1]))

fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), dpi=200, sharey=True)
trechos = np.array(GRADE)
def degrau(ax, k, cor, ls="-", lw=2):
    m = marg(k)
    ax.step(trechos, np.append(m, m[-1]), where="post", color=cor, ls=ls, lw=lw, label=rot[k])
exc = [("preco_35_5", "#9ecae1"), ("preco_35_11", "#6baed6"), ("ref", "#14223A"), ("preco_35_24", "#e08214"),
       ("preco_35_26", "#c0392b"), ("preco_35_28", "#7f0000")]
for k, c in exc:
    if k in q:
        degrau(axs[0], k, c, lw=3 if k == "ref" else 1.8)
axs[0].set_title("Preço do excedente (preço cheio de R$ 35/kg)", fontsize=10)
for k, c, ls in (("preco_18_16", "#7f9bb5", "-"), ("preco_27_16", "#4a6f8f", "--"), ("ref", "#14223A", "-"),
                 ("preco_54_16", "#2c3e50", ":"), ("faixas_3t", "#c0392b", "-")):
    degrau(axs[1], k, c, ls, 3 if k == "ref" else 1.8)
axs[1].set_title("Preço cheio (excedente de R$ 16/kg) e teto de 3 t/dia", fontsize=10)
for ax in axs:
    ax.axhline(600, color="#333", ls="--", lw=1)
    ax.set_xlabel("Potência contratada no LRCAP (MW)")
    ax.legend(fontsize=7.5, loc="upper left", frameon=False, title="cheio / excedente (R$/kg)", title_fontsize=7.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(30, 60); ax.set_ylim(0, 1000)
axs[0].set_ylabel("Custo marginal do trecho (R$ mil/(MW·ano))")
axs[0].text(60, 612, "receita fixa de R$ 600 mil", fontsize=7.5, ha="right", va="bottom")
plt.tight_layout()
plt.savefig("docs/dissertacao/figuras/sensibilidade_preco_h2_faixas.png")
