"""Decomposição de Benders para o problema anual, com cortes de Benders reforçados.

Estrutura: a potência contratada no LRCAP (P_cap) é a única variável que acopla os
blocos do ano (semanas). Cada bloco é resolvido de forma independente, com estados
cíclicos (SOC do módulo mercantil e estoque de H2 terminam no valor inicial).

    max  R_cap * P_cap * horas/8760 + sum_w Q_w(P_cap)
    s.a. P_cap = 0 ou P_min <= P_cap <= P_max

Q_w é o lucro operacional ótimo do bloco w com P_cap fixo. Como os subproblemas têm
variáveis binárias, Q_w não é côncava em geral e o corte de Benders clássico (dual do
LP) não é válido. Usa-se o corte de Benders reforçado (Zou, Ahmed & Sun, 2019,
Math. Programming 175:461-502): com lambda = dual da restrição de cópia no LP
relaxado,

    C_w(lambda) = max { f_w(y, z) - lambda * z : (y, z) viável no MILP do bloco }
    Q_w(x) <= C_w(lambda) + lambda * x     para todo x   (corte válido)

C_w é tomado como o LIMITE DUAL do solver (não a solução incumbente), o que mantém o
corte válido mesmo sem otimalidade exata. O mestre fornece um limite superior (UB) e
cada avaliação de P_cap fornece uma solução viável (LB); o gap UB-LB certifica a
qualidade da solução.
"""

from __future__ import annotations

import copy
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import pandas as pd
import pyomo.environ as pyo
from pyomo.contrib.appsi.solvers import Highs

from .dados import montar_series
from .modelo import construir_modelo, potencia_lrcap_max
from .parametros import Parametros
from .resultados import indicadores, serie_resultados


