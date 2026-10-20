"""Lance mínimo como distribuição: Monte Carlo das premissas de custo e de regra.

A camada estocástica do modelo de operação trata a incerteza de preço e de geração, que pouco altera a
decisão (VSS ≈ 0). A incerteza que move o lance é a de custos e de regras ainda não definidas. Este script
sorteia essas premissas (config/economia.yaml, monte_carlo), de forma independente, e recalcula o lance
mínimo do BESS de referência (60 MW/300 MWh, pela curva de oferta do caso base) e do BESS dimensionado para
o contrato (60 MW/288 MWh), com a mesma rotina da análise determinística (scripts/viabilidade.py).

Saídas (resultados/viabilidade/): lance_monte_carlo.csv (amostras), lance_monte_carlo_resumo.csv
(percentis, probabilidades e importância das premissas) e lance_monte_carlo.png.
Importância: razão de correlação η² do lance com cada premissa (fração da variância explicada por ela
isoladamente, com as contínuas agrupadas em decis).

Uso:  python scripts/lance_monte_carlo.py [--amostras 5000]
"""

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from viabilidade import decomposicao, info_despacho, lance_dimensionado, potencia_bess, premissas  # noqa: E402

SAIDA = RAIZ / "resultados" / "viabilidade"
NOMES = {"c_ref": "Investimento de referência (R$/kW)", "h3": "Referência da EPE para 3 h",
         "f_energia": "Parcela de energia no custo", "taxa": "Taxa de desconto", "om_bess": "O&M do BESS",
         "tust": "TUST de geração", "dupla": "Cobrança dupla da TUST", "aux": "Consumo auxiliar",
         "sem_folga": "Sem folga da CONCAP", "disp": "Disponibilidade", "nao_cumulativo": "PIS/Cofins não cumulativo",
         "sem_reajuste": "Receita sem reajuste pelo IPCA", "implantacao": "Prazo de implantação",
         "dois_ciclos": "Despacho de 2 ciclos/dia"}


def sorteio(mc, n, rng):
    def cont(d):
        tipo, *a = d
        return rng.triangular(a[0], a[1], a[2], n) if tipo == "triangular" else rng.uniform(a[0], a[1], n)
    imp = mc["implantacao_anos"]
    return pd.DataFrame({
        "c_ref": cont(mc["bess_rs_kw"]), "h3": rng.random(n) < mc["duracao_referencia_3h_prob"],
        "f_energia": cont(mc["fracao_energia"]), "taxa": cont(mc["taxa"]), "om_bess": cont(mc["om_bess"]),
        "tust": cont(mc["tust_rs_kw_mes"]), "dupla": rng.random(n) < mc["cobranca_dupla_prob"],
        "aux": cont(mc["consumo_auxiliar"]), "sem_folga": rng.random(n) < mc["sem_folga_concap_prob"],
        "disp": cont(mc["disponibilidade"]), "nao_cumulativo": rng.random(n) < mc["pis_cofins_nao_cumulativo_prob"],
        "sem_reajuste": rng.random(n) < mc["sem_reajuste_ipca_prob"],
        "implantacao": rng.choice([int(k) for k in imp], n, p=[float(v) for v in imp.values()]),
        "dois_ciclos": rng.random(n) < mc["dois_ciclos_dia_prob"]})


def premissas_amostra(eco, x):
    return premissas(eco, c_ref=float(x.c_ref), h_ref=3 if x.h3 else eco["bess_duracao_referencia_h"],
                     f_energia=float(x.f_energia), taxa=float(x.taxa), om_bess=float(x.om_bess), tust=float(x.tust),
                     dupla=bool(x.dupla), aux=float(x.aux), folga=not x.sem_folga, disp=float(x.disp),
                     trib=eco["tributos_receita_sensibilidade"] if x.nao_cumulativo else eco["tributos_receita"],
                     reajuste=not x.sem_reajuste, implantacao=int(x.implantacao),
                     reposicao={"ciclos_dia": 2, "descontar_ciclos_dia": 1} if x.dois_ciclos else None)


