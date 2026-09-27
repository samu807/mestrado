"""Resolve o problema anual por decomposição de Benders (blocos semanais) e salva
convergência, cortes, operação horária do ano e indicadores em resultados/.

Uso:  python scripts/anual_benders.py [config/itajuba_2025.yaml] [--inicio 2025-01-01]
          [--dias 365] [--dias-bloco 7] [--tol 1e-3] [--processos 4]
"""

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.decomposicao import operacao_anual, resolver_benders  # noqa: E402


def graficos(hist, cortes, r_cap, p_min, saida):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    h = hist[np.isfinite(hist.limite_superior_rs)]
    ax[0].plot(h.iteracao, h.limite_superior_rs / 1e6, "o-", color="#c0392b", label="Limite superior (mestre)")
    ax[0].plot(h.iteracao, h.limite_inferior_rs / 1e6, "s-", color="#1f5fbf", label="Limite inferior (melhor viável)")
    ax[0].xaxis.get_major_locator().set_params(integer=True)
    ax[0].set_xlabel("Iteração")
    ax[0].set_ylabel("Lucro anual [R$ mi]")
    ax[0].set_title("Convergência de Benders")
    ax[0].legend()

    # Função valor aproximada pelos cortes: R_cap*x + sum_w min_k (c_wk + lam_wk*x)
    x = np.linspace(0, cortes.p_cap_mw.max(), 400)
    env = np.zeros_like(x)
    for _, g in cortes.groupby("bloco"):
        env += np.min(g.c_rs.to_numpy()[:, None] + g.lambda_rs_mw.to_numpy()[:, None] * x[None, :], axis=0)
    ax[1].plot(x, (r_cap * x + env) / 1e6, color="#c0392b", lw=1.2, label="Aproximação por cortes (UB)")
    pts = hist.dropna(subset=["lucro_candidato_rs"]).drop_duplicates("p_cap_mw")
    ax[1].plot(pts.p_cap_mw, pts.lucro_candidato_rs / 1e6, "o", color="#1f5fbf", label="Pontos avaliados (viáveis)")
    if p_min > 0:
        ax[1].axvspan(0, p_min, color="#999999", alpha=0.15, lw=0,
                      label=f"Inviável (0 < P < {p_min:g} MW, art. 7º, III)")
    ax[1].set_xlabel("Potência contratada no LRCAP [MW]")
    ax[1].set_ylabel("Lucro anual [R$ mi]")
    ax[1].set_title("Função valor do 1º estágio")
    lo = min(pts.lucro_candidato_rs.min(), (r_cap * x + env).min()) / 1e6
    ax[1].set_ylim(lo * 0.98, (r_cap * x + env).max() / 1e6 * 1.01)
    ax[1].legend()
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(saida / "benders.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "itajuba_2025.yaml"))
    ap.add_argument("--inicio", default="2025-01-01")
    ap.add_argument("--dias", type=int, default=365)
    ap.add_argument("--dias-bloco", type=int, default=7)
    ap.add_argument("--tol", type=float, default=1e-3)
    ap.add_argument("--max-iter", type=int, default=30)
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)

    p = carregar_parametros(args.config)
    x, lucro, hist, cortes = resolver_benders(
        p, args.inicio, args.dias, args.dias_bloco, tol=args.tol,
        max_iter=args.max_iter, processos=args.processos)

    print(f"\nP_cap ótimo = {x:.3f} MW   lucro anual = R$ {lucro:,.0f}")
    df, kpi = operacao_anual(p, args.inicio, args.dias, x, args.dias_bloco, args.processos)

    saida = RAIZ / "resultados" / (Path(args.config).stem + "_benders")
    saida.mkdir(parents=True, exist_ok=True)
    tab = hist.tabela()
    tab.to_csv(saida / "convergencia.csv", index=False)
    cortes.to_csv(saida / "cortes.csv", index=False)
    df.to_csv(saida / "operacao_horaria.csv", index_label="timestamp")
    kpi.to_csv(saida / "indicadores.csv", header=["valor"])
    horas = len(df) * p.horizonte.dt_h
    graficos(tab, cortes, p.lrcap.receita_fixa_rs_mw_ano * horas / 8760.0, p.lrcap.potencia_min_mw, saida)
    print(kpi.to_string())
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
