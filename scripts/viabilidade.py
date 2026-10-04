"""Viabilidade econômica: VPL, TIR, valor da bateria e preço de equilíbrio do H2.

Combina o lucro operacional esperado dos casos da curva de oferta (resultados/curva_oferta,
receita fixa de referência) com os custos de investimento e de O&M fixo de config/economia.yaml.
Fluxo anual constante em termos reais durante `vida_anos`, sem valor residual.

  VPL  = -CAPEX + FA(i, n) * (lucro operacional - O&M fixo)
  Valor da bateria = lucro com BESS - lucro sem BESS (modelo resolvido sem bateria)
  Preço de equilíbrio do H2 ≈ preço - VPL / (FA * H2 vendido)   (operação mantida fixa)

Uso:  python scripts/viabilidade.py [config/estocastico_unifei.yaml] [--sem-bess] [--processos 4]
"""

import argparse
import copy
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia  # noqa: E402

sys.path.insert(0, str(RAIZ / "scripts"))
from curva_oferta import CASOS, aplicar, oferta  # noqa: E402

NIVEIS = ["baixo", "central", "alto"]


def fator_anuidade(i, n):
    return (1 - (1 + i) ** -n) / i


def tir(capex, fluxo, n):
    if fluxo <= 0:
        return np.nan
    lo, hi = -0.99, 1.0
    for _ in range(200):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if -capex + fluxo * fator_anuidade(m, n) > 0 else (lo, m)
    return m


def capex_om(p, eco, nivel):
    k = NIVEIS.index(nivel)
    c = eco["capex"]
    pv = c["pv_rs_kw"][k] * p.pv.potencia_pico_mw * 1e3
    bess = c["bess_rs_kw"][k] * max(p.bess.potencia_carga_mw, p.bess.potencia_descarga_mw) * 1e3
    el = c["eletrolisador_usd_kw"][k] * eco["cambio_rs_usd"] * p.eletrolisador.potencia_max_mw * 1e3
    om = eco["om_fixo_frac"]
    return {"pv": pv, "bess": bess, "eletrolisador": el,
            "om": pv * om["pv"] + bess * om["bess"] + el * om["eletrolisador"],
            "om_bess": bess * om["bess"]}


def lucro_sem_bess(base, processos):
    """Lucro esperado nos cenários sem bateria (e, portanto, sem LRCAP)."""
    p = copy.deepcopy(base)
    p.lrcap.habilitado = False
    p.bess.energia_mwh, p.bess.potencia_carga_mw, p.bess.potencia_descarga_mw = 1e-6, 0.0, 0.0
    return avaliar_potencia(p, 0.0, processos=processos).esperado


def grafico(res, curva, q_sem, eco, base, saida):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    casos = ["base", "contrato_2t", "contrato_3t", "importacao", "importacao_contrato_3t", "el_10", "el_25", "deg_200"]
    rot = {"base": "Referência", "contrato_2t": "Contrato\n2 t/dia", "contrato_3t": "Contrato\n3 t/dia",
           "importacao": "Importação", "importacao_contrato_3t": "Import.\n+ 3 t/dia", "el_10": "Eletrol.\n10 MW",
           "el_25": "Eletrol.\n25 MW", "deg_200": "Degrad.\nR$ 200"}
    casos = [c for c in casos if c in set(res.caso)]
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    for j, (taxa, cor) in enumerate([(0.08, "#256abf"), (0.1211, "#d9731a")]):
        r = res[res.taxa == taxa].set_index(["caso", "capex_nivel"]).vpl_rs / 1e6
        x = np.arange(len(casos)) + (j - 0.5) * 0.38
        cen = [r[(c, "central")] for c in casos]
        lo = [cen[k] - r[(c, "alto")] for k, c in enumerate(casos)]
        hi = [r[(c, "baixo")] - cen[k] for k, c in enumerate(casos)]
        ax[0].bar(x, cen, width=0.36, color=cor, yerr=[lo, hi], capsize=3, error_kw={"lw": 0.8},
                  label=f"taxa de {taxa:.1%}".replace(".", ","))
    ax[0].axhline(0, color="#1a1a1a", lw=0.8)
    ax[0].set_xticks(np.arange(len(casos)), [rot[c] for c in casos], fontsize=8)
    ax[0].set_ylabel("VPL em 15 anos [R$ mi, dez/2025]")
    ax[0].set_title("(a) VPL do projeto (barras: CAPEX central; traços: baixo e alto)", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8, loc="lower left")

    P, Q = curva.p_cap_mw.to_numpy(), curva.q_rs.to_numpy()
    rs = np.arange(0, 1.6e6 + 1, 1e4)
    ganho = np.array([np.max(r * P + Q) - q_sem for r in rs]) / 1e6
    ax[1].plot(rs / 1e3, ganho, color="#256abf", lw=2, label="Ganho anual da bateria (com − sem BESS)")
    for taxa, cor in [(0.08, "#2a9d5c"), (0.1211, "#d9731a")]:
        cs = [capex_om(base, eco, nv) for nv in NIVEIS]
        custos = [c["bess"] / fator_anuidade(taxa, eco["vida_anos"]) / 1e6 + c["om_bess"] / 1e6 for c in cs]
        ax[1].axhspan(custos[0], custos[2], color=cor, alpha=0.15, lw=0)
        ax[1].axhline(custos[1], color=cor, lw=1.2, ls="--",
                      label=f"Custo anual do BESS, taxa de {taxa:.1%}".replace(".", ","))
    ax[1].axvline(base.lrcap.receita_fixa_rs_mw_ano / 1e3, color="#9a9a9a", lw=0.8, ls=":")
    ax[1].set_xlabel("Receita fixa do LRCAP [R$ mil/MW·ano]")
    ax[1].set_ylabel("R$ mi/ano")
    ax[1].set_title("(b) A bateria se paga quando o ganho supera o custo anual", fontsize=10)
    ax[1].legend(frameon=False, fontsize=8, loc="upper left")
    for a in ax:
        a.grid(alpha=0.25, lw=0.6)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(saida / "viabilidade.png", dpi=150)
    plt.close(fig)


