"""Análise de sensibilidade da arbitragem LRCAP x MCP: fixa a potência contratada no
LRCAP em diferentes níveis e reotimiza a operação, mostrando como as receitas se
redistribuem entre capacidade, energia (MCP) e hidrogênio.

Uso:  python scripts/varredura_lrcap.py [config/caso_base.yaml] [--passos 11]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import (carregar_parametros, construir_modelo, indicadores,  # noqa: E402
                       montar_series, resolver, serie_resultados)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "caso_base.yaml"))
    ap.add_argument("--passos", type=int, default=11)
    args = ap.parse_args()

    p = carregar_parametros(args.config)
    series = montar_series(p)

    # Potência máxima viável pela reserva de energia exigida na janela
    b = p.bess
    p_cap_energia = (b.soc_max_frac - b.soc_min_frac) * b.energia_mwh * b.eficiencia_descarga / p.lrcap.duracao_h
    p_cap_max = min(b.potencia_descarga_mw, p.rede.exportacao_max_mw, p_cap_energia)

    linhas = []
    for pcap in np.linspace(0, p_cap_max, args.passos):
        p.lrcap.potencia_fixa_mw = float(pcap)
        m = construir_modelo(p, series)
        resolver(m)
        linhas.append(indicadores(m, serie_resultados(m, series), p))
        print(f"P_cap = {pcap:6.2f} MW  ->  lucro = R$ {linhas[-1]['lucro_rs']:,.0f}")

    res = pd.DataFrame(linhas)
    saida = RAIZ / "resultados" / (Path(args.config).stem + "_varredura_lrcap")
    saida.mkdir(parents=True, exist_ok=True)
    res.to_csv(saida / "varredura.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    x = res["potencia_lrcap_mw"]
    for col, rot, cor in [("receita_lrcap_rs", "Receita LRCAP", "#1f5fbf"),
                          ("receita_mcp_rs", "Receita MCP", "#e6a100"),
                          ("receita_h2_rs", "Receita H2", "#2a9d5c"),
                          ("lucro_rs", "Lucro total", "#333333")]:
        ax.plot(x, res[col] / 1e3, marker="o", label=rot, color=cor)
    ax.set_xlabel("Potência contratada no LRCAP [MW]")
    ax.set_ylabel("mil R$ no horizonte")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(saida / "varredura.png", dpi=150)
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
