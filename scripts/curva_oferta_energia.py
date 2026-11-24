"""Curva de oferta Q(P) da H1 (demanda em faixas) para uma capacidade de energia da bateria diferente da referência.

A potência contratada máxima passa a ser min(potência da bateria, E / rho). Salva resultados/curva_oferta/<subdir>/E<energia>.csv
com as mesmas colunas de faixas_2t.csv, para comparar com a bateria de 300 MWh.

Uso:  python scripts/curva_oferta_energia.py config/estocastico_unifei_faixas.yaml --energia 200 [--passo 2.5] [--processos 4]
"""

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia  # noqa: E402
from pvbess_h2.modelo import potencia_lrcap_max  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--energia", type=float, required=True)
    ap.add_argument("--passo", type=float, default=2.5)
    ap.add_argument("--processos", type=int, default=4)
    ap.add_argument("--subdir", default="curva_oferta/dimensionamento_bess")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    saida = RAIZ / "resultados" / args.subdir
    saida.mkdir(parents=True, exist_ok=True)
    p = carregar_parametros(args.config)
    p.lrcap.receita_fixa_rs_mw_ano = 0.0
    p.bess.energia_mwh = args.energia
    p.validar()
    pmax = potencia_lrcap_max(p)
    grade = [0.0] + [float(x) for x in np.arange(p.lrcap.potencia_min_mw, pmax + 1e-6, args.passo)]
    if abs(grade[-1] - pmax) > 1e-6:
        grade.append(float(pmax))
    print(f"E = {args.energia:g} MWh: potência máxima {pmax:.2f} MW; grade {grade}", flush=True)
    arq = saida / f"curva_E{args.energia:g}.csv"
    parcial = saida / f"curva_E{args.energia:g}_parcial.csv"
    linhas = pd.read_csv(parcial).to_dict("records") if parcial.exists() else []
    feitos = {round(r["p_cap_mw"], 6) for r in linhas}
    for x in grade:
        if round(x, 6) in feitos:
            continue
        av = avaliar_potencia(p, x, processos=args.processos)
        linhas.append({"p_cap_mw": x, "q_rs": av.esperado,
                       **{f"q_{c.nome}": v for c, v in zip(p.estocastico.cenarios, av.lucro_cenarios)}})
        print(f"P = {x:5.2f} MW  Q = R$ {av.esperado / 1e6:7.3f} mi", flush=True)
        pd.DataFrame(linhas).to_csv(parcial, index=False)
    pd.DataFrame(linhas).sort_values("p_cap_mw").to_csv(arq, index=False)
    parcial.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
