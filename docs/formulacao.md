# Formulação matemática — versão 0.1 (determinística)

**Título de trabalho:** Otimização da Operação de um Sistema Híbrido PV-BESS com
Produção de Hidrogênio Verde: arbitragem entre o Leilão de Reserva de Capacidade
(LRCAP) e o Mercado de Curto Prazo (MCP).

Modelo de **Programação Linear Inteira Mista (MILP)**, horizonte discreto horário,
visão de um agente tomador de preço (*price-taker*) que decide:

1. quanto de potência do BESS comprometer com o LRCAP (decisão "de planejamento", $P^{cap}$);
2. a operação horária de PV, BESS, eletrolisador e intercâmbio com a rede.

A implementação está em `src/pvbess_h2/modelo.py`, com os mesmos nomes de variáveis.

---

## 1. Conjuntos

| Símbolo | Descrição |
|---|---|
| $t \in \mathcal{T} = \{0,\dots,N-1\}$ | intervalos de tempo (passo $\Delta t$, h) |
| $d \in \mathcal{D}$ | dias do horizonte; $\mathcal{T}_d$ = intervalos do dia $d$ |
| $\mathcal{J} \subseteq \mathcal{T}$ | intervalos da janela de disponibilidade do LRCAP |
| $\mathcal{A} \subseteq \mathcal{T}$ | intervalos com acionamento pelo ONS |

## 2. Parâmetros

| Símbolo | Descrição | Unidade | Config (`caso_base.yaml`) |
|---|---|---|---|
| $\bar P^{pv}_t$ | potência PV disponível | MW | `pv.*` |
| $\lambda_t$ | PLD horário | R\$/MWh | `mercado.*` |
| $\bar E,\ \underline E,\ E_0$ | SOC máx., mín., inicial do BESS | MWh | `bess.*_frac × energia_mwh` |
| $\bar P^{ch},\ \bar P^{dis}$ | potências máx. de carga/descarga | MW | `bess.potencia_*` |
| $\eta^{ch},\ \eta^{dis}$ | eficiências de carga/descarga | – | `bess.eficiencia_*` |
| $c^{deg}$ | custo de degradação por MWh descarregado | R\$/MWh | `bess.custo_degradacao_rs_mwh` |
| $\bar P^{el},\ \alpha^{el}$ | potência nominal e carga mínima (fração) do eletrolisador | MW, – | `eletrolisador.*` |
| $k^{el}$ | consumo específico | kWh/kg | `eletrolisador.consumo_especifico_kwh_kg` |
| $c^{h2}$ | custo variável de produção (água, O&M) | R\$/kg | `eletrolisador.custo_variavel_rs_kg` |
| $\pi^{h2}$ | preço de venda do H₂ | R\$/kg | `hidrogenio.preco_venda_rs_kg` |
| $\bar S,\ S_0$ | capacidade e estoque inicial do tanque | kg | `hidrogenio.*` |
| $D^{h2}$ | entrega mínima diária de H₂ | kg/dia | `hidrogenio.entrega_min_diaria_kg` |
| $\bar P^{exp},\ \bar P^{imp}$ | limites de exportação/importação | MW | `rede.*` |
| $c^{imp}$ | adicional sobre a energia importada (encargos, TUSD) | R\$/MWh | `rede.custo_adicional_importacao_rs_mwh` |
| $R^{cap}$ | receita fixa do LRCAP | R\$/MW·ano | `lrcap.receita_fixa_rs_mw_ano` |
| $H^{cap}$ | duração mínima de entrega exigida | h | `lrcap.duracao_h` |
| $c^{def}$ | penalidade por potência não entregue | R\$/MWh | `lrcap.penalidade_deficit_rs_mwh` |

## 3. Variáveis de decisão

| Símbolo | Descrição | Domínio |
|---|---|---|
| $p^{pv}_t$ | PV aproveitado (a diferença é *curtailment*) | $[0, \bar P^{pv}_t]$ |
| $p^{ch}_t,\ p^{dis}_t$ | carga / descarga do BESS | $[0,\bar P^{ch}],\ [0,\bar P^{dis}]$ |
| $e_t$ | energia armazenada (SOC) | $[\underline E, \bar E]$ |
| $p^{el}_t$ | potência do eletrolisador | $[0, \bar P^{el}]$ |
| $m_t,\ v_t$ | produção e venda de H₂ | kg/h, $\ge 0$ |
| $s_t$ | estoque de H₂ | $[0, \bar S]$ |
| $p^{exp}_t,\ p^{imp}_t$ | exportação / importação | $[0,\bar P^{exp}],\ [0,\bar P^{imp}]$ |
| $P^{cap}$ | potência contratada no LRCAP | $\ge 0$ |
| $\delta_t$ | déficit de entrega no acionamento | $\ge 0$ |
| $y^{bat}_t,\ y^{rede}_t,\ z_t$ | carregando? / exportando? / eletrolisador ligado? | $\{0,1\}$ |

