# Formulação matemática — versão 0.2 (determinística)

**Título de trabalho:** Otimização da Operação de um Sistema Híbrido PV-BESS com
Produção de Hidrogênio Verde: arbitragem entre o Leilão de Reserva de Capacidade
(LRCAP) e o Mercado de Curto Prazo (MCP).

Modelo de **Programação Linear Inteira Mista (MILP)**, horizonte discreto horário,
visão de um agente tomador de preço (*price-taker*). As regras do LRCAP seguem a
**Portaria Normativa MME nº 136, de 1º de junho de 2026** (LRCAP de 2026 — Armazenamento),
citada abaixo como "PN 136".

A implementação está em `src/pvbess_h2/modelo.py`, com os mesmos nomes de variáveis.

---

## 0. Interpretação regulatória que orienta o modelo

1. **O SAE contratado não pode fazer arbitragem no MCP.** A receita fixa deve
   "remunerar integralmente todo e qualquer uso que o ONS fizer [...] sem geração de
   receitas adicionais fora do CRCAP" (PN 136, art. 9º §5º, IV). A energia de recarga e a
   injetada são liquidadas ao PLD, mas o resultado vai para a CONCAP (art. 9º §6º).
2. **Quem opera o SAE contratado é o ONS**: descarga **e** recarga, na programação diária
   e em tempo real (art. 4º §§ 2º, 8º e 14; art. 9º §5º, III). O risco de incerteza do
   despacho é do empreendedor (art. 5º §2º).
3. **O SAE pode compartilhar a conexão** com outros empreendimentos (art. 4º §1º, II).
   Os empreendimentos de geração que compartilham a conexão não passam pela habilitação
   da EPE (art. 6º §4º).

Por isso, a "arbitragem" LRCAP × MCP é modelada como uma **decisão de alocação do BESS
instalado** entre dois módulos com medição (PMI) própria:

- **módulo LRCAP**: potência contratada $P^{cap}$, operado pelo ONS e remunerado só pela
  Receita Fixa;
- **módulo mercantil**: o restante da potência e da energia do BESS, operado pelo
  empreendedor junto com o PV e o eletrolisador (MCP + H₂).

Os dois módulos disputam a capacidade do **ponto de conexão compartilhado**.

## 1. Conjuntos

| Símbolo | Descrição |
|---|---|
| $t \in \mathcal{T} = \{0,\dots,N-1\}$ | intervalos de tempo (passo $\Delta t$, h) |
| $d \in \mathcal{D}$ | dias do horizonte; $\mathcal{T}_d$ = intervalos do dia $d$ |

## 2. Parâmetros

| Símbolo | Descrição | Unidade | Config (`caso_base.yaml`) |
|---|---|---|---|
| $\bar P^{pv}_t$ | potência PV disponível | MW | `pv.*` |
| $\lambda_t$ | PLD horário | R\$/MWh | `mercado.*` |
| $E^{tot},\ \bar P^{ch},\ \bar P^{dis}$ | energia e potências **totais** instaladas do BESS | MWh, MW | `bess.*` |
| $\underline\sigma,\ \bar\sigma,\ \sigma_0$ | SOC mín., máx. e inicial (fração da energia de cada módulo) | – | `bess.soc_*_frac` |
| $\eta^{ch},\ \eta^{dis}$ | eficiências de carga/descarga | – | `bess.eficiencia_*` |
| $c^{deg}$ | custo de degradação por MWh descarregado | R\$/MWh | `bess.custo_degradacao_rs_mwh` |
| $\bar P^{el},\ \alpha^{el}$ | potência nominal e carga mínima (fração) do eletrolisador | MW, – | `eletrolisador.*` |
| $k^{el}$ | consumo específico | kWh/kg | `eletrolisador.consumo_especifico_kwh_kg` |
| $c^{h2}$ | custo variável de produção (água, O&M) | R\$/kg | `eletrolisador.custo_variavel_rs_kg` |
| $\pi^{h2}$ | preço de venda do H₂ | R\$/kg | `hidrogenio.preco_venda_rs_kg` |
| $\bar S,\ S_0,\ D^{h2}$ | tanque, estoque inicial, entrega mínima diária | kg | `hidrogenio.*` |
| $\bar P^{exp},\ \bar P^{imp}$ | limites do ponto de conexão compartilhado | MW | `rede.*` |
| $\bar P^{imp,m}$ | limite de importação do lado mercantil ($=0$ se H₂ verde estrito) | MW | `rede.*` |
| $c^{imp}$ | adicional sobre a energia importada (encargos, TUSD) | R\$/MWh | `rede.custo_adicional_importacao_rs_mwh` |
| $R^{cap}$ | receita fixa | R\$/MW·ano | `lrcap.receita_fixa_rs_mw_ano` |
| $\underline P^{cap}$ | disponibilidade mínima (30 MW, art. 7º, III) | MW | `lrcap.potencia_min_mw` |
| $H^{cap}$ | duração do ciclo completo (4 h, art. 4º §3º) | h | `lrcap.duracao_h` |
| $\rho$ | energia instalada no módulo LRCAP por MW contratado | MWh/MW | `lrcap.energia_por_mw_h` |
| $RTE^{ref}$ | eficiência de referência para custeio da recarga (0,85; art. 7º, VI e art. 9º §7º) | – | `lrcap.rte_referencia` |
| $\delta_t,\ r_t$ | despacho do ONS: descarga e recarga do módulo LRCAP, em p.u. de $P^{cap}$ | – | `lrcap.despacho_ons` |

