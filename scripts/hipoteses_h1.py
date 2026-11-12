"""Hipóteses da H1 sobre a curva de oferta, uma por vez, contra o caso de referência com demanda de H2 em faixas.

Para cada caso (os de scripts/curva_oferta.py aplicados à configuração dada), avalia o lucro operacional esperado
Q(P) numa grade de potências e resume: a receita mínima de entrada, a potência ótima com a receita de referência e o
custo marginal do último MW (entre 57,5 e 60 MW). A grade é grosseira e refinada em torno do ótimo, em passos de
2,5 MW, para manter o tempo de cálculo baixo: o resumo só depende dos valores perto de P* e do último degrau.

Uso:  python scripts/hipoteses_h1.py config/estocastico_unifei_faixas.yaml --casos importacao pv_75 ...
Saída: resultados/curva_oferta/<subdir>/<caso>.csv (p_cap_mw, q_rs, q_<ano>) e resumo_hipoteses.csv
"""

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia  # noqa: E402
from pvbess_h2.modelo import potencia_lrcap_max  # noqa: E402
from curva_oferta import CASOS, aplicar, oferta  # noqa: E402

PASSO = 2.5


def resumir(c: pd.DataFrame, r_ref: float) -> dict:
    c = c.sort_values("p_cap_mw").reset_index(drop=True)
    P, Q = c.p_cap_mw.to_numpy(), c.q_rs.to_numpy()
    v = c[c.p_cap_mw > 0]
    entrada = float(((Q[0] - v.q_rs) / v.p_cap_mw).min())
    otimo = float(oferta(c, np.array([r_ref])).p_cap_mw.iloc[0])
    ultimo = float((Q[-2] - Q[-1]) / (P[-1] - P[-2])) if abs(P[-1] - P[-2] - PASSO) < 1e-6 else float("nan")
    return {"q0_rs": Q[0], "entrada_rs_mw_ano": entrada, "otimo_ref_mw": otimo, "ultimo_mw_rs_mw_ano": ultimo,
            "lucro_ref_rs": float(oferta(c, np.array([r_ref])).lucro_rs.iloc[0])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--casos", nargs="+", required=True)
    ap.add_argument("--subdir", default="hipoteses_h1_faixas")
    ap.add_argument("--processos", type=int, default=4)
    ap.add_argument("--grade", type=float, nargs="*", default=[0, 30, 45, 52.5, 57.5, 60],
                    help="grade inicial; o ótimo é refinado em passos de 2,5 MW")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    base = carregar_parametros(args.config)
    r_ref = base.lrcap.receita_fixa_rs_mw_ano
    saida = RAIZ / "resultados" / "curva_oferta" / args.subdir
    saida.mkdir(parents=True, exist_ok=True)

    resumo = []
    for caso in args.casos:
        p = aplicar(base, CASOS[caso][1])
        p.lrcap.receita_fixa_rs_mw_ano = 0.0
        pmax = potencia_lrcap_max(p)
        arq = saida / f"{caso}.csv"
        linhas = pd.read_csv(arq).to_dict("records") if arq.exists() else []
        feitos = {round(r["p_cap_mw"], 6): r for r in linhas}

        def avaliar(x):
            x = round(float(x), 6)
            if x in feitos or x < 0 or x > pmax + 1e-6 or (0 < x < p.lrcap.potencia_min_mw - 1e-6):
                return
            av = avaliar_potencia(p, x, processos=args.processos)
            r = {"p_cap_mw": x, "q_rs": av.esperado,
                 **{f"q_{c.nome}": v for c, v in zip(p.estocastico.cenarios, av.lucro_cenarios)}}
            feitos[x] = r
            pd.DataFrame(list(feitos.values())).to_csv(arq, index=False)
            print(f"[{caso}] P = {x:5.1f} MW  Q = R$ {av.esperado / 1e6:7.3f} mi", flush=True)

        for x in args.grade:
            avaliar(min(x, pmax))
        for _ in range(4):                                    # refina em torno do ótimo
            c = pd.DataFrame(list(feitos.values())).sort_values("p_cap_mw")
            xo = float(oferta(c, np.array([r_ref])).p_cap_mw.iloc[0])
            n0 = len(feitos)
            for d in (-5.0, -2.5, 2.5, 5.0):
                avaliar(xo + d)
            if len(feitos) == n0:
                break
        avaliar(pmax - PASSO)                                 # custo do último degrau
        avaliar(pmax)
        c = pd.DataFrame(list(feitos.values())).sort_values("p_cap_mw").reset_index(drop=True)
        c.to_csv(arq, index=False)
        r = {"caso": caso, "descricao": CASOS[caso][0], **resumir(c, r_ref)}
        resumo.append(r)
        print(f"[{caso}] ótimo {r['otimo_ref_mw']:.1f} MW, entrada {r['entrada_rs_mw_ano']/1e3:.0f} mil, "
              f"último MW {r['ultimo_mw_rs_mw_ano']/1e3:.0f} mil", flush=True)
        pd.DataFrame(resumo).to_csv(saida / "resumo_hipoteses.csv", index=False)


if __name__ == "__main__":
    main()
