"""Teste dos cortes de geração solar do ONS (constrained-off) sobre a curva de oferta.

Para cada caso, avalia o lucro operacional esperado Q(P) numa grade de potências (fronteira "lp") com a geração
FV disponível reduzida pelo perfil de cortes do ONS (scripts/importar_cortes_fv.py), e compara com a mesma
avaliação sem cortes. Casos: referencia (sem cortes), observado (cada ano com os cortes que teve) e recente
(os cortes dos últimos 12 meses em todos os cenários), mais o dobro do recente como estresse.

Uso:  python scripts/teste_curtailment.py [--casos referencia observado recente recente_x2] [--processos 4]
Saída: resultados/curtailment/<caso>.csv (p_cap_mw, q_rs, q_<ano>) e resumo.csv
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

GRADE = [0.0, 30.0, 40.0, 50.0, 52.5, 55.0, 57.5, 60.0]
CASOS = {
    "referencia": {},
    "observado": {"corte_arquivo": "data/ons_corte_fv_observado_{ano}.csv"},
    "recente": {"corte_arquivo": "data/ons_corte_fv_recente_{ano}.csv"},
    "recente_x2": {"corte_arquivo": "data/ons_corte_fv_recente_{ano}.csv", "corte_fator": 2.0},
}
SAIDA = RAIZ / "resultados" / "curtailment"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--casos", nargs="+", default=list(CASOS))
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    SAIDA.mkdir(parents=True, exist_ok=True)

    for caso in args.casos:
        p = carregar_parametros(args.config)
        p.lrcap.receita_fixa_rs_mw_ano = 0.0            # lucro avaliado = Q(P)
        p.estocastico.fronteira_blocos = "lp"
        for k, v in CASOS[caso].items():
            setattr(p.pv, k, v)
        arq = SAIDA / f"{caso}.csv"
        linhas = pd.read_csv(arq).to_dict("records") if arq.exists() else []
        feitos = {round(r["p_cap_mw"], 6) for r in linhas}
        for x in GRADE:
            if round(x, 6) in feitos:
                continue
            av = avaliar_potencia(p, x, processos=args.processos)
            linhas.append({"p_cap_mw": x, "q_rs": av.esperado,
                           **{f"q_{c.nome}": v for c, v in zip(p.estocastico.cenarios, av.lucro_cenarios)}})
            pd.DataFrame(linhas).to_csv(arq, index=False)
            print(f"[{caso}] P = {x:5.1f} MW  Q = R$ {av.esperado / 1e6:7.3f} mi", flush=True)

    ref = pd.read_csv(SAIDA / "referencia.csv").set_index("p_cap_mw")
    saida = []
    for caso in CASOS:
        if not (SAIDA / f"{caso}.csv").exists():
            continue
        c = pd.read_csv(SAIDA / f"{caso}.csv").set_index("p_cap_mw").sort_index()
        if len(c) < len(GRADE):
            continue
        P, Q = c.index.to_numpy(), c.q_rs.to_numpy()
        otimo = P[int(np.argmax(600e3 * P + Q))]
        entrada = float(((Q[0] - Q[1:]) / np.where(P[1:] > 0, P[1:], np.nan)).min())
        saida.append({"caso": caso, "q0_rs": Q[0], "q0_var_pct": 100 * (Q[0] / ref.q_rs.loc[0.0] - 1),
                      "entrada_rs_mw": entrada, "ultimo_mw_rs_mw": (Q[-2] - Q[-1]) / (P[-1] - P[-2]),
                      "perda_0_60_rs": Q[0] - Q[-1], "otimo_600mil_mw": otimo,
                      **{f"q_{x:g}": q for x, q in zip(P, Q)}})
    pd.DataFrame(saida).to_csv(SAIDA / "resumo.csv", index=False)
    pd.set_option("display.width", 200)
    print(pd.DataFrame(saida)[["caso", "q0_rs", "q0_var_pct", "entrada_rs_mw", "ultimo_mw_rs_mw", "otimo_600mil_mw"]]
          .round(2).to_string(index=False))


if __name__ == "__main__":
    main()