## 3. Variáveis de decisão

| Símbolo | Descrição | Domínio |
|---|---|---|
| $P^{cap}$ | potência contratada no LRCAP | $\ge 0$ |
| $w$ | participa do LRCAP? | $\{0,1\}$ |
| $p^{pv}_t$ | PV aproveitado (a diferença é *curtailment*) | $[0, \bar P^{pv}_t]$ |
| $p^{ch}_t,\ p^{dis}_t$ | carga / descarga do módulo mercantil | $\ge 0$ |
| $e_t$ | energia armazenada no módulo mercantil | $\ge 0$ |
| $p^{el}_t$ | potência do eletrolisador | $[0, \bar P^{el}]$ |
| $m_t,\ v_t$ | produção e venda de H₂ | kg/h, $\ge 0$ |
| $s_t$ | estoque de H₂ | $[0, \bar S]$ |
| $p^{exp}_t,\ p^{imp}_t$ | exportação / importação do lado mercantil | $\ge 0$ |
| $y^{bat}_t,\ y^{rede}_t,\ z_t$ | carregando? / exportando? / eletrolisador ligado? | $\{0,1\}$ |

## 4. Função objetivo — maximização do lucro do empreendedor no horizonte

$$
\max\ \underbrace{\sum_t \lambda_t\, p^{exp}_t \Delta t}_{\text{MCP (só mercantil)}}
\;-\; \sum_t (\lambda_t + c^{imp})\, p^{imp}_t \Delta t
\;+\; \sum_t \pi^{h2} v_t \Delta t
\;-\; \sum_t c^{h2} m_t \Delta t
\;+\; \underbrace{R^{cap}\,\tfrac{N\Delta t}{8760}\,P^{cap}}_{\text{Receita Fixa}}
\;-\; \underbrace{\kappa\, P^{cap}}_{\text{recarga excedente}}
\;-\; \sum_t c^{deg}\big(p^{dis}_t + \delta_t P^{cap}\big)\Delta t
$$

A energia do módulo LRCAP **não** entra na receita do MCP (vai para a CONCAP). O termo
$\kappa P^{cap}$ é o custo da recarga que excede $\text{injetada}/RTE^{ref}$, pago pelo
empreendedor ao PLD (art. 9º §§ 7º e 8º):

$$
\kappa = \max\!\Big(0,\ 1 - \frac{\sum_t \delta_t \Delta t}{RTE^{ref}\sum_t r_t \Delta t}\Big)\sum_t \lambda_t\, r_t\, \Delta t
$$

Com $\eta^{ch}\eta^{dis} \ge RTE^{ref}$, esse custo tende a zero.

## 5. Restrições

**Contratação no LRCAP** (0 ou pelo menos 30 MW, art. 7º, III)
$$ \underline P^{cap} w \le P^{cap} \le \bar P^{cap} w, \qquad
\bar P^{cap} = \min\big(\bar P^{dis},\ \bar P^{ch},\ E^{tot}/\rho,\ \bar P^{exp},\ \bar P^{imp}\big) $$

**Módulo LRCAP (despacho exógeno do ONS)**
$$ p^{dis,lr}_t = \delta_t P^{cap}, \qquad p^{ch,lr}_t = r_t P^{cap} $$
O perfil $(\delta_t, r_t)$ é pré-processado em `dados.despacho_ons` e validado:
o SOC do módulo, $e^{lr}_t = P^{cap}\,\varepsilon_t$ com
$\varepsilon_t = \varepsilon_{t-1} + (\eta^{ch} r_t - \delta_t/\eta^{dis})\Delta t$, fica em
$[\underline\sigma\rho,\ \bar\sigma\rho]$; e são verificados os limites de 2 ciclos
completos por dia e 366 por ano (art. 4º §3º).

