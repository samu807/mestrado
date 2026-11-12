"""Operação anual da H1 em cada cenário para algumas potências contratadas: série horária e indicadores.

Salva, por potência e ano, a operação horária (resultados/<subdir>/op_<P>MW_<ano>.csv) e um resumo com a média dos
cenários: hidrogênio vendido, horas e partidas do eletrolisador, exportação e lucro operacional. Uma partida é uma
passagem do eletrolisador de desligado a ligado.

Uso:  python scripts/operacao_h1.py config/estocastico_unifei_faixas.yaml --p-cap 0 60 [--subdir curva_oferta/faixas_ref]
"""

import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.decomposicao import operacao_anual  # noqa: E402
from pvbess_h2.estocastico import dias_cenario, parametros_cenario  # noqa: E402

COLUNAS = ["pv_disp_mw", "pld_rs_mwh", "p_eletrolisador_mw", "p_exportacao_mw", "p_importacao_mw", "p_carga_bess_mw",
           "p_descarga_bess_mw", "soc_mwh", "tanque_h2_kg", "venda_h2_kg_h", "p_descarga_lrcap_mw", "p_recarga_lrcap_mw"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--p-cap", type=float, nargs="+", required=True)
    ap.add_argument("--subdir", default="curva_oferta/faixas_ref")
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    p = carregar_parametros(args.config)
    p.lrcap.receita_fixa_rs_mw_ano = 0.0
    saida = RAIZ / "resultados" / args.subdir
    saida.mkdir(parents=True, exist_ok=True)
    for x in args.p_cap:
        linhas = []
        for c in p.estocastico.cenarios:
            q = parametros_cenario(p, c)
            df, k = operacao_anual(q, f"{c.ano}-01-01", dias_cenario(p, c), x, processos=args.processos)
            df[[col for col in COLUNAS if col in df]].to_csv(saida / f"op_{x:g}MW_{c.ano}.csv", index_label="timestamp")
            on = df["p_eletrolisador_mw"] > 1e-6
            partidas = int((on & ~on.shift(1, fill_value=False)).sum())
            dt = q.horizonte.dt_h
            linhas.append({"ano": c.ano, "h2_vendido_t": k["h2_vendido_kg"] / 1e3, "horas_eletrolisador": float(on.sum() * dt),
                           "partidas": partidas, "exportacao_gwh": k["energia_exportada_mwh"] / 1e3,
                           "lucro_operacional_rs": k["lucro_rs"]})
            print(f"[{x:g} MW] {c.ano}: {linhas[-1]}", flush=True)
        t = pd.DataFrame(linhas)
        t.to_csv(saida / f"resumo_op_{x:g}MW.csv", index=False)
        print(f"[{x:g} MW] média:", t.drop(columns="ano").mean().round(3).to_dict(), flush=True)


if __name__ == "__main__":
    main()
