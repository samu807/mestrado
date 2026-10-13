"""Viabilidade econômica: VPL, TIR, valor da bateria, lance mínimo e preço de equilíbrio do H2.

Combina o lucro operacional esperado dos casos da curva de oferta (resultados/curva_oferta) com os
custos de config/economia.yaml. Fluxo anual constante em termos reais durante `vida_anos`, sem valor
residual, descontado à taxa antes de impostos (central), coerente com o fluxo antes de impostos.

  VPL = -I + FA(i, n) * (lucro operacional - O&M fixo - uso da rede)
  Lance mínimo = menor R para a qual  max_P {R d P + Q_inv(P)} - C_bess > lucro sem BESS
  C_bess = I_bess / FA(i, n) + O&M fixo do BESS + TUST sobre a potência do BESS

Q_inv(P) é o lucro operacional da curva de oferta, Q(P), ajustado para a decisão de construir o BESS:
  - sem o custo de degradação por MWh do módulo LRCAP: o desgaste do uso contratado já está no O&M
    fixo, que inclui a reposição parcial de módulos (augmentation) ao longo do contrato, e o
    investimento é amortizado em 15 anos sem valor residual. Cobrá-lo também por MWh pagaria a
    bateria duas vezes. O uso mercantil mantém o custo por MWh (desgaste além do uso contratado);
  - com o consumo auxiliar do BESS: o do módulo mercantil e o excedente do módulo LRCAP sobre a
    folga de recarga custeada pela CONCAP (injetada / RTE de referência) são pagos ao PLD médio.
d é a disponibilidade (fração da receita fixa recebida). A curva Q(P), sem esses ajustes, continua
sendo a do proponente que já dispõe do BESS (custo de oportunidade de um ativo existente).

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

from pvbess_h2 import carregar_parametros, montar_series  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia, dias_cenario, parametros_cenario  # noqa: E402

sys.path.insert(0, str(RAIZ / "scripts"))
from curva_oferta import CASOS, aplicar, oferta  # noqa: E402

NIVEIS = ["baixo", "central", "alto"]
PASSO = 1e3                       # resolução do lance [R$/MW·ano]
RECEITAS = np.arange(0, 3e6 + 1, PASSO)
# Casos cujo lucro sem bateria é igual ao do caso base (só alteram o BESS ou o LRCAP)
SEM_BESS_IGUAL_BASE = ("deg_", "ciclos_")


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


def fmt_taxa(i):
    return f"{i:.1%}".replace(".", ",")


# ------------------------------------------------------------------------------ premissas e custos
def premissas(eco, **troca):
    """Premissas centrais da análise de investimento, com trocas pontuais (sensibilidade)."""
    pr = {"capex": "central", "taxa": eco["taxa_central"], "om_bess": eco["om_fixo_frac"]["bess"],
          "h_ref": eco["bess_duracao_referencia_h"], "f_energia": eco["bess_fracao_energia"][1],
          "tust": eco["tust_geracao_rs_kw_mes"][1], "must_compartilhado": eco["must_compartilhado"],
          "dupla": False, "aux": eco["consumo_auxiliar_frac"][1], "disp": eco["disponibilidade"]}
    pr.update(troca)
    return pr


def potencia_bess(p):
    return max(p.bess.potencia_carga_mw, p.bess.potencia_descarga_mw)


def tust_anual(tust_rs_kw_mes, mw):
    return tust_rs_kw_mes * 12 * 1000 * mw


def must_injecao(p, pr, com_bess=True):
    """Montante de uso de injeção [MW]: com a conexão compartilhada, a FV é limitada quando a
    bateria injeta, e basta o maior dos dois; sem compartilhar, as potências se somam."""
    if not com_bess or potencia_bess(p) <= 0:
        return p.pv.potencia_pico_mw
    if pr["must_compartilhado"]:
        return max(p.pv.potencia_pico_mw, potencia_bess(p))
    return p.pv.potencia_pico_mw + potencia_bess(p)


def uso_rede(p, eco, pr, com_bess=True):
    """Custo anual de uso da rede da usina [R$]: TUST de geração sobre o MUST de injeção e, na
    cobrança dupla, TUST de consumo sobre a potência de recarga do BESS."""
    custo = tust_anual(pr["tust"], must_injecao(p, pr, com_bess))
    if com_bess and pr["dupla"]:
        custo += tust_anual(eco["tust_consumo_rs_kw_mes"], potencia_bess(p))
    return custo


def capex_bess(p, eco, pr):
    """Investimento no BESS com parcelas de potência e de energia:
    C = c_ref [(1 - f) P + f E / h_ref], com c_ref em R$/kW para um sistema de h_ref horas."""
    c_ref = eco["capex"]["bess_rs_kw"][NIVEIS.index(pr["capex"])]
    f = pr["f_energia"]
    return c_ref * ((1 - f) * potencia_bess(p) * 1e3 + f * p.bess.energia_mwh * 1e3 / pr["h_ref"])


def capex_om(p, eco, pr):
    k = NIVEIS.index(pr["capex"])
    c = eco["capex"]
    pv = c["pv_rs_kw"][k] * p.pv.potencia_pico_mw * 1e3
    bess = capex_bess(p, eco, pr)
    el = c["eletrolisador_usd_kw"][k] * eco["cambio_rs_usd"] * p.eletrolisador.potencia_max_mw * 1e3
    om = eco["om_fixo_frac"]
    om_b = bess * pr["om_bess"]
    return {"pv": pv, "bess": bess, "eletrolisador": el,
            "om": pv * om["pv"] + om_b + el * om["eletrolisador"], "om_bess": om_b}


def custo_anual_bess(p, eco, pr):
    """Custo anual equivalente do BESS: capital, O&M fixo (com augmentation) e acréscimo de uso da rede."""
    c = capex_om(p, eco, pr)
    capital = c["bess"] / fator_anuidade(pr["taxa"], eco["vida_anos"])
    rede = uso_rede(p, eco, pr, True) - uso_rede(p, eco, pr, False)
    return {"capital": capital, "om": c["om_bess"], "tust": rede, "total": capital + c["om_bess"] + rede}


def info_despacho(p):
    """Por cenário: energia injetada pelo módulo LRCAP por MW contratado, PLD médio e horas."""
    est = p.estocastico
    linhas = []
    for c in est.cenarios:
        q = parametros_cenario(p, c)
        q.horizonte.inicio, q.horizonte.dias = f"{c.ano}-01-01 00:00", dias_cenario(p, c)
        s = montar_series(q)
        dt = q.horizonte.dt_h
        linhas.append({"e_inj": float(s.ons_descarga_pu.sum() * dt), "pld_medio": float(s.pld_rs_mwh.mean()),
                       "horas": len(s) * dt})
    return linhas, est.probabilidades()


def ajuste_investimento(p, info, aux, P):
    """Q_inv(P) - Q(P), separado em (degradação do módulo LRCAP devolvida, consumo auxiliar)."""
    b, lr = p.bess, p.lrcap
    P = np.asarray(P, dtype=float)
    folga_mwh = 1 / lr.rte_referencia - 1 / (b.eficiencia_carga * b.eficiencia_descarga)   # por MWh injetado
    deg = np.zeros_like(P)
    cons = np.zeros_like(P)
    linhas, probs = info
    for d, pi in zip(linhas, probs):
        deg += pi * b.custo_degradacao_rs_mwh * d["e_inj"] * P
        aux_lr = aux * d["horas"] * P                                   # MWh/ano medidos no PMI do módulo LRCAP
        excesso = np.maximum(0.0, aux_lr - folga_mwh * d["e_inj"] * P)  # além da recarga custeada pela CONCAP
        aux_merc = aux * d["horas"] * np.maximum(0.0, potencia_bess(p) - P)
        cons += pi * d["pld_medio"] * (aux_merc + excesso)
    return deg, cons


def curva_investimento(curva, p, info, aux):
    P, Q = curva.p_cap_mw.to_numpy(), curva.q_rs.to_numpy()
    deg, cons = ajuste_investimento(p, info, aux, P)
    return P, Q + deg - cons


def oferta_com_investimento(P, Qi, q_sem, custo_anual, receitas, disp=1.0):
    """Curva de oferta quando a bateria ainda será construída.

    Para cada receita fixa R, o proponente compara não construir o BESS (lucro q_sem, oferta 0)
    com construí-lo e contratar a melhor potência: max_P {R d P + Q_inv(P)} - custo anual do BESS.
    """
    linhas = []
    for r in receitas:
        v = r * disp * P + Qi
        k = int(np.argmax(v))
        constroi = v[k] - custo_anual > q_sem
        linhas.append({"receita_fixa_rs_mw_ano": r, "p_cap_mw": P[k] if constroi else 0.0,
                       "constroi_bess": constroi, "lucro_liquido_rs": max(v[k] - custo_anual, q_sem)})
    return pd.DataFrame(linhas)


def lance_minimo(P, Qi, q_sem, custo_anual, disp=1.0):
    o = oferta_com_investimento(P, Qi, q_sem, custo_anual, RECEITAS, disp)
    ok = o[o.constroi_bess]
    return (float(ok.receita_fixa_rs_mw_ano.iloc[0]), float(ok.p_cap_mw.iloc[0])) if len(ok) else (np.nan, np.nan)


def decomposicao(p, eco, pr, curva, info, q_sem):
    """Parcelas do lance mínimo por MW ofertado: capital, O&M, TUST, consumo auxiliar e uso mercantil."""
    P, Q = curva.p_cap_mw.to_numpy(), curva.q_rs.to_numpy()
    deg, cons = ajuste_investimento(p, info, pr["aux"], P)
    custo = custo_anual_bess(p, eco, pr)
    r, pk = lance_minimo(P, Q + deg - cons, q_sem, custo["total"], pr["disp"])
    k = int(np.where(P == pk)[0][0])
    d = pr["disp"]
    # Indiferença: R d P + Q(P) + deg - cons - C = q_sem  =>  R d = C/P + cons/P + (q_sem - Q - deg)/P
    parcelas = {"capital": custo["capital"] / pk / d, "om_augmentation": custo["om"] / pk / d,
                "tust": custo["tust"] / pk / d, "consumo_auxiliar": cons[k] / pk / d,
                "uso_mercantil": (q_sem - Q[k] - deg[k]) / pk / d}
    return {"lance_minimo_rs_mw_ano": r, "p_cap_mw": pk, **parcelas, "soma_parcelas": sum(parcelas.values())}


def lucro_sem_bess(base, processos):
    """Lucro esperado nos cenários sem bateria (e, portanto, sem LRCAP)."""
    p = copy.deepcopy(base)
    p.lrcap.habilitado = False
    p.bess.energia_mwh, p.bess.potencia_carga_mw, p.bess.potencia_descarga_mw = 1e-6, 0.0, 0.0
    return avaliar_potencia(p, 0.0, processos=processos).esperado


# ------------------------------------------------------------------------------------------ gráficos
def grafico(res, P, Qi, q_sem, eco, base, saida):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    casos = ["base", "contrato_2t", "contrato_3t", "importacao", "importacao_contrato_3t", "el_10", "el_25"]
    rot = {"base": "Referência", "contrato_2t": "Contrato\n2 t/dia", "contrato_3t": "Contrato\n3 t/dia",
           "importacao": "Importação", "importacao_contrato_3t": "Import.\n+ 3 t/dia", "el_10": "Eletrol.\n10 MW",
           "el_25": "Eletrol.\n25 MW"}
    casos = [c for c in casos if c in set(res.caso)]
    cores = [(eco["taxa_central"], "#256abf"), (0.08, "#9a9a9a")]
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    for j, (taxa, cor) in enumerate(cores):
        r = res[res.taxa == taxa].set_index(["caso", "capex_nivel"]).vpl_rs / 1e6
        x = np.arange(len(casos)) + (j - 0.5) * 0.38
        cen = [r[(c, "central")] for c in casos]
        lo = [cen[k] - r[(c, "alto")] for k, c in enumerate(casos)]
        hi = [r[(c, "baixo")] - cen[k] for k, c in enumerate(casos)]
        rotulo = f"taxa de {fmt_taxa(taxa)}" + (" (central, antes de impostos)" if taxa == eco["taxa_central"]
                                                  else " (após impostos, otimista)")
        ax[0].bar(x, cen, width=0.36, color=cor, yerr=[lo, hi], capsize=3, error_kw={"lw": 0.8}, label=rotulo)
    ax[0].axhline(0, color="#1a1a1a", lw=0.8)
    ax[0].set_xticks(np.arange(len(casos)), [rot[c] for c in casos], fontsize=8)
    ax[0].set_ylabel("VPL em 15 anos [R$ mi, dez/2025]")
    ax[0].set_title("(a) VPL do projeto (barras: investimento central; traços: baixo e alto)", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8, loc="lower left")

    pr = premissas(eco)
    rs = np.arange(0, 1.6e6 + 1, 1e4)
    ganho = np.array([np.max(r * pr["disp"] * P + Qi) - q_sem for r in rs]) / 1e6
    ax[1].plot(rs / 1e3, ganho, color="#256abf", lw=2, label="Ganho anual da bateria (com − sem BESS)")
    for taxa, cor in cores:
        cs = [custo_anual_bess(base, eco, premissas(eco, capex=nv, taxa=taxa))["total"] / 1e6 for nv in NIVEIS]
        ax[1].axhspan(cs[0], cs[2], color=cor, alpha=0.15, lw=0)
        ax[1].axhline(cs[1], color=cor, lw=1.2, ls="--", label=f"Custo anual do BESS, taxa de {fmt_taxa(taxa)}")
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


def grafico_oferta(curva, P, Qi, q_sem, eco, base, dec, saida):
    """(a) curva de oferta com e sem o investimento; (b) parcelas do lance mínimo central."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rs = np.arange(0, 1.5e6 + 1, 5e3)
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={"width_ratios": [1, 1.05]})
    op = oferta(curva, rs)
    ax[0].step(rs / 1e3, op.p_cap_mw, where="post", color="#9a9a9a", lw=1.5, ls="--",
               label="Bateria existente (só custo de oportunidade)")
    for taxa, cor in [(eco["taxa_central"], "#256abf"), (0.08, "#d9731a")]:
        pr = premissas(eco, taxa=taxa)
        o = oferta_com_investimento(P, Qi, q_sem, custo_anual_bess(base, eco, pr)["total"], rs, pr["disp"])
        ax[0].step(rs / 1e3, o.p_cap_mw, where="post", color=cor, lw=2,
                   label=f"Bateria a construir, taxa de {fmt_taxa(taxa)}")
    for v, rot in [(600, "referência"), (831, "LRCAP 3/2026")]:
        ax[0].axvline(v, color="#9a9a9a", lw=0.8, ls=":")
        ax[0].annotate(rot, (v, 2), xytext=(3, 0), textcoords="offset points", fontsize=8, color="#555555")
    ax[0].set_xlabel("Receita fixa do LRCAP [R$ mil/MW·ano]")
    ax[0].set_ylabel("Potência ótima a ofertar [MW]")
    ax[0].set_title("(a) Curva de oferta com e sem o investimento no BESS", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14))

    # Cascata: parcelas positivas empilhadas até o lance; o uso mercantil desconta
    nomes = [("capital", "Capital"), ("om_augmentation", "O&M e\naugmentation"), ("tust", "Uso da\nrede"),
             ("consumo_auxiliar", "Consumo\nauxiliar"), ("uso_mercantil", "Uso\nmercantil")]
    base_y, xs = 0.0, []
    for k, (chave, rot) in enumerate(nomes):
        v = dec[chave] / 1e3
        y0, altura = (base_y, v) if v >= 0 else (base_y + v, -v)
        cor = "#256abf" if v >= 0 else "#2a9d5c"
        ax[1].bar(k, altura, bottom=y0, width=0.62, color=cor)
        texto = "0" if abs(v) < 0.5 else f"{v:.0f}".replace("-", "−")
        if altura > 60:   # rótulo dentro da barra
            ax[1].annotate(texto, (k, y0 + altura / 2), ha="center", va="center", fontsize=8, color="white")
        else:
            ax[1].annotate(texto, (k, y0 + altura), xytext=(0, 3), textcoords="offset points", ha="center",
                           fontsize=8, color="#1a1a1a")
        if k < len(nomes) - 1:
            ax[1].plot([k + 0.31, k + 0.69], [base_y + v] * 2, color="#9a9a9a", lw=0.8)
        base_y += v
        xs.append(rot)
    k = len(nomes)
    ax[1].bar(k, dec["lance_minimo_rs_mw_ano"] / 1e3, width=0.62, color="#1a1a1a")
    ax[1].annotate(f"{dec['lance_minimo_rs_mw_ano'] / 1e3:.0f}", (k, dec["lance_minimo_rs_mw_ano"] / 1e3),
                   xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, fontweight="bold")
    xs.append("Lance\nmínimo")
    for v, rot, ls in [(600, "R$ 600 mil (referência)", ":"), (831, "R$ 831 mil (LRCAP 3/2026)", "--")]:
        ax[1].axhline(v, color="#555555", lw=0.9, ls=ls, zorder=0)
        ax[1].annotate(rot, (3.5, v), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8,
                       color="#555555")
    ax[1].set_xticks(range(len(xs)), xs, fontsize=8)
    ax[1].set_ylabel("R$ mil/MW·ano")
    ax[1].set_title(f"(b) Parcelas do lance mínimo (investimento central, taxa de {fmt_taxa(eco['taxa_central'])})",
                    fontsize=10)
    ax[1].set_ylim(0, max(1300, dec["lance_minimo_rs_mw_ano"] / 1e3 * 1.12))
    for a in ax:
        a.grid(alpha=0.25, lw=0.6)
        a.spines[["top", "right"]].set_visible(False)
    ax[1].grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(saida / "curva_oferta_investimento.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------------------------------- tabelas
def lance_minimo_por_caso(base, eco, saida, processos, infos):
    """Lance mínimo (BESS a construir) para cada caso da curva de oferta, premissas centrais."""
    dirc = RAIZ / "resultados" / "curva_oferta"
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
            pr = premissas(eco, taxa=taxa)
            P, Qi = curva_investimento(curva, p, infos[caso], pr["aux"])
            r, pk = lance_minimo(P, Qi, sem[chave], custo_anual_bess(p, eco, pr)["total"], pr["disp"])
            linhas.append({"caso": caso, "descricao": desc, "taxa": taxa, "lucro_sem_bess_rs": sem[chave],
                           "lance_minimo_rs_mw_ano": r, "p_cap_mw": pk})
    df = pd.DataFrame(linhas)
    df.to_csv(saida / "lance_minimo_casos.csv", index=False)
    return df


def sensibilidade(base, eco, curva, info, q_sem, saida):
    """Lance mínimo do caso de referência com uma premissa alterada de cada vez."""
    t, a = eco["tust_geracao_rs_kw_mes"], eco["consumo_auxiliar_frac"]
    om = eco["om_fixo_frac"]["bess"]
    fe = eco["bess_fracao_energia"]
    casos = [("Central", {}),
             ("Investimento de referência de R$ 5.000/kW", {"capex": "baixo"}),
             ("Investimento de referência de R$ 6.000/kW", {"capex": "alto"}),
             (f"Referência da EPE para {eco['bess_duracao_referencia_sensibilidade_h']} h",
              {"h_ref": eco["bess_duracao_referencia_sensibilidade_h"]}),
             (f"Parcela de energia de {fe[0]:.0%}", {"f_energia": fe[0]}),
             (f"Parcela de energia de {fe[2]:.0%}", {"f_energia": fe[2]}),
             (f"Taxa de {fmt_taxa(0.08)} (após impostos)", {"taxa": 0.08}),
             (f"O&M de {om - 0.01:.1%}".replace(".", ","), {"om_bess": om - 0.01}),
             (f"O&M de {om + 0.01:.1%}".replace(".", ","), {"om_bess": om + 0.01}),
             (f"TUST de R$ {t[0]:.2f}/kW·mês".replace(".", ","), {"tust": t[0]}),
             (f"TUST de R$ {t[2]:.2f}/kW·mês".replace(".", ","), {"tust": t[2]}),
             ("Conexão não compartilhada", {"must_compartilhado": False}),
             (f"Cobrança dupla (TUST de consumo de R$ {eco['tust_consumo_rs_kw_mes']:.2f})".replace(".", ","),
              {"dupla": True}),
             ("Sem consumo auxiliar", {"aux": a[0]}),
             (f"Consumo auxiliar de {a[2]:.0%}", {"aux": a[2]}),
             (f"Disponibilidade de {eco['disponibilidade_sensibilidade']:.0%}",
              {"disp": eco["disponibilidade_sensibilidade"]})]
    linhas = []
    for nome, troca in casos:
        pr = premissas(eco, **troca)
        dec = decomposicao(base, eco, pr, curva, info, q_sem)
        linhas.append({"caso": nome, "capex_nivel": pr["capex"], "taxa": pr["taxa"], "om_bess_frac": pr["om_bess"],
                       "duracao_referencia_h": pr["h_ref"], "fracao_energia": pr["f_energia"],
                       "tust_rs_kw_mes": pr["tust"], "must_compartilhado": pr["must_compartilhado"],
                       "cobranca_dupla": pr["dupla"], "consumo_auxiliar_frac": pr["aux"], "disponibilidade": pr["disp"],
                       "capex_bess_rs": capex_bess(base, eco, pr), **dec})
    df = pd.DataFrame(linhas)
    df.to_csv(saida / "lance_sensibilidade.csv", index=False)
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

    print("Energia despachada pelo ONS por caso...", flush=True)
    infos = {caso: info_despacho(aplicar(base, ajustes)) for caso, (_, ajustes) in CASOS.items()
             if (dirc / f"{caso}.csv").exists()}

    # VPL do empreendimento com a receita de referência
    linhas = []
    for caso, (desc, ajustes) in CASOS.items():
        if caso not in infos:
            continue
        p = aplicar(base, ajustes)
        curva = pd.read_csv(dirc / f"{caso}.csv")
        op = pd.read_csv(dirc / f"{caso}_operacao.csv", index_col=0)["valor"]
        for nivel in NIVEIS:
            for i in eco["taxas_desconto"]:
                pr = premissas(eco, capex=nivel, taxa=i)
                P, Qi = curva_investimento(curva, p, infos[caso], pr["aux"])
                v = r_ref * pr["disp"] * P + Qi
                k = int(np.argmax(v))
                c = capex_om(p, eco, pr)
                capex = c["pv"] + c["bess"] + c["eletrolisador"]
                rede = uso_rede(p, eco, pr, True)
                fluxo = v[k] - c["om"] - rede
                fa = fator_anuidade(i, n)
                vpl = -capex + fa * fluxo
                h2 = op["h2_vendido_kg"]
                linhas.append({
                    "caso": caso, "descricao": desc, "capex_nivel": nivel, "taxa": i, "p_cap_mw": P[k],
                    "lucro_operacional_rs": v[k], "om_fixo_rs": c["om"], "uso_rede_rs": rede,
                    "capex_pv_rs": c["pv"], "capex_bess_rs": c["bess"], "capex_el_rs": c["eletrolisador"],
                    "capex_total_rs": capex, "fluxo_anual_rs": fluxo, "vpl_rs": vpl, "tir": tir(capex, fluxo, n),
                    "h2_vendido_kg": h2,
                    "preco_h2_equilibrio_rs_kg": p.hidrogenio.preco_venda_rs_kg - vpl / (fa * h2),
                })
    res = pd.DataFrame(linhas)
    res.to_csv(saida / "viabilidade.csv", index=False)

    # Valor da bateria e lance mínimo no caso de referência, por nível de investimento e taxa
    curva = pd.read_csv(dirc / "base.csv")
    bat = []
    for nivel in NIVEIS:
        for i in eco["taxas_desconto"]:
            pr = premissas(eco, capex=nivel, taxa=i)
            P, Qi = curva_investimento(curva, base, infos["base"], pr["aux"])
            custo = custo_anual_bess(base, eco, pr)
            ganho = float(np.max(r_ref * pr["disp"] * P + Qi) - q_sem)
            r, pk = lance_minimo(P, Qi, q_sem, custo["total"], pr["disp"])
            bat.append({"capex_nivel": nivel, "taxa": i, "custo_anual_bess_rs": custo["total"],
                        "custo_capital_rs": custo["capital"], "custo_om_rs": custo["om"], "custo_tust_rs": custo["tust"],
                        "custo_anual_bess_rs_mw": custo["total"] / potencia_bess(base),
                        "ganho_bess_ref_rs": ganho, "vpl_bess_ref_rs": fator_anuidade(i, n) * (ganho - custo["total"]),
                        "lance_minimo_rs_mw_ano": r, "p_cap_no_lance_minimo_mw": pk})
    bat = pd.DataFrame(bat)
    bat.to_csv(saida / "lance_minimo.csv", index=False)

    pr = premissas(eco)
    P, Qi = curva_investimento(curva, base, infos["base"], pr["aux"])
    sens = sensibilidade(base, eco, curva, infos["base"], q_sem, saida)
    dec = sens.iloc[0].to_dict()
    grafico(res, P, Qi, q_sem, eco, base, saida)
    grafico_oferta(curva, P, Qi, q_sem, eco, base, dec, saida)
    lmc = lance_minimo_por_caso(base, eco, saida, args.processos, infos)
    pd.DataFrame({c: {k: float(np.dot(probs, [d[k] for d in linhas])) for k in ["e_inj", "pld_medio", "horas"]}
                  for c, (linhas, probs) in infos.items()}).T.to_csv(saida / "despacho_ons_casos.csv")

    pd.set_option("display.width", 250)
    pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
    cen = res[(res.capex_nivel == "central")]
    t = cen.pivot_table(index="caso", columns="taxa", values=["lucro_operacional_rs", "vpl_rs", "tir",
                                                               "preco_h2_equilibrio_rs_kg"])
    print(f"Lucro sem bateria: R$ {q_sem / 1e6:.2f} mi/ano\n")
    print(t.to_string())
    print("\nLance mínimo e valor da bateria (caso de referência):")
    print(bat.to_string(index=False))
    print("\nSensibilidade e parcelas do lance mínimo (caso de referência):")
    print(sens[["caso", "taxa", "capex_bess_rs", "lance_minimo_rs_mw_ano", "p_cap_mw", "capital", "om_augmentation",
                "tust", "consumo_auxiliar", "uso_mercantil"]].to_string(index=False))
    print("\nLance mínimo por caso:")
    print(lmc.pivot_table(index="caso", columns="taxa", values=["lance_minimo_rs_mw_ano", "p_cap_mw"]).to_string())
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
