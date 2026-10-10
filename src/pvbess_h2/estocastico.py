"""Programa estocástico de dois estágios com CVaR, resolvido por Benders.

1º estágio: potência contratada no LRCAP, P (0 ou entre o mínimo e o máximo viável).
2º estágio: operação em cada cenário anual s (um ano histórico de PLD e FV), dividida em
blocos semanais w com condição cíclica — cada par (s, w) é um subproblema MILP.

    max  sum_s pi_s Pi_s + beta * CVaR_alpha(Pi)
    Pi_s = R_cap * P + sum_w Q_{s,w}(P)

O CVaR entra no mestre pela forma de Rockafellar–Uryasev:
    CVaR_alpha(Pi) = max_zeta  zeta - 1/(1-alpha) * sum_s pi_s (zeta - Pi_s)^+
Os cortes reforçados (Zou, Ahmed e Sun, 2019) limitam cada Q_{s,w} por cima; como o
objetivo é não decrescente em cada Pi_s, o valor do mestre é um limite superior válido.
"""

from __future__ import annotations

import calendar
import copy
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyomo.environ as pyo

from .decomposicao import _fronteiras_lp, _gap, _solver, avaliar_bloco, dividir_em_blocos
from .modelo import potencia_lrcap_max
from .parametros import Cenario, Parametros


def parametros_cenario(p: Parametros, c: Cenario) -> Parametros:
    q = copy.deepcopy(p)
    q.pv.arquivo = c.pv_arquivo
    q.mercado.arquivo = c.pld_arquivo
    q.mercado.fator_preco = c.fator_preco
    return q


def dias_cenario(p: Parametros, c: Cenario) -> int:
    return p.estocastico.dias_por_cenario or (366 if calendar.isleap(c.ano) else 365)


def blocos_cenario(p: Parametros, c: Cenario) -> list[tuple[Parametros, str, int]]:
    q = parametros_cenario(p, c)
    return [(q, ini, d) for ini, d in dividir_em_blocos(f"{c.ano}-01-01", dias_cenario(p, c), p.estocastico.dias_bloco)]


def cvar(valores, probs, alpha: float) -> float:
    """CVaR_alpha de um lucro (média da cauda inferior de massa 1 - alpha)."""
    v, pr = np.asarray(valores, float), np.asarray(probs, float)
    return max(z - (pr * np.maximum(z - v, 0)).sum() / (1 - alpha) for z in v)


def objetivo(valores, probs, alpha: float, beta: float) -> float:
    return float(np.dot(probs, valores)) + beta * cvar(valores, probs, alpha)


@dataclass
class Avaliacao:
    p_cap: float
    lucro_cenarios: list[float]      # Pi_s (R$/ano)
    esperado: float
    cvar: float
    objetivo: float
    limite_superior: list[float] | None = None   # relaxação linear de cada cenário (fronteira "lp")


def _executar(tarefas, processos):
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        return list(ex.map(avaliar_bloco, tarefas, chunksize=4))


def avaliar_potencia(p: Parametros, x: float, processos: int = 4, gap_sub: float = 1e-4) -> Avaliacao:
    """Lucro de cada cenário com P_cap = x fixo (sem cortes).

    Com estocastico.fronteira_blocos = "lp", os estados na fronteira dos blocos vêm da
    relaxação linear de cada ano (decomposicao.fronteiras_lp), cujo valor também é
    devolvido como limite superior do lucro de cada cenário.
    """
    est = p.estocastico
    probs = est.probabilidades()
    blocos = [(s, b) for s, c in enumerate(est.cenarios) for b in blocos_cenario(p, c)]
    if est.fronteira_blocos == "lp":
        anos = [(parametros_cenario(p, c), f"{c.ano}-01-01", dias_cenario(p, c), x, est.dias_bloco)
                for c in est.cenarios]
        with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
            lps = list(ex.map(_fronteiras_lp, anos))
        fronteiras = [f for _, fs in lps for f in fs]
        res = _executar([(q, ini, d, x, gap_sub, True, f) for (_, (q, ini, d)), f in zip(blocos, fronteiras)],
                        processos)
        av = _resumir(p, x, blocos, res, probs)
        av.limite_superior = [p.lrcap.receita_fixa_rs_mw_ano * x + ub for ub, _ in lps]
        return av
    res = _executar([(q, ini, d, x, gap_sub, True) for _, (q, ini, d) in blocos], processos)
    return _resumir(p, x, blocos, res, probs)


def _resumir(p, x, blocos, res, probs):
    est = p.estocastico
    lucro = [p.lrcap.receita_fixa_rs_mw_ano * x] * len(est.cenarios)
    for (s, _), r in zip(blocos, res):
        lucro[s] += r.q
    return Avaliacao(x, lucro, float(np.dot(probs, lucro)), cvar(lucro, probs, est.alpha),
                     objetivo(lucro, probs, est.alpha, est.beta))


