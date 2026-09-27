"""Converte arquivos brutos da CCEE (PLD horário) e do PVGIS (geração PV horária) para
os CSVs de entrada do modelo, em data/.

Uso:
  python scripts/importar_dados.py --pld data/brutos/pld_horario_2025.csv --submercado SE \
      --pv data/brutos/pvgis_itajuba_2023.csv --ano 2025

Gera data/pld_<submercado>_<ano>.csv e data/pv_itajuba_<ano>.csv (nome ajustável com --local).
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2.importacao import importar_pld_ccee, importar_pvgis  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pld", help="CSV anual de PLD horário da CCEE")
    ap.add_argument("--submercado", default="SE")
    ap.add_argument("--pv", help="CSV ou JSON horário do PVGIS (potência para 1 kWp)")
    ap.add_argument("--kwp", type=float, default=1.0, help="potência pico usada no PVGIS [kWp]")
    ap.add_argument("--ano", type=int, required=True, help="ano de destino das séries")
    ap.add_argument("--local", default="itajuba")
    args = ap.parse_args()

    destino = RAIZ / "data"
    if args.pld:
        pld = importar_pld_ccee(args.pld, args.submercado)
        pld = pld[pld.timestamp.dt.year == args.ano]
        saida = destino / f"pld_{args.submercado.lower()}_{args.ano}.csv"
        pld.to_csv(saida, index=False)
        print(f"PLD: {len(pld)} horas, média R$ {pld.pld.mean():.2f}/MWh, "
              f"mín {pld.pld.min():.2f}, máx {pld.pld.max():.2f} -> {saida}")
    if args.pv:
        pv = importar_pvgis(args.pv, kwp=args.kwp, ano_destino=args.ano)
        saida = destino / f"pv_{args.local}_{args.ano}.csv"
        pv.to_csv(saida, index=False)
        print(f"PV: {len(pv)} horas, fator de capacidade médio {pv.fator_capacidade.mean():.3f} -> {saida}")


if __name__ == "__main__":
    main()