**Requisitos de habilitação** (checados em `Parametros.validar`)
$$ (\bar\sigma-\underline\sigma)\,\rho\,\eta^{dis} \ge H^{cap} \ \text{(4 h contínuas, art. 7º, IV)},\qquad
\eta^{ch}\eta^{dis} \ge 0{,}85 \ \text{(art. 7º, VI)},\qquad
\frac{H^{cap}}{\eta^{ch}\eta^{dis}} \le 6\,\text{h} \ \text{(art. 7º, VII)} $$

**Módulo mercantil** — recebe o que sobra do BESS:
$$ E^{m} = E^{tot} - \rho P^{cap} $$
$$ e_t = e_{t-1} + \Big(\eta^{ch} p^{ch}_t - \frac{p^{dis}_t}{\eta^{dis}}\Big)\Delta t, \quad e_{-1}=\sigma_0 E^{m}, \quad e_{N-1} \ge \sigma_0 E^{m} $$
$$ \underline\sigma E^{m} \le e_t \le \bar\sigma E^{m} $$
$$ p^{ch}_t \le \bar P^{ch} y^{bat}_t,\quad p^{ch}_t \le \bar P^{ch} - P^{cap}, \qquad
   p^{dis}_t \le \bar P^{dis} (1-y^{bat}_t),\quad p^{dis}_t \le \bar P^{dis} - P^{cap} $$

**Balanço de potência do lado mercantil**
$$ p^{pv}_t + p^{dis}_t + p^{imp}_t = p^{ch}_t + p^{el}_t + p^{exp}_t \qquad \forall t $$

**Rede**
$$ p^{exp}_t \le \bar P^{exp} y^{rede}_t, \qquad p^{imp}_t \le \bar P^{imp,m} (1-y^{rede}_t) $$
Ponto de conexão compartilhado (fluxo líquido; o MUST deve comportar a descarga e a
recarga total do SAE, art. 9º §13):
$$ -\bar P^{imp} \le p^{exp}_t - p^{imp}_t + p^{dis,lr}_t - p^{ch,lr}_t \le \bar P^{exp} $$
Com `h2_verde_estrito: true` impõe-se $\bar P^{imp,m}=0$: o eletrolisador só recebe
energia renovável local (PV direto ou PV armazenado no módulo mercantil).

**Eletrolisador e hidrogênio**
$$ \alpha^{el}\bar P^{el} z_t \le p^{el}_t \le \bar P^{el} z_t, \qquad m_t = \frac{1000}{k^{el}}\, p^{el}_t $$
$$ s_t = s_{t-1} + (m_t - v_t)\Delta t,\quad s_{-1}=S_0,\quad s_{N-1}\ge S_0, \qquad \sum_{t\in\mathcal{T}_d} v_t\Delta t \ge D^{h2}\ \ \forall d $$

## 6. Solução do problema anual — decomposição de Benders

Resolver as 8.760 horas de uma vez (≈ 26 mil variáveis binárias) não terminou em 15 min.
O problema tem, porém, uma estrutura favorável: **$P^{cap}$ é a única variável que acopla
o ano**. Dividindo o ano em blocos $w \in \mathcal{W}$ (semanas), com estados cíclicos em cada
bloco (SOC do módulo mercantil e estoque de H₂ voltam ao valor inicial):

$$
\max_{P^{cap}\in\{0\}\cup[\underline P^{cap},\,\bar P^{cap}]}\ \ R^{cap}\tfrac{H}{8760}P^{cap} + \sum_{w\in\mathcal{W}} Q_w(P^{cap})
$$

onde $Q_w(x)$ é o lucro operacional ótimo do bloco $w$ com $P^{cap}=x$ (um MILP de 168 h).

**Por que não o Benders clássico.** Os subproblemas têm binárias ($y^{bat}, y^{rede}, z$),
então $Q_w$ não é côncava em geral e o corte obtido do dual do LP não é válido.

**Cortes de Benders reforçados** (Zou, Ahmed & Sun, 2019). Com a restrição de cópia
$P^{cap}_w = x$ e $\lambda_w$ = dual dessa restrição no LP relaxado em $\hat x$:

$$
C_w(\lambda_w) = \max_{(y,\,z)\,\in\,X_w}\ f_w(y,z) - \lambda_w z
\qquad\Longrightarrow\qquad
\theta_w \le C_w(\lambda_w) + \lambda_w P^{cap}
$$

