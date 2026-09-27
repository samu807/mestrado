"""Mapa de sensibilidade: receita fixa do LRCAP x preço do H2.

Para cada combinação da grade, resolve o problema anual por Benders e registra a
potência ótima no LRCAP, o lucro, a produção de H2 e o arrependimento de contratar uma
potência de referência fixa (lucro ótimo - lucro com P_ref).

Cada célula é gravada ao terminar (resultados/<caso>_mapa/mapa.csv); rodar de novo
retoma de onde parou. Com --so-graficos, apenas refaz as figuras a partir do CSV.

Uso:  python scripts/mapa_sensibilidade.py [config/unifei_escalonada.yaml] [--p-ref 54.44]
"""

import argparse
import copy
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.decomposicao import operacao_anual, resolver_benders  # noqa: E402

RECEITAS = [330e3, 600e3, 830e3, 1.0e6, 1.5e6, 2.334e6]      # R$/MW.ano
PRECOS_H2 = [10, 15, 20, 25, 30, 35, 40, 45]                  # R$/kg
ROTULO_RF = {330e3: "330 mil\n(MACSE)", 600e3: "600 mil", 830e3: "830 mil\n(térmica exist.)",
             1.0e6: "1,0 mi", 1.5e6: "1,5 mi\n(custo bateria)", 2.334e6: "2,33 mi\n(térmica nova)"}

# Rampa sequencial azul (claro = baixo, escuro = alto)
AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def rodar(cfg, p_ref, inicio, dias, processos, arq):
    feitos = pd.read_csv(arq) if arq.exists() else pd.DataFrame()
    base = carregar_parametros(cfg)
    t0 = time.time()
    total = len(RECEITAS) * len(PRECOS_H2)
    for rf in RECEITAS:
        for h2 in PRECOS_H2:
            if not feitos.empty and ((feitos.receita_fixa == rf) & (feitos.preco_h2 == h2)).any():
                continue
            p = copy.deepcopy(base)
            p.lrcap.receita_fixa_rs_mw_ano = rf
            p.hidrogenio.preco_venda_rs_kg = h2
            x, lucro, hist, _ = resolver_benders(p, inicio, dias, processos=processos, verbose=False)
            tab = hist.tabela()
            _, kpi = operacao_anual(p, inicio, dias, x, processos=processos)
            _, kpi_ref = operacao_anual(p, inicio, dias, p_ref, processos=processos)
            linha = {
                "receita_fixa": rf, "preco_h2": h2, "p_cap_otimo_mw": x, "lucro_rs": lucro,
                "gap": (tab.limite_superior_rs.iloc[-1] - lucro) / abs(lucro),
                "iteracoes": int(tab.iteracao.max()),
                "h2_t": kpi.h2_produzido_kg / 1e3,
                "fc_eletrolisador": kpi.fator_capacidade_eletrolisador,
                "receita_mcp_rs": kpi.receita_mcp_rs, "receita_h2_rs": kpi.receita_h2_rs,
                "receita_lrcap_rs": kpi.receita_lrcap_rs,
                "lucro_p_ref_rs": kpi_ref.lucro_rs, "arrependimento_rs": lucro - kpi_ref.lucro_rs,
            }
            feitos = pd.concat([feitos, pd.DataFrame([linha])], ignore_index=True)
            feitos.to_csv(arq, index=False)
            print(f"[{len(feitos):2d}/{total}] RF {rf / 1e3:6.0f} mil  H2 {h2:2d} R$/kg -> "
                  f"P_cap {x:5.1f} MW  lucro R$ {lucro / 1e6:6.2f} mi  gap {linha['gap']:.2%}  "
                  f"[{time.time() - t0:5.0f} s]", flush=True)
    return feitos


def _heatmap(ax, z, titulo, fmt, rotulo_barra, vmin=None, vmax=None, destaque=None):
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("azul", AZUL)
    im = ax.imshow(z, cmap=cmap, origin="lower", aspect="auto", vmin=vmin, vmax=vmax)
    lim = (np.nanmin(z) + np.nanmax(z)) / 2 if vmin is None else (vmin + vmax) / 2
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            if np.isfinite(z[i, j]):
                ax.text(j, i, fmt(z[i, j]), ha="center", va="center", fontsize=9,
                        color="#ffffff" if z[i, j] > lim else "#1a1a1a")
    if destaque is not None:
        i, j = destaque
        ax.add_patch(__import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle(
            (j - 0.5, i - 0.5), 1, 1, fill=False, ec="#1a1a1a", lw=2))
    ax.set_xticks(range(len(PRECOS_H2)), [str(v) for v in PRECOS_H2])
    ax.set_yticks(range(len(RECEITAS)), [ROTULO_RF[r] for r in RECEITAS], fontsize=8)
    ax.set_xlabel("Preço do H₂ [R$/kg]")
    ax.set_ylabel("Receita fixa do LRCAP [R$/MW·ano]")
    ax.set_title(titulo)
    cb = ax.figure.colorbar(im, ax=ax, shrink=0.85)
    cb.set_label(rotulo_barra)
    cb.outline.set_visible(False)
    for s in ax.spines.values():
        s.set_visible(False)


def graficos(df, p_ref, saida):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def grade(col):
        z = np.full((len(RECEITAS), len(PRECOS_H2)), np.nan)
        for _, r in df.iterrows():
            z[RECEITAS.index(r.receita_fixa), PRECOS_H2.index(int(r.preco_h2))] = r[col]
        return z

    ref = (RECEITAS.index(600e3), PRECOS_H2.index(35))
    fig, ax = plt.subplots(1, 2, figsize=(15, 5.8))
    _heatmap(ax[0], grade("p_cap_otimo_mw"), "Potência ótima no LRCAP", lambda v: f"{v:.0f}",
             "MW", vmin=0, vmax=60, destaque=ref)
    _heatmap(ax[1], grade("lucro_rs") / 1e6, "Lucro anual no ótimo", lambda v: f"{v:.0f}",
             "R$ mi/ano", destaque=ref)
    fig.text(0.01, 0.01, "Quadro destacado: cenário atual (R$ 600 mil/MW·ano; H₂ a R$ 35/kg). "
             "Potência 0 = não participa; mínimo de 30 MW (Portaria MME 136/2026, art. 7º, III).",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(saida / "mapa_potencia_lucro.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.8))
    _heatmap(ax, grade("arrependimento_rs") / 1e6, f"Arrependimento de contratar {p_ref:.1f} MW",
             lambda v: f"{v:.1f}", "R$ mi/ano perdidos vs. o ótimo", vmin=0, destaque=ref,
             vmax=max(np.nanmax(grade("arrependimento_rs") / 1e6), 1e-6))
    fig.tight_layout()
    fig.savefig(saida / "mapa_arrependimento.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "unifei_escalonada.yaml"))
    ap.add_argument("--p-ref", type=float, default=54.44, help="potência de referência para o arrependimento [MW]")
    ap.add_argument("--inicio", default="2025-01-01")
    ap.add_argument("--dias", type=int, default=365)
    ap.add_argument("--processos", type=int, default=4)
    ap.add_argument("--so-graficos", action="store_true")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)

    saida = RAIZ / "resultados" / (Path(args.config).stem + "_mapa")
    saida.mkdir(parents=True, exist_ok=True)
    arq = saida / "mapa.csv"
    df = pd.read_csv(arq) if args.so_graficos else rodar(args.config, args.p_ref, args.inicio,
                                                          args.dias, args.processos, arq)
    graficos(df, args.p_ref, saida)
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
