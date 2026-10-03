"""Resolve o programa estocástico de dois estágios com CVaR (cenários anuais) por Benders.

Para cada beta da lista, encontra a potência ótima no LRCAP; os cortes são reaproveitados
entre os valores de beta. Depois avalia a curva de lucro esperado e CVaR em função da
potência contratada e salva tabelas e figuras em resultados/<caso>_estocastico/.

Uso:  python scripts/estocastico.py [config/estocastico_unifei.yaml] [--betas 0 0.5 1 2]
          [--alpha 0.8] [--curva 0 30 40 50 60] [--processos 4]
"""

import argparse
import copy
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia, resolver_estocastico  # noqa: E402

AZUL, LARANJA, CINZA, TINTA = "#256abf", "#d9731a", "#9a9a9a", "#1a1a1a"


def graficos(curva, p_otimo, nomes, p_min, saida):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.6))
    c = curva.sort_values("p_cap_mw")
    viavel = c[c.p_cap_mw >= p_min - 1e-6]
    zero = c[c.p_cap_mw < 1e-6]
    for n in nomes:
        ax[0].plot(viavel.p_cap_mw, viavel[f"lucro_{n}"] / 1e6, color=CINZA, lw=0.8)
        ax[0].annotate(n, (viavel.p_cap_mw.iloc[-1], viavel[f"lucro_{n}"].iloc[-1] / 1e6), xytext=(4, 0),
                       textcoords="offset points", va="center", fontsize=8, color="#555555")
    ax[0].plot(viavel.p_cap_mw, viavel.esperado_rs / 1e6, "o-", color=AZUL, lw=2, label="Lucro esperado")
    ax[0].plot(viavel.p_cap_mw, viavel.cvar_rs / 1e6, "s-", color=LARANJA, lw=2, label="CVaR (pior ano)")
    if not zero.empty:
        ax[0].plot(0, zero.esperado_rs.iloc[0] / 1e6, "o", color=AZUL)
        ax[0].plot(0, zero.cvar_rs.iloc[0] / 1e6, "s", color=LARANJA)
        ax[0].annotate("sem LRCAP", (0, zero.esperado_rs.iloc[0] / 1e6), xytext=(6, 6),
                       textcoords="offset points", fontsize=8, color="#555555")
    ax[0].axvspan(1e-3, p_min, color="#999999", alpha=0.12, lw=0, label="Inviável (0 < P < 30 MW)")
    ax[0].axvline(p_otimo, color=TINTA, lw=0.8, ls="--")
    ax[0].annotate(f"ótimo {p_otimo:.1f} MW".replace(".", ","), (p_otimo, ax[0].get_ylim()[0]), xytext=(-4, 6),
                   textcoords="offset points", ha="right", fontsize=8)
    ax[0].set_xlabel("Potência contratada no LRCAP [MW]")
    ax[0].set_ylabel("Lucro anual [R$ mi, dez/2025]")
    ax[0].set_title("(a) Lucro por ano e indicadores × potência contratada", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8, loc="upper left")

    escolhas = [(0.0, "Sem LRCAP", CINZA), (p_min, f"{p_min:g} MW (mínimo)", "#9ec5f4"),
                (p_otimo, f"{p_otimo:.1f} MW (ótimo)".replace(".", ","), AZUL), (c.p_cap_mw.max(), f"{c.p_cap_mw.max():g} MW", LARANJA)]
    x = np.arange(len(nomes))
    larg = 0.8 / len(escolhas)
    for i, (pc, rot, cor) in enumerate(escolhas):
        linha = c.iloc[(c.p_cap_mw - pc).abs().argmin()]
        ax[1].bar(x + (i - (len(escolhas) - 1) / 2) * larg, [linha[f"lucro_{n}"] / 1e6 for n in nomes],
                  width=larg * 0.92, color=cor, label=rot)
    ax[1].set_xticks(x, nomes)
    ax[1].set_xlabel("Cenário (ano histórico)")
    ax[1].set_ylabel("Lucro anual [R$ mi, dez/2025]")
    ax[1].set_title("(b) Lucro por ano para cada decisão de contratação", fontsize=10)
    ax[1].legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    for a in ax:
        a.grid(alpha=0.25, lw=0.6)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(saida / "estocastico.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--betas", type=float, nargs="+", default=[0.0, 0.5, 1.0, 2.0])
    ap.add_argument("--alpha", type=float)
    ap.add_argument("--curva", type=float, nargs="*", default=[0, 30, 40, 50, 60])
    ap.add_argument("--tol", type=float, default=1e-3)
    ap.add_argument("--so-graficos", action="store_true", help="refaz as figuras a partir dos CSVs")
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)

    base = carregar_parametros(args.config)
    if args.alpha is not None:
        base.estocastico.alpha = args.alpha
    nomes = [c.nome for c in base.estocastico.cenarios]
    saida = RAIZ / "resultados" / (Path(args.config).stem + "_estocastico")
    saida.mkdir(parents=True, exist_ok=True)

    if args.so_graficos:
        curva = pd.read_csv(saida / "curva_potencia.csv")
        p_otimo = pd.read_csv(saida / "fronteira.csv").p_cap_mw.iloc[0]
        # Ótimo refinado (tolerância menor) do cálculo do VSS/EVPI, se existir
        arq_rp = saida / "vss_evpi_decisoes.csv"
        if arq_rp.exists():
            rp = pd.read_csv(arq_rp).iloc[0]
            p_otimo = float(rp.p_cap_mw)
            linha = {"p_cap_mw": p_otimo, "esperado_rs": rp.esperado_rs, "cvar_rs": rp.cvar_rs,
                     **{f"lucro_{n}": rp[n] for n in nomes}}
            curva = pd.concat([curva[(curva.p_cap_mw - p_otimo).abs() > 1e-3], pd.DataFrame([linha])])
            curva = curva.sort_values("p_cap_mw").reset_index(drop=True)
        graficos(curva, p_otimo, nomes, base.lrcap.potencia_min_mw, saida)
        return
    memoria, linhas, historicos = {}, [], []
    for beta in args.betas:
        p = copy.deepcopy(base)
        p.estocastico.beta = beta
        print(f"\n=== beta = {beta:g}, alpha = {p.estocastico.alpha:g} ===", flush=True)
        av, hist, _ = resolver_estocastico(p, tol=args.tol, processos=args.processos, memoria=memoria)
        gap = (hist.limite_superior_rs.iloc[-1] - av.objetivo) / abs(av.objetivo)
        linhas.append({"beta": beta, "alpha": p.estocastico.alpha, "p_cap_mw": av.p_cap,
                       "esperado_rs": av.esperado, "cvar_rs": av.cvar, "objetivo_rs": av.objetivo,
                       "gap": gap, **{f"lucro_{n}": v for n, v in zip(nomes, av.lucro_cenarios)}})
        historicos.append(hist.assign(beta=beta))
        print(f"beta = {beta:g}: P_cap = {av.p_cap:.2f} MW  E = R$ {av.esperado / 1e6:.2f} mi  "
              f"CVaR = R$ {av.cvar / 1e6:.2f} mi  gap = {gap:.3%}", flush=True)

    fronteira = pd.DataFrame(linhas)
    fronteira.to_csv(saida / "fronteira.csv", index=False)
    pd.concat(historicos).to_csv(saida / "convergencia.csv", index=False)

    # Curva: pontos pedidos + pontos já avaliados pelo Benders
    probs = base.estocastico.probabilidades()
    pontos = dict(memoria["lucros"])
    for x in args.curva:
        if round(x, 6) not in pontos and (x == 0 or x >= base.lrcap.potencia_min_mw):
            print(f"curva: avaliando P_cap = {x:g} MW", flush=True)
            pontos[round(x, 6)] = avaliar_potencia(base, x, processos=args.processos).lucro_cenarios
    from pvbess_h2.estocastico import cvar
    curva = pd.DataFrame([{"p_cap_mw": x, "esperado_rs": float(np.dot(probs, v)),
                           "cvar_rs": cvar(v, probs, base.estocastico.alpha),
                           **{f"lucro_{n}": l for n, l in zip(nomes, v)}}
                          for x, v in sorted(pontos.items())])
    curva.to_csv(saida / "curva_potencia.csv", index=False)
    graficos(curva, fronteira.p_cap_mw.iloc[0], nomes, base.lrcap.potencia_min_mw, saida)
    (saida / "memoria_cortes.json").write_text(json.dumps(
        {"lucros": {str(k): v for k, v in memoria["lucros"].items()}}, indent=1))
    print("\n" + fronteira[["beta", "p_cap_mw", "esperado_rs", "cvar_rs", "gap"]].to_string(index=False))
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
