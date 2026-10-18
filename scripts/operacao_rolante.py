"""Operação em horizonte rolante (controle preditivo): quanto do lucro de previsão perfeita é alcançável.

A cada hora t, resolve o MILP de operação numa janela [t, t + H) com:
  - o PLD conhecido na janela (PLD horário publicado na véspera, D-1);
  - o perfil de despacho do ONS conhecido;
  - a geração FV da hora t medida e, nas horas seguintes, uma previsão;
  - os estados reais do módulo mercantil, do tanque e do eletrolisador (ligado ou não) em t.
Só a decisão da hora t é executada; na hora seguinte o problema é resolvido de novo. A janela não
impõe estado final (os estados ao fim de H horas ficam livres), como é usual no controle preditivo.

Previsões da geração FV:
  perfeita     a geração realizada (isola o efeito da janela finita);
  persistencia a geração da mesma hora do dia anterior.

O lucro operacional realizado é apurado com os dados reais e comparado com o da operação de
previsão perfeita no ano (blocos semanais, maior limite entre as fronteiras lp e cíclica).

Uso:  python scripts/operacao_rolante.py [--ano 2025] [--p-cap 55] [--janela 48]
          [--previsao persistencia] [--dias N] [--referencia]
"""

import argparse
import copy
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyomo.environ as pyo

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros, montar_series  # noqa: E402
from pvbess_h2.decomposicao import _solver, operacao_anual  # noqa: E402
from pvbess_h2.estocastico import dias_cenario, parametros_cenario  # noqa: E402
from pvbess_h2.modelo import construir_modelo  # noqa: E402

SAIDA = RAIZ / "resultados" / "operacao_rolante"


def cenario(base, ano):
    c = next(c for c in base.estocastico.cenarios if c.ano == ano)
    q = parametros_cenario(base, c)
    q.horizonte.inicio, q.horizonte.dias = f"{ano}-01-01 00:00", dias_cenario(base, c)
    return q


def previsao_pv(s, tipo):
    pv = s["pv_disp_mw"].to_numpy()
    if tipo == "perfeita":
        return pv.copy()
    if tipo == "persistencia":
        f = np.roll(pv, 24)
        f[:24] = pv[:24]
        return f
    raise ValueError(tipo)


def custo_recarga_anual(q, s, p_cap):
    """Recarga do módulo LRCAP acima de injetada/RTE de referência, apurada no ano (R$)."""
    dt, rte = q.horizonte.dt_h, q.lrcap.rte_referencia
    er, ei = float((s.ons_recarga_pu * dt).sum()), float((s.ons_descarga_pu * dt).sum())
    f = max(0.0, er - ei / rte) / er if er > 0 else 0.0
    return f * float((s.pld_rs_mwh * s.ons_recarga_pu * dt).sum()) * p_cap


def lucro(q, s, op, p_cap):
    """Lucro operacional (sem receita fixa) de uma trajetória horária, com os dados reais."""
    dt, h2, el, b = q.horizonte.dt_h, q.hidrogenio, q.eletrolisador, q.bess
    on = (op["p_eletrolisador_mw"].to_numpy() > 1e-6).astype(int)
    partidas = int(on[0] + ((on[1:] == 1) & (on[:-1] == 0)).sum())
    pld = s["pld_rs_mwh"].to_numpy()
    parc = {
        "receita_mcp_rs": float((pld * op["p_exportacao_mw"]).sum() * dt),
        "custo_importacao_rs": float(((pld + q.rede.custo_adicional_importacao_rs_mwh)
                                      * op["p_importacao_mw"]).sum() * dt),
        "receita_h2_rs": float(h2.preco_venda_rs_kg * op["venda_h2_kg_h"].sum() * dt),
        "custo_h2_rs": float(el.custo_variavel_rs_kg * op["producao_h2_kg_h"].sum() * dt
                             + el.custo_partida_rs * partidas),
        "custo_degradacao_rs": float(b.custo_degradacao_rs_mwh
                                     * (op["p_descarga_bess_mw"] + s["ons_descarga_pu"] * p_cap).sum() * dt),
        "custo_recarga_lrcap_rs": custo_recarga_anual(q, s, p_cap),
    }
    parc["lucro_operacional_rs"] = (parc["receita_mcp_rs"] + parc["receita_h2_rs"] - parc["custo_importacao_rs"]
                                    - parc["custo_h2_rs"] - parc["custo_degradacao_rs"]
                                    - parc["custo_recarga_lrcap_rs"])
    parc.update({"partidas": partidas, "h2_vendido_kg": float(op["venda_h2_kg_h"].sum() * dt),
                 "energia_exportada_mwh": float(op["p_exportacao_mw"].sum() * dt),
                 "energia_eletrolisador_mwh": float(op["p_eletrolisador_mw"].sum() * dt),
                 "descarga_mercantil_mwh": float(op["p_descarga_bess_mw"].sum() * dt),
                 "horas_eletrolisador_ligado": int(on.sum()),
                 "tanque_final_kg": float(op["tanque_h2_kg"].iloc[-1]),
                 "soc_final_mwh": float(op["soc_mwh"].iloc[-1])})
    return parc


