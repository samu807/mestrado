"""Decomposição do lucro esperado da H1 por fonte de receita, com 0, 30 e 60 MW contratados no LRCAP.

Média dos cenários (operacao_media): receita do MCP, receita e custo do hidrogênio e degradação do BESS, sem a receita
fixa; a receita do LRCAP é R * P. O O&M fixo e a TUST vêm de config/economia.yaml (premissas centrais de viabilidade.py)
e não dependem da potência contratada, pois o BESS já existe e o montante de uso é o maior entre a FV e o BESS.

Uso:  python scripts/decomposicao_receita_h1.py config/estocastico_unifei_faixas.yaml [--receita 600000]
Saída: resultados/curva_oferta/faixas_ref/decomposicao_receita.csv (R$ por ano)
"""
import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "src"))


def main():
    from curva_oferta import operacao_media
    from pvbess_h2 import carregar_parametros
    import viabilidade as v

    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--receita", type=float, default=600e3, help="receita fixa [R$/(MW·ano)]")
    ap.add_argument("--p-cap", type=float, nargs="+", default=[0, 30, 60])
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    p = carregar_parametros(args.config)
    p.lrcap.receita_fixa_rs_mw_ano = 0.0
    eco = yaml.safe_load(open(RAIZ / "config" / "economia.yaml", encoding="utf-8"))
    pr = v.premissas(eco)
    c = v.capex_om(p, eco, pr)
    om = c["om"]
    tust = v.uso_rede(p, eco, pr, True)
    linhas = {}
    for x in args.p_cap:
        k = operacao_media(p, float(x))
        lr = args.receita * x
        op = lr + k["receita_h2_rs"] + k["receita_mcp_rs"] - k["custo_h2_rs"] - k["custo_degradacao_rs"] - k["custo_importacao_rs"]
        linhas[x] = {"receita_lrcap_rs": lr, "receita_h2_rs": k["receita_h2_rs"], "receita_mcp_rs": k["receita_mcp_rs"],
                     "custo_h2_rs": k["custo_h2_rs"], "custo_degradacao_rs": k["custo_degradacao_rs"],
                     "custo_importacao_rs": k["custo_importacao_rs"], "lucro_operacional_rs": op,
                     "om_fixo_rs": om, "tust_rs": tust, "resultado_rs": op - om - tust}
    saida = RAIZ / "resultados" / "curva_oferta" / "faixas_ref"
    saida.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(linhas).T
    df.index.name = "p_cap_mw"
    df.to_csv(saida / "decomposicao_receita.csv")
    print((df / 1e6).round(2).to_string())


if __name__ == "__main__":
    main()