def eta2(y, x):
    """Razão de correlação: Var(E[y|x]) / Var(y)."""
    g = x if x.dtype == bool or x.nunique() <= 5 else pd.qcut(x, 10, labels=False, duplicates="drop")
    m = y.groupby(g).transform("mean")
    return float(m.var() / y.var())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--economia", default=str(RAIZ / "config" / "economia.yaml"))
    ap.add_argument("--amostras", type=int)
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    base = carregar_parametros(args.config)
    eco = yaml.safe_load(open(args.economia, encoding="utf-8"))
    mc = eco["monte_carlo"]
    n = args.amostras or mc["amostras"]
    curva = pd.read_csv(RAIZ / "resultados" / "curva_oferta" / "base.csv")
    q_sem = float(pd.read_csv(SAIDA / "sem_bess.csv").lucro_sem_bess_rs.iloc[0])
    info = info_despacho(base)
    x = sorteio(mc, n, np.random.default_rng(mc["semente"]))
    ref, dim = [], []
    for k, linha in enumerate(x.itertuples(index=False)):
        pr = premissas_amostra(eco, linha)
        ref.append(decomposicao(base, eco, pr, curva, info, q_sem)["lance_minimo_rs_mw_ano"])
        dim.append(lance_dimensionado(base, eco, pr, potencia_bess(base), info)["lance_minimo_rs_mw_ano"])
        if (k + 1) % 1000 == 0:
            print(f"  {k + 1} amostras", flush=True)
    x["lance_referencia_rs_mw_ano"], x["lance_dimensionado_rs_mw_ano"] = ref, dim
    x.to_csv(SAIDA / "lance_monte_carlo.csv", index=False)

    linhas = []
    for col, rot in (("lance_referencia_rs_mw_ano", "BESS de referência"),
                     ("lance_dimensionado_rs_mw_ano", "BESS dimensionado")):
        y = x[col]
        d = {"bess": rot, "media": y.mean(), "desvio": y.std(),
             **{f"p{q}": y.quantile(q / 100) for q in (5, 10, 25, 50, 75, 90, 95)},
             **{f"prob_abaixo_{r:.0f}": float((y < r).mean()) for r in mc["referencias_rs_mw_ano"]},
             **{f"eta2_{c}": eta2(y, x[c]) for c in NOMES}}
        linhas.append(d)
    res = pd.DataFrame(linhas)
    res.to_csv(SAIDA / "lance_monte_carlo_resumo.csv", index=False)

    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.8))
    y = x.lance_dimensionado_rs_mw_ano / 1e3
    a.hist(y, bins=60, color="#2C5D8B", alpha=0.85)
    for q, ls in ((0.1, ":"), (0.5, "-"), (0.9, ":")):
        a.axvline(y.quantile(q), color="#14223A", ls=ls, lw=1.2)
    a.axvline(mc["referencias_rs_mw_ano"][0] / 1e3, color="#A4531A", lw=1.5, label="Térmicas existentes, LRCAP 2026")
    a.set_xlabel("Lance mínimo do BESS dimensionado (R$ mil/(MW·ano))")
    a.set_ylabel("Amostras")
    a.set_title("(a) Distribuição do lance mínimo (P10, mediana, P90)")
    a.legend(frameon=False)
    imp = pd.Series({NOMES[c]: res.iloc[1][f"eta2_{c}"] for c in NOMES}).sort_values()
    b.barh(imp.index, imp.values * 100, color="#C0661C")
    b.set_xlabel("Variância explicada isoladamente (%)")
    b.set_title("(b) Importância das premissas (η²)")
    fig.tight_layout()
    fig.savefig(SAIDA / "lance_monte_carlo.png", dpi=150)
    pd.set_option("display.width", 200)
    print(res.T.to_string())


if __name__ == "__main__":
    main()