# ----------------------------------------------------------------------------- blocos
def dividir_em_blocos(inicio: str, dias: int, dias_bloco: int = 7) -> list[tuple[str, int]]:
    """Divide o horizonte em blocos de `dias_bloco` dias; o último absorve o resto."""
    n = max(dias // dias_bloco, 1)
    t0 = pd.Timestamp(inicio)
    blocos = []
    for i in range(n):
        d = dias_bloco if i < n - 1 else dias - dias_bloco * (n - 1)
        blocos.append((str(t0 + pd.Timedelta(days=dias_bloco * i)), d))
    return blocos


def _params_bloco(p: Parametros, inicio: str, dias: int) -> Parametros:
    q = copy.deepcopy(p)
    q.horizonte.inicio, q.horizonte.dias = inicio, dias
    q.lrcap.potencia_fixa_mw = None
    return q


def _solver(gap: float, threads: int = 1) -> Highs:
    opt = Highs()
    opt.config.mip_gap = gap
    # Uma thread por subproblema: o paralelismo é entre blocos (processos). Várias
    # threads do HiGHS por processo disputam os núcleos e degradam o desempenho.
    opt.highs_options = {"threads": threads}
    opt.config.stream_solver = False
    opt.config.load_solution = False
    return opt


def _construir_subproblema(q: Parametros):
    s = montar_series(q)
    m = construir_modelo(q, s)
    # Receita fixa vai para o mestre; o subproblema tem só o lucro operacional.
    m.lucro.deactivate()
    m.f_oper = pyo.Expression(expr=m.lucro.expr - m.receita_lrcap)
    m.obj = pyo.Objective(expr=m.f_oper, sense=pyo.maximize)
    m.x_hat = pyo.Param(initialize=0.0, mutable=True)
    m.copia = pyo.Constraint(expr=m.P_cap == m.x_hat)
    return m, s


def _binarias(m) -> list:
    return [v for v in m.component_data_objects(pyo.Var) if v.domain is pyo.Binary]


@dataclass
class ResultadoBloco:
    q: float          # lucro operacional ótimo (incumbente) com P_cap = x_hat
    lam: float        # inclinação do corte
    c: float          # intercepto do corte (limite dual do MILP lagrangiano)


def avaliar_bloco(args) -> ResultadoBloco:
    """Resolve um bloco em x_hat: valor viável Q e corte reforçado (lam, c)."""
    p, inicio, dias, x_hat, gap = args
    q = _params_bloco(p, inicio, dias)
    m, _ = _construir_subproblema(q)
    m.x_hat = x_hat
    opt = _solver(gap)

    # 1) MILP com P_cap fixo: solução viável (limite inferior)
    r = opt.solve(m)
    q_val = r.best_feasible_objective

    # 2) LP relaxado com P_cap fixo: dual da restrição de cópia
    binarias = _binarias(m)
    for v in binarias:
        v.domain = pyo.UnitInterval
    r = opt.solve(m)
    lam = r.solution_loader.get_duals([m.copia])[m.copia]
    for v in binarias:
        v.domain = pyo.Binary

    # 3) MILP lagrangiano: cópia relaxada, penalizada por lam
    m.copia.deactivate()
    m.obj.deactivate()
    m.obj_lag = pyo.Objective(expr=m.f_oper - lam * m.P_cap, sense=pyo.maximize)
    r = opt.solve(m)
    c = r.best_objective_bound
    return ResultadoBloco(q_val, lam, c)


# ----------------------------------------------------------------------------- mestre
@dataclass
class Historico:
    iteracao: list[int] = field(default_factory=list)
    p_cap: list[float] = field(default_factory=list)
    lb_candidato: list[float] = field(default_factory=list)
    lb: list[float] = field(default_factory=list)
    ub: list[float] = field(default_factory=list)
    tempo_s: list[float] = field(default_factory=list)

    def tabela(self) -> pd.DataFrame:
        return pd.DataFrame({"iteracao": self.iteracao, "p_cap_mw": self.p_cap,
                             "lucro_candidato_rs": self.lb_candidato, "limite_inferior_rs": self.lb,
                             "limite_superior_rs": self.ub, "tempo_s": self.tempo_s})


def resolver_benders(p: Parametros, inicio: str, dias: int, dias_bloco: int = 7,
                     tol: float = 1e-3, max_iter: int = 30, gap_sub: float = 1e-4,
                     processos: int = 4, verbose: bool = True):
    """Resolve o problema anual por Benders. Retorna (P_cap ótimo, lucro, histórico, cortes)."""
    blocos = dividir_em_blocos(inicio, dias, dias_bloco)
    p_max = potencia_lrcap_max(p)
    p_min = p.lrcap.potencia_min_mw if p_max > 0 else 0.0
    horas = sum(d for _, d in blocos) * 24
    r_cap = p.lrcap.receita_fixa_rs_mw_ano * horas / 8760.0

    # Mestre
    ms = pyo.ConcreteModel()
    ms.W = pyo.RangeSet(0, len(blocos) - 1)
    ms.P = pyo.Var(bounds=(0, p_max))
    ms.w = pyo.Var(within=pyo.Binary)
    ms.theta = pyo.Var(ms.W)
    ms.cmin = pyo.Constraint(expr=ms.P >= p_min * ms.w)
    ms.cmax = pyo.Constraint(expr=ms.P <= p_max * ms.w)
    ms.cortes = pyo.ConstraintList()
    ms.obj = pyo.Objective(expr=r_cap * ms.P + sum(ms.theta[w] for w in ms.W), sense=pyo.maximize)
    opt_m = _solver(1e-9)
    opt_m.config.load_solution = True

    hist, cortes = Historico(), []
    avaliados: dict[float, float] = {}
    melhor_x, melhor_lb = None, -float("inf")
    t0 = time.time()

    def avaliar(x: float, it: int, ub: float):
        nonlocal melhor_x, melhor_lb
        tarefas = [(p, ini, d, x, gap_sub) for ini, d in blocos]
        with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
            res = list(ex.map(avaliar_bloco, tarefas))
        lb_x = r_cap * x + sum(r.q for r in res)
        avaliados[round(x, 6)] = lb_x
        for w, r in enumerate(res):
            ms.cortes.add(ms.theta[w] <= r.c + r.lam * ms.P)
            cortes.append({"iteracao": it, "bloco": w, "p_cap_mw": x, "q_rs": r.q,
                           "lambda_rs_mw": r.lam, "c_rs": r.c})
        if lb_x > melhor_lb:
            melhor_x, melhor_lb = x, lb_x
        hist.iteracao.append(it); hist.p_cap.append(x); hist.lb_candidato.append(lb_x)
        hist.lb.append(melhor_lb); hist.ub.append(ub); hist.tempo_s.append(time.time() - t0)
        if verbose:
            print(f"it {it:2d}  P_cap = {x:7.3f} MW  lucro = R$ {lb_x / 1e6:8.4f} mi  "
                  f"LB = {melhor_lb / 1e6:8.4f}  UB = {ub / 1e6:8.4f}  "
                  f"gap = {_gap(ub, melhor_lb):7.3%}  [{time.time() - t0:5.0f} s]", flush=True)

    # Pontos iniciais: extremos do conjunto viável
    iniciais = [0.0] + ([p_min, p_max] if p_max > 0 else [])
    for x in iniciais:
        avaliar(x, 0, float("inf"))

    for it in range(1, max_iter + 1):
        r = opt_m.solve(ms)
        ub = r.best_objective_bound
        x = round(pyo.value(ms.P), 6)
        if _gap(ub, melhor_lb) <= tol:
            hist.iteracao.append(it); hist.p_cap.append(x); hist.lb_candidato.append(float("nan"))
            hist.lb.append(melhor_lb); hist.ub.append(ub); hist.tempo_s.append(time.time() - t0)
            if verbose:
                print(f"Convergiu: gap {_gap(ub, melhor_lb):.3%} <= {tol:.3%}")
            break
        if x in avaliados:
            # Mestre repropõe um ponto já avaliado: os cortes não fecham o gap
            # (não convexidade de Q_w). O gap reportado é o certificado final.
            hist.iteracao.append(it); hist.p_cap.append(x); hist.lb_candidato.append(avaliados[x])
            hist.lb.append(melhor_lb); hist.ub.append(ub); hist.tempo_s.append(time.time() - t0)
            if verbose:
                print(f"Parou: mestre repropôs P_cap = {x} MW; gap final {_gap(ub, melhor_lb):.3%}")
            break
        avaliar(x, it, ub)

    return melhor_x, melhor_lb, hist, pd.DataFrame(cortes)


def _gap(ub: float, lb: float) -> float:
    return (ub - lb) / abs(lb) if lb not in (0, -float("inf")) else float("inf")


# ------------------------------------------------------------------ solução detalhada
def operacao_anual(p: Parametros, inicio: str, dias: int, p_cap: float, dias_bloco: int = 7,
                   processos: int = 4) -> tuple[pd.DataFrame, pd.Series]:
    """Resolve todos os blocos com P_cap fixo e concatena a operação e os indicadores."""
    blocos = dividir_em_blocos(inicio, dias, dias_bloco)
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        partes = list(ex.map(_operacao_bloco, [(p, ini, d, p_cap) for ini, d in blocos]))
    df = pd.concat([d for d, _ in partes])
    k = pd.concat([k for _, k in partes], axis=1)
    # Indicadores somáveis; taxas recalculadas sobre o ano
    total = k.sum(axis=1)
    total["potencia_lrcap_mw"] = p_cap
    total["energia_modulo_lrcap_mwh"] = k.loc["energia_modulo_lrcap_mwh"].iloc[0]
    total["energia_modulo_mercantil_mwh"] = k.loc["energia_modulo_mercantil_mwh"].iloc[0]
    total["fator_capacidade_eletrolisador"] = df["p_eletrolisador_mw"].mean() / p.eletrolisador.potencia_max_mw
    total["preco_medio_exportacao_rs_mwh"] = ((df["pld_rs_mwh"] * df["p_exportacao_mw"]).sum()
                                              / max(df["p_exportacao_mw"].sum(), 1e-9))
    total["ciclos_equivalentes_mercantil"] = (df["p_descarga_bess_mw"].sum() * p.horizonte.dt_h
                                              / max(total["energia_modulo_mercantil_mwh"], 1e-9))
    return df, total.round(4)


def _operacao_bloco(args):
    p, inicio, dias, p_cap = args
    q = _params_bloco(p, inicio, dias)
    q.lrcap.potencia_fixa_mw = p_cap
    s = montar_series(q)
    m = construir_modelo(q, s)
    opt = _solver(1e-4)
    opt.config.load_solution = True
    opt.solve(m)
    df = serie_resultados(m, s)
    return df, indicadores(m, df, q)
