# 3 METODOLOGIA

Este capítulo descreve o modelo de otimização desenvolvido para apoiar a decisão de um empreendedor que opera um sistema híbrido composto por usina fotovoltaica (FV), sistema de armazenamento de energia em baterias (*Battery Energy Storage System*, BESS) e eletrolisador para produção de hidrogênio verde, diante da possibilidade de comercializar parte da capacidade de armazenamento no Leilão de Reserva de Capacidade na forma de Potência (LRCAP) e o restante no Mercado de Curto Prazo (MCP). A Seção 3.1 apresenta o problema e o escopo do estudo; a Seção 3.2 discute o enquadramento regulatório que orienta a modelagem; a Seção 3.3 descreve o sistema; a Seção 3.4 apresenta a formulação matemática; a Seção 3.5 trata dos dados de entrada; a Seção 3.6 descreve o método de solução; a Seção 3.7 apresenta a extensão estocástica do modelo e os indicadores de valor da informação; a Seção 3.8 descreve a decisão de oferta no leilão — a curva de oferta, a viabilidade econômica e o lance mínimo — e as análises de sensibilidade; a Seção 3.9 resume a implementação computacional; e a Seção 3.10 consolida as hipóteses e limitações.

## 3.1 Definição do problema e escopo

O problema consiste em determinar, sob a ótica de um agente privado tomador de preço (*price-taker*), a potência a ser contratada no LRCAP e a operação horária ótima do sistema híbrido ao longo de um horizonte anual, de modo a maximizar o lucro operacional do empreendimento. As duas decisões são interdependentes: a potência comprometida com o leilão reduz a capacidade de armazenamento disponível para a operação mercantil, que por sua vez determina quanto da energia fotovoltaica pode ser deslocada no tempo para abastecer o eletrolisador ou para ser comercializada nas horas de maior preço.

Quando o BESS ainda será construído — situação prevista na Portaria, que trata da contratação de novos sistemas de armazenamento —, essas decisões são precedidas pela decisão de investimento: construir ou não a bateria e, portanto, qual a menor receita fixa, ou lance mínimo, que justifica a construção. O trabalho considera as duas situações: a de um proponente que precisa construir o BESS, foco principal da análise, e a de um proponente que já dispõe dele, para o qual se determina quanto da capacidade contratar no leilão.

O estudo adota as seguintes delimitações de escopo:

a) as capacidades instaladas da usina FV, do BESS e do eletrolisador são dados de entrada, e não variáveis de decisão — o dimensionamento ótimo dos equipamentos está fora do escopo desta etapa, e o efeito do tamanho do eletrolisador e do tanque de hidrogênio é avaliado por análise de sensibilidade (Seção 3.8.4); para o BESS a construir, avalia-se ainda a bateria dimensionada para o contrato do leilão (Seção 3.8.3);

b) o horizonte de análise é de um ano, com resolução horária, representativo da operação ao longo do contrato de 15 anos previsto para o LRCAP;

c) na formulação básica, a abordagem é determinística, com conhecimento perfeito das séries de preço, de geração e de despacho do Operador Nacional do Sistema Elétrico (ONS); a incerteza entre anos é tratada pela extensão estocástica da Seção 3.7;

d) a função objetivo considera receitas e custos operacionais; os custos de investimento não entram na otimização, uma vez que as capacidades são fixas, e são considerados a posteriori na análise de viabilidade econômica e do lance mínimo (Seção 3.8.2).

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

A Figura 3.1 apresenta a topologia do sistema modelado. No lado mercantil, a usina FV, o módulo mercantil do BESS e o eletrolisador estão conectados a um barramento comum, no qual se impõe o balanço de potência. O hidrogênio produzido é armazenado em um tanque e comercializado a preço fixo, seja sem limite de volume, seja por meio de um contrato de fornecimento com entrega diária (Seção 3.4.5). A energia excedente pode ser exportada ao SIN e liquidada ao PLD. O módulo LRCAP, embora fisicamente instalado no mesmo sítio, possui ponto de medição próprio e segue um perfil de descarga e recarga determinado pelo ONS. Os fluxos de ambos os lados convergem para o ponto de conexão compartilhado, cuja capacidade limita o fluxo líquido em cada hora.

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

Seja $\mathcal{T} = \{0, 1, \dots, N-1\}$ o conjunto de intervalos de tempo de duração $\Delta t$ (em horas) e $\mathcal{D}$ o conjunto de dias do horizonte, sendo $\mathcal{T}_d \subseteq \mathcal{T}$ os intervalos pertencentes ao dia $d$. No limite de emissões do hidrogênio (Seção 3.4.5), $\mathcal{W}$ denota o conjunto de semanas do horizonte, cada qual tratada como o conjunto de seus intervalos.

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
| $c^{deg}$ | Custo de degradação por energia descarregada | R\$/MWh | 50 (sensibilidade: 100; 200) |
| $\bar P^{el}$ | Potência nominal do eletrolisador | MW | 17,5 |
| $\alpha^{el}$ | Carga mínima do eletrolisador (fração de $\bar P^{el}$) | – | 0,10 |
| $k^{el}$ | Consumo específico de energia | kWh/kg | 55 |
| $c^{h2}$ | Custo variável de produção de H₂ | R\$/kg | 1,5 |
| $c^{part}$ | Custo por partida do eletrolisador | R\$/partida | 0 (determinístico); 500 (estocástico) |
| $\pi^{h2}$ | Preço de venda do H₂ | R\$/kg | 35 |
| $\bar S, S_0$ | Capacidade e estoque inicial do tanque de H₂ | kg | 2.000; 0 |
| $D^{h2}$ | Entrega mínima diária de H₂ (contrato) | kg/dia | 0 (sem contrato); 2.000 ou 3.000 |
| $\bar D^{h2}$ | Entrega máxima diária de H₂ (demanda do comprador) | kg/dia | ilimitada (sem contrato); igual a $D^{h2}$ |
| $\pi^{def}$ | Multa por kg de H₂ não entregue | R\$/kg | 35 |
| $\bar P^{exp}, \bar P^{imp}$ | Limites de exportação e importação no ponto de conexão | MW | 80 |
| $c^{imp}$ | Custo adicional sobre a energia importada | R\$/MWh | 250 |
| $f_t$ | Fator de emissão da energia da rede no intervalo $t$ | kgCO₂/MWh | série (Seção 3.5) ou 449 (marginal) |
| $L$ | Limite de intensidade de emissões do hidrogênio | kgCO₂/kgH₂ | sem limite (referência); 7 ou 3,4 |
| $f^{pv}, e^{proc}$ | Emissões atribuídas à energia FV e às demais etapas da produção de H₂ | kgCO₂/MWh; kgCO₂/kg | 0; 0 |
| $R^{cap}$ | Receita fixa do LRCAP | R\$/(MW·ano) | 600.000 (sensibilidade: 330.000 a 2.334.000) |
| $\underline P^{cap}$ | Disponibilidade mínima para participação no LRCAP | MW | 30 |
| $H^{cap}$ | Duração do ciclo completo exigida | h | 4 |
| $\rho$ | Energia instalada no módulo LRCAP por MW contratado | MWh/MW | 4,8 |
| $\mathrm{RTE}^{ref}$ | Eficiência de referência para custeio da recarga | – | 0,85 |
| $\delta_t, r_t$ | Despacho do ONS: descarga e recarga do módulo LRCAP (p.u. de $P^{cap}$) | – | perfil (Seção 3.5) |
| $N^{ons}$ | Número de despachos do ONS por ano | – | 365 (sensibilidade: 50; 150) |

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
| $q^{def}_d$ | Déficit de entrega de H₂ no dia $d$ | $\mathbb{R}_{\geq 0}$, kg |
| $p^{exp}_t, p^{imp}_t$ | Exportação e importação do lado mercantil | $\mathbb{R}_{\geq 0}$, MW |
| $y^{bat}_t$ | Estado do módulo mercantil (1 = carregando) | $\{0, 1\}$ |
| $y^{rede}_t$ | Sentido do intercâmbio (1 = exportando) | $\{0, 1\}$ |
| $z_t$ | Estado do eletrolisador (1 = ligado) | $\{0, 1\}$ |
| $u_t$ | Partida do eletrolisador no intervalo $t$ | $[0, 1]$ |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

### 3.4.4 Função objetivo

O objetivo é maximizar o lucro operacional do empreendedor no horizonte, expresso pela Equação {eq:fo}:

$$
\max\; \sum_{t \in \mathcal{T}} \lambda_t\, p^{exp}_t\, \Delta t
- \sum_{t \in \mathcal{T}} \left(\lambda_t + c^{imp}\right) p^{imp}_t\, \Delta t
+ \sum_{t \in \mathcal{T}} \left(\pi^{h2} v_t - c^{h2} m_t\right) \Delta t
- \sum_{t \in \mathcal{T}} c^{part} u_t
- \sum_{d \in \mathcal{D}} \pi^{def} q^{def}_d
+ R^{cap}\, \frac{N \Delta t}{8760}\, P^{cap}
- \kappa\, P^{cap}
- \sum_{t \in \mathcal{T}} c^{deg} \left(p^{dis}_t + \delta_t P^{cap}\right) \Delta t
$$ {#eq:fo}

Os termos correspondem, respectivamente, à receita da energia exportada ao MCP, ao custo da energia importada, à margem da comercialização do hidrogênio, ao custo de partida do eletrolisador, à multa por déficit de entrega de hidrogênio, à receita fixa do LRCAP rateada no horizonte, ao custo da recarga excedente do módulo LRCAP e ao custo de degradação do BESS, aplicado à energia descarregada por ambos os módulos. Ressalta-se que a energia injetada pelo módulo LRCAP não compõe a receita do MCP do empreendedor, em conformidade com o art. 9º, § 6º, da Portaria.

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

Como o perfil é exógeno, o estado de carga do módulo LRCAP é proporcional a $P^{cap}$ e pode ser verificado previamente à otimização. Define-se o estado de carga por MW contratado, $\varepsilon_t$, pela recursão da Equação {eq:epsilon}. O perfil é calculado uma única vez para o ano civil inteiro, com condição cíclica no ano — $\varepsilon_{-1}$ igual ao estado ao fim do ano —, e cada bloco da decomposição da Seção 3.6 recebe o trecho correspondente. Desse modo, o módulo inicia cada bloco no estado deixado pelo dia anterior, e a energia de recarga repõe exatamente a energia descarregada dividida pela eficiência do ciclo:

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

O balanço do tanque de hidrogênio, com condição de contorno análoga à do BESS, é expresso pela Equação {eq:tanque}:

$$
s_t = s_{t-1} + \left(m_t - v_t\right) \Delta t, \qquad s_{-1} = S_0, \qquad s_{N-1} \geq S_0
$$ {#eq:tanque}

**Contrato de fornecimento de hidrogênio.** Sem limite de volume, o hidrogênio funciona como um consumidor de energia de capacidade ilimitada a preço fixo. Com os valores da Tabela 3.1, cada MWh entregue ao eletrolisador vale $(\pi^{h2} - c^{h2}) \cdot 1000/k^{el} \approx$ R\$ 609/MWh, valor muito superior ao PLD médio, de modo que o eletrolisador absorve quase toda a energia disponível e o MCP perde relevância. Na prática, a comercialização de hidrogênio em escala depende de contratos bilaterais com um comprador industrial, cuja demanda é limitada e cuja entrega deve ser regular. Para representar essa situação, o modelo admite um contrato de fornecimento com entrega diária entre $D^{h2}$ e $\bar D^{h2}$, conforme as Equações {eq:entrega} e {eq:entrega-max}:

$$
\sum_{t \in \mathcal{T}_d} v_t\, \Delta t + q^{def}_d \geq D^{h2} \qquad \forall d \in \mathcal{D}
$$ {#eq:entrega}

$$
\sum_{t \in \mathcal{T}_d} v_t\, \Delta t \leq \bar D^{h2} \qquad \forall d \in \mathcal{D}
$$ {#eq:entrega-max}

A variável $q^{def}_d$ representa a parcela da entrega mínima não cumprida no dia $d$, sujeita à multa $\pi^{def}$ na função objetivo. Sem ela, um dia de baixa irradiância tornaria o problema inviável, já que a importação de energia é vedada no caso de referência; com ela, o modelo decide entre produzir o hidrogênio, inclusive com energia previamente armazenada no BESS, e pagar a multa. Quando não há multa definida, adota-se $q^{def}_d = 0$ e a entrega mínima é obrigatória. Nos casos com contrato, adota-se $D^{h2} = \bar D^{h2}$, isto é, um volume diário firme, e $\pi^{def} = \pi^{h2}$, isto é, uma multa igual ao preço por kg não entregue. Esse valor não deve ser lido como ressarcimento do produto: se o comprador repuser o hidrogênio com outro fornecedor ao mesmo preço, seu prejuízo direto é nulo, pois ele deixa de pagar o empreendedor, e uma indenização desse tipo corresponderia apenas à diferença entre o preço de reposição e o do contrato. A multa adotada representa, antes, uma cláusula de firmeza, que remunera o custo da interrupção para um comprador que depende da entrega diária. Como o kg não entregue também deixa de ser vendido, seu custo efetivo para o empreendedor é a soma $\pi^{h2} + \pi^{def}$, de R\$ 70/kg, e cada MWh entregue ao eletrolisador para evitar o déficit passa a valer $(\pi^{h2} + \pi^{def} - c^{h2}) \cdot 1000/k^{el} \approx$ R\$ 1.245/MWh, o dobro do valor sem contrato. Os casos com contrato representam, portanto, um contrato praticamente firme, e o valor do BESS no seu cumprimento depende diretamente de $\pi^{def}$. Os volumes de 2.000 e 3.000 kg/dia correspondem, respectivamente, a cerca de 65% e 98% da produção média do caso sem contrato (3.060 kg/dia). Nessa configuração, o hidrogênio produzido além do volume contratado não pode ser vendido, e a energia excedente passa a ser exportada ao MCP ou vertida, o que restabelece o papel do mercado de curto prazo na arbitragem. O caso sem contrato corresponde a $D^{h2} = 0$ e $\bar D^{h2}$ ilimitado.

**Limite de emissões do hidrogênio.** No caso de referência, a vedação à importação ($\bar P^{imp,m} = 0$) assegura que o hidrogênio seja produzido apenas com energia renovável local. O marco legal do hidrogênio de baixa emissão de carbono, porém, qualifica o hidrogênio pela intensidade de emissões de gases de efeito estufa, apurada por análise de ciclo de vida, com valor inicial de até 7 kgCO₂eq/kgH₂, mantido até 2030 (BRASIL, 2024). Para representar esse critério, o modelo admite, como alternativa à vedação, um limite $L$ à intensidade de emissões do hidrogênio. A energia importada pode ser destinada apenas ao eletrolisador, no mesmo intervalo, e é integralmente atribuída ao hidrogênio (Equação {eq:imp-el}); em cada semana $w \in \mathcal{W}$, as emissões atribuídas ao hidrogênio não podem exceder $L$ vezes a sua produção (Equação {eq:emissoes}):

$$
p^{imp}_t \leq p^{el}_t \qquad \forall t \in \mathcal{T}
$$ {#eq:imp-el}

$$
\sum_{t \in w} \Big[ f_t\, p^{imp}_t + f^{pv} \left(p^{el}_t - p^{imp}_t\right) + e^{proc}\, m_t \Big] \Delta t \;\leq\; L \sum_{t \in w} m_t\, \Delta t \qquad \forall w \in \mathcal{W}
$$ {#eq:emissoes}

em que $f_t$ é o fator de emissão da energia da rede no intervalo $t$, $f^{pv}$ é o fator atribuído à energia FV, consumida diretamente ou após o armazenamento no módulo mercantil, e $e^{proc}$ representa as emissões das demais etapas por kg de hidrogênio. Pela Equação {eq:prod}, com $f^{pv} = e^{proc} = 0$, a restrição equivale a limitar o fator de emissão médio da energia do eletrolisador, em cada semana, a $L\,k^{el}/1000$: 127 kgCO₂/MWh para $L = 7$ e 62 kgCO₂/MWh para $L = 3{,}4$. Cada MWh de origem FV consumido pelo eletrolisador abre espaço, assim, para a importação de uma fração de MWh da rede. A restrição é linear e não introduz variáveis binárias; com $L = 0$, ela reproduz a vedação à importação. A janela semanal coincide com os blocos da decomposição (Seção 3.6.2), de modo que a restrição pertence integralmente a cada subproblema. O valor de 3,4 kgCO₂/kgH₂ corresponde aproximadamente ao critério europeu para combustíveis renováveis de origem não biológica, de redução de 70% das emissões em relação ao comparador fóssil de 94 gCO₂eq/MJ (UNIÃO EUROPEIA, 2023), e é avaliado como sensibilidade.

O modelo resultante, composto pela função objetivo da Equação {eq:fo} e pelas restrições das Equações {eq:cap} a {eq:emissoes}, é um MILP. Sem contrato de hidrogênio, para um horizonte de uma semana (168 h), o problema possui 1.688 variáveis contínuas, 505 variáveis binárias e 2.692 restrições; para um ano (8.760 h), 87.966 variáveis contínuas, 26.281 binárias e 140.164 restrições. O contrato acrescenta duas restrições por dia, e o limite de emissões, uma restrição por intervalo e uma por semana.

## 3.5 Dados de entrada

**Preço de Liquidação das Diferenças.** Utiliza-se a série horária do PLD de 2025 para o submercado Sudeste/Centro-Oeste, no qual se localiza o município de Itajubá (MG), obtida no portal de dados abertos da Câmara de Comercialização de Energia Elétrica (CCEE, 2026a). A série apresenta média de R\$ 224,31/MWh, com mínimo de R\$ 58,60/MWh — valor do PLD mínimo, observado em 2.030 horas, concentradas no período úmido — e máximo de R\$ 1.421,87/MWh. A Figura 3.2(a) evidencia o perfil diário característico do período recente: preços reduzidos nas horas de maior geração solar e elevados na rampa noturna, com maior amplitude no período seco.

**Geração fotovoltaica.** A disponibilidade de geração FV foi obtida na plataforma *Photovoltaic Geographical Information System* (PVGIS), mantida pelo Centro Comum de Investigação da Comissão Europeia (HULD; MÜLLER; GAMBARDELLA, 2012), a partir da base de reanálise ERA5 (HERSBACH *et al.*, 2020), para as coordenadas de Itajubá (latitude −22,425°; longitude −45,457°; altitude de 848 m). Considerou-se um sistema de silício cristalino de 1 kWp, com perdas de 14% e inclinação e azimute ótimos (25° e −165°, respectivamente), no ano de 2023, o mais recente disponível. A potência horária foi convertida em fator de capacidade, deslocada do tempo universal coordenado para o horário oficial de Brasília (UTC−3) e reposicionada no calendário de 2025, preservando mês, dia e hora, para compatibilização com a série de preços. O fator de capacidade médio resultante é de 16,9%, equivalente a 1.478 kWh/kWp por ano (Figura 3.2(b)). A série é multiplicada pela potência instalada da usina para obter $\bar P^{pv}_t$.

::: {custom-style="Legenda"}
Figura 3.2 – Perfis horários médios dos dados de entrada: (a) PLD do submercado SE/CO em 2025, por período hidrológico; (b) fator de capacidade FV em Itajubá
:::

::: {custom-style="Figura"}
![](figuras/fig_perfis_entrada.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor com dados de CCEE (2026a) e do PVGIS.
:::

**Despacho do ONS.** Na ausência de histórico de despacho de sistemas de armazenamento contratados no LRCAP, adota-se um perfil diário sintético: descarga na potência contratada entre 18 h e 22 h, horário de maior demanda líquida, e recarga entre 10 h e 15 h, até a restauração completa do estado de carga, limitada à potência nominal. O perfil é coerente com a diretriz de que a programação da recarga busque minimizar o custo total de operação do SIN (BRASIL, 2026, art. 4º, § 14), o que tende a deslocá-la para as horas de excedente de geração solar. O perfil resulta em um ciclo completo por dia (365 no ano), dentro dos limites regulatórios. Trata-se da hipótese mais intensa de uso do módulo LRCAP; o efeito de despachos menos frequentes é avaliado na Seção 3.8.3.

**Fator de emissão da rede.** Nos casos com limite de emissões, o fator de emissão horário da energia da rede, $f_t$, foi estimado a partir da geração horária por usina do Sistema Interligado Nacional (SIN), disponibilizada pelo ONS em seu portal de dados abertos (ONS, 2026), para os anos de 2021 a 2025. Em cada hora, somam-se as emissões das termelétricas a combustíveis fósseis — a geração de cada usina multiplicada pelo fator de emissão do combustível (IPCC, 2006) e dividida por um rendimento típico: 45% para o gás natural (449 kgCO₂/MWh), 35% para o carvão mineral (988 kgCO₂/MWh) e 38% para os óleos diesel e combustível (702 e 733 kgCO₂/MWh) — e divide-se o total pela geração do SIN, excluídas a micro e a minigeração distribuídas. A biomassa, os resíduos industriais, a fonte nuclear e as demais renováveis entram com emissão nula. Os fatores médios anuais resultantes são de 94, 31, 27, 37 e 42 kgCO₂/MWh, de 2021 a 2025. De janeiro a abril de 2025, as médias mensais ficam entre 2% e 5% abaixo dos fatores publicados pelo Ministério da Ciência, Tecnologia e Inovação (MCTI, 2025), cuja metodologia passou a incluir, naquele ano, os novos empreendimentos renováveis conectados ao SIN; pela metodologia anterior, os fatores oficiais de 2021 a 2023 são de 34% a 42% maiores que os aqui estimados. Como alternativa, considera-se um fator marginal constante, de 449 kgCO₂/MWh, que supõe que toda energia importada é suprida por uma termelétrica a gás natural. Os fatores consideram apenas as emissões de operação; para manter a mesma fronteira, a energia FV entra com fator nulo ($f^{pv} = 0$).

**Parâmetros técnico-econômicos.** Os parâmetros do eletrolisador foram definidos a partir da faixa típica da tecnologia PEM, cujo consumo específico de energia situa-se entre 4,3 e 5,2 kWh/Nm³, ou aproximadamente 48 a 58 kWh/kg, até que os dados do fabricante do equipamento da UNIFEI sejam incorporados. O preço do hidrogênio não possui, até o momento, referência de mercado consolidada no Brasil e é, por isso, objeto de análise de sensibilidade. O mesmo se aplica aos termos do contrato de fornecimento de hidrogênio — volume diário e multa por déficit —, avaliados em cenários alternativos ao caso sem contrato.

**Custo de degradação do BESS.** No modelo de operação, o desgaste da bateria é representado por um custo por MWh descarregado, $c^{deg}$, que mede o custo marginal de usar uma bateria existente: cada ciclo adicional antecipa a perda de capacidade e a reposição dos módulos. O custo integral de reposição dividido pela energia descarregada ao longo da vida útil é um limite superior desse custo marginal. Com o preço médio de *packs* de baterias de íons de lítio para armazenamento estacionário de US\$ 70/kWh em 2025 (BNEF, 2025), convertido pela taxa PTAX de 09/12/2025 (R\$ 5,4025/US\$) e acrescido de 74% de tributos incidentes no Brasil (EPE, 2024), e com vida útil de 4.000 a 6.000 ciclos a 90% de profundidade de descarga, esse limite fica entre R\$ 120 e R\$ 185 por MWh descarregado. Adota-se R\$ 50/MWh no caso de referência, e o efeito de valores de R\$ 100 e R\$ 200/MWh é avaliado na Seção 3.8.4. Na decisão de construir o BESS (Seção 3.8.2), porém, o desgaste do uso contratado não é cobrado por MWh: o investimento é amortizado no prazo do contrato, sem valor residual, e o O&M fixo inclui a reposição parcial de módulos (*augmentation*) que mantém a capacidade nominal durante a vida útil, com cerca de um ciclo por dia (NREL, 2024). Cobrar também o desgaste por MWh pagaria a bateria duas vezes.

**Receita fixa do LRCAP.** Como ainda não houve leilão de armazenamento em baterias no Brasil, a receita fixa foi delimitada por quatro referências. A inferior é o primeiro leilão do mecanismo italiano de contratação de capacidade de armazenamento (MACSE), realizado em setembro de 2025 com contratos de 15 anos e desenho semelhante ao do LRCAP, cujo preço médio de € 12.959/(MWh·ano) (TERNA, 2025) corresponde, para um sistema de 4 h e com a taxa de câmbio PTAX de 30/09/2025 (R\$ 6,2396/€), a cerca de R\$ 323 mil/(MW·ano). No LRCAP de março de 2026, que contratou o mesmo produto — potência disponível ao ONS —, termelétricas existentes a óleo e biodiesel obtiveram preço médio de R\$ 831 mil/(MW·ano) (CCEE, 2026c), e o conjunto de termelétricas a gás natural, biometano e carvão e de ampliações de hidrelétricas, novas e existentes, R\$ 2,334 milhões/(MW·ano) (CCEE, 2026b). Por fim, o custo de investimento de referência de sistemas de baterias, de R\$ 5.000 a R\$ 6.000/kW (BRASIL; EPE, 2025), corresponde, anualizado à taxa central de 12,1% ao ano em 15 anos (Seção 3.8.2), a R\$ 738 mil a R\$ 886 mil/(MW·ano), sem considerar operação e manutenção, encargos e reposição de módulos. Com base nessas referências, a análise de sensibilidade abrange receitas fixas de R\$ 330 mil a R\$ 2,33 milhões/(MW·ano). O valor de R\$ 600 mil/(MW·ano) adotado no caso de referência situa-se no extremo inferior dessa faixa, abaixo do preço obtido por usinas existentes e do custo anualizado de investimento em baterias, e constitui, portanto, uma hipótese conservadora quanto à atratividade do leilão.

## 3.6 Método de solução

### 3.6.1 Solução por ramificação e limitação

Problemas MILP são usualmente resolvidos por algoritmos de ramificação e limitação (*branch-and-bound*) combinados à geração de planos de corte, nos quais relaxações lineares sucessivas fornecem limites para o valor ótimo e permitem certificar a qualidade da solução por meio do *gap* de otimalidade. Neste trabalho utiliza-se o *solver* de código aberto HiGHS (HUANGFU; HALL, 2018). Para o horizonte de uma semana, o problema é resolvido em menos de um segundo. Para o horizonte anual, entretanto, a solução direta não foi obtida em 15 minutos de processamento, o que motivou a adoção de uma estratégia de decomposição.

### 3.6.2 Decomposição de Benders

A estrutura do problema favorece a decomposição: a potência contratada $P^{cap}$ é a única variável que acopla todo o horizonte, enquanto as variáveis operacionais de um período se relacionam com as dos períodos vizinhos apenas pelos estados de armazenamento. Dividindo-se o ano em blocos semanais $w \in \mathcal{W}$ e impondo-se condições de contorno cíclicas em cada bloco — aproximação cujo efeito é avaliado ao final desta seção —, o problema anual pode ser reescrito conforme a Equação {eq:benders}:

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

As condições de contorno cíclicas restringem o problema anual, pois impedem transferências de energia e de hidrogênio entre blocos: cada semana começa com o módulo mercantil em $\sigma_0 E^{m}$ e o tanque em $S_0$ e precisa terminar nesses níveis. O valor obtido com blocos semanais é, portanto, um limite inferior do valor do problema anual. Como a solução direta do problema anual não foi obtida, o efeito dessa restrição é estimado comparando-se o lucro anual, para uma mesma potência contratada, com blocos de 7, 14 e 28 dias, e refazendo-se a decomposição com blocos de 14 dias. Se o lucro não aumentar com o tamanho do bloco, a restrição pode ser considerada inativa.

Quando a potência contratada é fixada — caso das avaliações da curva de oferta e da viabilidade econômica (Seção 3.8) —, a restrição pode ser removida quase integralmente por um procedimento em duas etapas. Primeiro, resolve-se a relaxação linear do problema do ano inteiro, isto é, com as variáveis binárias tratadas como contínuas, e com condição cíclica no ano e nível inicial livre. Sem variáveis binárias, esse problema é resolvido em menos de um minuto, e seu valor ótimo é um limite superior $\bar Q$ do lucro operacional do ano. Em seguida, os estados de armazenamento da relaxação no início e no fim de cada semana — o estado de carga do módulo mercantil, em fração de $E^{m}$, e o estoque de hidrogênio — substituem $\sigma_0$ e $S_0$ como condições de contorno dos blocos MILP. Os blocos continuam independentes e são resolvidos em paralelo, e a concatenação de suas soluções é uma operação viável do ano inteiro, cujo lucro $\underline Q$ é um limite inferior do ótimo anual. A diferença relativa $(\bar Q - \underline Q)/\bar Q$ certifica, assim, a qualidade da aproximação. Para que $\underline Q$ seja de fato viável, admite-se, nesses blocos, o eletrolisador desligado antes da primeira hora, o que pode acrescentar uma partida por semana. O procedimento não se aplica ao algoritmo de Benders, porque os estados de fronteira dependeriam do ponto $\hat x$ em que a relaxação foi resolvida, e o conjunto viável $X_w$ da Equação {eq:lagr} deixaria de ser o mesmo entre iterações.

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

## 3.7 Extensão estocástica e valor da informação

A formulação das Seções 3.4 a 3.6 supõe que as séries de preço e de geração do ano de análise sejam conhecidas no momento da contratação. Na prática, a potência ofertada no LRCAP é definida antes do início do contrato e permanece fixa durante 15 anos, enquanto o PLD e a irradiância variam de um ano para outro. Esta seção apresenta a extensão estocástica do modelo, que trata essa incerteza, e os indicadores utilizados para quantificar o benefício de considerá-la: o valor da solução estocástica (VSS) e o valor esperado da informação perfeita (EVPI).

### 3.7.1 Formulação em dois estágios

O problema é reescrito como um programa estocástico de dois estágios com recurso (BIRGE; LOUVEAUX, 2011; CONEJO; CARRIÓN; MORALES, 2010). No primeiro estágio, decide-se a potência contratada $P^{cap}$, comum a todos os cenários. No segundo estágio, observado o cenário $s \in \mathcal{S}$, com probabilidade $\pi_s$, a operação horária se ajusta de forma ótima à decisão de contratação. O lucro anual do cenário $s$ é dado pela Equação {eq:lucro-cenario}:

$$
\Pi_s\!\left(P^{cap}\right) = R^{cap}\, P^{cap} + \sum_{w \in \mathcal{W}_s} Q_{s,w}\!\left(P^{cap}\right)
$$ {#eq:lucro-cenario}

em que $\mathcal{W}_s$ é o conjunto de blocos semanais do ano associado ao cenário $s$ e $Q_{s,w}$ é o lucro operacional ótimo do bloco, definido como na Seção 3.6.2, com as séries daquele cenário.

Para representar a aversão ao risco do empreendedor, o objetivo combina o lucro esperado com o valor condicional em risco (*Conditional Value-at-Risk*, CVaR), conforme a Equação {eq:estoc}:

$$
\max_{P^{cap} \in \mathcal{X}} \; \sum_{s \in \mathcal{S}} \pi_s\, \Pi_s\!\left(P^{cap}\right) + \beta\, \mathrm{CVaR}_\alpha\!\left(\Pi\!\left(P^{cap}\right)\right)
$$ {#eq:estoc}

em que $\mathcal{X} = \{0\} \cup [\underline P^{cap}, \bar P^{cap}]$ é o conjunto de potências admissíveis, $\beta \geq 0$ é o peso atribuído ao risco ($\beta = 0$ corresponde a um agente neutro ao risco) e $\alpha$ é o nível de confiança do CVaR. Para uma distribuição discreta de lucros, o CVaR corresponde ao lucro médio na cauda inferior de probabilidade $1 - \alpha$ e pode ser escrito na forma linear de Rockafellar e Uryasev (2000), apresentada na Equação {eq:cvar}:

$$
\mathrm{CVaR}_\alpha(\Pi) = \max_{\zeta,\, \nu \geq 0} \left\{ \zeta - \frac{1}{1-\alpha} \sum_{s \in \mathcal{S}} \pi_s\, \nu_s \;\; : \;\; \nu_s \geq \zeta - \Pi_s \;\; \forall s \in \mathcal{S} \right\}
$$ {#eq:cvar}

em que $\zeta$ é uma variável auxiliar cujo valor ótimo corresponde ao valor em risco (VaR) e $\nu_s$ mede o quanto o lucro do cenário $s$ fica abaixo de $\zeta$.

### 3.7.2 Cenários

Os cenários correspondem aos cinco anos históricos de 2021 a 2025, considerados equiprováveis ($\pi_s = 1/5$). Cada cenário reúne:

a) a série horária do PLD do submercado SE/CO do respectivo ano (CCEE, 2026a), corrigida para valores de dezembro de 2025 pelo IPCA (IBGE, 2026), por meio do fator $f_s = \prod_{a = a_s + 1}^{2025} (1 + \mathrm{IPCA}_a)$, em que $a_s$ é o ano do cenário. Com variações anuais do IPCA de 5,79% (2022), 4,62% (2023), 4,83% (2024) e 4,26% (2025), obtêm-se fatores de 1,2097, 1,1435, 1,0930, 1,0426 e 1,0000 para os cenários de 2021 a 2025, respectivamente;

b) a série de fator de capacidade FV obtida no PVGIS a partir da base de satélite SARAH-3, para as mesmas coordenadas e configuração descritas na Seção 3.5. Como a base cobre apenas o período até 2023, os cenários de 2024 e 2025 utilizam a série de 2023;

c) o perfil de despacho do ONS, que, em lugar do perfil fixo da Seção 3.5, passa a depender do preço do cenário: em cada dia, a descarga ocorre no bloco de $H^{cap} = 4$ horas consecutivas de maior PLD médio após o período de geração solar, e a recarga, nas horas de menor PLD da janela entre 8 h e 16 h, até a restauração do estado de carga. Trata-se de uma aproximação do despacho por mínimo custo previsto na Portaria (BRASIL, 2026, art. 4º, § 14), que preserva a correlação entre o despacho e o preço em cada cenário.

No caso estocástico, o custo por partida do eletrolisador da Equação {eq:fo}, $c^{part}$, é de R\$ 500 (valor de referência, a calibrar com o fabricante) e incide sobre a variável $u_t \geq z_t - z_{t-1}$, que penaliza ligamentos frequentes; no caso determinístico, $c^{part} = 0$.

Com cinco cenários equiprováveis e $\alpha = 0{,}8$, a cauda de probabilidade $1 - \alpha = 0{,}2$ contém exatamente um cenário, de modo que o CVaR coincide com o lucro do pior ano. Ressalta-se que cinco anos constituem uma amostra pequena da variabilidade hidrológica e de preços, de forma que os resultados refletem a amostra histórica disponível e não uma distribuição de probabilidade ajustada.

### 3.7.3 Método de solução

A decomposição de Benders da Seção 3.6 estende-se naturalmente ao caso estocástico: cada par (cenário, bloco semanal) constitui um subproblema independente, e o problema mestre passa a conter uma variável $\theta_{s,w}$ por subproblema, além das variáveis do CVaR, conforme as Equações {eq:mestre-estoc} a {eq:mestre-estoc-cvar}:

$$
\max\; \sum_{s \in \mathcal{S}} \pi_s\, \Pi_s + \beta \left( \zeta - \frac{1}{1-\alpha} \sum_{s \in \mathcal{S}} \pi_s\, \nu_s \right)
$$ {#eq:mestre-estoc}

sujeito a:

$$
\Pi_s = R^{cap} P + \sum_{w \in \mathcal{W}_s} \theta_{s,w} \quad \forall s; \qquad \theta_{s,w} \leq C^{k}_{s,w} + \lambda^{k}_{s,w}\, P \quad \forall s, w, k
$$ {#eq:mestre-estoc-cortes}

$$
\nu_s \geq \zeta - \Pi_s, \quad \nu_s \geq 0 \quad \forall s; \qquad \underline P^{cap} w \leq P \leq \bar P^{cap} w
$$ {#eq:mestre-estoc-cvar}

Como o objetivo é não decrescente em cada $\Pi_s$ e os cortes superestimam $Q_{s,w}$, o valor ótimo do mestre continua a ser um limite superior válido. Os cortes não dependem de $\alpha$ e de $\beta$, o que permite reaproveitá-los na construção da fronteira entre risco e retorno.

Quanto à validade dos cortes reforçados com uma variável de primeiro estágio contínua, observa-se que a desigualdade $Q_{s,w}(x) \leq C_{s,w}(\lambda_{s,w}) + \lambda_{s,w}\, x$ decorre apenas da dualidade lagrangiana e vale para qualquer $x$ admissível, seja ele contínuo ou inteiro. O que exige variáveis de primeiro estágio binárias, no trabalho de Zou, Ahmed e Sun (2019), é a garantia de que os cortes sejam exatos nos pontos avaliados e, portanto, a convergência finita do algoritmo. Como essa garantia não se aplica a $P^{cap}$, a qualidade da solução é atestada pelo *gap* entre os limites superior e inferior, e não pela convergência teórica.

### 3.7.4 Valor da solução estocástica e valor esperado da informação perfeita

O VSS e o EVPI (BIRGE, 1982; BIRGE; LOUVEAUX, 2011) quantificam, respectivamente, o ganho de resolver o problema estocástico em lugar de um problema determinístico baseado em valores médios e o ganho que se obteria caso o cenário fosse conhecido antes da contratação. Ambos são definidos para o objetivo de valor esperado e, por isso, são calculados com $\beta = 0$. Para um problema de maximização, definem-se quatro quantidades.

O valor do **problema estocástico** (*recourse problem*, RP) é o lucro esperado ótimo da Equação {eq:estoc} com $\beta = 0$, dado pela Equação {eq:rp}:

$$
\mathrm{RP} = \max_{P^{cap} \in \mathcal{X}} \; \sum_{s \in \mathcal{S}} \pi_s\, \Pi_s\!\left(P^{cap}\right)
$$ {#eq:rp}

A **solução espera-e-vê** (*wait-and-see*, WS) corresponde a um agente que conhece o cenário antes de decidir a potência e escolhe, em cada um, a contratação ótima, conforme a Equação {eq:ws}:

$$
\mathrm{WS} = \sum_{s \in \mathcal{S}} \pi_s \max_{P^{cap} \in \mathcal{X}} \Pi_s\!\left(P^{cap}\right)
$$ {#eq:ws}

O **problema do valor esperado** (*expected value*, EV) substitui os cenários por um único cenário médio, $\bar\xi$, e fornece a decisão $\bar x^{EV}$, segundo a Equação {eq:ev}:

$$
\bar x^{EV} \in \arg\max_{P^{cap} \in \mathcal{X}} \; \Pi_{\bar\xi}\!\left(P^{cap}\right)
$$ {#eq:ev}

O **valor esperado da solução EV** (EEV) é o lucro esperado obtido quando a decisão $\bar x^{EV}$ é aplicada aos cenários originais, dado pela Equação {eq:eev}:

$$
\mathrm{EEV} = \sum_{s \in \mathcal{S}} \pi_s\, \Pi_s\!\left(\bar x^{EV}\right)
$$ {#eq:eev}

A partir dessas quantidades, os indicadores são dados pelas Equações {eq:evpi} e {eq:vss}:

$$
\mathrm{EVPI} = \mathrm{WS} - \mathrm{RP}
$$ {#eq:evpi}

$$
\mathrm{VSS} = \mathrm{RP} - \mathrm{EEV}
$$ {#eq:vss}

Como $\bar x^{EV}$ é uma decisão admissível para o problema estocástico, e como o agente com informação perfeita pode, em particular, repetir a decisão estocástica em todos os cenários, vale a relação $\mathrm{EEV} \leq \mathrm{RP} \leq \mathrm{WS}$, de modo que ambos os indicadores são não negativos. Um VSS reduzido indica que o modelo determinístico baseado no cenário médio já conduz a uma boa decisão de contratação; um EVPI reduzido indica que a incerteza modelada tem pouco impacto sobre o lucro alcançável, e que, portanto, haveria pouco a ganhar com previsões mais precisas.

O cenário médio $\bar\xi$ é construído pela média hora a hora das séries dos cinco anos, alinhadas por mês, dia e hora, com a exclusão do dia 29 de fevereiro de 2024: $\bar\lambda_t = \sum_{s \in \mathcal{S}} \pi_s\, f_s\, \lambda_{s,t}$ para o PLD corrigido e, analogamente, para o fator de capacidade FV. O perfil de despacho do ONS do cenário médio é obtido pela mesma regra da Seção 3.7.2, aplicada a $\bar\lambda_t$. Destaca-se que o valor ótimo do problema EV não é utilizado como estimativa do lucro: a média hora a hora suaviza os picos e vales de preço e de irradiância e tende a distorcer o lucro operacional. O problema EV serve apenas para gerar a decisão $\bar x^{EV}$, cujo desempenho é avaliado pelo EEV.

O cálculo segue as etapas abaixo:

a) **RP:** resolve-se o problema estocástico com $\beta = 0$ pelo método da Seção 3.7.3;

b) **WS:** resolve-se, para cada cenário $s$ isoladamente, o problema determinístico anual pelo mesmo método, e calcula-se a média ponderada dos valores ótimos;

c) **EV e EEV:** resolve-se o problema anual com o cenário médio para obter $\bar x^{EV}$; em seguida, fixa-se $P^{cap} = \bar x^{EV}$ e resolvem-se os subproblemas de todos os pares (cenário, bloco), o que fornece $\Pi_s(\bar x^{EV})$ e, pela Equação {eq:eev}, o EEV.

Como RP e WS são obtidos com uma tolerância $\varepsilon$ de convergência, adotada como 0,01% nesta etapa, cada um é conhecido por um intervalo $[LB, UB]$. Os indicadores são, então, reportados com os respectivos limites: $\mathrm{EVPI} \in [\mathrm{WS}^{LB} - \mathrm{RP}^{UB},\; \mathrm{WS}^{UB} - \mathrm{RP}^{LB}]$ e $\mathrm{VSS} \in [\mathrm{RP}^{LB} - \mathrm{EEV},\; \mathrm{RP}^{UB} - \mathrm{EEV}]$. Diferenças inferiores à ordem de $\varepsilon \cdot \mathrm{RP}$ não são distinguíveis do erro de convergência e devem ser interpretadas como nulas.

## 3.8 Decisão de oferta no leilão e análises de sensibilidade

As Seções 3.4 a 3.7 tratam a receita fixa $R^{cap}$ como parâmetro e determinam a potência ótima correspondente. No leilão, contudo, $R^{cap}$ não é um dado: é o preço ofertado pelo próprio empreendedor, e a informação de que ele necessita é a relação entre esse preço e a potência que vale a pena comprometer. Esta seção apresenta os procedimentos utilizados para obter essa relação nas duas situações consideradas: a curva de oferta de um BESS disponível (Seção 3.8.1) e, para um BESS a construir, a análise de viabilidade e o lance mínimo (Seção 3.8.2), que constitui o resultado principal do trabalho. Em seguida, trata-se do efeito da frequência do despacho do ONS (Seção 3.8.3) e dos casos de sensibilidade avaliados (Seção 3.8.4).

### 3.8.1 Custo de oportunidade e curva de oferta

Seja $Q(P)$ o lucro operacional esperado do empreendimento, sem a receita fixa do LRCAP, quando a potência contratada é $P$, dado pela Equação {eq:q} (na prática, calculado com $R^{cap} = 0$):

$$
Q(P) = \sum_{s \in \mathcal{S}} \pi_s\, \Pi_s(P) - R^{cap} P
$$ {#eq:q}

A diferença $Q(0) - Q(P)$ mede quanto lucro operacional o empreendedor perde por comprometer $P$ MW com o leilão. Ela reúne duas parcelas: o lucro que deixa de obter no MCP e na venda de hidrogênio, que é o custo de oportunidade em sentido estrito, e o custo de degradação do módulo LRCAP pelo despacho do ONS, de $c^{deg} E^{ons}$ por MW contratado, em que $E^{ons}$ é a energia injetada pelo módulo por MW em um ano (Seção 3.8.2). Neste trabalho, denomina-se custo de oportunidade da contratação a soma das duas parcelas, pois é ela que a receita fixa precisa cobrir quando o BESS já existe. Seu valor por MW adicional, $c^{op}(P) = -\mathrm{d}Q/\mathrm{d}P$, é o custo de oportunidade marginal. Como a decisão envolve uma única variável e o interesse está na curva inteira, e não apenas no seu máximo, $Q$ é avaliada numa grade $\mathcal{X}_h = \{0\} \cup \{\underline P^{cap}, \underline P^{cap} + h, \dots, \bar P^{cap}\}$, com $h = 2{,}5$ MW, resolvendo-se para cada ponto os subproblemas de todos os pares (cenário, bloco) com $P^{cap}$ fixo e com os estados de fronteira dos blocos dados pela relaxação linear de cada ano (Seção 3.6.2). O custo de oportunidade marginal é aproximado pelas diferenças finitas da Equação {eq:custo-op}:

$$
c^{op}_j = -\,\frac{Q(P_{j+1}) - Q(P_j)}{P_{j+1} - P_j}, \qquad P_j,\, P_{j+1} \in \mathcal{X}_h, \;\; P_j \geq \underline P^{cap}
$$ {#eq:custo-op}

Para uma receita fixa $R$, a potência ótima a ofertar é dada pela Equação {eq:oferta}, e o conjunto de pares $(R, P^*(R))$ constitui a curva de oferta do empreendedor:

$$
P^*(R) \in \arg\max_{P \in \mathcal{X}_h} \; R\, P + Q(P)
$$ {#eq:oferta}

Dois valores resumem a curva. A receita mínima de entrada, $R^{ent}$, é a menor receita fixa para a qual participar do leilão é preferível a não participar, conforme a Equação {eq:entrada}; a receita de oferta integral, $R^{int}$, é a menor receita para a qual ofertar a potência máxima supera qualquer alternativa, conforme a Equação {eq:integral}:

$$
R^{ent} = \min_{P \in \mathcal{X}_h,\, P > 0} \; \frac{Q(0) - Q(P)}{P}
$$ {#eq:entrada}

$$
R^{int} = \max_{P \in \mathcal{X}_h,\, P < \bar P^{cap}} \; \frac{Q(P) - Q(\bar P^{cap})}{\bar P^{cap} - P}
$$ {#eq:integral}

A curva de oferta não depende do formato do leilão nem do comportamento dos demais proponentes: ela indica, para cada preço, quanta potência o empreendedor estaria disposto a comprometer. Ressalta-se que o investimento no BESS não entra em $Q(P)$, pois as capacidades instaladas são fixas. Esse custo não altera $P^*(R)$ quando o BESS já existe, mas altera a decisão quando ele ainda será construído, situação tratada na Seção 3.8.2.

### 3.8.2 Viabilidade econômica e lance mínimo

A viabilidade do empreendimento é avaliada pelo valor presente líquido (VPL) de um fluxo de caixa anual constante, em termos reais, ao longo do prazo do contrato do LRCAP ($n = 15$ anos), sem valor residual, conforme a Equação {eq:vpl}:

$$
\mathrm{VPL} = -I + F(i, n)\,\left(\Pi - C^{om} - C^{rede}\right), \qquad F(i, n) = \frac{1 - (1 + i)^{-n}}{i}
$$ {#eq:vpl}

em que $I$ é o investimento total na usina FV, no BESS e no eletrolisador, $\Pi$ é o lucro operacional esperado na potência ótima para a receita fixa considerada (Seção 3.8.1), $C^{om}$ é o custo anual de operação e manutenção fixo, $C^{rede} = 12\,\tau\,M$ é o custo anual de uso da rede, com a tarifa de uso do sistema de transmissão na geração (TUST) $\tau$, em R\$/kW·mês, aplicada ao montante de uso de injeção $M$, e $F(i, n)$ é o fator de valor presente de uma série uniforme à taxa real $i$. A taxa interna de retorno (TIR) é a taxa para a qual o VPL é nulo. Os parâmetros adotados são apresentados no Quadro 3.3.

::: {custom-style="Legenda"}
Quadro 3.3 – Parâmetros da análise de viabilidade econômica
:::

| Parâmetro | Valores (baixo; central; alto) | Referência |
|------------------------|------------------------------|------------------------------------|
| Investimento na usina FV | R\$ 3.000; 4.250; 5.500/kW | BRASIL; EPE (2025) |
| Investimento no BESS | R\$ 5.000; 5.500; 6.000/kW de um sistema de 4 h (sensibilidade: 3 h), com 45%; 60%; 75% do custo proporcionais à energia | BRASIL; EPE (2025), sem duração informada (as edições anteriores usavam 3 h); composição típica de sistemas de 4 h: bloco de baterias de 35% a 55%, conversores de 10% a 20% e conexão, obras e custos indiretos de 25% a 40% (BESS-MARKET, 2026; EMBER, 2025) |
| Investimento no eletrolisador | US\$ 1.100; 2.000; 2.500/kW | IEA (2025): sistemas chineses de US\$ 500 a 1.100/kW e demais de US\$ 1.900 a 2.500/kW; convertidos pela PTAX de 09/12/2025 (R\$ 5,4025/US\$) |
| O&M fixo anual | 1,5% (FV), 2,5% (BESS) e 3% (eletrolisador) do investimento | BESS: NREL (2024), incluída a reposição parcial de módulos que mantém a capacidade nominal em 15 anos, com cerca de um ciclo por dia e sem O&M variável; FV e eletrolisador: hipótese do autor |
| Taxa de desconto real | 12,1% (central) e 8,0% ao ano | ANEEL (2026): custo de capital regulatório da geração antes e após impostos |
| Uso da rede (TUST de geração) | R\$ 5,68; 10,93; 19,49/kW·mês, sobre o montante de uso de injeção compartilhado pela FV e pelo BESS (sensibilidades: montantes somados; cobrança também da TUST de consumo, de R\$ 15,23/kW·mês) | Ciclo 2026/2027: média nacional e faixa entre regiões (MOVIMENTO ECONÔMICO, 2026; RADAR ENERGIA, 2026); armazenamento despachado pelo ONS paga apenas na injeção (CENÁRIO ENERGIA, 2026), embora a REN ANEEL nº 1.162/2026 preveja o faturamento das duas parcelas para armazenamento colocalizado (CESCON BARRIEU, 2026) |
| Consumo auxiliar do BESS | 0; 1%; 2% da potência nominal | Valor indicativo de fornecedores, de 0,8% a 1,6% da potência do conversor (ENERGY CENTRAL, 2025) |
| Disponibilidade | 100% (sensibilidade: 97%) | Portaria MME nº 136/2026: disponibilidade integral, com isenção de penalidade para a indisponibilidade acordada com o ONS |
| Horizonte | 15 anos, sem valor residual | Prazo do contrato do LRCAP |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

Como o fluxo de caixa é calculado antes dos tributos sobre a renda, adota-se como taxa central o custo de capital antes de impostos (12,1%), que já incorpora o efeito desses tributos. A taxa após impostos (8,0%) é apresentada apenas como sensibilidade, pois, aplicada a um fluxo antes de impostos, ignora o imposto de renda e superestima o VPL. A partir do VPL, calcula-se ainda o preço de equilíbrio do hidrogênio, $\pi^{h2,eq} = \pi^{h2} - \mathrm{VPL} / (F(i, n)\, V)$, em que $V$ é a quantidade anual de hidrogênio vendida. Essa expressão mantém a operação fixa e, portanto, superestima ligeiramente o preço de equilíbrio, pois um preço maior levaria a uma produção maior.

Para isolar a contribuição da bateria, o modelo é resolvido também sem o BESS e, consequentemente, sem participação no leilão, o que fornece o lucro operacional $\Pi^{0}$ da usina FV com o eletrolisador. Quando o BESS ainda será construído, o proponente compara, para cada receita fixa $R$, a alternativa de não construí-lo com a de construí-lo e contratar a melhor potência, deduzido o custo anual equivalente do BESS, $C^{bess} = I^{bess} / F(i, n) + C^{om,bess} + 12\,\tau\,(M - M^{0})$, que inclui o capital, o O&M fixo com a reposição parcial de módulos e o acréscimo de uso da rede. O investimento separa as parcelas de potência e de energia, $I^{bess} = c^{ref} \left[(1 - f)\,\bar P^{dis} + f\,E^{tot}/h^{ref}\right]$, em que $c^{ref}$ é o custo por kW de um sistema de $h^{ref}$ horas e $f$ é a parcela desse custo proporcional à energia; assim, a energia instalada além da duração de referência tem custo. O montante de uso de injeção sem o BESS é $M^{0} = P^{pv}$. Com o BESS, adota-se a conexão compartilhada do art. 4º, § 1º, II, da Portaria: $M = \max(P^{pv}, \bar P^{dis})$, com a geração FV limitada quando a bateria injeta, o que atende à exigência de que o montante permita a descarga e a recarga totais do sistema de armazenamento (BRASIL, 2026, art. 9º, § 13). As curvas de oferta foram obtidas com conexão de 80 MW; com 60 MW, a diferença a partir de 50 MW contratados limita-se à geração FV nas horas de descarga do ONS, de cerca de R\$ 1 mil/(MW·ano). Como sensibilidade, avaliam-se os montantes somados, $M = P^{pv} + \bar P^{dis}$, e a cobrança também da TUST de consumo sobre a potência do BESS. Nessa decisão, o lucro operacional $Q(P)$ da Seção 3.8.1 é ajustado em dois pontos, conforme a Equação {eq:qinv}: devolve-se o custo de degradação do módulo LRCAP, cujo desgaste já está no investimento e no O&M fixo (Seção 3.5), e desconta-se o consumo auxiliar do BESS que não é custeado pela CONCAP:

$$
Q^{inv}(P) = Q(P) + c^{deg} E^{ons} P - \bar\lambda \left[ a H \left(\bar P^{dis} - P\right) + \max\!\left(0,\; a H - \phi E^{ons}\right) P \right]
$$ {#eq:qinv}

em que $E^{ons}$ é a energia injetada pelo módulo LRCAP por MW contratado em um ano, $a$ é o consumo auxiliar em fração da potência, $H$ é o número de horas do ano e $\bar\lambda$ é o PLD médio. O primeiro termo entre colchetes é o consumo do módulo mercantil, pago pelo empreendedor. O segundo é a parcela do consumo do módulo LRCAP que, medida no seu ponto de medição e contada como recarga, excede a folga $\phi E^{ons}$ entre a recarga custeada pela CONCAP, $E^{ons}/\mathrm{RTE}^{ref}$, e a recarga necessária, $E^{ons}/(\eta^{ch}\eta^{dis})$, isto é, $\phi = 1/\mathrm{RTE}^{ref} - 1/(\eta^{ch}\eta^{dis})$ (BRASIL, 2026, art. 9º, §§ 7º e 8º). Com despacho diário, $E^{ons} \approx 1.461$ MWh/MW, a folga é de cerca de 100 MWh/MW por ano e cobre um consumo auxiliar de até 1,1% da potência. A receita fixa é multiplicada pela disponibilidade $d$, e a potência ofertada passa a ser dada pela Equação {eq:oferta-inv}:

$$
P^{*}_{inv}(R) = \begin{cases} \arg\max_{P \in \mathcal{X}_h} \left\{ R d P + Q^{inv}(P) \right\}, & \text{se } \max_{P \in \mathcal{X}_h} \left\{ R d P + Q^{inv}(P) \right\} - C^{bess} > \Pi^{0} \\ 0, & \text{caso contrário} \end{cases}
$$ {#eq:oferta-inv}

O lance mínimo, $R^{min}$, é a menor receita fixa para a qual a construção do BESS é vantajosa, isto é, o menor $R$ para o qual $P^{*}_{inv}(R) > 0$. Ele é calculado com resolução de R\$ 1 mil/(MW·ano) para as três faixas de investimento e as duas taxas de desconto do Quadro 3.3 e, no caso central, decomposto nas parcelas de capital, O&M, uso da rede, consumo auxiliar e uso mercantil, cuja soma é o lance.

### 3.8.3 Frequência do despacho do ONS

A frequência com que o ONS acionará os sistemas de armazenamento contratados no LRCAP é desconhecida, e o perfil das Seções 3.5 e 3.7.2 adota a hipótese mais intensa, com um ciclo completo por dia. Para avaliar essa hipótese, o modelo admite um número $N^{ons}$ de despachos por ano. Na ausência de informação sobre o critério do ONS, adota-se como critério o próprio PLD, indicador de quão apertado está o sistema: em cada ano civil, são despachados apenas os $N^{ons}$ dias com maior PLD médio no período de descarga — o bloco de $H^{cap}$ horas de maior preço após o período solar, no perfil baseado em preço, ou as horas de descarga fixas, no perfil fixo. A seleção é feita sobre o ano inteiro, de modo que a decomposição em blocos semanais não a altera. Dias com PLD igual, situação frequente em anos com o PLD no piso, são selecionados por uma sequência de baixa discrepância sobre o dia do ano, o que os distribui uniformemente ao longo do ano em vez de concentrá-los nos primeiros dias. Nos dias sem despacho, o módulo LRCAP permanece carregado e não há recarga.

Como a receita fixa independe da energia despachada e, com os parâmetros da Tabela 3.1, $\kappa = 0$, o despacho afeta o lucro do empreendedor apenas por meio do custo de degradação do módulo LRCAP e do limite do ponto de conexão compartilhado. Se o efeito sobre a conexão for desprezível, o custo associado ao despacho é linear em $P^{cap}$, conforme a Equação {eq:custo-ons}:

$$
C^{ons}(P^{cap}) \approx c^{deg}\, H^{cap}\, N^{ons}\, P^{cap}
$$ {#eq:custo-ons}

e uma variação de $N^{ons}$ desloca o custo de oportunidade marginal de um valor constante, sem alterar a operação do lado mercantil. As simulações com diferentes valores de $N^{ons}$ permitem verificar essa aproximação.

Essa relação vale para o BESS existente. Para o BESS a construir, ela permite aproximar o lance mínimo da Seção 3.8.2. No lance mínimo, a potência ofertada tende à potência total do BESS ($P \approx \bar P^{dis}$), de modo que o módulo mercantil se anula e a operação do lado mercantil se aproxima da operação sem BESS. Nessa condição, $Q(\bar P^{dis}) \approx \Pi^{0} - \left(c^{deg} H^{cap} N^{ons} + \kappa\right) \bar P^{dis}$. Como a Equação {eq:qinv} devolve o termo de degradação, $Q^{inv}(\bar P^{dis}) \approx \Pi^{0} - \left(\kappa + \kappa^{aux}\right) \bar P^{dis}$, em que $\kappa^{aux}$ é o consumo auxiliar não custeado, por MW. A condição de indiferença $R\, d\, \bar P^{dis} + Q^{inv}(\bar P^{dis}) - C^{bess} = \Pi^{0}$ resulta na Equação {eq:lance-aprox}:

$$
R^{min} \approx \frac{1}{d} \left( \frac{I^{bess} / F(i, n) + C^{om,bess}}{\bar P^{dis}} + \frac{12\,\tau\,(M - M^{0})}{\bar P^{dis}} + \kappa + \kappa^{aux} \right)
$$ {#eq:lance-aprox}

isto é, o lance mínimo de um BESS a construir corresponde aproximadamente ao seu custo anual equivalente por MW — capital, O&M com reposição de módulos e uso da rede —, acrescido da recarga e do consumo auxiliar não custeados pela CONCAP e dividido pela disponibilidade. Como o desgaste do despacho já está no O&M, o lance não depende do custo de degradação por MWh e só depende da frequência do despacho por meio do consumo auxiliar, cuja folga diminui quando o módulo é despachado menos vezes. A aproximação desconsidera o valor residual do uso mercantil da bateria e é verificada no Capítulo 4.

**Dimensionamento do BESS e bateria isolada.** As curvas de oferta são obtidas para o BESS de referência, de 60 MW e 300 MWh. Para um BESS construído para o leilão, porém, a potência e a energia podem ser escolhidas junto com o lance. Avalia-se, por isso, o BESS dimensionado para o contrato, com $\bar P^{dis} = P^{cap}$ e $E^{tot} = \rho P^{cap}$, isto é, um módulo LRCAP sem módulo mercantil. Como a energia desse módulo é liquidada na CONCAP, ele não altera a operação da usina, e $Q^{inv}(P^{cap}) = \Pi^{0} - \kappa^{aux} P^{cap}$. O lance mínimo é, então, dado exatamente pela Equação {eq:lance-aprox}, com $\kappa = 0$, para cada potência entre $\underline P^{cap}$ e a potência do BESS de referência. Para isolar o papel do arranjo híbrido, o mesmo cálculo é feito para uma bateria isolada, sem a usina FV e o eletrolisador, cujo montante de uso de injeção é a própria potência ($M^{0} = 0$ e $M = P^{cap}$). Como, no lance, ambas operam apenas o módulo LRCAP, a diferença entre os dois lances mede o valor do compartilhamento da conexão. O valor do módulo mercantil é avaliado comparando-se o lucro que ele acrescenta na curva de oferta com o seu custo anual.

### 3.8.4 Casos avaliados

A curva de oferta é construída para os cenários anuais da Seção 3.7.2, com o lucro esperado ($\beta = 0$), nos casos do Quadro 3.2. Os casos variam as hipóteses que a análise do caso de referência indicou como determinantes para o custo de oportunidade: a existência de um limite de demanda de hidrogênio (Seção 3.4.5), a regra de suprimento do eletrolisador pela rede — vedação, limite de emissões ou importação livre —, a frequência do despacho do ONS, o custo de degradação do BESS e o dimensionamento do eletrolisador e do tanque de hidrogênio.

::: {custom-style="Legenda"}
Quadro 3.2 – Casos avaliados na construção da curva de oferta
:::

| Caso | Contrato de H₂ | Importação da rede | Outras alterações em relação à referência |
|------------------------|------------------------------|----------------------|------------------------|
| Referência | Sem limite de volume | Vedada | – (365 despachos/ano; $c^{deg}$ de R\$ 50/MWh; eletrolisador de 17,5 MW; tanque de 2 t) |
| Contrato 2 t/dia | $D^{h2} = \bar D^{h2} = 2.000$ kg/dia | Vedada | – |
| Contrato 3 t/dia | $D^{h2} = \bar D^{h2} = 3.000$ kg/dia | Vedada | – |
| Importação | Sem limite de volume | Permitida | – |
| Importação e contrato 3 t/dia | $D^{h2} = \bar D^{h2} = 3.000$ kg/dia | Permitida | – |
| Limite de emissões, fator médio | Sem limite de volume | Só ao eletrolisador, com $L$ de 7 ou 3,4 kgCO₂/kgH₂ | $f_t$ médio horário do SIN |
| Limite de emissões, fator marginal | Sem limite de volume | Só ao eletrolisador, com $L$ de 7 ou 3,4 kgCO₂/kgH₂ | $f_t$ = 449 kgCO₂/MWh |
| Frequência do despacho | Sem limite de volume | Vedada | 50; 150 ou 365 despachos/ano |
| Degradação | Sem limite de volume | Vedada | $c^{deg}$ de R\$ 100 ou 200/MWh |
| Eletrolisador | Sem limite de volume | Vedada | Eletrolisador de 10 ou 25 MW |
| Tanque | $D^{h2} = \bar D^{h2} = 3.000$ kg/dia | Vedada | Tanque de 10 t |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

Nos casos com importação, o eletrolisador e o BESS mercantil podem ser supridos pela rede ao PLD acrescido de $c^{imp}$, sem limite de emissões. Nos casos com limite de emissões, a energia da rede, ao mesmo custo, supre apenas o eletrolisador e está sujeita às Equações {eq:imp-el} e {eq:emissoes}, o que representa o critério de qualificação do hidrogênio pela intensidade de emissões (BRASIL, 2024). Ambas as configurações são avaliadas como alternativas à hipótese de suprimento exclusivamente fotovoltaico. Para cada caso, além da curva de oferta, registram-se a potência ótima e a operação média nos cenários para a receita fixa de referência, de R\$ 600 mil/(MW·ano), e calcula-se o lance mínimo para a construção do BESS (Seção 3.8.2), com o lucro sem BESS recalculado nos casos que alteram o contrato de hidrogênio, a importação ou o eletrolisador.

## 3.9 Implementação computacional

O modelo foi implementado na linguagem Python, com o uso da biblioteca de modelagem algébrica Pyomo (BYNUM *et al.*, 2021) e do *solver* HiGHS (HUANGFU; HALL, 2018). A estrutura do código separa: (i) a leitura e validação dos parâmetros, organizados em arquivos de configuração em formato YAML, com verificação automática dos requisitos regulatórios; (ii) a importação e o tratamento das séries de dados; (iii) a construção do modelo de otimização; (iv) a decomposição de Benders, nas versões determinística e estocástica; (v) o cálculo do VSS e do EVPI; (vi) a construção da curva de oferta; (vii) a análise de viabilidade econômica e do lance mínimo; e (viii) o pós-processamento dos resultados. Os subproblemas semanais são resolvidos em paralelo em processos independentes, cada qual restrito a uma linha de execução do *solver*, a fim de evitar a concorrência por núcleos de processamento. A consistência do modelo é verificada por um conjunto de testes automatizados que conferem, entre outros aspectos, o balanço de potência, os limites dos estados de carga, a exclusividade entre carga e descarga, o cumprimento do despacho do ONS e a seleção dos dias de despacho, o limite do ponto de conexão, as entregas do contrato de hidrogênio, o limite de emissões do hidrogênio e a validade dos cortes de Benders. O código e os dados são mantidos sob controle de versão, o que assegura a reprodutibilidade dos resultados.

## 3.10 Hipóteses e limitações

As principais hipóteses adotadas, e as respectivas implicações, são as seguintes:

a) **previsão perfeita dentro de cada ano:** mesmo na extensão estocástica, a operação de cada cenário é otimizada com conhecimento antecipado das séries daquele ano, o que tende a superestimar o lucro alcançável na operação real. A incerteza tratada pela Seção 3.7 é apenas a variação entre anos; a incerteza do despacho do ONS, cujo risco é alocado ao empreendedor pela Portaria, é representada somente pela regra de despacho baseada no PLD e pela sensibilidade ao número de despachos por ano (Seção 3.8.3), que supõe despachos completos, de $H^{cap}$ horas na potência contratada, nos dias de maior PLD;

b) **agente tomador de preço:** a operação do sistema não altera o PLD;

c) **receita fixa simplificada:** a receita fixa é rateada linearmente no horizonte, sem reajuste pelo Índice Nacional de Preços ao Consumidor Amplo (IPCA), sem o abatimento mensal por desempenho e sem as penalidades por indisponibilidade, cujos detalhes dependem do edital do leilão; o efeito de uma disponibilidade de 97% sobre o lance é avaliado como sensibilidade;

d) **disponibilidade integral:** o módulo LRCAP atende a 100% do despacho, sem indisponibilidades programadas ou forçadas;

e) **eletrolisador simplificado:** eficiência constante em toda a faixa de operação, com custo de partida apenas na extensão estocástica e sem tempos mínimos de operação e de parada, estado de espera (*standby*) ou limites de rampa;

f) **degradação linear:** o custo de degradação do BESS existente é proporcional à energia descarregada, sem dependência da profundidade de descarga, e seu valor de referência (R\$ 50/MWh) é inferior ao custo integral de reposição dos módulos, o que é tratado por análise de sensibilidade; na decisão de construir o BESS, o desgaste do uso contratado está no O&M fixo, e o uso mercantil mantém o custo por MWh, hipótese conservadora, pois o O&M de referência já cobre cerca de um ciclo por dia;

g) **divisão contínua do BESS:** a alocação entre os módulos é tratada como contínua, embora na prática seja discreta, em função da modularidade dos contêineres e conversores;

h) **fronteira entre blocos semanais:** no algoritmo de Benders, os estados de armazenamento retornam ao valor inicial ao final de cada semana, o que impede transferências de energia ou de hidrogênio entre semanas; nas avaliações com potência fixa (Seção 3.8), esses estados seguem a relaxação linear do ano inteiro, e a perda em relação ao ótimo anual é limitada pela diferença entre os limites inferior e superior (Seção 3.6.2);

i) **anos distintos:** no caso determinístico, a série de irradiância (2023) e a de preços (2025) referem-se a anos diferentes; no caso estocástico, o mesmo ocorre nos cenários de 2024 e 2025, que utilizam a irradiância de 2023. Para uma usina de pequeno porte em relação ao SIN, a correlação horária entre a geração local e o PLD tende a ser fraca, mas a hipótese deve ser considerada na interpretação dos resultados;

j) **contrato de hidrogênio simplificado:** o contrato é representado por um volume diário fixo, a preço fixo e com multa linear por déficit. Não se consideram cláusulas de *take-or-pay* sobre volumes anuais, flexibilidade de entrega entre dias, reajuste de preço ou a venda do excedente a outros compradores, e a multa adotada, igual ao preço do hidrogênio, é um valor de referência ainda não calibrado com contratos reais. Somada à receita perdida, ela custa ao empreendedor R\$ 70 por kg não entregue, o que torna o contrato praticamente firme e eleva o valor atribuído ao BESS no seu cumprimento (Seção 3.4.5);

k) **curva de oferta discreta:** a curva é obtida numa grade de 2,5 MW, de modo que a potência ótima e os custos marginais são conhecidos com essa resolução, e não inclui o investimento no BESS;

l) **viabilidade simplificada:** a análise de viabilidade considera fluxo de caixa constante em termos reais, antes dos tributos sobre a renda e descontado à taxa antes de impostos, sem financiamento, sem benefícios fiscais e sem valor residual; o O&M fixo da FV e do eletrolisador é hipotético, a TUST é a média nacional, e não a do barramento de conexão, a regra de cobrança do armazenamento ainda deve ser confirmada no texto da REN ANEEL nº 1.162/2026, a duração de referência e a composição do custo do BESS são estimadas e o consumo auxiliar é um valor indicativo; o lucro operacional é calculado com os parâmetros provisórios de operação;

m) **amostra de cenários:** os cinco anos históricos são tratados como equiprováveis e constituem uma amostra pequena; o VSS e o EVPI são, portanto, medidos dentro da amostra, e a avaliação da decisão fora da amostra é deixada para trabalhos futuros;

n) **limite de emissões simplificado:** a intensidade de emissões é apurada por semana, e não por hora ou por ano, e toda a energia importada é atribuída ao hidrogênio; o fator de emissão da rede é estimado com fatores do IPCC e rendimentos típicos por combustível, e não com o consumo de combustível de cada usina, e os fatores oficiais usados na comparação foram obtidos em fontes secundárias; a energia FV entra com emissão nula, ao passo que seu ciclo de vida, com mediana de 48 gCO₂eq/kWh em usinas de grande porte (SCHLÖMER *et al.*, 2014), corresponderia, sozinho, a 2,6 kgCO₂eq/kgH₂; e a metodologia de certificação — fator médio ou marginal, janela de apuração e fronteira do ciclo de vida — depende da regulamentação do Sistema Brasileiro de Certificação do Hidrogênio.

## REFERÊNCIAS

::: {custom-style="Referencia"}
ANEEL – AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA. **Atualização das taxas regulatórias de remuneração do capital (WACC) dos segmentos de geração, transmissão e distribuição**. Brasília: ANEEL, mar. 2026.
:::

::: {custom-style="Referencia"}
BENDERS, J. F. Partitioning procedures for solving mixed-variables programming problems. **Numerische Mathematik**, v. 4, n. 1, p. 238–252, 1962.
:::

::: {custom-style="Referencia"}
BESS-MARKET. **CAPEX Benchmark**: what does a BESS project cost in 2026? 2026. Disponível em: https://bess-market.com/en/knowledge/bess-capex-benchmark-2026/. Acesso em: 13 out. 2026.
:::

::: {custom-style="Referencia"}
BIRGE, J. R. The value of the stochastic solution in stochastic linear programs with fixed recourse. **Mathematical Programming**, v. 24, n. 1, p. 314–325, 1982.
:::

::: {custom-style="Referencia"}
BIRGE, J. R.; LOUVEAUX, F. **Introduction to stochastic programming**. 2. ed. New York: Springer, 2011.
:::

::: {custom-style="Referencia"}
BNEF – BLOOMBERGNEF. **Lithium-ion battery pack prices fall to \$108 per kilowatt-hour, despite rising metal prices**. Londres: BloombergNEF, 9 dez. 2025. Disponível em: https://about.bnef.com. Acesso em: 3 out. 2026.
:::

::: {custom-style="Referencia"}
BRASIL. Lei nº 14.948, de 2 de agosto de 2024. Institui o marco legal do hidrogênio de baixa emissão de carbono e dispõe sobre a Política Nacional do Hidrogênio de Baixa Emissão de Carbono. Brasília, DF: Presidência da República, 2024.
:::

::: {custom-style="Referencia"}
BRASIL. Ministério de Minas e Energia. Portaria Normativa MME nº 136, de 1º de junho de 2026. Estabelece as Diretrizes e a Sistemática para a realização dos Leilões para Contratação de Potência Elétrica, a partir de novos sistemas de armazenamento de energia em baterias. **Diário Oficial da União**: seção 1, Brasília, DF, n. 103, p. 98, 3 jun. 2026.
:::

::: {custom-style="Referencia"}
BRASIL. Ministério de Minas e Energia; EPE – EMPRESA DE PESQUISA ENERGÉTICA. **Caderno de parâmetros de custos**: geração e transmissão – PDE 2035. Brasília: MME/EPE, nov. 2025.
:::

::: {custom-style="Referencia"}
BYNUM, M. L. *et al.* **Pyomo**: optimization modeling in Python. 3. ed. Cham: Springer, 2021.
:::

::: {custom-style="Referencia"}
CCEE – CÂMARA DE COMERCIALIZAÇÃO DE ENERGIA ELÉTRICA. **PLD horário**. Portal de Dados Abertos da CCEE. 2026a. Disponível em: https://dadosabertos.ccee.org.br. Acesso em: 27 set. 2026.
:::

::: {custom-style="Referencia"}
CCEE – CÂMARA DE COMERCIALIZAÇÃO DE ENERGIA ELÉTRICA. **InfoLeilão Expresso**: 04º LRCAP 2026 – Leilão nº 2/2026-ANEEL. São Paulo: CCEE, mar. 2026b. Disponível em: https://www.ccee.org.br. Acesso em: 3 out. 2026.
:::

::: {custom-style="Referencia"}
CCEE – CÂMARA DE COMERCIALIZAÇÃO DE ENERGIA ELÉTRICA. **InfoLeilão Expresso**: 05º LRCAP 2026 – Leilão nº 3/2026-ANEEL. São Paulo: CCEE, mar. 2026c. Disponível em: https://www.ccee.org.br. Acesso em: 3 out. 2026.
:::

::: {custom-style="Referencia"}
CENÁRIO ENERGIA. **ANEEL aprova marco de baterias com tarifação dupla para sistemas sem despacho do ONS**. 2 jun. 2026. Disponível em: https://cenarioenergia.com.br/2026/06/02/aneel-aprova-marco-de-baterias-com-tarifacao-dupla-para-sistemas-sem-despacho-do-ons/. Acesso em: 13 out. 2026.
:::

::: {custom-style="Referencia"}
CESCON BARRIEU. **ANEEL publishes regulation on energy storage systems**. São Paulo, jun. 2026. Disponível em: https://cesconbarrieu.com.br/en/aneel-publishes-regulation-on-energy-storage-systems/. Acesso em: 13 out. 2026.
:::

::: {custom-style="Referencia"}
CONEJO, A. J. *et al.* **Decomposition techniques in mathematical programming**: engineering and science applications. Berlin: Springer, 2006.
:::

::: {custom-style="Referencia"}
CONEJO, A. J.; CARRIÓN, M.; MORALES, J. M. **Decision making under uncertainty in electricity markets**. New York: Springer, 2010.
:::

::: {custom-style="Referencia"}
EMBER. **How cheap is battery storage?** Londres: Ember, dez. 2025. Disponível em: https://ember-energy.org/latest-insights/how-cheap-is-battery-storage/. Acesso em: 13 out. 2026.
:::

::: {custom-style="Referencia"}
ENERGY CENTRAL. **BESS 5 MWh aux consumption**. 2025. Disponível em: https://www.energycentral.com/energy-biz/post/bess-5-mwh-aux-consumption-nB19OmDcUfffS2B. Acesso em: 13 out. 2026.
:::

::: {custom-style="Referencia"}
EPE – EMPRESA DE PESQUISA ENERGÉTICA. **Plano Decenal de Expansão de Energia 2034**: caderno de micro e minigeração distribuída e baterias. Rio de Janeiro: EPE, 2024.
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
IBGE – INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA. **Índice Nacional de Preços ao Consumidor Amplo (IPCA)**: séries históricas. Rio de Janeiro: IBGE, 2026. Disponível em: https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html. Acesso em: 3 out. 2026.
:::

::: {custom-style="Referencia"}
IEA – INTERNATIONAL ENERGY AGENCY. **Global Hydrogen Review 2025**. Paris: IEA, out. 2025.
:::

::: {custom-style="Referencia"}
IPCC – INTERGOVERNMENTAL PANEL ON CLIMATE CHANGE. **2006 IPCC Guidelines for National Greenhouse Gas Inventories**. v. 2: Energy. Hayama: IGES, 2006.
:::

::: {custom-style="Referencia"}
MCTI – MINISTÉRIO DA CIÊNCIA, TECNOLOGIA E INOVAÇÃO. **Fatores de emissão de CO₂ pela geração de energia elétrica no Sistema Interligado Nacional**. Brasília: MCTI, 2025. Disponível em: https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/sirene/dados-e-ferramentas/fatores-de-emissao.
:::

::: {custom-style="Referencia"}
MOVIMENTO ECONÔMICO. **Aneel conclui tarifas de transmissão e NE sai favorecido no ciclo 2026/2027**. 29 jun. 2026. Disponível em: https://movimentoeconomico.com.br/economia/energia/2026/06/29/aneel-conclui-tarifas-de-transmissao-e-ne-sai-favorecido-no-ciclo-2026-2027/. Acesso em: 13 out. 2026.
:::

::: {custom-style="Referencia"}
NREL – NATIONAL RENEWABLE ENERGY LABORATORY. **2024 Annual Technology Baseline**: utility-scale battery storage. Golden: NREL, 2024. Disponível em: https://atb.nrel.gov/electricity/2024/utility-scale_battery_storage. Acesso em: 13 out. 2026.
:::

::: {custom-style="Referencia"}
ONS – OPERADOR NACIONAL DO SISTEMA ELÉTRICO. **Geração por usina em base horária**. Portal de Dados Abertos do ONS, 2026. Disponível em: https://dados.ons.org.br. Acesso em: 14 out. 2026.
:::

::: {custom-style="Referencia"}
RADAR ENERGIA. **Aneel homologa tarifas de transmissão 2026/2027 com alta de 9,41% na RAP e impacto médio de 1,1% ao consumidor**. 2026. Disponível em: https://portalradarenergia.com.br/noticias/aneel-homologa-tarifas-de-transmissao-2026-2027-com-alta-de-9-41-na-rap-e-impact-9e740a13. Acesso em: 13 out. 2026.
:::

::: {custom-style="Referencia"}
ROCKAFELLAR, R. T.; URYASEV, S. Optimization of conditional value-at-risk. **Journal of Risk**, v. 2, n. 3, p. 21–41, 2000.
:::

::: {custom-style="Referencia"}
SCHLÖMER, S. *et al.* Annex III: technology-specific cost and performance parameters. *In*: IPCC – INTERGOVERNMENTAL PANEL ON CLIMATE CHANGE. **Climate Change 2014**: mitigation of climate change. Cambridge: Cambridge University Press, 2014.
:::

::: {custom-style="Referencia"}
TERNA. **Terna completes first MACSE auction**: 10 GWh of energy storage capacity awarded. Roma: Terna S.p.A., 1 out. 2025. Comunicado de imprensa. Disponível em: https://www.terna.it. Acesso em: 3 out. 2026.
:::

::: {custom-style="Referencia"}
UNIÃO EUROPEIA. Regulamento Delegado (UE) 2023/1185 da Comissão, de 10 de fevereiro de 2023, que estabelece um limiar mínimo de redução das emissões de gases com efeito de estufa para os combustíveis de carbono reciclado e uma metodologia de avaliação da redução das emissões dos combustíveis renováveis de origem não biológica. **Jornal Oficial da União Europeia**, L 157, 20 jun. 2023.
:::

::: {custom-style="Referencia"}
ZOU, J.; AHMED, S.; SUN, X. A. Stochastic dual dynamic integer programming. **Mathematical Programming**, v. 175, n. 1–2, p. 461–502, 2019.
:::