em que $X_w$ é o conjunto viável do MILP do bloco (com $z$ livre). O corte é válido para
qualquer $P^{cap}$, pois é uma relaxação lagrangiana. $C_w$ é tomado como o **limite dual**
do solver, o que preserva a validade mesmo com *gap* de MIP.

**Algoritmo**
1. Avaliar $\hat x \in \{0,\ \underline P^{cap},\ \bar P^{cap}\}$: para cada bloco, MILP com
   $P^{cap}=\hat x$ (valor $Q_w$, solução viável), LP relaxado (dual $\lambda_w$) e MILP
   lagrangiano ($C_w$). Os blocos são independentes e rodam em paralelo.
2. Mestre (MILP pequeno): $\max R^{cap}\tfrac{H}{8760}P + \sum_w\theta_w$ sujeito aos cortes
   e a $\underline P^{cap} w \le P \le \bar P^{cap} w$. O valor do mestre é um **limite
   superior** (UB).
3. Avaliar o $\hat x$ proposto pelo mestre: $R^{cap}\tfrac{H}{8760}\hat x + \sum_w Q_w(\hat x)$ é
   uma solução viável, ou seja, um **limite inferior** (LB).
4. Parar quando $(UB-LB)/LB \le 0{,}1\%$. Se o mestre repropõe um ponto já avaliado, o *gap*
   restante é reportado como certificado.

Implementação: `src/pvbess_h2/decomposicao.py`; execução: `scripts/anual_benders.py`.
No caso Itajubá 2025 converge em 3 iterações (~75 s em 4 núcleos), *gap* 0,04%.

**Hipótese introduzida:** a condição cíclica semanal restringe um pouco a operação em
relação ao ano contínuo (não se transfere energia ou H₂ entre semanas). Com o tanque de H₂
e a bateria mercantil operando em ciclos diários, o efeito tende a ser pequeno.

## 7. Hipóteses simplificadoras (v0.2) — a revisar

1. **Determinístico e com previsão perfeita** de PLD, geração PV **e despacho do ONS**.
   O despacho real é incerto (art. 5º §2º): é o principal candidato à versão estocástica.
2. **Agente tomador de preço**: a operação não altera o PLD.
3. **Receita fixa** rateada linearmente no horizonte. Não se modelam o reajuste por
   IPCA (art. 9º §12), o pagamento mensal com abatimento por desempenho (art. 5º) nem as
   penalidades por indisponibilidade (art. 9º §10), que dependem do edital da ANEEL.
4. **Módulo LRCAP sempre disponível** e cumprindo 100% do despacho: sem indisponibilidades
   programadas ou forçadas.
5. Perfil de despacho sintético: descarga plena nas horas de ponta e recarga nas horas
   de excedente solar (coerente com o art. 4º §14: o ONS minimiza o custo do SIN).
   O ONS pode despachar por até 12 h a potência reduzida (art. 4º §4º). Isso pode ser
   representado com um CSV de despacho.
6. Energia exportada pelo lado mercantil é liquidada integralmente ao PLD (sem contratos no ACL).
7. Eficiências constantes, degradação linear no *throughput*, eletrolisador sem custo de
   partida e sem curva de eficiência em carga parcial.
8. A divisão do BESS em módulos é contínua em $P^{cap}$. Na prática ela é discreta
   (contêineres/inversores) e a habilitação exige baterias **novas** (art. 7º §2º).
9. Séries sintéticas no caso base (ver `src/pvbess_h2/dados.py`).

## 8. Extensões previstas

- **Estocástica em dois estágios**: $P^{cap}$ no 1º estágio; operação por cenário (PLD,
  PV, **despacho do ONS**) no 2º estágio; medidas de risco (CVaR). A decomposição da
  seção 6 se estende diretamente: cada par (bloco, cenário) vira um subproblema.
- **Dias representativos** (clusterização) para simular o ano todo; o limite de 366
  ciclos/ano passa a ser relevante.
- Penalidades e abatimento da receita fixa por indisponibilidade, quando o edital sair.
- Curva de eficiência do eletrolisador em carga parcial, custos de partida e tempo
  mínimo ligado/desligado.
- Degradação dependente da profundidade de descarga; custo de reposição de módulos
  para manter a disponibilidade ao longo dos 15 anos do CRCAP (art. 9º §4º, II-j).
- Critérios de certificação do H₂ verde (correlação temporal, adicionalidade).
- Dimensionamento ótimo (capacidades como variáveis, CAPEX anualizado) e avaliação
  econômica no horizonte do CRCAP (15 anos, início em 1º/08/2028).
