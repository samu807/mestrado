"""Resolve um caso e salva série horária, indicadores e gráfico em resultados/.

Uso:  python scripts/rodar_caso.py [config/caso_base.yaml] [--verbose]
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import (carregar_parametros, construir_modelo, grafico_operacao,  # noqa: E402
                       indicadores, montar_series, resolver, serie_resultados)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "caso_base.yaml"))
    ap.add_argument("--solver", default="appsi_highs")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    p = carregar_parametros(args.config)
    series = montar_series(p)
    m = construir_modelo(p, series)
    resolver(m, solver=args.solver, verbose=args.verbose)

    df = serie_resultados(m, series)
    kpi = indicadores(m, df, p)

    saida = RAIZ / "resultados" / Path(args.config).stem
    saida.mkdir(parents=True, exist_ok=True)
    df.to_csv(saida / "operacao_horaria.csv", index_label="timestamp")
    kpi.to_csv(saida / "indicadores.csv", header=["valor"])
    grafico_operacao(df, saida / "operacao.png")

    print(kpi.to_string())
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
