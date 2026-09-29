"""Modelo MILP determinístico da operação do sistema híbrido PV-BESS-H2.

O BESS instalado é dividido em dois módulos com medição (PMI) própria:
  - módulo LRCAP: potência contratada P_cap, despachado pelo ONS (descarga e recarga),
    remunerado apenas pela Receita Fixa (Portaria MME 136/2026, art. 9º §5º, IV);
  - módulo mercantil: o restante, operado pelo empreendedor no MCP e para o H2.
Ambos compartilham o ponto de conexão com o PV e o eletrolisador (art. 4º §1º, II).

Formulação completa em docs/formulacao.md. A notação dos componentes Pyomo segue
a do documento.
"""

from __future__ import annotations

import pandas as pd
import pyomo.environ as pyo

from .parametros import Parametros


def potencia_lrcap_max(p: Parametros) -> float:
    """Maior potência contratável: limitada pela potência e energia do BESS e pela conexão."""
    b, lr, rede = p.bess, p.lrcap, p.rede
    if not lr.habilitado:
        return 0.0
    limite = min(b.potencia_descarga_mw, b.potencia_carga_mw, b.energia_mwh / lr.energia_por_mw_h,
                 rede.exportacao_max_mw, rede.importacao_max_mw)
    if lr.potencia_max_oferta_mw is not None:
        limite = min(limite, lr.potencia_max_oferta_mw)
    return limite if limite >= lr.potencia_min_mw else 0.0  # abaixo do mínimo: não habilita


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
    m.d_ons = pyo.Param(m.T, initialize=dict(enumerate(series["ons_descarga_pu"])))
    m.r_ons = pyo.Param(m.T, initialize=dict(enumerate(series["ons_recarga_pu"])))

    kg_por_mwh = 1000.0 / el.consumo_especifico_kwh_kg
    P_imp_max = rede.importacao_max_mw if (rede.permitir_importacao and not rede.h2_verde_estrito) else 0.0
    P_cap_max = potencia_lrcap_max(p)
    P_cap_min = lr.potencia_min_mw if P_cap_max > 0 else 0.0

    # ----------------------------------------------------------------- Variáveis
    # LRCAP
    m.P_cap = pyo.Var(bounds=(0, P_cap_max))       # potência contratada [MW]
    m.w_cap = pyo.Var(within=pyo.Binary)           # 1 = participa do LRCAP
    # Fluxos de potência do lado mercantil [MW] (médios no intervalo)
    m.p_pv = pyo.Var(m.T, bounds=lambda m, t: (0, m.P_pv_disp[t]))
    m.p_ch = pyo.Var(m.T, bounds=(0, b.potencia_carga_mw))
    m.p_dis = pyo.Var(m.T, bounds=(0, b.potencia_descarga_mw))
    m.p_el = pyo.Var(m.T, bounds=(0, el.potencia_max_mw))
    m.p_exp = pyo.Var(m.T, bounds=(0, rede.exportacao_max_mw))
    m.p_imp = pyo.Var(m.T, bounds=(0, P_imp_max))
    # Estados
    m.soc = pyo.Var(m.T, bounds=(0, b.energia_mwh))                # módulo mercantil [MWh]
    m.s_h2 = pyo.Var(m.T, bounds=(0, h2.tanque_max_kg))            # [kg]
    # Hidrogênio [kg/h]
    m.m_h2 = pyo.Var(m.T, within=pyo.NonNegativeReals)             # produção
    m.v_h2 = pyo.Var(m.T, bounds=(0, h2.venda_max_kg_h))           # venda/entrega
    # Binárias
    m.y_bat = pyo.Var(m.T, within=pyo.Binary)   # 1 = módulo mercantil carregando
    m.y_rede = pyo.Var(m.T, within=pyo.Binary)  # 1 = exportando
    m.z_el = pyo.Var(m.T, within=pyo.Binary)    # 1 = eletrolisador ligado

    # -------------------------------------------------- Módulo LRCAP (despacho ONS)
    # Contratação: 0 ou [P_cap_min, P_cap_max] (art. 7º, III)
    m.cap_min = pyo.Constraint(expr=m.P_cap >= P_cap_min * m.w_cap)
    m.cap_max = pyo.Constraint(expr=m.P_cap <= P_cap_max * m.w_cap)
    if lr.potencia_fixa_mw is not None:
        m.P_cap.fix(lr.potencia_fixa_mw)
        m.w_cap.fix(1 if lr.potencia_fixa_mw > 0 else 0)

    # Descarga/recarga do módulo LRCAP: perfil do ONS (p.u.) x potência contratada
    m.p_dis_lr = pyo.Expression(m.T, rule=lambda m, t: m.d_ons[t] * m.P_cap)
    m.p_ch_lr = pyo.Expression(m.T, rule=lambda m, t: m.r_ons[t] * m.P_cap)

    # ----------------------------------------------------- Módulo mercantil do BESS
    # Energia e potência remanescentes após reservar o módulo LRCAP
    m.E_merc = pyo.Expression(expr=b.energia_mwh - lr.energia_por_mw_h * m.P_cap)
    m.E_0 = pyo.Expression(expr=b.soc_inicial_frac * m.E_merc)

    @m.Constraint(m.T)
    def balanco_potencia(m, t):
        return m.p_pv[t] + m.p_dis[t] + m.p_imp[t] == m.p_ch[t] + m.p_el[t] + m.p_exp[t]

    @m.Constraint(m.T)
    def balanco_soc(m, t):
        anterior = m.E_0 if t == 0 else m.soc[t - 1]
        return m.soc[t] == anterior + (b.eficiencia_carga * m.p_ch[t]
                                       - m.p_dis[t] / b.eficiencia_descarga) * dt

    @m.Constraint(m.T)
    def soc_min(m, t):
        return m.soc[t] >= b.soc_min_frac * m.E_merc

    @m.Constraint(m.T)
    def soc_max(m, t):
        return m.soc[t] <= b.soc_max_frac * m.E_merc

    m.soc_final = pyo.Constraint(expr=m.soc[n - 1] >= m.E_0)

    @m.Constraint(m.T)
    def limite_carga(m, t):
        return m.p_ch[t] <= b.potencia_carga_mw * m.y_bat[t]

    @m.Constraint(m.T)
    def limite_carga_merc(m, t):
        return m.p_ch[t] <= b.potencia_carga_mw - m.P_cap

    @m.Constraint(m.T)
    def limite_descarga(m, t):
        return m.p_dis[t] <= b.potencia_descarga_mw * (1 - m.y_bat[t])

    @m.Constraint(m.T)
    def limite_descarga_merc(m, t):
        return m.p_dis[t] <= b.potencia_descarga_mw - m.P_cap

    # --------------------------------------------------------------------- Rede
    # Lado mercantil: não exporta e importa simultaneamente
    @m.Constraint(m.T)
    def limite_exportacao(m, t):
        return m.p_exp[t] <= rede.exportacao_max_mw * m.y_rede[t]

    @m.Constraint(m.T)
    def limite_importacao(m, t):
        return m.p_imp[t] <= P_imp_max * (1 - m.y_rede[t])

    # Ponto de conexão compartilhado: fluxo líquido (mercantil + módulo LRCAP)
    m.fluxo_conexao = pyo.Expression(
        m.T, rule=lambda m, t: m.p_exp[t] - m.p_imp[t] + m.p_dis_lr[t] - m.p_ch_lr[t])

    @m.Constraint(m.T)
    def conexao_exportacao(m, t):
        return m.fluxo_conexao[t] <= rede.exportacao_max_mw

    @m.Constraint(m.T)
    def conexao_importacao(m, t):
        return m.fluxo_conexao[t] >= -rede.importacao_max_mw

    # ------------------------------------------------------------ Eletrolisador
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

    # Partidas do eletrolisador (u_t = 1 quando liga em t), com condição cíclica no
    # horizonte: o estado anterior à primeira hora é o da última.
    m.u_el = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, 1))

    @m.Constraint(m.T)
    def partida_el(m, t):
        if el.custo_partida_rs <= 0:
            return pyo.Constraint.Skip
        return m.u_el[t] >= m.z_el[t] - m.z_el[t - 1 if t > 0 else n - 1]

    @m.Constraint(m.D)
    def entrega_min_diaria(m, d):
        if h2.entrega_min_diaria_kg <= 0:
            return pyo.Constraint.Skip
        return sum(m.v_h2[t] * dt for t in horas_do_dia[d]) >= h2.entrega_min_diaria_kg

    # ------------------------------------------------------------ Função objetivo
    fracao_ano = horas_horizonte / 8760.0
    # Recarga do módulo LRCAP acima de (energia injetada / RTE de referência) é
    # custeada pelo empreendedor ao PLD (art. 9º §§ 7º e 8º). O restante da
    # liquidação da energia do módulo LRCAP vai para a CONCAP (art. 9º §6º).
    e_rec = float((series["ons_recarga_pu"] * dt).sum())
    e_inj = float((series["ons_descarga_pu"] * dt).sum())
    frac_excesso = max(0.0, e_rec - e_inj / lr.rte_referencia) / e_rec if e_rec > 0 else 0.0
    custo_rec_pu = frac_excesso * float((series["pld_rs_mwh"] * series["ons_recarga_pu"] * dt).sum())

    m.receita_mcp = pyo.Expression(expr=sum(m.pld[t] * m.p_exp[t] * dt for t in m.T))
    m.custo_importacao = pyo.Expression(
        expr=sum((m.pld[t] + rede.custo_adicional_importacao_rs_mwh) * m.p_imp[t] * dt for t in m.T))
    m.receita_h2 = pyo.Expression(expr=sum(h2.preco_venda_rs_kg * m.v_h2[t] * dt for t in m.T))
    m.custo_h2 = pyo.Expression(expr=sum(el.custo_variavel_rs_kg * m.m_h2[t] * dt for t in m.T)
                                + sum(el.custo_partida_rs * m.u_el[t] for t in m.T))
    m.receita_lrcap = pyo.Expression(expr=lr.receita_fixa_rs_mw_ano * fracao_ano * m.P_cap)
    m.custo_recarga_lrcap = pyo.Expression(expr=custo_rec_pu * m.P_cap)
    m.custo_degradacao = pyo.Expression(
        expr=sum(b.custo_degradacao_rs_mwh * (m.p_dis[t] + m.p_dis_lr[t]) * dt for t in m.T))

    m.lucro = pyo.Objective(
        expr=m.receita_mcp + m.receita_h2 + m.receita_lrcap
        - m.custo_importacao - m.custo_h2 - m.custo_degradacao - m.custo_recarga_lrcap,
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
