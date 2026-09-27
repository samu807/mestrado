# 3 METODOLOGIA

Este capítulo descreve o modelo de otimização desenvolvido para apoiar a decisão de um empreendedor que opera um sistema híbrido composto por usina fotovoltaica (FV), sistema de armazenamento de energia em baterias (*Battery Energy Storage System*, BESS) e eletrolisador para produção de hidrogênio verde, diante da possibilidade de comercializar parte da capacidade de armazenamento no Leilão de Reserva de Capacidade na forma de Potência (LRCAP) e o restante no Mercado de Curto Prazo (MCP). A Seção 3.1 apresenta o problema e o escopo do estudo; a Seção 3.2 discute o enquadramento regulatório que orienta a modelagem; a Seção 3.3 descreve o sistema; a Seção 3.4 apresenta a formulação matemática; a Seção 3.5 trata dos dados de entrada; a Seção 3.6 descreve o método de solução; a Seção 3.7 resume a implementação computacional; e a Seção 3.8 consolida as hipóteses e limitações.

## 3.1 Definição do problema e escopo

O problema consiste em determinar, sob a ótica de um agente privado tomador de preço (*price-taker*), a potência a ser contratada no LRCAP e a operação horária ótima do sistema híbrido ao longo de um horizonte anual, de modo a maximizar o lucro operacional do empreendimento. As duas decisões são interdependentes: a potência comprometida com o leilão reduz a capacidade de armazenamento disponível para a operação mercantil, que por sua vez determina quanto da energia fotovoltaica pode ser deslocada no tempo para abastecer o eletrolisador ou para ser comercializada nas horas de maior preço.

O estudo adota as seguintes delimitações de escopo:

a) as capacidades instaladas da usina FV, do BESS e do eletrolisador são dados de entrada, e não variáveis de decisão — o dimensionamento ótimo dos equipamentos está fora do escopo desta etapa;

b) o horizonte de análise é de um ano, com resolução horária, representativo da operação ao longo do contrato de 15 anos previsto para o LRCAP;

c) a abordagem é determinística, com conhecimento perfeito das séries de preço, de geração e de despacho do Operador Nacional do Sistema Elétrico (ONS) — a extensão estocástica é discutida na Seção 3.8;

d) a função objetivo considera receitas e custos operacionais; custos de investimento não são incluídos, uma vez que as capacidades são fixas.

## 3.2 Enquadramento regulatório

As regras aplicáveis ao armazenamento no LRCAP foram estabelecidas pela Portaria Normativa MME nº 136, de 1º de junho de 2026, que define as diretrizes e a sistemática dos leilões de 2026 destinados à contratação de potência a partir de novos sistemas de armazenamento em baterias (BRASIL, 2026). Três aspectos dessa norma condicionam diretamente a formulação.

O primeiro diz respeito à remuneração. A receita fixa contratada deve ser suficiente para "remunerar integralmente todo e qualquer uso que o ONS fizer dos empreendimentos vencedores [...] sem geração de receitas adicionais fora do CRCAP" (BRASIL, 2026, art. 9º, § 5º, IV). Além disso, a energia utilizada na recarga e a energia injetada pelo sistema de armazenamento são liquidadas no MCP ao Preço de Liquidação das Diferenças (PLD), mas os resultados dessa liquidação são destinados à Conta de Potência para Reserva de Capacidade (CONCAP), e não ao empreendedor (art. 9º, § 6º). Consequentemente, a parcela contratada no leilão não pode realizar arbitragem de preços em benefício do seu titular.

O segundo aspecto refere-se ao controle operativo. O empreendimento contratado deve atender à totalidade dos despachos de recarga e de descarga estabelecidos pelo ONS na programação diária e na operação em tempo real (art. 4º, § 2º), e a totalidade da potência contratada deve ser disponibilizada para esse despacho (art. 4º, § 8º). O risco associado à incerteza do despacho é alocado ao empreendedor (art. 5º, § 2º).

O terceiro aspecto é a possibilidade de compartilhamento da conexão. A norma admite que os sistemas de armazenamento sejam instalados no mesmo ponto de conexão de outros agentes, compartilhando as instalações de interesse restrito (art. 4º, § 1º, II).

Diante disso, a "arbitragem" entre o LRCAP e o MCP é modelada neste trabalho como uma **decisão de alocação da capacidade de armazenamento instalada** entre dois módulos com medição individualizada: um **módulo LRCAP**, cuja potência é contratada no leilão, operado exclusivamente segundo o despacho do ONS e remunerado apenas pela receita fixa; e um **módulo mercantil**, que recebe a capacidade remanescente e é operado pelo empreendedor em conjunto com a usina FV e o eletrolisador. Ambos compartilham o ponto de conexão com o Sistema Interligado Nacional (SIN).

A Portaria estabelece, ainda, requisitos técnicos que são incorporados ao modelo como restrições ou como condições de validação dos parâmetros, sintetizados no Quadro 3.1.

