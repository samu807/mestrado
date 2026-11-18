"""Teste: a curva de oferta da H1 em uma única corrida de Benders, com os cortes compartilhados entre receitas.

Os cortes de Benders dos subproblemas (cenário, semana) não dependem da receita fixa R; só o objetivo do mestre
depende. Aqui, o mestre é resolvido para uma sequência de receitas, reaproveitando os cortes e as avaliações já
feitas, e só se avalia um novo P_cap quando o mestre o propõe. Compara-se, com a curva por grade (`faixas_2t.csv`):
(i) quantas avaliações completas (todos os blocos) foram necessárias; (ii) a potência ótima P*(R); (iii) o
envelope de cortes, que é um limite superior de Q(P), contra o Q(P) da grade.

Uso:  python scripts/teste_curva_unica_benders.py config/estocastico_unifei_faixas.yaml [--receitas 600 400 300 200 100]
Saída: resultados/curva_oferta/teste_benders_unico/{resumo.csv,cortes.csv,envelope.csv,avaliacoes.csv}
"""
import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyomo.environ as pyo

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))


def main():
    from pvbess_h2 import carregar_parametros
    from pvbess_h2.decomposicao import _solver
    from pvbess_h2.estocastico import _executar, blocos_cenario, fracao_cenario
    from pvbess_h2.modelo import potencia_lrcap_max

    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--receitas", type=float, nargs="+", default=[600, 400, 300, 200, 100], help="R$ mil/(MW·ano), em ordem")
    ap.add_argument("--tol", type=float, default=1e-3)
    ap.add_argument("--max-iter", type=int, default=15)
    ap.add_argument("--processos", type=int, default=4)
    ap.add_argument("--gap-sub", type=float, default=1e-4)
    ap.add_argument("--subdir", default="curva_oferta/teste_benders_unico")
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    p = carregar_parametros(args.config)
    est = p.estocastico
    assert est.beta == 0, "o teste usa o lucro esperado (beta = 0)"
    probs = est.probabilidades()
    S = range(len(est.cenarios))
    blocos = [(s, b) for s in S for b in blocos_cenario(p, est.cenarios[s])]
    peso = [probs[s] * fracao_cenario(p, est.cenarios[s]) for s, _ in blocos]  # peso de cada bloco no lucro esperado
    frac = sum(probs[s] * fracao_cenario(p, est.cenarios[s]) for s in S)        # fração média do ano (1 se ano completo)
    p_max = potencia_lrcap_max(p)
    p_min = p.lrcap.potencia_min_mw
    saida = RAIZ / "resultados" / args.subdir
    saida.mkdir(parents=True, exist_ok=True)

    cache, cortes, aval = {}, [], []
    t0 = time.time()

    def avaliar(x):
        res = _executar([(q, ini, d, x, args.gap_sub) for _, (q, ini, d) in blocos], args.processos)
        cache[round(x, 6)] = sum(w * r.q for w, r in zip(peso, res))
        for i, r in enumerate(res):
            cortes.append({"bloco": i, "p_cap_mw": x, "q_rs": r.q, "lambda_rs_mw": r.lam, "c_rs": r.c})
        aval.append({"ordem": len(aval) + 1, "p_cap_mw": x, "q_esperado_rs": cache[round(x, 6)], "tempo_s": time.time() - t0})
        print(f"  avaliação {len(aval)}: P_cap = {x:.3f} MW  Q = R$ {cache[round(x, 6)] / 1e6:.3f} mi  [{time.time() - t0:.0f} s]", flush=True)

    def mestre(r_rs):
        ms = pyo.ConcreteModel()
        ms.B = pyo.RangeSet(0, len(blocos) - 1)
        ms.P = pyo.Var(bounds=(0, p_max)); ms.w = pyo.Var(within=pyo.Binary); ms.theta = pyo.Var(ms.B)
        ms.c1 = pyo.Constraint(expr=ms.P >= p_min * ms.w); ms.c2 = pyo.Constraint(expr=ms.P <= p_max * ms.w)
        ms.cortes = pyo.ConstraintList()
        for c in cortes:
            ms.cortes.add(ms.theta[c["bloco"]] <= c["c_rs"] + c["lambda_rs_mw"] * ms.P)
        ms.obj = pyo.Objective(expr=r_rs * frac * ms.P + sum(peso[i] * ms.theta[i] for i in ms.B), sense=pyo.maximize)
        opt = _solver(1e-9); opt.config.load_solution = True
        r = opt.solve(ms)
        return round(pyo.value(ms.P), 6), r.best_objective_bound

    for x in (0.0, p_min, p_max):
        avaliar(x)
    linhas = []
    for r_mil in args.receitas:
        r_rs = r_mil * 1e3
        n0 = len(aval)
        lb_de = lambda x: r_rs * frac * x + cache[round(x, 6)]
        for it in range(args.max_iter + 1):
            x, ub = mestre(r_rs)
            melhor = max(cache, key=lb_de); lb = lb_de(melhor)
            gap = (ub - lb) / abs(lb)
            if gap <= args.tol or round(x, 6) in cache:
                break
            avaliar(x)
        melhor = max(cache, key=lb_de); lb = lb_de(melhor)
        linhas.append({"receita_mil": r_mil, "p_otimo_mw": melhor, "lucro_rs": lb, "limite_superior_rs": ub, "gap": (ub - lb) / abs(lb),
                       "novas_avaliacoes": len(aval) - n0, "avaliacoes_acumuladas": len(aval), "tempo_s": time.time() - t0})
        print(f"R = {r_mil:.0f} mil: P* = {melhor} MW, gap {linhas[-1]['gap']:.3%}, novas avaliações {linhas[-1]['novas_avaliacoes']}", flush=True)
        pd.DataFrame(linhas).to_csv(saida / "resumo.csv", index=False)
    pd.DataFrame(cortes).to_csv(saida / "cortes.csv", index=False)
    pd.DataFrame(aval).to_csv(saida / "avaliacoes.csv", index=False)
    # envelope de cortes (limite superior de Q) contra a curva por grade
    ct = pd.DataFrame(cortes)
    ref = pd.read_csv(RAIZ / "resultados" / "curva_oferta" / "faixas_2t.csv")
    env = []
    for P in ref.p_cap_mw:
        if P != 0 and P < p_min:
            continue
        q_env = sum(peso[b] * (g.c_rs + g.lambda_rs_mw * P).min() for b, g in ct.groupby("bloco"))
        env.append({"p_cap_mw": P, "q_grade_rs": float(ref.loc[ref.p_cap_mw == P, "q_rs"].iloc[0]), "q_envelope_rs": q_env})
    env = pd.DataFrame(env); env["dif_rs"] = env.q_envelope_rs - env.q_grade_rs; env["dif_pct"] = env.dif_rs / env.q_grade_rs
    env.to_csv(saida / "envelope.csv", index=False)
    print(env.assign(q_grade_mi=env.q_grade_rs / 1e6, q_env_mi=env.q_envelope_rs / 1e6)[["p_cap_mw", "q_grade_mi", "q_env_mi", "dif_pct"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