def rolante(q, s, p_cap, janela, previsao, horas):
    q = copy.deepcopy(q)
    q.lrcap.potencia_fixa_mw = p_cap
    q.horizonte.nivel_inicial_livre = False
    q.horizonte.partida_ciclica = False
    b, h2 = q.bess, q.hidrogenio
    e_merc = b.energia_mwh - q.lrcap.energia_por_mw_h * p_cap
    f = previsao_pv(s, previsao)
    soc = (b.soc_inicial_frac if b.soc_inicial_frac is not None else 0.5) * e_merc
    tanque, ligado = h2.tanque_inicial_kg, False
    opt = _solver(1e-4)
    opt.config.load_solution = True
    linhas, t0 = [], time.time()
    for t in range(horas):
        w = s.iloc[t:min(t + janela, len(s))].copy()
        w.iloc[1:, w.columns.get_loc("pv_disp_mw")] = f[t + 1:t + len(w)]
        qw = copy.deepcopy(q)
        qw.bess.soc_inicial_frac = min(max(soc / e_merc, b.soc_min_frac), b.soc_max_frac)
        qw.hidrogenio.tanque_inicial_kg = min(max(tanque, 0.0), h2.tanque_max_kg)
        m = construir_modelo(qw, w)
        m.soc_final.deactivate()
        m.tanque_final.deactivate()
        if ligado and hasattr(m, "partida_el") and 0 in m.partida_el:
            m.partida_el[0].deactivate()
        opt.solve(m)
        v = lambda var: float(pyo.value(var[0]))  # noqa: E731
        linha = {"p_pv_mw": v(m.p_pv), "p_carga_bess_mw": v(m.p_ch), "p_descarga_bess_mw": v(m.p_dis),
                 "p_eletrolisador_mw": v(m.p_el), "p_exportacao_mw": v(m.p_exp), "p_importacao_mw": v(m.p_imp),
                 "producao_h2_kg_h": v(m.m_h2), "venda_h2_kg_h": v(m.v_h2), "soc_mwh": v(m.soc),
                 "tanque_h2_kg": v(m.s_h2)}
        linhas.append(linha)
        soc, tanque, ligado = linha["soc_mwh"], linha["tanque_h2_kg"], linha["p_eletrolisador_mw"] > 1e-6
        if (t + 1) % 720 == 0:
            print(f"  [{previsao}] {t + 1} h  ({time.time() - t0:.0f} s)", flush=True)
    return pd.DataFrame(linhas, index=s.index[:horas])


def referencia(q, p_cap, processos):
    """Previsão perfeita no ano: maior lucro entre as fronteiras lp e cíclica, por blocos semanais."""
    melhor = None
    for fr in ("lp", "ciclica"):
        df, _ = operacao_anual(q, q.horizonte.inicio, q.horizonte.dias, p_cap, processos=processos, fronteira=fr)
        par = lucro(q, df, df, p_cap)
        print(f"  previsão perfeita, fronteira {fr}: R$ {par['lucro_operacional_rs'] / 1e6:.3f} mi", flush=True)
        if melhor is None or par["lucro_operacional_rs"] > melhor[1]["lucro_operacional_rs"]:
            melhor = (df, par)
    return melhor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--ano", type=int, default=2025)
    ap.add_argument("--p-cap", type=float, default=55.0)
    ap.add_argument("--janela", type=int, default=48, help="horas da janela de otimização")
    ap.add_argument("--previsao", default="persistencia", choices=["persistencia", "perfeita"])
    ap.add_argument("--dias", type=int, help="limita a simulação aos primeiros N dias (teste)")
    ap.add_argument("--referencia", action="store_true", help="calcula a operação de previsão perfeita")
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    SAIDA.mkdir(parents=True, exist_ok=True)

    base = carregar_parametros(args.config)
    q = cenario(base, args.ano)
    s = montar_series(q)
    rot = f"{args.ano}_{args.p_cap:g}MW"
    if args.referencia:
        df, par = referencia(q, args.p_cap, args.processos)
        df.to_csv(SAIDA / f"perfeita_{rot}.csv")
        pd.Series(par).to_csv(SAIDA / f"resumo_perfeita_{rot}.csv", header=["valor"])
        return

    horas = len(s) if args.dias is None else 24 * args.dias
    op = rolante(q, s, args.p_cap, args.janela, args.previsao, horas)
    par = lucro(q, s.iloc[:horas], op, args.p_cap)
    sufixo = f"{args.previsao}_j{args.janela}_{rot}" + (f"_{args.dias}d" if args.dias else "")
    op.to_csv(SAIDA / f"rolante_{sufixo}.csv")
    pd.Series(par).to_csv(SAIDA / f"resumo_rolante_{sufixo}.csv", header=["valor"])
    print(pd.Series(par).to_string())


if __name__ == "__main__":
    main()
