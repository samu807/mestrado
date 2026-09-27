"""Modelo MILP determinístico da operação do sistema híbrido PV-BESS-H2.

Formulação completa em docs/formulacao.md. A notação dos componentes Pyomo segue
a do documento.
"""

from __future__ import annotations

import pandas as pd
import pyomo.environ as pyo

from .parametros import Parametros


def construir_modelo(p: Parametros, series: pd.DataFrame) -> pyo.ConcreteModel:
    b, el, h2, rede, lr = p.bess, p.eletrolisador, p.hidrogenio, p.rede, p.lrcap
    dt = p.horizonte.dt_h
    n = len(series)
    horas_horizonte = n * dt

    m = pyo.ConcreteModel(name="PV-BESS-H2 LRCAP x MCP")

    # ------------------------------------------------------------------ Conjuntos
    m.T = pyo.RangeSet(0, n - 1)
    m.D = pyo.Set(initialize=sorted(series["dia"].unique()))
    horas_do_dia = {d: [t for t in range(n) if series["dia"].iat[t] == d] for d in m.D}

    # ---------------------------------------------------------------- Parâmetros
    m.P_pv_disp = pyo.Param(m.T, initialize=dict(enumerate(series["pv_disp_mw"])))
    m.pld = pyo.Param(m.T, initialize=dict(enumerate(series["pld_rs_mwh"])))
    m.janela = pyo.Param(m.T, initialize=dict(enumerate(series["janela_lrcap"])))
    m.acion = pyo.Param(m.T, initialize=dict(enumerate(series["acionamento_lrcap"])))

    E_min = b.soc_min_frac * b.energia_mwh
    E_max = b.soc_max_frac * b.energia_mwh
    E_0 = b.soc_inicial_frac * b.energia_mwh
    kg_por_mwh = 1000.0 / el.consumo_especifico_kwh_kg
    P_imp_max = rede.importacao_max_mw if (rede.permitir_importacao and not rede.h2_verde_estrito) else 0.0

    # ----------------------------------------------------------------- Variáveis
    # Fluxos de potência [MW] (médios no intervalo)
    m.p_pv = pyo.Var(m.T, bounds=lambda m, t: (0, m.P_pv_disp[t]))
    m.p_ch = pyo.Var(m.T, bounds=(0, b.potencia_carga_mw))
    m.p_dis = pyo.Var(m.T, bounds=(0, b.potencia_descarga_mw))
    m.p_el = pyo.Var(m.T, bounds=(0, el.potencia_max_mw))
    m.p_exp = pyo.Var(m.T, bounds=(0, rede.exportacao_max_mw))
    m.p_imp = pyo.Var(m.T, bounds=(0, P_imp_max))
    # Estados
    m.soc = pyo.Var(m.T, bounds=(E_min, E_max))                 # [MWh]
    m.s_h2 = pyo.Var(m.T, bounds=(0, h2.tanque_max_kg))         # [kg]
    # Hidrogênio [kg/h]
    m.m_h2 = pyo.Var(m.T, within=pyo.NonNegativeReals)          # produção
    m.v_h2 = pyo.Var(m.T, bounds=(0, h2.venda_max_kg_h))        # venda/entrega
    # Binárias
    m.y_bat = pyo.Var(m.T, within=pyo.Binary)   # 1 = BESS carregando
    m.y_rede = pyo.Var(m.T, within=pyo.Binary)  # 1 = exportando
    m.z_el = pyo.Var(m.T, within=pyo.Binary)    # 1 = eletrolisador ligado
    # LRCAP
    P_cap_max = min(b.potencia_descarga_mw, rede.exportacao_max_mw)
    if lr.potencia_max_oferta_mw is not None:
        P_cap_max = min(P_cap_max, lr.potencia_max_oferta_mw)
    if not lr.habilitado:
        P_cap_max = 0.0
    m.P_cap = pyo.Var(bounds=(0, P_cap_max))                     # potência contratada [MW]
    m.deficit = pyo.Var(m.T, within=pyo.NonNegativeReals)        # potência não entregue [MW]
    if lr.habilitado and lr.potencia_fixa_mw is not None:
        m.P_cap.fix(lr.potencia_fixa_mw)

    # -------------------------------------------------------------- Restrições
    @m.Constraint(m.T)
    def balanco_potencia(m, t):
        return m.p_pv[t] + m.p_dis[t] + m.p_imp[t] == m.p_ch[t] + m.p_el[t] + m.p_exp[t]

    # BESS
    @m.Constraint(m.T)
    def balanco_soc(m, t):
        anterior = E_0 if t == 0 else m.soc[t - 1]
        return m.soc[t] == anterior + (b.eficiencia_carga * m.p_ch[t]
                                       - m.p_dis[t] / b.eficiencia_descarga) * dt

    m.soc_final = pyo.Constraint(expr=m.soc[n - 1] >= E_0)

    @m.Constraint(m.T)
    def limite_carga(m, t):
        return m.p_ch[t] <= b.potencia_carga_mw * m.y_bat[t]

    @m.Constraint(m.T)
    def limite_descarga(m, t):
        return m.p_dis[t] <= b.potencia_descarga_mw * (1 - m.y_bat[t])

    # Rede: não exporta e importa simultaneamente
    @m.Constraint(m.T)
    def limite_exportacao(m, t):
        return m.p_exp[t] <= rede.exportacao_max_mw * m.y_rede[t]

    @m.Constraint(m.T)
    def limite_importacao(m, t):
        return m.p_imp[t] <= P_imp_max * (1 - m.y_rede[t])

    # Eletrolisador
    @m.Constraint(m.T)
    def el_max(m, t):
        return m.p_el[t] <= el.potencia_max_mw * m.z_el[t]

    @m.Constraint(m.T)
    def el_min(m, t):
        return m.p_el[t] >= el.carga_min_frac * el.potencia_max_mw * m.z_el[t]

    @m.Constraint(m.T)
    def producao_h2(m, t):
        return m.m_h2[t] == kg_por_mwh * m.p_el[t]

    @m.Constraint(m.T)
    def balanco_tanque(m, t):
        anterior = h2.tanque_inicial_kg if t == 0 else m.s_h2[t - 1]
        return m.s_h2[t] == anterior + (m.m_h2[t] - m.v_h2[t]) * dt

    m.tanque_final = pyo.Constraint(expr=m.s_h2[n - 1] >= h2.tanque_inicial_kg)

    @m.Constraint(m.D)
    def entrega_min_diaria(m, d):
        if h2.entrega_min_diaria_kg <= 0:
            return pyo.Constraint.Skip
        return sum(m.v_h2[t] * dt for t in horas_do_dia[d]) >= h2.entrega_min_diaria_kg

    # LRCAP - (i) reserva de energia na janela de disponibilidade: o BESS deve ter
    # energia para sustentar P_cap por `duracao_h` horas acima do SOC mínimo.
    @m.Constraint(m.T)
    def reserva_lrcap(m, t):
        if not m.janela[t]:
            return pyo.Constraint.Skip
        return m.soc[t] >= E_min + m.P_cap * lr.duracao_h / b.eficiencia_descarga

    # LRCAP - (ii) entrega de P_cap nas horas de acionamento pelo ONS.
    @m.Constraint(m.T)
    def entrega_lrcap(m, t):
        if not m.acion[t]:
            return pyo.Constraint.Skip
        return m.p_exp[t] + m.deficit[t] >= m.P_cap

    # ------------------------------------------------------------ Função objetivo
    fracao_ano = horas_horizonte / 8760.0
    m.receita_mcp = pyo.Expression(expr=sum(m.pld[t] * m.p_exp[t] * dt for t in m.T))
    m.custo_importacao = pyo.Expression(
        expr=sum((m.pld[t] + rede.custo_adicional_importacao_rs_mwh) * m.p_imp[t] * dt for t in m.T))
    m.receita_h2 = pyo.Expression(expr=sum(h2.preco_venda_rs_kg * m.v_h2[t] * dt for t in m.T))
    m.custo_h2 = pyo.Expression(expr=sum(el.custo_variavel_rs_kg * m.m_h2[t] * dt for t in m.T))
    m.receita_lrcap = pyo.Expression(expr=lr.receita_fixa_rs_mw_ano * fracao_ano * m.P_cap)
    m.custo_degradacao = pyo.Expression(
        expr=sum(b.custo_degradacao_rs_mwh * m.p_dis[t] * dt for t in m.T))
    m.penalidade_lrcap = pyo.Expression(
        expr=sum(lr.penalidade_deficit_rs_mwh * m.deficit[t] * dt for t in m.T))

    m.lucro = pyo.Objective(
        expr=m.receita_mcp + m.receita_h2 + m.receita_lrcap
        - m.custo_importacao - m.custo_h2 - m.custo_degradacao - m.penalidade_lrcap,
        sense=pyo.maximize,
    )
    return m


def resolver(m: pyo.ConcreteModel, solver: str = "appsi_highs", gap: float = 1e-4,
             tempo_max_s: float | None = None, verbose: bool = False):
    opt = pyo.SolverFactory(solver)
    if solver.endswith("highs"):
        opt.config.mip_gap = gap
        if tempo_max_s is not None:
            opt.config.time_limit = tempo_max_s
    res = opt.solve(m, tee=verbose)
    cond = res.solver.termination_condition
    if cond not in (pyo.TerminationCondition.optimal, pyo.TerminationCondition.maxTimeLimit):
        raise RuntimeError(f"Solver terminou com condição '{cond}'")
    return res