## 4. Função objetivo — maximização do lucro no horizonte

$$
\max\ \underbrace{\sum_t \lambda_t\, p^{exp}_t \Delta t}_{\text{MCP}}
\;-\; \underbrace{\sum_t (\lambda_t + c^{imp})\, p^{imp}_t \Delta t}_{\text{importação}}
\;+\; \underbrace{\sum_t \pi^{h2} v_t \Delta t}_{\text{venda de H}_2}
\;+\; \underbrace{R^{cap}\,\tfrac{N\Delta t}{8760}\,P^{cap}}_{\text{LRCAP}}
\;-\; \sum_t c^{h2} m_t \Delta t
\;-\; \sum_t c^{deg} p^{dis}_t \Delta t
\;-\; \sum_t c^{def}\,\delta_t \Delta t
$$

## 5. Restrições

**Balanço de potência no barramento**
$$ p^{pv}_t + p^{dis}_t + p^{imp}_t = p^{ch}_t + p^{el}_t + p^{exp}_t \qquad \forall t $$

**BESS**
$$ e_t = e_{t-1} + \Big(\eta^{ch} p^{ch}_t - \frac{p^{dis}_t}{\eta^{dis}}\Big)\Delta t, \quad e_{-1}=E_0, \quad e_{N-1} \ge E_0 $$
$$ p^{ch}_t \le \bar P^{ch} y^{bat}_t, \qquad p^{dis}_t \le \bar P^{dis} (1-y^{bat}_t) $$

**Rede** (sem exportação e importação simultâneas)
$$ p^{exp}_t \le \bar P^{exp} y^{rede}_t, \qquad p^{imp}_t \le \bar P^{imp} (1-y^{rede}_t) $$
Com `h2_verde_estrito: true` impõe-se $\bar P^{imp}=0$: toda a energia do eletrolisador
é de origem renovável local (PV direto ou PV armazenado no BESS).

**Eletrolisador e hidrogênio**
$$ \alpha^{el}\bar P^{el} z_t \le p^{el}_t \le \bar P^{el} z_t, \qquad m_t = \frac{1000}{k^{el}}\, p^{el}_t $$
$$ s_t = s_{t-1} + (m_t - v_t)\Delta t,\quad s_{-1}=S_0,\quad s_{N-1}\ge S_0, \qquad \sum_{t\in\mathcal{T}_d} v_t\Delta t \ge D^{h2}\ \ \forall d $$

**LRCAP**

(i) Reserva de energia: durante a janela de disponibilidade o BESS deve manter energia
suficiente para sustentar $P^{cap}$ por $H^{cap}$ horas:
$$ e_t \ge \underline E + \frac{P^{cap} H^{cap}}{\eta^{dis}} \qquad \forall t \in \mathcal{J} $$

(ii) Entrega quando acionado:
$$ p^{exp}_t + \delta_t \ge P^{cap} \qquad \forall t\in\mathcal{A} $$

(iii) Limites: $P^{cap} \le \min(\bar P^{dis}, \bar P^{exp})$.

## 6. Hipóteses simplificadoras (v0.1) — a revisar

1. **Determinístico e com previsão perfeita** de PLD e geração PV.
2. **Agente tomador de preço**: a operação não altera o PLD.
3. **Regras do LRCAP simplificadas**: receita fixa rateada linearmente no horizonte; a
   obrigação é representada por reserva de SOC na janela + entrega quando acionado.
   *Conferir com o edital/Portaria MME e as Regras de Comercialização da CCEE*:
   duração exigida, janela/critério de acionamento pelo ONS, forma de apuração da
   disponibilidade, penalidades, e como a energia entregue é liquidada.
4. Energia exportada liquidada integralmente ao PLD (sem contratos bilaterais no ACL).
5. Eficiências constantes; degradação linear no *throughput*; eletrolisador sem custo de
   partida nem curva de eficiência em carga parcial.
6. Um único barramento, sem perdas internas nem restrições de rede interna.
7. Séries sintéticas no caso base (ver `src/pvbess_h2/dados.py`).

## 7. Extensões previstas

- **Estocástica em dois estágios**: $P^{cap}$ no 1º estágio; operação por cenário
  (PLD, PV, acionamentos do ONS) no 2º estágio; medidas de risco (CVaR).
- **Dias representativos** (clusterização k-means/k-medoids) para simular o ano todo.
- Curva de eficiência do eletrolisador em carga parcial (linearização por partes),
  custos de partida e tempo mínimo ligado/desligado.
- Degradação do BESS dependente da profundidade de descarga (*rainflow* linearizado).
- Critérios de certificação do H₂ verde (correlação temporal horária/mensal, adicionalidade).
- Dimensionamento ótimo (capacidades de PV, BESS e eletrolisador como variáveis — CAPEX anualizado).