::: {custom-style="Legenda"}
Quadro 3.1 – Requisitos da Portaria Normativa MME nº 136/2026 incorporados ao modelo
:::

| Requisito | Dispositivo | Tratamento no modelo |
|------------------------------|------------------|--------------------------------------------------|
| Disponibilidade mínima de 30 MW | art. 7º, III | Restrição disjuntiva na potência contratada (Eq. {eq:cap}) |
| Compromisso de 4 h por ciclo completo | art. 4º, § 3º; art. 7º, IV | Dimensionamento energético do módulo LRCAP (Eq. {eq:hab}) |
| Até 2 ciclos completos diários e 366 anuais | art. 4º, § 3º | Validação do perfil de despacho do ONS |
| Eficiência total (RTE) mínima de 85% | art. 7º, VI | Validação dos parâmetros de eficiência |
| Recarga completa em até 6 h | art. 4º, § 10; art. 7º, VII | Validação dos parâmetros de eficiência |
| Recarga excedente custeada pelo empreendedor | art. 9º, §§ 7º e 8º | Termo de custo na função objetivo (Eq. {eq:kappa}) |
| Uso do sistema para descarga e recarga totais | art. 9º, § 13 | Limite no fluxo líquido do ponto de conexão |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor com base em Brasil (2026).
:::

## 3.3 Descrição do sistema

A Figura 3.1 apresenta a topologia do sistema modelado. No lado mercantil, a usina FV, o módulo mercantil do BESS e o eletrolisador estão conectados a um barramento comum, no qual se impõe o balanço de potência. O hidrogênio produzido é armazenado em um tanque e comercializado a preço fixo. A energia excedente pode ser exportada ao SIN e liquidada ao PLD. O módulo LRCAP, embora fisicamente instalado no mesmo sítio, possui ponto de medição próprio e segue um perfil de descarga e recarga determinado pelo ONS. Os fluxos de ambos os lados convergem para o ponto de conexão compartilhado, cuja capacidade limita o fluxo líquido em cada hora.

::: {custom-style="Legenda"}
Figura 3.1 – Topologia do sistema híbrido FV–BESS–H₂ com divisão do BESS entre os módulos LRCAP e mercantil
:::

