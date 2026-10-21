"""Efeito do pareamento entre a irradiância e o PLD nos cenários de 2024 e 2025.

A base SARAH-3 vai até 2023, e os cenários de 2024 e 2025 usam a irradiância de 2023. Para medir quanto a
escolha do ano de irradiância afeta a decisão, este script calcula a curva de oferta Q(P) de um cenário só
(PLD de 2024 ou de 2025), com a irradiância de cada ano disponível (2021, 2022 e 2023), transposta para o
calendário do PLD (no ano bissexto, 29/02 repete 28/02, como em data/pv_itajuba_sarah3_2024.csv).

Saída: resultados/troca_irradiancia/curvas.csv e resumo.csv

Uso:  python scripts/troca_irradiancia.py [--anos-pld 2024 2025] [--anos-pv 2021 2022 2023]
"""

import argparse
import copy
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from curva_oferta import oferta  # noqa: E402
from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia  # noqa: E402

SAIDA = RAIZ / "resultados" / "troca_irradiancia"


def transpor(ano_pv, ano_destino):
    """CSV da irradiância de ano_pv no calendário de ano_destino; devolve o caminho relativo à raiz."""
    arq = SAIDA / f"pv_sarah3_{ano_pv}_em_{ano_destino}.csv"
    d = pd.read_csv(RAIZ / "data" / f"pv_itajuba_sarah3_{ano_pv}.csv", parse_dates=["timestamp"])
    d = d[~((d.timestamp.dt.month == 2) & (d.timestamp.dt.day == 29))]
    d["timestamp"] = d.timestamp.map(lambda t: t.replace(year=ano_destino))
    if ano_destino % 4 == 0:
        extra = d[(d.timestamp.dt.month == 2) & (d.timestamp.dt.day == 28)].copy()
        extra["timestamp"] = extra.timestamp + pd.Timedelta(days=1)
        d = pd.concat([d, extra]).sort_values("timestamp")
    d.to_csv(arq, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return str(arq.relative_to(RAIZ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--anos-pld", nargs="+", type=int, default=[2024, 2025])
    ap.add_argument("--anos-pv", nargs="+", type=int, default=[2021, 2022, 2023])
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    SAIDA.mkdir(parents=True, exist_ok=True)
    base = carregar_parametros(args.config)
    base.estocastico.fronteira_blocos = "lp"
    r_ref = base.lrcap.receita_fixa_rs_mw_ano
    linhas = []
    for ano in args.anos_pld:
        c0 = next(c for c in base.estocastico.cenarios if c.ano == ano)
        for ano_pv in args.anos_pv:
            p = copy.deepcopy(base)
            c = copy.deepcopy(c0)
            c.nome, c.pv_arquivo, c.probabilidade = f"{ano}_pv{ano_pv}", transpor(ano_pv, ano), 1.0
            p.estocastico.cenarios = [c]
            p.lrcap.receita_fixa_rs_mw_ano = 0.0
            for x in [0.0] + list(np.arange(p.lrcap.potencia_min_mw, 60 + 1e-6, 2.5)):
                av = avaliar_potencia(p, float(x), processos=args.processos)
                linhas.append({"ano_pld": ano, "ano_pv": ano_pv, "p_cap_mw": x, "q_rs": av.esperado})
                print(linhas[-1], flush=True)
            pd.DataFrame(linhas).to_csv(SAIDA / "curvas.csv", index=False)
    df = pd.DataFrame(linhas)
    res = []
    for (ano, ano_pv), g in df.groupby(["ano_pld", "ano_pv"]):
        g = g.reset_index(drop=True)
        o = oferta(g, np.array([r_ref]))
        q0 = g.q_rs.iloc[0]
        res.append({"ano_pld": ano, "ano_pv": ano_pv, "q0_rs": q0,
                    "entrada_rs_mw": ((q0 - g.q_rs.iloc[1:]) / g.p_cap_mw.iloc[1:]).min(),
                    "marginal_ultimo_rs_mw": (g.q_rs.iloc[-2] - g.q_rs.iloc[-1]) / 2.5,
                    "perda_60mw_rs": q0 - g.q_rs.iloc[-1],
                    "p_otima_mw": o.p_cap_mw.iloc[0], "lucro_ref_rs": o.lucro_rs.iloc[0]})
    res = pd.DataFrame(res)
    res.to_csv(SAIDA / "resumo.csv", index=False)
    print(res.to_string(index=False))


if __name__ == "__main__":
    main()
