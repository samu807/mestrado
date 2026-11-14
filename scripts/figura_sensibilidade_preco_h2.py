"""Figura e tabela da sensibilidade ao preço do H2 (demanda em faixas, H1).

Lê resultados/curva_oferta/sensibilidade_preco_h2/resumo_hipoteses.csv e a referência
resultados/curva_oferta/faixas_ref/resumo_h1_faixas.csv; grava a figura em docs/dissertacao/figuras
e imprime a tabela em Markdown.
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = 600_000.0  # receita fixa de referência, R$/(MW·ano)
d = pd.read_csv("resultados/curva_oferta/sensibilidade_preco_h2/resumo_hipoteses.csv").set_index("caso")
r = pd.read_csv("resultados/curva_oferta/faixas_ref/resumo_h1_faixas.csv").iloc[0]
d.loc["ref"] = {"q0_rs": r.q0_rs, "entrada_rs_mw_ano": r.receita_minima_entrada_rs_mw_ano,
                "otimo_ref_mw": r.p_otimo_ref_mw, "ultimo_mw_rs_mw_ano": r.receita_para_60mw_rs_mw_ano,
                "lucro_ref_rs": r.lucro_ref_rs}
ordem = [("preco_11_5", "11 / 5", "Piso: custo aceito pelo comprador"),
         ("preco_35_5", "35 / 5", ""), ("preco_35_11", "35 / 11", ""),
         ("preco_18_16", "18 / 16", ""), ("preco_27_16", "27 / 16", ""),
         ("ref", "35 / 16", "Referência"), ("preco_54_16", "54 / 16", ""),
         ("preco_35_24", "35 / 24", ""), ("faixas_3t", "35 / 16, até 3 t/dia", "Teto de demanda cheia maior")]

print("| Preço cheio / excedente (R$/kg) | Q(0) (R$ mi/ano) | Receita de entrada (R$ mil) | Receita para ofertar 60 MW (R$ mil) | Potência ótima (MW) | Ganho líquido (R$ mi/ano) |")
print("|---|---|---|---|---|---|")
ent = []
for k, rot, _ in ordem:
    x = d.loc[k]
    ganho = (x.lucro_ref_rs - x.q0_rs) / 1e6
    f = lambda v, n=1: f"{v:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    print(f"| {rot} | {f(x.q0_rs/1e6,2)} | {f(x.entrada_rs_mw_ano/1e3,0)} | {f(x.ultimo_mw_rs_mw_ano/1e3,0)} | {f(x.otimo_ref_mw,1)} | {f(ganho,2)} |")
    ent.append((rot, x.ultimo_mw_rs_mw_ano / 1e3, k))

fig, ax = plt.subplots(figsize=(8.2, 4.4), dpi=200)
rots = [e[0] for e in ent][::-1]; vals = [e[1] for e in ent][::-1]; ks = [e[2] for e in ent][::-1]
cores = ["#c0392b" if v > R/1e3 else ("#1f4e79" if k == "ref" else "#7f9bb5") for v, k in zip(vals, ks)]
b = ax.barh(rots, vals, color=cores)
ax.axvline(R/1e3, color="#333", ls="--", lw=1)
ax.text(R/1e3 + 8, len(rots) - 0.45, "receita fixa de referência (R$ 600 mil)", fontsize=8, va="top")
for bar, v in zip(b, vals):
    ax.text(v + 8, bar.get_y() + bar.get_height()/2, f"{v:,.0f}".replace(",", "."), va="center", fontsize=8)
ax.set_xlabel("Receita a partir da qual se oferta toda a potência (R$ mil/(MW·ano))")
ax.set_ylabel("Preço cheio / excedente (R$/kg)")
ax.set_xlim(0, 1000)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("docs/dissertacao/figuras/sensibilidade_preco_h2_faixas.png")