::: {custom-style="Figura"}
![](figuras/fig_topologia.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

Adota-se como caso de referência uma versão escalonada da planta de produção de hidrogênio da Universidade Federal de Itajubá (UNIFEI), que conta com usina FV de aproximadamente 1 MWp e eletrolisador do tipo membrana de troca de prótons (*Proton Exchange Membrane*, PEM) de 350 kW, sem armazenamento em baterias. Como o LRCAP exige disponibilidade mínima de 30 MW, a planta real não pode participar do leilão; por isso, preserva-se a relação entre as potências do eletrolisador e da usina FV observada na planta (0,35) e escala-se o sistema para 50 MWp de geração FV e 17,5 MW de eletrolisador. O BESS é hipotético e dimensionado para atender aos requisitos do leilão. A justificativa para o escalonamento reside na modularidade dos eletrolisadores PEM, cujas pilhas são associadas em paralelo, de forma que o consumo específico de energia por unidade de hidrogênio é pouco sensível à escala.

## 3.4 Formulação matemática

O problema é formulado como um problema de Programação Linear Inteira Mista (PLIM, ou *Mixed-Integer Linear Programming*, MILP), em que a função objetivo e as restrições são lineares e parte das variáveis é binária.

### 3.4.1 Conjuntos e índices

Seja $\mathcal{T} = \{0, 1, \dots, N-1\}$ o conjunto de intervalos de tempo de duração $\Delta t$ (em horas) e $\mathcal{D}$ o conjunto de dias do horizonte, sendo $\mathcal{T}_d \subseteq \mathcal{T}$ os intervalos pertencentes ao dia $d$.

### 3.4.2 Parâmetros

Os parâmetros do modelo são apresentados na Tabela 3.1, juntamente com os valores adotados no caso de referência.

::: {custom-style="Legenda"}
Tabela 3.1 – Parâmetros do modelo e valores do caso de referência
:::

| Símbolo | Descrição | Unidade | Valor |
|--------------|------------------------------------------------|----------------|------------------|
| $\bar P^{pv}_t$ | Potência FV disponível no intervalo $t$ | MW | série (Seção 3.5) |
| $\lambda_t$ | PLD horário | R\$/MWh | série (Seção 3.5) |
| $E^{tot}$ | Capacidade energética total instalada do BESS | MWh | 300 |
| $\bar P^{ch}, \bar P^{dis}$ | Potências máximas de carga e de descarga do BESS | MW | 60 |
| $\eta^{ch}, \eta^{dis}$ | Eficiências de carga e de descarga | – | 0,95 |
| $\underline\sigma, \bar\sigma$ | Estados de carga mínimo e máximo (fração da energia do módulo) | – | 0,10; 1,00 |
| $\sigma_0$ | Estado de carga inicial do módulo mercantil | – | 0,50 |
| $c^{deg}$ | Custo de degradação por energia descarregada | R\$/MWh | 50 |
| $\bar P^{el}$ | Potência nominal do eletrolisador | MW | 17,5 |
| $\alpha^{el}$ | Carga mínima do eletrolisador (fração de $\bar P^{el}$) | – | 0,10 |
| $k^{el}$ | Consumo específico de energia | kWh/kg | 55 |
| $c^{h2}$ | Custo variável de produção de H₂ | R\$/kg | 1,5 |
| $\pi^{h2}$ | Preço de venda do H₂ | R\$/kg | 35 |
| $\bar S, S_0$ | Capacidade e estoque inicial do tanque de H₂ | kg | 2.000; 0 |
| $D^{h2}$ | Entrega mínima diária de H₂ | kg/dia | 0 |
| $\bar P^{exp}, \bar P^{imp}$ | Limites de exportação e importação no ponto de conexão | MW | 80 |
| $c^{imp}$ | Custo adicional sobre a energia importada | R\$/MWh | 250 |
| $R^{cap}$ | Receita fixa do LRCAP | R\$/(MW·ano) | 600.000 |
| $\underline P^{cap}$ | Disponibilidade mínima para participação no LRCAP | MW | 30 |
| $H^{cap}$ | Duração do ciclo completo exigida | h | 4 |
| $\rho$ | Energia instalada no módulo LRCAP por MW contratado | MWh/MW | 4,8 |
| $\mathrm{RTE}^{ref}$ | Eficiência de referência para custeio da recarga | – | 0,85 |
| $\delta_t, r_t$ | Despacho do ONS: descarga e recarga do módulo LRCAP (p.u. de $P^{cap}$) | – | perfil (Seção 3.5) |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

### 3.4.3 Variáveis de decisão

As variáveis de decisão são apresentadas na Tabela 3.2. Destaca-se que $P^{cap}$ é a única variável que não é indexada no tempo: ela representa a decisão de contratação, válida para todo o horizonte, enquanto as demais descrevem a operação horária.

::: {custom-style="Legenda"}
Tabela 3.2 – Variáveis de decisão
:::

| Símbolo | Descrição | Domínio |
|------------------|------------------------------------------------------|--------------------------|
| $P^{cap}$ | Potência contratada no LRCAP | $\mathbb{R}_{\geq 0}$, MW |
| $w$ | Indicador de participação no LRCAP | $\{0, 1\}$ |
| $p^{pv}_t$ | Potência FV aproveitada | $[0, \bar P^{pv}_t]$, MW |
| $p^{ch}_t, p^{dis}_t$ | Potências de carga e descarga do módulo mercantil | $\mathbb{R}_{\geq 0}$, MW |
| $e_t$ | Energia armazenada no módulo mercantil | $\mathbb{R}_{\geq 0}$, MWh |
| $p^{el}_t$ | Potência consumida pelo eletrolisador | $[0, \bar P^{el}]$, MW |
| $m_t, v_t$ | Produção e venda de H₂ | $\mathbb{R}_{\geq 0}$, kg/h |
| $s_t$ | Estoque de H₂ | $[0, \bar S]$, kg |
| $p^{exp}_t, p^{imp}_t$ | Exportação e importação do lado mercantil | $\mathbb{R}_{\geq 0}$, MW |
| $y^{bat}_t$ | Estado do módulo mercantil (1 = carregando) | $\{0, 1\}$ |
| $y^{rede}_t$ | Sentido do intercâmbio (1 = exportando) | $\{0, 1\}$ |
| $z_t$ | Estado do eletrolisador (1 = ligado) | $\{0, 1\}$ |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

### 3.4.4 Função objetivo

O objetivo é maximizar o lucro operacional do empreendedor no horizonte, expresso pela Equação {eq:fo}:

$$
\max\; \sum_{t \in \mathcal{T}} \lambda_t\, p^{exp}_t\, \Delta t
- \sum_{t \in \mathcal{T}} \left(\lambda_t + c^{imp}\right) p^{imp}_t\, \Delta t
+ \sum_{t \in \mathcal{T}} \left(\pi^{h2} v_t - c^{h2} m_t\right) \Delta t
+ R^{cap}\, \frac{N \Delta t}{8760}\, P^{cap}
- \kappa\, P^{cap}
- \sum_{t \in \mathcal{T}} c^{deg} \left(p^{dis}_t + \delta_t P^{cap}\right) \Delta t
$$ {#eq:fo}

Os termos correspondem, respectivamente, à receita da energia exportada ao MCP, ao custo da energia importada, à margem da comercialização do hidrogênio, à receita fixa do LRCAP rateada no horizonte, ao custo da recarga excedente do módulo LRCAP e ao custo de degradação do BESS, aplicado à energia descarregada por ambos os módulos. Ressalta-se que a energia injetada pelo módulo LRCAP não compõe a receita do MCP do empreendedor, em conformidade com o art. 9º, § 6º, da Portaria.

O coeficiente $\kappa$ representa o custo, por MW contratado, da energia de recarga que excede o quociente entre a energia injetada e a eficiência de referência, a qual deve ser custeada pelo empreendedor (BRASIL, 2026, art. 9º, §§ 7º e 8º). Como o perfil de despacho é exógeno e proporcional a $P^{cap}$, $\kappa$ é calculado previamente pela Equação {eq:kappa}:

$$
\kappa = \max\!\left(0,\; 1 - \frac{\sum_{t} \delta_t\, \Delta t}{\mathrm{RTE}^{ref} \sum_{t} r_t\, \Delta t}\right) \sum_{t \in \mathcal{T}} \lambda_t\, r_t\, \Delta t
$$ {#eq:kappa}

Quando a eficiência real do BESS ($\eta^{ch}\eta^{dis}$) supera $\mathrm{RTE}^{ref}$, a recarga determinada pelo ONS não excede o limite custeado pela CONCAP e, portanto, $\kappa = 0$.

### 3.4.5 Restrições

**Contratação no LRCAP.** A potência contratada deve ser nula ou estar entre o mínimo regulatório e o máximo viável, o que é representado pela restrição disjuntiva da Equação {eq:cap}, em que $w$ indica a participação no leilão:

$$
\underline P^{cap}\, w \;\leq\; P^{cap} \;\leq\; \bar P^{cap}\, w
$$ {#eq:cap}

O limite superior $\bar P^{cap}$ é o menor valor entre as potências de carga e descarga do BESS, a razão $E^{tot}/\rho$ e os limites do ponto de conexão.

**Módulo LRCAP.** As potências de descarga e de recarga do módulo LRCAP seguem o perfil de despacho do ONS, expresso em valores por unidade da potência contratada, conforme a Equação {eq:ons}:

$$
p^{dis,lr}_t = \delta_t\, P^{cap}, \qquad p^{ch,lr}_t = r_t\, P^{cap} \qquad \forall t \in \mathcal{T}
$$ {#eq:ons}

Como o perfil é exógeno, o estado de carga do módulo LRCAP é proporcional a $P^{cap}$ e pode ser verificado previamente à otimização. Define-se o estado de carga por MW contratado, $\varepsilon_t$, pela recursão da Equação {eq:epsilon}, com $\varepsilon_{-1} = \bar\sigma\rho$ (módulo inicialmente carregado):

$$
\varepsilon_t = \varepsilon_{t-1} + \left(\eta^{ch} r_t - \frac{\delta_t}{\eta^{dis}}\right) \Delta t, \qquad \underline\sigma\rho \leq \varepsilon_t \leq \bar\sigma\rho
$$ {#eq:epsilon}

Um perfil que viole esses limites é rejeitado na etapa de pré-processamento. O parâmetro $\rho$ deve, ainda, permitir a descarga contínua na potência contratada pela duração exigida, considerando a faixa de operação adotada pelo empreendedor, conforme a Equação {eq:hab}:

$$
\left(\bar\sigma - \underline\sigma\right) \rho\, \eta^{dis} \geq H^{cap}
$$ {#eq:hab}

Com os valores da Tabela 3.1, tem-se $(1{,}0 - 0{,}1) \times 4{,}8 \times 0{,}95 = 4{,}10 \geq 4$ h.

**Módulo mercantil.** O módulo mercantil dispõe da energia e da potência remanescentes após a alocação ao módulo LRCAP. A energia disponível é dada pela Equação {eq:emerc}:

$$
E^{m} = E^{tot} - \rho\, P^{cap}
$$ {#eq:emerc}

A dinâmica do estado de carga e seus limites são descritos pelas Equações {eq:soc} e {eq:soclim}. A condição de contorno impõe que o estado de carga ao final do horizonte não seja inferior ao inicial, evitando que o modelo esvazie o armazenamento para aumentar artificialmente o lucro:

$$
e_t = e_{t-1} + \left(\eta^{ch} p^{ch}_t - \frac{p^{dis}_t}{\eta^{dis}}\right) \Delta t, \qquad e_{-1} = \sigma_0 E^{m}, \qquad e_{N-1} \geq \sigma_0 E^{m}
$$ {#eq:soc}

$$
\underline\sigma\, E^{m} \leq e_t \leq \bar\sigma\, E^{m} \qquad \forall t \in \mathcal{T}
$$ {#eq:soclim}

As potências de carga e de descarga são limitadas pelas Equações {eq:pch} e {eq:pdis}. As restrições com a variável binária $y^{bat}_t$ impedem a carga e a descarga simultâneas, e as restrições com $P^{cap}$ garantem que a potência somada dos dois módulos não exceda a capacidade dos conversores:

$$
p^{ch}_t \leq \bar P^{ch}\, y^{bat}_t, \qquad p^{ch}_t \leq \bar P^{ch} - P^{cap} \qquad \forall t \in \mathcal{T}
$$ {#eq:pch}

$$
p^{dis}_t \leq \bar P^{dis} \left(1 - y^{bat}_t\right), \qquad p^{dis}_t \leq \bar P^{dis} - P^{cap} \qquad \forall t \in \mathcal{T}
$$ {#eq:pdis}

Observa-se que as Equações {eq:soclim}, {eq:pch} e {eq:pdis} são lineares porque $E^{m}$ e os limites remanescentes são funções afins de $P^{cap}$, e não produtos entre variáveis.

**Balanço de potência.** No barramento do lado mercantil, a potência injetada deve igualar a potência consumida em cada intervalo, conforme a Equação {eq:balanco}:

$$
p^{pv}_t + p^{dis}_t + p^{imp}_t = p^{ch}_t + p^{el}_t + p^{exp}_t \qquad \forall t \in \mathcal{T}
$$ {#eq:balanco}

**Intercâmbio com a rede.** A variável binária $y^{rede}_t$ impede a exportação e a importação simultâneas pelo lado mercantil (Equação {eq:rede}). O fluxo líquido no ponto de conexão compartilhado, que inclui os fluxos do módulo LRCAP, é limitado pela Equação {eq:conexao}:

$$
p^{exp}_t \leq \bar P^{exp}\, y^{rede}_t, \qquad p^{imp}_t \leq \bar P^{imp,m} \left(1 - y^{rede}_t\right) \qquad \forall t \in \mathcal{T}
$$ {#eq:rede}

$$
-\bar P^{imp} \;\leq\; p^{exp}_t - p^{imp}_t + p^{dis,lr}_t - p^{ch,lr}_t \;\leq\; \bar P^{exp} \qquad \forall t \in \mathcal{T}
$$ {#eq:conexao}

O parâmetro $\bar P^{imp,m}$ corresponde ao limite de importação do lado mercantil. Para assegurar que todo o hidrogênio produzido seja de origem renovável, adota-se $\bar P^{imp,m} = 0$ no caso de referência: o eletrolisador é suprido exclusivamente pela geração FV, diretamente ou por meio da energia armazenada no módulo mercantil.

**Eletrolisador e hidrogênio.** O eletrolisador opera entre sua carga mínima e sua potência nominal quando ligado, e sua produção é proporcional à potência consumida, com eficiência constante (Equações {eq:el} e {eq:prod}):

$$
\alpha^{el}\, \bar P^{el}\, z_t \;\leq\; p^{el}_t \;\leq\; \bar P^{el}\, z_t \qquad \forall t \in \mathcal{T}
$$ {#eq:el}

$$
m_t = \frac{1000}{k^{el}}\, p^{el}_t \qquad \forall t \in \mathcal{T}
$$ {#eq:prod}

O balanço do tanque de hidrogênio, com condição de contorno análoga à do BESS, e a entrega mínima diária são expressos pelas Equações {eq:tanque} e {eq:entrega}:

$$
s_t = s_{t-1} + \left(m_t - v_t\right) \Delta t, \qquad s_{-1} = S_0, \qquad s_{N-1} \geq S_0
$$ {#eq:tanque}

$$
\sum_{t \in \mathcal{T}_d} v_t\, \Delta t \geq D^{h2} \qquad \forall d \in \mathcal{D}
$$ {#eq:entrega}

O modelo resultante, composto pela função objetivo da Equação {eq:fo} e pelas restrições das Equações {eq:cap} a {eq:entrega}, é um MILP. Para um horizonte de uma semana (168 h), o problema possui 1.681 variáveis contínuas, 505 variáveis binárias e 2.692 restrições; para um ano (8.760 h), 87.601 variáveis contínuas, 26.281 binárias e 140.164 restrições.

## 3.5 Dados de entrada

**Preço de Liquidação das Diferenças.** Utiliza-se a série horária do PLD de 2025 para o submercado Sudeste/Centro-Oeste, no qual se localiza o município de Itajubá (MG), obtida no portal de dados abertos da Câmara de Comercialização de Energia Elétrica (CCEE, 2026). A série apresenta média de R\$ 224,31/MWh, com mínimo de R\$ 58,60/MWh — valor do PLD mínimo, observado em 2.030 horas, concentradas no período úmido — e máximo de R\$ 1.421,87/MWh. A Figura 3.2(a) evidencia o perfil diário característico do período recente: preços reduzidos nas horas de maior geração solar e elevados na rampa noturna, com maior amplitude no período seco.

**Geração fotovoltaica.** A disponibilidade de geração FV foi obtida na plataforma *Photovoltaic Geographical Information System* (PVGIS), mantida pelo Centro Comum de Investigação da Comissão Europeia (HULD; MÜLLER; GAMBARDELLA, 2012), a partir da base de reanálise ERA5 (HERSBACH *et al.*, 2020), para as coordenadas de Itajubá (latitude −22,425°; longitude −45,457°; altitude de 848 m). Considerou-se um sistema de silício cristalino de 1 kWp, com perdas de 14% e inclinação e azimute ótimos (25° e −165°, respectivamente), no ano de 2023, o mais recente disponível. A potência horária foi convertida em fator de capacidade, deslocada do tempo universal coordenado para o horário oficial de Brasília (UTC−3) e reposicionada no calendário de 2025, preservando mês, dia e hora, para compatibilização com a série de preços. O fator de capacidade médio resultante é de 16,9%, equivalente a 1.478 kWh/kWp por ano (Figura 3.2(b)). A série é multiplicada pela potência instalada da usina para obter $\bar P^{pv}_t$.

::: {custom-style="Legenda"}
Figura 3.2 – Perfis horários médios dos dados de entrada: (a) PLD do submercado SE/CO em 2025, por período hidrológico; (b) fator de capacidade FV em Itajubá
:::

::: {custom-style="Figura"}
![](figuras/fig_perfis_entrada.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor com dados de CCEE (2026) e do PVGIS.
:::

**Despacho do ONS.** Na ausência de histórico de despacho de sistemas de armazenamento contratados no LRCAP, adota-se um perfil diário sintético: descarga na potência contratada entre 18 h e 22 h, horário de maior demanda líquida, e recarga entre 10 h e 15 h, até a restauração completa do estado de carga, limitada à potência nominal. O perfil é coerente com a diretriz de que a programação da recarga busque minimizar o custo total de operação do SIN (BRASIL, 2026, art. 4º, § 14), o que tende a deslocá-la para as horas de excedente de geração solar. O perfil resulta em um ciclo completo por dia (365 no ano), dentro dos limites regulatórios.

**Parâmetros técnico-econômicos.** Os parâmetros do eletrolisador foram definidos a partir da faixa típica da tecnologia PEM, cujo consumo específico de energia situa-se entre 4,3 e 5,2 kWh/Nm³, ou aproximadamente 48 a 58 kWh/kg, até que os dados do fabricante do equipamento da UNIFEI sejam incorporados. A receita fixa do LRCAP e o preço do hidrogênio não possuem, até o momento, referências de mercado consolidadas no Brasil e são, por isso, objeto de análise de sensibilidade.

## 3.6 Método de solução

### 3.6.1 Solução por ramificação e limitação

Problemas MILP são usualmente resolvidos por algoritmos de ramificação e limitação (*branch-and-bound*) combinados à geração de planos de corte, nos quais relaxações lineares sucessivas fornecem limites para o valor ótimo e permitem certificar a qualidade da solução por meio do *gap* de otimalidade. Neste trabalho utiliza-se o *solver* de código aberto HiGHS (HUANGFU; HALL, 2018). Para o horizonte de uma semana, o problema é resolvido em menos de um segundo. Para o horizonte anual, entretanto, a solução direta não foi obtida em 15 minutos de processamento, o que motivou a adoção de uma estratégia de decomposição.

### 3.6.2 Decomposição de Benders

A estrutura do problema favorece a decomposição: a potência contratada $P^{cap}$ é a única variável que acopla todo o horizonte, enquanto as variáveis operacionais de um período se relacionam com as dos períodos vizinhos apenas pelos estados de armazenamento. Dividindo-se o ano em blocos semanais $w \in \mathcal{W}$ e impondo-se condições de contorno cíclicas em cada bloco, o problema anual pode ser reescrito conforme a Equação {eq:benders}:

$$
\max_{P^{cap} \in \{0\} \cup [\underline P^{cap},\, \bar P^{cap}]} \; R^{cap}\, \frac{H}{8760}\, P^{cap} + \sum_{w \in \mathcal{W}} Q_w\!\left(P^{cap}\right)
$$ {#eq:benders}

em que $H$ é o número de horas do horizonte e $Q_w(x)$ é o lucro operacional ótimo do bloco $w$ quando $P^{cap} = x$, obtido pela solução do MILP de 168 horas descrito na Seção 3.4, sem o termo de receita fixa. Esse arranjo corresponde à estrutura clássica da decomposição de Benders (BENDERS, 1962; CONEJO *et al.*, 2006), com $P^{cap}$ como variável do problema mestre e os blocos semanais como subproblemas independentes, que podem ser resolvidos em paralelo.

A decomposição de Benders clássica pressupõe subproblemas lineares contínuos, cuja função valor é côncava (em problemas de maximização) e aproximável por hiperplanos obtidos a partir das variáveis duais. No presente caso, os subproblemas contêm variáveis binárias ($y^{bat}_t$, $y^{rede}_t$ e $z_t$), de modo que $Q_w$ não é, em geral, côncava, e os cortes derivados do dual da relaxação linear não são necessariamente válidos. Para contornar essa limitação, empregam-se os **cortes de Benders reforçados** (*strengthened Benders cuts*) propostos por Zou, Ahmed e Sun (2019). Introduz-se em cada subproblema uma variável de cópia $z_w$, vinculada à decisão do mestre pela restrição $z_w = \hat x$. Sendo $\lambda_w$ o multiplicador dual dessa restrição na relaxação linear do subproblema, calcula-se o valor da relaxação lagrangiana da Equação {eq:lagr}:

$$
C_w\!\left(\lambda_w\right) = \max_{(y,\, z_w) \in X_w} \; f_w(y, z_w) - \lambda_w\, z_w
$$ {#eq:lagr}

em que $X_w$ é o conjunto viável do MILP do bloco, com $z_w$ livre, e $f_w$ é a sua função objetivo operacional. Por dualidade lagrangiana, para qualquer $x$ vale $Q_w(x) \leq C_w(\lambda_w) + \lambda_w x$, o que fornece o corte válido da Equação {eq:corte}:

$$
\theta_w \leq C_w\!\left(\lambda_w\right) + \lambda_w\, P^{cap}
$$ {#eq:corte}

Para preservar a validade do corte mesmo quando o MILP lagrangiano não é resolvido até a otimalidade exata, $C_w$ é tomado como o limite dual reportado pelo *solver*, e não como o valor da melhor solução encontrada.

O problema mestre, apresentado na Equação {eq:mestre}, é um MILP de pequeno porte, com uma variável contínua para a potência, uma binária para a participação e uma variável $\theta_w$ por bloco:

$$
\max\; R^{cap}\, \frac{H}{8760}\, P + \sum_{w \in \mathcal{W}} \theta_w \quad \text{s.a.} \quad \theta_w \leq C^{k}_w + \lambda^{k}_w\, P \;\; \forall w, k; \qquad \underline P^{cap} w \leq P \leq \bar P^{cap} w
$$ {#eq:mestre}

em que $k$ indexa os cortes acumulados ao longo das iterações.

### 3.6.3 Algoritmo e critério de convergência

O procedimento, ilustrado na Figura 3.3, é composto pelas seguintes etapas:

a) **inicialização:** avaliam-se os pontos $\hat x \in \{0,\; \underline P^{cap},\; \bar P^{cap}\}$;

b) **subproblemas:** para cada bloco $w$ e para o ponto $\hat x$, resolvem-se (i) o MILP com $P^{cap} = \hat x$, que fornece $Q_w(\hat x)$; (ii) a relaxação linear, que fornece $\lambda_w$; e (iii) o MILP lagrangiano, que fornece $C_w(\lambda_w)$;

c) **limite inferior:** como o valor $R^{cap} (H/8760)\hat x + \sum_w Q_w(\hat x)$ corresponde a uma solução viável do problema original, ele constitui um limite inferior ($LB$), atualizado com o melhor valor obtido;

d) **problema mestre:** adicionam-se os novos cortes e resolve-se o mestre, cuja solução fornece o próximo ponto $\hat x$ e cujo valor ótimo constitui um limite superior ($UB$), uma vez que os cortes superestimam a função valor;

e) **critério de parada:** o algoritmo termina quando o *gap* relativo $(UB - LB)/LB$ é inferior a uma tolerância $\varepsilon$, adotada como 0,1%. Caso o mestre proponha um ponto já avaliado, o procedimento é interrompido e o *gap* remanescente é reportado como certificado da qualidade da solução.

::: {custom-style="Legenda"}
Figura 3.3 – Fluxograma do algoritmo de decomposição de Benders com cortes reforçados
:::

::: {custom-style="Figura"}
![](figuras/fig_fluxograma_benders.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

Uma propriedade relevante do método é que ele fornece, a cada iteração, limites superior e inferior para o lucro ótimo, de modo que a qualidade da solução final é certificada, e não apenas estimada. Essa característica o distingue de métodos heurísticos e meta-heurísticos, como algoritmos genéticos, frequentemente empregados em problemas de dimensionamento e operação de sistemas de armazenamento (FENG *et al.*, 2022), mas que não oferecem garantia de otimalidade.

## 3.7 Implementação computacional

O modelo foi implementado na linguagem Python, com o uso da biblioteca de modelagem algébrica Pyomo (BYNUM *et al.*, 2021) e do *solver* HiGHS (HUANGFU; HALL, 2018). A estrutura do código separa: (i) a leitura e validação dos parâmetros, organizados em arquivos de configuração em formato YAML, com verificação automática dos requisitos regulatórios; (ii) a importação e o tratamento das séries de dados; (iii) a construção do modelo de otimização; (iv) a decomposição de Benders; e (v) o pós-processamento dos resultados. Os subproblemas semanais são resolvidos em paralelo em processos independentes, cada qual restrito a uma linha de execução do *solver*, a fim de evitar a concorrência por núcleos de processamento. A consistência do modelo é verificada por um conjunto de testes automatizados que conferem, entre outros aspectos, o balanço de potência, os limites dos estados de carga, a exclusividade entre carga e descarga, o cumprimento do despacho do ONS, o limite do ponto de conexão e a validade dos cortes de Benders. O código e os dados são mantidos sob controle de versão, o que assegura a reprodutibilidade dos resultados.

## 3.8 Hipóteses e limitações

As principais hipóteses adotadas, e as respectivas implicações, são as seguintes:

a) **previsão perfeita:** as séries de PLD, de geração FV e de despacho do ONS são conhecidas antecipadamente, o que tende a superestimar o lucro alcançável na operação real. Em particular, a incerteza do despacho do ONS, cujo risco é alocado ao empreendedor pela Portaria, é candidata natural a uma extensão estocástica em dois estágios, em que $P^{cap}$ é decidida no primeiro estágio e a operação se adapta a cenários no segundo;

b) **agente tomador de preço:** a operação do sistema não altera o PLD;

c) **receita fixa simplificada:** a receita fixa é rateada linearmente no horizonte, sem reajuste pelo Índice Nacional de Preços ao Consumidor Amplo (IPCA), sem o abatimento mensal por desempenho e sem as penalidades por indisponibilidade, cujos detalhes dependem do edital do leilão;

d) **disponibilidade integral:** o módulo LRCAP atende a 100% do despacho, sem indisponibilidades programadas ou forçadas;

e) **eletrolisador simplificado:** eficiência constante em toda a faixa de operação, sem custos de partida, tempos mínimos de operação e de parada, estado de espera (*standby*) ou limites de rampa;

f) **degradação linear:** o custo de degradação do BESS é proporcional à energia descarregada, sem dependência da profundidade de descarga;

g) **divisão contínua do BESS:** a alocação entre os módulos é tratada como contínua, embora na prática seja discreta, em função da modularidade dos contêineres e conversores;

h) **condições cíclicas semanais:** a decomposição impõe que os estados de armazenamento retornem ao valor inicial ao final de cada semana, impedindo transferências de energia ou de hidrogênio entre semanas;

i) **anos distintos:** a série de irradiância (2023) e a de preços (2025) referem-se a anos diferentes. Para uma usina de pequeno porte em relação ao SIN, a correlação horária entre a geração local e o PLD tende a ser fraca, mas a hipótese deve ser considerada na interpretação dos resultados.

## REFERÊNCIAS

::: {custom-style="Referencia"}
BENDERS, J. F. Partitioning procedures for solving mixed-variables programming problems. **Numerische Mathematik**, v. 4, n. 1, p. 238–252, 1962.
:::

::: {custom-style="Referencia"}
BRASIL. Ministério de Minas e Energia. Portaria Normativa MME nº 136, de 1º de junho de 2026. Estabelece as Diretrizes e a Sistemática para a realização dos Leilões para Contratação de Potência Elétrica, a partir de novos sistemas de armazenamento de energia em baterias. **Diário Oficial da União**: seção 1, Brasília, DF, n. 103, p. 98, 3 jun. 2026.
:::

::: {custom-style="Referencia"}
BYNUM, M. L. *et al.* **Pyomo**: optimization modeling in Python. 3. ed. Cham: Springer, 2021.
:::

::: {custom-style="Referencia"}
CCEE – CÂMARA DE COMERCIALIZAÇÃO DE ENERGIA ELÉTRICA. **PLD horário**. Portal de Dados Abertos da CCEE. Disponível em: https://dadosabertos.ccee.org.br. Acesso em: 27 set. 2026.
:::

::: {custom-style="Referencia"}
CONEJO, A. J. *et al.* **Decomposition techniques in mathematical programming**: engineering and science applications. Berlin: Springer, 2006.
:::

::: {custom-style="Referencia"}
FENG, L. *et al.* Optimization analysis of energy storage application based on electricity price arbitrage and ancillary services. **Journal of Energy Storage**, v. 55, p. 105508, 2022.
:::

::: {custom-style="Referencia"}
HERSBACH, H. *et al.* The ERA5 global reanalysis. **Quarterly Journal of the Royal Meteorological Society**, v. 146, n. 730, p. 1999–2049, 2020.
:::

::: {custom-style="Referencia"}
HUANGFU, Q.; HALL, J. A. J. Parallelizing the dual revised simplex method. **Mathematical Programming Computation**, v. 10, n. 1, p. 119–142, 2018.
:::

::: {custom-style="Referencia"}
HULD, T.; MÜLLER, R.; GAMBARDELLA, A. A new solar radiation database for estimating PV performance in Europe and Africa. **Solar Energy**, v. 86, n. 6, p. 1803–1815, 2012.
:::

::: {custom-style="Referencia"}
ZOU, J.; AHMED, S.; SUN, X. A. Stochastic dual dynamic integer programming. **Mathematical Programming**, v. 175, n. 1–2, p. 461–502, 2019.
:::