def oferta_com_investimento(curva, q_sem, custo_anual_bess, receitas):
    """Curva de oferta quando a bateria ainda será construída.

    Para cada receita fixa R, o proponente compara não construir o BESS (lucro q_sem, oferta 0)
    com construí-lo e contratar a melhor potência: max_P {R P + Q(P)} - custo anual do BESS.
    """
    P, Q = curva.p_cap_mw.to_numpy(), curva.q_rs.to_numpy()
    linhas = []
    for r in receitas:
        v = r * P + Q
        k = int(np.argmax(v))
        constroi = v[k] - custo_anual_bess > q_sem
        linhas.append({"receita_fixa_rs_mw_ano": r, "p_cap_mw": P[k] if constroi else 0.0,
                       "constroi_bess": constroi, "lucro_liquido_rs": max(v[k] - custo_anual_bess, q_sem)})
    return pd.DataFrame(linhas)


def grafico_oferta(curva, q_sem, eco, base, saida):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = eco["vida_anos"]
    rs = np.arange(0, 1.5e6 + 1, 5e3)
    P, Q = curva.p_cap_mw.to_numpy(), curva.q_rs.to_numpy()
    op = [P[np.argmax(r * P + Q)] for r in rs]
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.6))
    ax[0].step(rs / 1e3, op, where="post", color="#9a9a9a", lw=1.5, ls="--", label="Bateria existente (só custo de oportunidade)")
    linhas = []
    for taxa, cor in [(0.08, "#256abf"), (0.1211, "#d9731a")]:
        for nivel in NIVEIS:
            c = capex_om(base, eco, nivel)
            custo = c["bess"] / fator_anuidade(taxa, n) + c["om_bess"]
            o = oferta_com_investimento(curva, q_sem, custo, rs)
            r_min = o[o.constroi_bess].receita_fixa_rs_mw_ano.min()
            linhas.append({"taxa": taxa, "capex_nivel": nivel, "custo_anual_bess_rs": custo,
                           "custo_anual_bess_rs_mw": custo / max(base.bess.potencia_descarga_mw, 1e-9),
                           "lance_minimo_rs_mw_ano": r_min,
                           "p_cap_no_lance_minimo_mw": o[o.constroi_bess].p_cap_mw.iloc[0]})
            if nivel == "central":
                ax[0].step(rs / 1e3, o.p_cap_mw, where="post", color=cor, lw=2,
                           label=f"Bateria a construir, taxa de {taxa:.1%} (CAPEX central)".replace(".", ","))
    lm = pd.DataFrame(linhas)
    lm.to_csv(saida / "lance_minimo.csv", index=False)
    for v, rot in [(600, "referência"), (831, "LRCAP 3/2026")]:
        ax[0].axvline(v, color="#9a9a9a", lw=0.8, ls=":")
        ax[0].annotate(rot, (v, 2), xytext=(3, 0), textcoords="offset points", fontsize=8, color="#555555")
    ax[0].set_xlabel("Receita fixa do LRCAP [R$ mil/MW·ano]")
    ax[0].set_ylabel("Potência ótima a ofertar [MW]")
    ax[0].set_title("(a) Curva de oferta com e sem o investimento no BESS", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14))

    x = np.arange(len(NIVEIS))
    for j, (taxa, cor) in enumerate([(0.08, "#256abf"), (0.1211, "#d9731a")]):
        v = lm[lm.taxa == taxa].set_index("capex_nivel").loc[NIVEIS].lance_minimo_rs_mw_ano / 1e3
        b = ax[1].bar(x + (j - 0.5) * 0.38, v, width=0.36, color=cor, label=f"taxa de {taxa:.1%}".replace(".", ","))
        ax[1].bar_label(b, fmt="%.0f", fontsize=8)
    ax[1].axhline(600, color="#555555", lw=0.9, ls=":", label="R$ 600 mil (caso de referência)")
    ax[1].axhline(831, color="#555555", lw=0.9, ls="--", label="R$ 831 mil (LRCAP 3/2026, térmicas existentes)")
    ax[1].set_xticks(x, ["CAPEX baixo\n(R$ 5.000/kW)", "CAPEX central\n(R$ 5.500/kW)", "CAPEX alto\n(R$ 6.000/kW)"])
    ax[1].set_ylabel("Lance mínimo [R$ mil/MW·ano]")
    ax[1].set_title("(b) Menor receita fixa que justifica construir o BESS", fontsize=10)
    ax[1].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    ax[1].set_ylim(0, 1300)
    for a in ax:
        a.grid(alpha=0.25, lw=0.6)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(saida / "curva_oferta_investimento.png", dpi=150)
    plt.close(fig)
    return lm