def resolver_estocastico(p: Parametros, tol: float = 1e-3, max_iter: int = 30,
                         gap_sub: float = 1e-4, processos: int = 4, verbose: bool = True,
                         memoria: dict | None = None):
    """Retorna (melhor Avaliacao, histórico DataFrame, cortes DataFrame).

    `memoria` (dict, reaproveitado entre chamadas com os mesmos cenários) guarda cortes e
    lucros por cenário já avaliados: os cortes não dependem de alpha e beta, então uma
    fronteira risco x retorno reaproveita o trabalho das rodadas anteriores.
    """
    memoria = {} if memoria is None else memoria
    memoria.setdefault("cortes", [])
    memoria.setdefault("lucros", {})
    est = p.estocastico
    probs = est.probabilidades()
    S = range(len(est.cenarios))
    blocos = [(s, b) for s in S for b in blocos_cenario(p, est.cenarios[s])]
    W = {s: [i for i, (ss, _) in enumerate(blocos) if ss == s] for s in S}
    p_max = potencia_lrcap_max(p)
    p_min = p.lrcap.potencia_min_mw if p_max > 0 else 0.0
    r_cap = p.lrcap.receita_fixa_rs_mw_ano

    ms = pyo.ConcreteModel()
    ms.B = pyo.RangeSet(0, len(blocos) - 1)
    ms.S = pyo.Set(initialize=list(S))
    ms.P = pyo.Var(bounds=(0, p_max))
    ms.w = pyo.Var(within=pyo.Binary)
    ms.theta = pyo.Var(ms.B)
    ms.zeta = pyo.Var()
    ms.nu = pyo.Var(ms.S, within=pyo.NonNegativeReals)
    ms.cmin = pyo.Constraint(expr=ms.P >= p_min * ms.w)
    ms.cmax = pyo.Constraint(expr=ms.P <= p_max * ms.w)
    ms.Pi = pyo.Expression(ms.S, rule=lambda m, s: r_cap * m.P + sum(m.theta[i] for i in W[s]))
    ms.cauda = pyo.Constraint(ms.S, rule=lambda m, s: m.nu[s] >= m.zeta - m.Pi[s])
    ms.cortes = pyo.ConstraintList()
    ms.obj = pyo.Objective(
        expr=sum(probs[s] * ms.Pi[s] for s in S)
        + est.beta * (ms.zeta - sum(probs[s] * ms.nu[s] for s in S) / (1 - est.alpha)),
        sense=pyo.maximize)
    if est.beta == 0:
        ms.zeta.fix(0)
    opt = _solver(1e-9)
    opt.config.load_solution = True

    hist, cortes, avaliados = [], memoria["cortes"], {}
    melhor: Avaliacao | None = None
    t0 = time.time()
    for c in cortes:
        ms.cortes.add(ms.theta[c["bloco"]] <= c["c_rs"] + c["lambda_rs_mw"] * ms.P)
    for x, lucro in memoria["lucros"].items():
        av = Avaliacao(x, lucro, float(np.dot(probs, lucro)), cvar(lucro, probs, est.alpha),
                       objetivo(lucro, probs, est.alpha, est.beta))
        avaliados[x] = av
        if melhor is None or av.objetivo > melhor.objetivo:
            melhor = av

    def avaliar(x, it, ub):
        nonlocal melhor
        res = _executar([(q, ini, d, x, gap_sub) for _, (q, ini, d) in blocos], processos)
        for i, r in enumerate(res):
            ms.cortes.add(ms.theta[i] <= r.c + r.lam * ms.P)
            cortes.append({"iteracao": it, "cenario": blocos[i][0], "bloco": i, "p_cap_mw": x,
                           "q_rs": r.q, "lambda_rs_mw": r.lam, "c_rs": r.c})
        av = _resumir(p, x, blocos, res, probs)
        avaliados[round(x, 6)] = av
        memoria["lucros"][round(x, 6)] = av.lucro_cenarios
        if melhor is None or av.objetivo > melhor.objetivo:
            melhor = av
        hist.append({"iteracao": it, "p_cap_mw": x, "objetivo_rs": av.objetivo,
                     "esperado_rs": av.esperado, "cvar_rs": av.cvar,
                     "limite_inferior_rs": melhor.objetivo, "limite_superior_rs": ub,
                     "tempo_s": time.time() - t0})
        if verbose:
            print(f"it {it:2d}  P_cap = {x:7.3f} MW  E = {av.esperado / 1e6:8.3f}  CVaR = "
                  f"{av.cvar / 1e6:8.3f}  obj = {av.objetivo / 1e6:8.3f} mi  LB = {melhor.objetivo / 1e6:8.3f}"
                  f"  UB = {ub / 1e6:9.3f}  gap = {_gap(ub, melhor.objetivo):7.3%}  [{time.time() - t0:5.0f} s]",
                  flush=True)

    for x in [0.0] + ([p_min, p_max] if p_max > 0 else []):
        if round(x, 6) not in avaliados:
            avaliar(x, 0, float("inf"))

    for it in range(1, max_iter + 1):
        r = opt.solve(ms)
        ub, x = r.best_objective_bound, round(pyo.value(ms.P), 6)
        fim = _gap(ub, melhor.objetivo) <= tol or x in avaliados
        if fim:
            hist.append({"iteracao": it, "p_cap_mw": x, "objetivo_rs": np.nan, "esperado_rs": np.nan,
                         "cvar_rs": np.nan, "limite_inferior_rs": melhor.objetivo,
                         "limite_superior_rs": ub, "tempo_s": time.time() - t0})
            if verbose:
                motivo = "convergiu" if _gap(ub, melhor.objetivo) <= tol else f"mestre repropôs {x} MW"
                print(f"Fim ({motivo}): gap {_gap(ub, melhor.objetivo):.3%}")
            break
        avaliar(x, it, ub)

    return melhor, pd.DataFrame(hist), pd.DataFrame(cortes)
