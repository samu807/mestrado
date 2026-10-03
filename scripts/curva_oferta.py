"""Curva de oferta no LRCAP: receita fixa mínima que justifica cada MW contratado.

Para cada caso (variações do contrato de H2 e da regra de importação), avalia o lucro
operacional esperado nos cenários anuais, sem a receita fixa, numa grade de potências:
    Q(P) = E_s[ lucro_s(P) ] - R_cap * P
O custo de oportunidade marginal de contratar mais um MW é -dQ/dP, e a potência ótima
para cada receita fixa R é argmax_P { R * P + Q(P) } — a curva de oferta do empreendedor.

Uso:  python scripts/curva_oferta.py [config/estocastico_unifei.yaml] [--casos base importacao]
          [--passo 2.5] [--processos 4] [--so-graficos] [--rotulo curva_oferta]
      python scripts/curva_oferta.py --casos ciclos_50 ciclos_150 ciclos_365 --rotulo curva_oferta_ciclos
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

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.decomposicao import operacao_anual  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia, parametros_cenario  # noqa: E402

# Multa por kg não entregue: PLACEHOLDER (= preço do H2, isto é, ressarcir o comprador
# pelo valor do produto que ele terá de comprar de outro fornecedor).
MULTA = 35.0
CASOS = {
    "base": ("H₂ ilimitado, sem importação", {}),
    "contrato_2t": ("Contrato 2 t/dia, sem importação",
                    {"hidrogenio": {"entrega_min_diaria_kg": 2000.0, "entrega_max_diaria_kg": 2000.0,
                                    "penalidade_deficit_rs_kg": MULTA}}),
    "contrato_3t": ("Contrato 3 t/dia, sem importação",
                    {"hidrogenio": {"entrega_min_diaria_kg": 3000.0, "entrega_max_diaria_kg": 3000.0,
                                    "penalidade_deficit_rs_kg": MULTA}}),
    "importacao": ("H₂ ilimitado, com importação", {"rede": {"h2_verde_estrito": False}}),
    "importacao_contrato_3t": ("Contrato 3 t/dia, com importação",
                               {"rede": {"h2_verde_estrito": False},
                                "hidrogenio": {"entrega_min_diaria_kg": 3000.0, "entrega_max_diaria_kg": 3000.0,
                                               "penalidade_deficit_rs_kg": MULTA}}),
    # Frequência do despacho do ONS (H2 ilimitado, sem importação)
    **{f"ciclos_{n}": (f"{n} despachos/ano", {"lrcap.despacho_ons": {"ciclos_ano": float(n)}})
       for n in (50, 150, 365)},
}
INDICADORES = ["receita_mcp_rs", "receita_h2_rs", "custo_importacao_rs", "custo_h2_rs", "custo_degradacao_rs",
               "energia_exportada_mwh", "energia_importada_mwh", "energia_eletrolisador_mwh", "curtailment_mwh",
               "h2_produzido_kg", "h2_vendido_kg", "deficit_h2_kg", "fator_capacidade_eletrolisador"]


def aplicar(base, ajustes):
    p = copy.deepcopy(base)
    for secao, valores in ajustes.items():
        alvo = p
        for parte in secao.split("."):
            alvo = getattr(alvo, parte)
        for k, v in valores.items():
            setattr(alvo, k, v)
    p.validar()
    return p


def oferta(curva: pd.DataFrame, receitas: np.ndarray) -> pd.DataFrame:
    """Potência ótima (na grade) para cada receita fixa."""
    P, Q = curva.p_cap_mw.to_numpy(), curva.q_rs.to_numpy()
    idx = [int(np.argmax(r * P + Q)) for r in receitas]
    return pd.DataFrame({"receita_fixa_rs_mw_ano": receitas, "p_cap_mw": P[idx],
                         "lucro_rs": [r * P[i] + Q[i] for r, i in zip(receitas, idx)]})


def graficos(curvas, nomes, saida, rotulo):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cores = ["#256abf", "#2a9d5c", "#7cc49a", "#d9731a", "#a64d79"]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    receitas = np.arange(0, 1.5e6 + 1, 5e3)
    for (caso, c), cor in zip(curvas.items(), cores):
        c = c.sort_values("p_cap_mw")
        v = c[c.p_cap_mw >= 30 - 1e-6]
        ax[0].plot(v.p_cap_mw, (v.q_rs - c.q_rs.iloc[0]) / 1e6, "o-", ms=3, color=cor, label=nomes[caso])
        m = v.iloc[1:]
        cm = -np.diff(v.q_rs) / np.diff(v.p_cap_mw)
        ax[1].step(m.p_cap_mw, cm / 1e3, where="pre", color=cor, lw=1.8)
        o = oferta(c, receitas)
        ax[2].step(o.receita_fixa_rs_mw_ano / 1e3, o.p_cap_mw, where="post", color=cor, lw=1.8)
    ax[0].axhline(0, color="#1a1a1a", lw=0.7)
    ax[0].set_xlabel("Potência contratada no LRCAP [MW]")
    ax[0].set_ylabel("Q(P) − Q(0) [R$ mi/ano]")
    ax[0].set_title("(a) Perda de lucro operacional esperado", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8, loc="lower left")
    ax[1].set_xlabel("Potência contratada no LRCAP [MW]")
    ax[1].set_ylabel("Custo de oportunidade marginal [R$ mil/MW·ano]")
    ax[1].set_title("(b) Custo marginal de contratar mais um MW", fontsize=10)
    ax[2].axvline(600, color="#9a9a9a", lw=0.8, ls="--")
    ax[2].annotate("R$ 600 mil\n(caso de referência)", (600, 2), xytext=(4, 0), textcoords="offset points",
                   fontsize=8, color="#555555")
    ax[2].set_xlabel("Receita fixa do LRCAP [R$ mil/MW·ano]")
    ax[2].set_ylabel("Potência ótima a ofertar [MW]")
    ax[2].set_title("(c) Curva de oferta no leilão", fontsize=10)
    for a in ax:
        a.grid(alpha=0.25, lw=0.6)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(saida / f"{rotulo}.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--casos", nargs="+", default=list(CASOS))
    ap.add_argument("--passo", type=float, default=2.5)
    ap.add_argument("--processos", type=int, default=4)
    ap.add_argument("--so-graficos", action="store_true")
    ap.add_argument("--rotulo", default="curva_oferta", help="nome da figura e do resumo")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)

    base = carregar_parametros(args.config)
    r_ref = base.lrcap.receita_fixa_rs_mw_ano
    saida = RAIZ / "resultados" / "curva_oferta"
    saida.mkdir(parents=True, exist_ok=True)
    nomes = {k: CASOS[k][0] for k in args.casos}

    if not args.so_graficos:
        for caso in args.casos:
            p = aplicar(base, CASOS[caso][1])
            p.lrcap.receita_fixa_rs_mw_ano = 0.0          # lucro avaliado = Q(P)
            grade = [0.0] + list(np.arange(p.lrcap.potencia_min_mw, 60 + 1e-6, args.passo))
            linhas = []
            for x in grade:
                av = avaliar_potencia(p, float(x), processos=args.processos)
                linhas.append({"p_cap_mw": x, "q_rs": av.esperado,
                               **{f"q_{c.nome}": v for c, v in zip(p.estocastico.cenarios, av.lucro_cenarios)}})
                print(f"[{caso}] P = {x:5.1f} MW  Q = R$ {av.esperado / 1e6:7.3f} mi", flush=True)
            curva = pd.DataFrame(linhas)
            curva.to_csv(saida / f"{caso}.csv", index=False)

            # Operação média nos cenários na potência ótima para a receita de referência
            x_ref = float(oferta(curva, np.array([r_ref])).p_cap_mw.iloc[0])
            ks = []
            for c in p.estocastico.cenarios:
                q = parametros_cenario(p, c)
                dias = 366 if c.ano % 4 == 0 else 365
                _, k = operacao_anual(q, f"{c.ano}-01-01", dias, x_ref, processos=args.processos)
                ks.append(k[INDICADORES])
            op = pd.concat(ks, axis=1).mean(axis=1)
            op["p_cap_mw"] = x_ref
            op.to_csv(saida / f"{caso}_operacao.csv", header=["valor"])
            print(f"[{caso}] ótimo com R$ {r_ref / 1e3:.0f} mil/MW·ano: {x_ref:.1f} MW", flush=True)

    curvas = {k: pd.read_csv(saida / f"{k}.csv") for k in args.casos if (saida / f"{k}.csv").exists()}
    graficos(curvas, nomes, saida, args.rotulo)

    # Resumo: limiar de entrada, potência ótima na referência e operação
    linhas = []
    for caso, c in curvas.items():
        q0 = c.q_rs.iloc[0]
        v = c[c.p_cap_mw > 0]
        limiar = ((q0 - v.q_rs) / v.p_cap_mw).min()      # menor receita que torna participar vantajoso
        # menor receita para a qual ofertar a potência máxima supera qualquer outra opção
        pm, qm = c.p_cap_mw.iloc[-1], c.q_rs.iloc[-1]
        tudo = ((c.q_rs.iloc[:-1] - qm) / (pm - c.p_cap_mw.iloc[:-1])).max()
        o = oferta(c, np.array([r_ref]))
        op = pd.read_csv(saida / f"{caso}_operacao.csv", index_col=0)["valor"]
        linhas.append({"caso": caso, "descricao": nomes[caso], "q0_rs": q0,
                       "receita_minima_entrada_rs_mw_ano": limiar,
                       "receita_para_60mw_rs_mw_ano": tudo,
                       "p_otimo_ref_mw": o.p_cap_mw.iloc[0], "lucro_ref_rs": o.lucro_rs.iloc[0], **op.drop("p_cap_mw")})
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(saida / f"resumo_{args.rotulo}.csv", index=False)
    pd.set_option("display.width", 200)
    print(resumo.T.to_string())
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