# Casos cujo lucro sem bateria é igual ao do caso base (só alteram o BESS ou o LRCAP)
SEM_BESS_IGUAL_BASE = ("deg_", "ciclos_")


def lance_minimo_por_caso(base, eco, saida, processos):
    """Lance mínimo (BESS a construir) para cada caso da curva de oferta."""
    dirc = RAIZ / "resultados" / "curva_oferta"
    n = eco["vida_anos"]
    rs = np.arange(0, 2.5e6 + 1, 5e3)
    cache = saida / "sem_bess_casos.csv"
    sem = pd.read_csv(cache, index_col=0)["lucro_sem_bess_rs"].to_dict() if cache.exists() else {}
    linhas = []
    for caso, (desc, ajustes) in CASOS.items():
        if not (dirc / f"{caso}.csv").exists():
            continue
        chave = "base" if caso.startswith(SEM_BESS_IGUAL_BASE) else caso
        if chave not in sem:
            print(f"Resolvendo {chave} sem bateria...", flush=True)
            sem[chave] = lucro_sem_bess(aplicar(base, CASOS[chave][1]), processos)
            pd.Series(sem, name="lucro_sem_bess_rs").to_csv(cache)
        p = aplicar(base, ajustes)
        curva = pd.read_csv(dirc / f"{caso}.csv")
        for taxa in eco["taxas_desconto"]:
            c = capex_om(p, eco, "central")
            custo = c["bess"] / fator_anuidade(taxa, n) + c["om_bess"]
            o = oferta_com_investimento(curva, sem[chave], custo, rs)
            ok = o[o.constroi_bess]
            linhas.append({"caso": caso, "descricao": desc, "taxa": taxa, "lucro_sem_bess_rs": sem[chave],
                           "lance_minimo_rs_mw_ano": ok.receita_fixa_rs_mw_ano.min() if len(ok) else np.nan,
                           "p_cap_mw": ok.p_cap_mw.iloc[0] if len(ok) else np.nan})
    df = pd.DataFrame(linhas)
    df.to_csv(saida / "lance_minimo_casos.csv", index=False)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--economia", default=str(RAIZ / "config" / "economia.yaml"))
    ap.add_argument("--sem-bess", action="store_true", help="recalcula o caso sem bateria")
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)

    base = carregar_parametros(args.config)
    eco = yaml.safe_load(open(args.economia, encoding="utf-8"))
    n = eco["vida_anos"]
    dirc = RAIZ / "resultados" / "curva_oferta"
    saida = RAIZ / "resultados" / "viabilidade"
    saida.mkdir(parents=True, exist_ok=True)
    r_ref = base.lrcap.receita_fixa_rs_mw_ano

    arq_sem = saida / "sem_bess.csv"
    if args.sem_bess or not arq_sem.exists():
        print("Resolvendo o caso sem bateria...", flush=True)
        pd.DataFrame([{"lucro_sem_bess_rs": lucro_sem_bess(base, args.processos)}]).to_csv(arq_sem, index=False)
    q_sem = float(pd.read_csv(arq_sem).lucro_sem_bess_rs.iloc[0])

    linhas = []
    for caso, (desc, ajustes) in CASOS.items():
        if not (dirc / f"{caso}.csv").exists():
            continue
        p = aplicar(base, ajustes)
        curva = pd.read_csv(dirc / f"{caso}.csv")
        op = pd.read_csv(dirc / f"{caso}_operacao.csv", index_col=0)["valor"]
        o = oferta(curva, np.array([r_ref]))
        lucro, p_cap = float(o.lucro_rs.iloc[0]), float(o.p_cap_mw.iloc[0])
        for nivel in NIVEIS:
            c = capex_om(p, eco, nivel)
            capex = c["pv"] + c["bess"] + c["eletrolisador"]
            fluxo = lucro - c["om"]
            for i in eco["taxas_desconto"]:
                fa = fator_anuidade(i, n)
                vpl = -capex + fa * fluxo
                h2 = op["h2_vendido_kg"]
                linhas.append({
                    "caso": caso, "descricao": desc, "capex_nivel": nivel, "taxa": i,
                    "p_cap_mw": p_cap, "lucro_operacional_rs": lucro, "om_fixo_rs": c["om"],
                    "capex_pv_rs": c["pv"], "capex_bess_rs": c["bess"], "capex_el_rs": c["eletrolisador"],
                    "capex_total_rs": capex, "vpl_rs": vpl, "tir": tir(capex, fluxo, n),
                    "h2_vendido_kg": h2,
                    "preco_h2_equilibrio_rs_kg": p.hidrogenio.preco_venda_rs_kg - vpl / (fa * h2),
                })
    res = pd.DataFrame(linhas)
    res.to_csv(saida / "viabilidade.csv", index=False)

    # Valor da bateria no caso de referência: receita fixa que paga o investimento no BESS
    curva = pd.read_csv(dirc / "base.csv")
    P, Q = curva.p_cap_mw.to_numpy(), curva.q_rs.to_numpy()
    bat = []
    for nivel in NIVEIS:
        c = capex_om(base, eco, nivel)
        for i in eco["taxas_desconto"]:
            custo_anual = c["bess"] / fator_anuidade(i, n) + c["om_bess"]
            ganho = lambda r: np.max(r * P + Q) - q_sem  # noqa: E731
            rs = np.arange(0, 3e6, 1e3)
            ok = [r for r in rs if ganho(r) >= custo_anual]
            bat.append({"capex_nivel": nivel, "taxa": i, "custo_anual_bess_rs": custo_anual,
                        "ganho_bess_ref_rs": ganho(r_ref), "vpl_bess_ref_rs": fator_anuidade(i, n) * (ganho(r_ref) - custo_anual),
                        "receita_fixa_equilibrio_rs_mw_ano": ok[0] if ok else np.nan,
                        "p_cap_equilibrio_mw": P[np.argmax(ok[0] * P + Q)] if ok else np.nan})
    bat = pd.DataFrame(bat)
    bat.to_csv(saida / "valor_bateria.csv", index=False)
    grafico(res, curva, q_sem, eco, base, saida)
    lm = grafico_oferta(curva, q_sem, eco, base, saida)
    lmc = lance_minimo_por_caso(base, eco, saida, args.processos)

    pd.set_option("display.width", 250)
    pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
    cen = res[(res.capex_nivel == "central")]
    t = cen.pivot_table(index="caso", columns="taxa", values=["vpl_rs", "tir", "preco_h2_equilibrio_rs_kg"])
    t[("vpl_rs", 0.08)] /= 1e6; t[("vpl_rs", 0.1211)] /= 1e6
    print(f"Lucro sem bateria: R$ {q_sem / 1e6:.2f} mi/ano\n")
    print(t.to_string())
    print("\nValor da bateria (caso de referência):")
    print(bat.assign(**{c: bat[c] / 1e6 for c in ["custo_anual_bess_rs", "ganho_bess_ref_rs", "vpl_bess_ref_rs"]}).to_string(index=False))
    print("\nLance mínimo com investimento no BESS:")
    print(lm.to_string(index=False))
    print("\nLance mínimo por caso (CAPEX central):")
    print(lmc.pivot_table(index="caso", columns="taxa", values=["lance_minimo_rs_mw_ano", "p_cap_mw"]).to_string())
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
