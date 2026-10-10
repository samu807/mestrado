# 4 RESULTADOS E DISCUSSÃO

Este capítulo apresenta os resultados do modelo descrito no Capítulo 3, aplicado ao caso de referência: a planta da UNIFEI escalonada para 50 MWp de geração FV e 17,5 MW de eletrolisador PEM, com BESS de 60 MW e 300 MWh, conectada ao submercado SE/CO. A Seção 4.1 avalia o desempenho do método de solução no caso determinístico de 2025. A Seção 4.2 apresenta o resultado principal, a decisão de um proponente que precisa construir o BESS: a viabilidade do empreendimento e o lance mínimo no leilão. A Seção 4.3 analisa a decisão de quanto contratar quando o BESS está disponível e os fatores que a determinam. A Seção 4.4 sintetiza os resultados. Salvo indicação em contrário, os resultados correspondem ao lucro esperado nos cinco cenários anuais de 2021 a 2025 (Seção 3.7.2), em valores de dezembro de 2025; a Seção 4.1 e a Subseção 4.3.7 utilizam o caso determinístico de 2025 (Seção 3.5).

Ressalta-se que parte dos parâmetros econômicos — em especial a receita fixa do LRCAP (R\$ 600 mil/(MW·ano)), o preço do hidrogênio (R\$ 35/kg), o custo de degradação do BESS (R\$ 50/MWh), a multa contratual por déficit de hidrogênio e o custo de O&M fixo — tem caráter provisório, conforme discutido nas Seções 3.5 e 3.8.2. Por isso, a ênfase deste capítulo recai sobre as relações entre as decisões e as hipóteses, e não sobre os valores absolutos de lucro.

## 4.1 Desempenho do método de solução

O caso determinístico utiliza o PLD do submercado SE/CO de 2025, a geração FV obtida da base ERA5 e o perfil fixo de despacho do ONS descritos na Seção 3.5, com o ano dividido em 52 blocos semanais. A Figura 4.1 apresenta a convergência do algoritmo de Benders e a aproximação da função valor do primeiro estágio construída pelos cortes.

::: {custom-style="Legenda"}
Figura 4.1 – Caso determinístico de 2025: (a) limites superior e inferior ao longo das iterações de Benders; (b) aproximação da função valor pelos cortes e pontos avaliados
:::

::: {custom-style="Figura"}
![](figuras/benders_unifei_escalonada.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

Após a avaliação dos três pontos iniciais (0, 30 e 60 MW), o limite superior parte de R\$ 72,7 milhões, e o algoritmo converge em quatro iterações, com *gap* final de 0,06%, em 67 segundos de processamento em quatro núcleos — tempo inferior ao de uma única tentativa de solução direta do MILP anual, interrompida após 15 minutos sem solução (Seção 3.6.1). A Figura 4.1(b) mostra que a função valor é crescente e aproximadamente linear até cerca de 45 MW e praticamente plana entre 50 e 60 MW, o que explica a convergência rápida: poucos cortes bastam para delimitar a região do ótimo.

O ótimo encontrado é $P^{cap} = 54{,}4$ MW, com lucro de R\$ 67,5 milhões no ano. A Tabela 4.1 compara a composição desse resultado com o ótimo do modelo estocástico, apresentado na Subseção 4.3.1.

::: {custom-style="Legenda"}
Tabela 4.1 – Comparação entre o caso determinístico de 2025 e o modelo estocástico
:::

| Indicador | Determinístico (2025) | Estocástico (2021–2025, média) |
|------------------------------------|--------------------|--------------------|
| Potência ótima no LRCAP (MW) | 54,4 | 54,4 |
| Lucro (R\$ milhões/ano) | 67,5 | 68,1 |
| Receita fixa do LRCAP (R\$ milhões/ano) | 32,7 | 32,6 |
| Receita de H₂ (R\$ milhões/ano) | 39,1 | 36,0 |
| Receita no MCP (R\$ milhões/ano) | 1,8 | 5,1 |
| Degradação do BESS (R\$ milhões/ano) | 4,4 | 4,4 |
| H₂ produzido (t/ano) | 1.117 | 1.029 |
| Fator de capacidade do eletrolisador | 0,40 | 0,37 |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor. Valores do modelo estocástico obtidos na grade de 55 MW, exceto potência, lucro e receita fixa.
:::

As duas abordagens conduzem à mesma potência ótima. As diferenças de composição decorrem principalmente do preço. Embora a série ERA5 de 2025 apresente fator de capacidade FV ligeiramente inferior ao da média dos cenários SARAH-3 (16,9% contra 17,5%), o caso determinístico produz mais hidrogênio. No modelo estocástico, os picos de PLD do cenário de 2021, que superam o valor da energia no eletrolisador, tornam a exportação ao MCP mais vantajosa em parte das horas, o que eleva a receita média no mercado de curto prazo e reduz a produção de hidrogênio. A coincidência das potências ótimas antecipa o resultado da Subseção 4.3.2: a variação entre anos pouco altera a decisão de contratação.

**Decomposição em blocos.** Para a potência de 54,44 MW, o lucro anual do caso determinístico de 2025 foi idêntico com blocos de 7, 14 e 28 dias (diferença relativa inferior a $10^{-11}$). Refeita a decomposição com blocos de 14 dias, o algoritmo de Benders convergiu para 55,5 MW e R\$ 67,53 milhões, contra 54,4 MW e R\$ 67,51 milhões com blocos semanais — diferença de 0,03%, inferior à tolerância de convergência e situada na região plana do ótimo. Sem contrato de hidrogênio, as condições cíclicas semanais, portanto, não restringem a operação de forma mensurável, o que é coerente com a operação em ciclos diários do módulo mercantil e do tanque, cujos estados de armazenamento tendem a retornar aos mesmos valores ao fim de cada semana.

O mesmo não vale quando há contrato de fornecimento de hidrogênio. Com entrega diária firme, guardar energia e hidrogênio de dias ensolarados para dias nublados tem valor, e a condição cíclica semanal — que obriga cada semana a começar com o módulo mercantil em 50% da carga e o tanque vazio — passa a restringir a operação. No contrato de 3 t/dia, o lucro operacional esperado com blocos cíclicos ficou entre 2,3% e 3,8% abaixo do obtido com os estados de fronteira da relaxação linear do ano (Seção 3.6.2), para potências de até 55 MW, e o déficit anual de entrega com 55 MW contratados caiu de 61 t para 40 t. Com o tanque de 10 t, a diferença chegou a 9%, pois a condição cíclica esvaziava o tanque no início de cada semana. Com a fronteira da relaxação, a diferença entre os limites inferior e superior do lucro foi inferior a 0,1% em todos os pontos das curvas de oferta dos casos com contrato até 55 MW, de até 0,33% com 57,5 MW e de até 1,6% com 60 MW. Nesse último ponto, o módulo mercantil fica sem potência e a relaxação linear, que admite o eletrolisador abaixo da carga mínima, é menos justa. No caso sem contrato, os dois tratamentos diferem em 0,01% (ano de 2021, 57,5 MW). Por isso, os casos com contrato de hidrogênio, apresentados nas Subseções 4.2.3, 4.3.4 e 4.3.6, foram calculados com a fronteira da relaxação.

## 4.2 BESS a construir: viabilidade e lance mínimo

Esta seção apresenta o resultado principal do trabalho: a decisão de um proponente que precisa construir o BESS para participar do leilão, situação prevista na Portaria, que trata da contratação de novos sistemas de armazenamento (BRASIL, 2026). A Subseção 4.2.1 avalia a viabilidade do empreendimento com a receita fixa de referência; a Subseção 4.2.2, o valor do BESS e o lance mínimo; e a Subseção 4.2.3, a sensibilidade do lance mínimo às hipóteses do modelo.

### 4.2.1 Viabilidade do empreendimento

O modelo de operação maximiza o lucro operacional, sem os custos de investimento. Esta subseção avalia, segundo o procedimento da Seção 3.8.2, se o empreendimento se paga com a receita fixa de referência. Os resultados são apresentados na Tabela 4.2 e na Figura 4.2.

::: {custom-style="Legenda"}
Tabela 4.2 – Viabilidade econômica em 15 anos (receita fixa de R\$ 600 mil/(MW·ano))
:::

| Caso | Invest. (R\$ mi) | Lucro op. (R\$ mi/ano) | VPL a 8,0% (R\$ mi) | VPL a 12,1% (R\$ mi) | TIR real | H₂ eq. (R\$/kg) |
|----------------------|----------|----------|----------------------|----------|--------|-----------|
| Referência | 732 | 68,1 | −295 (−461 a −81) | −386 | 0,6% | 68 |
| Contrato 2 t/dia | 732 | 61,8 | −349 (−515 a −135) | −429 | −1,1% | 91 |
| Contrato 3 t/dia | 732 | 65,5 | −317 (−483 a −103) | −404 | −0,1% | 70 |
| Importação | 732 | 88,5 | −120 (−287 a +94) | −248 | 5,2% | 41 |
| Importação e contrato 3 t/dia | 732 | 68,9 | −288 (−455 a −74) | −381 | 0,8% | 66 |
| Eletrolisador 10 MW | 651 | 60,4 | −259 (−400 a −91) | −341 | 0,7% | 71 |
| Eletrolisador 25 MW | 813 | 73,5 | −351 (−542 a −91) | −447 | 0,0% | 70 |
| Degradação R\$ 200/MWh | 732 | 54,9 | −408 (−574 a −194) | −475 | −3,0% | 79 |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor. Investimento, TIR e preço de equilíbrio do H₂ (H₂ eq., à taxa de 8,0%) com investimento central; entre parênteses, VPL com investimento alto e baixo.
:::

Com os parâmetros adotados, nenhum caso é economicamente viável com investimento central. No caso de referência, o investimento de R\$ 732 milhões — R\$ 213 milhões na usina FV, R\$ 330 milhões no BESS e R\$ 189 milhões no eletrolisador — gera fluxo anual de R\$ 51 milhões, após R\$ 17 milhões de O&M fixo, e a TIR real é de apenas 0,6%. O preço do hidrogênio que tornaria o VPL nulo à taxa de 8% é de cerca de R\$ 68/kg, praticamente o dobro do valor adotado. O único caso com VPL positivo é o de importação de energia com investimentos no limite inferior das faixas (R\$ 94 milhões), o que antecipa a importância da regra de suprimento do eletrolisador discutida na Subseção 4.3.4.

::: {custom-style="Legenda"}
Figura 4.2 – Viabilidade econômica: (a) VPL do projeto por caso; (b) ganho anual proporcionado pelo BESS em função da receita fixa, comparado com o seu custo anual equivalente
:::

::: {custom-style="Figura"}
![](figuras/viabilidade.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

### 4.2.2 Valor do BESS e lance mínimo

**Valor do BESS.** Sem a bateria, e portanto sem o leilão, o lucro operacional esperado é de R\$ 35,4 milhões por ano. Com o BESS e a contratação de 55 MW à receita de R\$ 600 mil/(MW·ano), passa a R\$ 68,1 milhões. O ganho de R\$ 32,8 milhões por ano não cobre o custo anual equivalente do BESS, de R\$ 46,8 milhões à taxa de 8% com investimento central (Figura 4.2(b)). Sem a receita do leilão, a bateria agrega apenas R\$ 9,7 milhões por ano, provenientes do suprimento noturno do eletrolisador e da arbitragem no MCP; é, portanto, a receita fixa do LRCAP que pode viabilizá-la.

**Lance mínimo.** A Figura 4.3 compara a curva de oferta de um BESS já existente, obtida na Subseção 4.3.3, com a de um BESS a construir, e a Tabela 4.3 apresenta o lance mínimo para cada faixa de investimento e taxa de desconto.

::: {custom-style="Legenda"}
Figura 4.3 – Curva de oferta com o investimento no BESS: (a) potência ótima a ofertar com BESS existente e a construir; (b) lance mínimo por faixa de investimento e taxa de desconto
:::

::: {custom-style="Figura"}
![](figuras/curva_oferta_investimento.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

::: {custom-style="Legenda"}
Tabela 4.3 – Lance mínimo para a construção do BESS, em R\$ mil/(MW·ano), e potência ofertada nesse lance
:::

| Taxa de desconto | Investimento baixo (R\$ 5.000/kW) | Investimento central (R\$ 5.500/kW) | Investimento alto (R\$ 6.000/kW) |
|------------------|------------------|------------------|------------------|
| 8,0% | 780 (57,5 MW) | 855 (57,5 MW) | 925 (60 MW) |
| 12,1% | 940 (60 MW) | 1.025 (60 MW) | 1.110 (60 MW) |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

Quando o BESS ainda será construído, a curva de oferta deixa de ser escalonada e passa a ser do tipo "tudo ou nada": abaixo do lance mínimo, o proponente não constrói a bateria e não oferta potência; acima dele, oferta entre 57,5 e 60 MW. A curva escalonada da Seção 4.3 descreve, portanto, a decisão de um proponente que já dispõe do BESS. O lance mínimo no caso central, de R\$ 855 mil/(MW·ano), é praticamente igual à soma do custo anual equivalente do BESS por MW (R\$ 780 mil) com o custo de degradação do despacho diário do módulo LRCAP (R\$ 73 mil), o que indica que o uso mercantil da bateria pouco reduz o lance quando ela é construída para o leilão. Esse valor é próximo do preço médio obtido por termelétricas existentes no LRCAP de março de 2026 (R\$ 831 mil/(MW·ano)) e muito inferior ao das termelétricas e hidrelétricas do leilão anterior (R\$ 2,33 milhões/(MW·ano)), o que sugere que o armazenamento em baterias é competitivo frente à expansão térmica, mas não frente às usinas existentes. A receita de R\$ 600 mil/(MW·ano) adotada no caso de referência é inferior ao lance mínimo em todas as combinações avaliadas: com ela, um proponente racional não construiria o BESS.

### 4.2.3 Sensibilidade do lance mínimo

O lance mínimo da Subseção 4.2.2 foi recalculado para cada caso de sensibilidade da Seção 3.8.4, com investimento central. Nos casos que alteram o contrato de hidrogênio, a importação e o tamanho do eletrolisador, o lucro sem BESS também foi recalculado. Os resultados são apresentados na Tabela 4.4.

::: {custom-style="Legenda"}
Tabela 4.4 – Lance mínimo para a construção do BESS por caso, em R\$ mil/(MW·ano), com investimento central, e potência ofertada nesse lance
:::

| Caso | Taxa de 8,0% | Taxa de 12,1% |
|------------------------------|------------------|------------------|
| Referência | 855 (57,5 MW) | 1.025 (60 MW) |
| Contrato 2 t/dia | 855 (60 MW) | 1.025 (60 MW) |
| Contrato 3 t/dia | 795 (55 MW) | 980 (55 MW) |
| Contrato 3 t/dia, tanque 10 t | 765 (55 MW) | 950 (55 MW) |
| Importação | 855 (60 MW) | 1.025 (60 MW) |
| Importação e contrato 3 t/dia | 855 (60 MW) | 1.025 (60 MW) |
| Eletrolisador 10 MW | 845 (57,5 MW) | 1.020 (57,5 MW) |
| Eletrolisador 25 MW | 855 (60 MW) | 1.025 (60 MW) |
| 50 despachos/ano | 790 (57,5 MW) | 960 (60 MW) |
| 150 despachos/ano | 810 (57,5 MW) | 980 (60 MW) |
| Degradação R\$ 100/MWh | 930 (60 MW) | 1.100 (60 MW) |
| Degradação R\$ 200/MWh | 1.075 (60 MW) | 1.245 (60 MW) |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

As hipóteses relativas ao hidrogênio, que determinam a quantidade a ofertar com um BESS disponível (Seção 4.3), alteram pouco o lance mínimo na maior parte dos casos: com o contrato de 2 t/dia, a importação e os dois tamanhos de eletrolisador, ele varia entre R\$ 845 mil e R\$ 855 mil/(MW·ano) à taxa de 8%. Isso ocorre porque, no lance mínimo, quase toda a bateria é destinada ao leilão, e o uso mercantil — o canal pelo qual o hidrogênio afeta a decisão — tem pouco peso. A exceção é o contrato firme de 3 t/dia sem importação. Nele, o proponente oferta 55 MW, e os 5 MW e 36 MWh restantes do BESS reduzem o déficit de entrega e a multa correspondente. Esse uso mercantil reduz o lance para R\$ 795 mil/(MW·ano) com o tanque de 2 t e para R\$ 765 mil com o tanque de 10 t, quedas de 7% e de 11% em relação ao caso de referência.

Por outro lado, o custo de degradação e a frequência do despacho deslocam o lance mínimo quase exatamente pelo custo de degradação do módulo LRCAP, $c^{deg} H^{cap} N^{ons}$ (Equação (3.43)): de R\$ 855 mil para R\$ 930 mil e R\$ 1,08 milhão com degradação de R\$ 100 e R\$ 200/MWh (acréscimos de R\$ 75 mil e R\$ 220 mil, contra R\$ 73 mil e R\$ 219 mil previstos), e para R\$ 790 mil com 50 despachos por ano (redução de R\$ 65 mil, contra R\$ 63 mil prevista). Esses resultados confirmam a aproximação da Equação (3.44): o lance mínimo de um BESS a construir corresponde ao custo anual equivalente do BESS por MW acrescido do custo de degradação imposto pelo despacho do ONS, com $\kappa = 0$ nos casos avaliados. Com os valores avaliados, o lance mínimo situa-se entre R\$ 780 mil e R\$ 1,25 milhão/(MW·ano), e sua incerteza decorre principalmente do custo de investimento, da taxa de desconto e da degradação da bateria.

## 4.3 BESS disponível: quantidade a contratar e operação

Esta seção supõe que o BESS está disponível — porque já existe ou porque foi construído com receita fixa acima do lance mínimo — e analisa quanto de sua potência contratar no leilão e como o sistema opera. Os resultados utilizam a receita fixa de referência de R\$ 600 mil/(MW·ano), inferior ao lance mínimo da Seção 4.2, mas a curva de oferta fornece a decisão para qualquer receita; acima do lance mínimo, ela indica a oferta de 57,5 a 60 MW. A análise identifica os mecanismos que determinam o custo de oportunidade da contratação e a sensibilidade da decisão às hipóteses de operação e de mercado.

### 4.3.1 Decisão de contratação no modelo estocástico

A Figura 4.4(a) apresenta o lucro anual de cada cenário, o lucro esperado e o CVaR em função da potência contratada no LRCAP. Participar do leilão é vantajoso em todos os cenários: a contratação do mínimo regulatório de 30 MW eleva o lucro esperado de R\$ 45,0 milhões para R\$ 60,7 milhões por ano, um acréscimo de 35%. A partir desse ponto, o lucro esperado continua a crescer, porém a taxas decrescentes, até um máximo e decresce em seguida, quando a potência contratada passa a retirar do módulo mercantil a capacidade que abastece o eletrolisador durante a noite.

::: {custom-style="Legenda"}
Figura 4.4 – Lucro anual em função da potência contratada no LRCAP: (a) por cenário, lucro esperado e CVaR; (b) por cenário, para quatro decisões de contratação
:::

::: {custom-style="Figura"}
![](figuras/estocastico_unifei.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

O ótimo, assinalado na Figura 4.4, é $P^{cap} = 54{,}4$ MW, com lucro esperado de R\$ 68,12 milhões por ano, obtido com tolerância de convergência de 0,01%. Com a tolerância de 0,1% usada inicialmente, o algoritmo de Benders havia encerrado em 53,4 MW, com lucro esperado apenas R\$ 20 mil inferior. A diferença ilustra uma característica central do problema: a função de lucro é muito plana na vizinhança do ótimo, com variação inferior a 0,4% entre 50 e 56 MW. Do ponto de vista prático, a decisão relevante é contratar entre 50 e 55 MW; a localização exata do máximo é menos importante do que as hipóteses que o determinam, examinadas nas subseções seguintes.

O lucro por cenário na potência ótima é apresentado na Tabela 4.5. O pior cenário é 2022, ano em que o PLD permaneceu próximo do piso regulatório, e o melhor, 2021, ano da crise hídrica. A diferença entre eles, de cerca de R\$ 8 milhões por ano, é pequena diante do ganho proporcionado pela participação no leilão.

::: {custom-style="Legenda"}
Tabela 4.5 – Lucro anual por cenário na potência ótima (54,4 MW)
:::

| Cenário | 2021 | 2022 | 2023 | 2024 | 2025 | Esperado | CVaR ($\alpha = 0{,}8$) |
|------------|---------|---------|---------|---------|---------|---------|---------|
| Lucro (R\$ milhões/ano) | 73,47 | 65,38 | 66,58 | 67,40 | 67,77 | 68,12 | 65,38 |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

A fronteira entre risco e retorno, obtida com pesos $\beta \in \{0;\ 0{,}5;\ 1;\ 2\}$ para o CVaR, degenerou em um único ponto: a mesma potência maximiza o lucro esperado e o lucro do pior ano, com *gap* inferior a 0,07% em todos os casos. Não há, portanto, troca entre risco e retorno nesta configuração, pois a dispersão entre os cenários pouco depende da decisão de contratação, como se observa na Figura 4.4(b): as barras de cada decisão se deslocam praticamente em paralelo entre os anos.

A composição do lucro médio na potência de 55 MW, ponto da grade da Seção 3.8 mais próximo do ótimo, é: R\$ 33,0 milhões de receita fixa do LRCAP, R\$ 36,0 milhões de receita com hidrogênio e R\$ 5,1 milhões no MCP, deduzidos R\$ 4,4 milhões de degradação do BESS e R\$ 1,6 milhão de custos variáveis de produção de hidrogênio. O eletrolisador consome 56,6 GWh por ano, cerca de três quartos da energia FV disponível, com fator de capacidade de 0,37, e produz 1.029 t de hidrogênio; os 19,4 GWh restantes são exportados ao MCP. Esse resultado antecipa a principal conclusão da Subseção 4.3.4: com o hidrogênio vendido sem limite de volume a R\$ 35/kg, cada MWh destinado ao eletrolisador vale cerca de R\$ 609, e o MCP tem papel secundário na operação.

### 4.3.2 Valor da solução estocástica e valor esperado da informação perfeita

A Tabela 4.6 compara a decisão estocástica (RP) com a decisão obtida no ano médio (EV) e com a solução espera-e-vê (WS), calculadas segundo a Seção 3.7.4.

::: {custom-style="Legenda"}
Tabela 4.6 – Decisões e lucro anual por cenário para o cálculo do VSS e do EVPI
:::

| Decisão | $P^{cap}$ (MW) | 2021 | 2022 | 2023 | 2024 | 2025 | Esperado |
|----------------------|------------------|-------|-------|-------|-------|-------|----------|
| RP (estocástica) | 54,38 | 73,47 | 65,38 | 66,58 | 67,40 | 67,77 | 68,121 |
| EV (ano médio) | 54,34 | 73,46 | 65,39 | 66,58 | 67,40 | 67,77 | 68,121 |
| WS (por cenário) | 60,0 / 51,5 / 51,0 / 52,7 / 54,6 | 73,95 | 65,47 | 66,70 | 67,44 | 67,77 | 68,266 |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor. Lucros em R\$ milhões/ano.
:::

O VSS resultou em cerca de R\$ 300 por ano (menos de 0,001% do RP), valor inferior à tolerância de convergência e, portanto, indistinguível de zero. A decisão obtida no ano médio coincide, para efeitos práticos, com a decisão estocástica. O EVPI foi de R\$ 145 mil por ano (0,21% do RP), com limite superior de R\$ 161 mil. Quase toda a perda decorre do cenário de 2021, no qual a decisão ótima com informação perfeita seria contratar toda a potência do BESS (60 MW); nos demais anos, as decisões ótimas situam-se entre 51 e 55 MW.

Dois aspectos merecem destaque. Primeiro, embora o ano médio conduza à decisão correta, ele superestima o lucro: o valor ótimo do problema EV foi de R\$ 68,89 milhões, contra R\$ 68,12 milhões do EEV. A diferença, de cerca de R\$ 0,8 milhão por ano, resulta da suavização dos picos e vales de preço e de irradiância pela média hora a hora, e confirma que o ano médio não deve ser usado para estimar a receita do empreendimento. Segundo, os baixos valores de VSS e de EVPI indicam que a incerteza modelada — a variação de preço e de geração entre anos — tem pouco efeito sobre a decisão de contratação. As subseções seguintes mostram que outras hipóteses, não representadas nos cenários, têm efeito muito maior.

### 4.3.3 Curva de oferta

A Figura 4.5 apresenta o resultado do procedimento da Seção 3.8 para os cinco casos de contrato de hidrogênio e de importação do Quadro 3.2. No caso de referência (curvas em azul), o custo de oportunidade marginal cresce de forma acentuada com a potência contratada: até 37,5 MW, cada MW adicional custa menos de R\$ 100 mil/(MW·ano), enquanto os últimos 5 MW custam entre R\$ 760 mil e R\$ 900 mil/(MW·ano) (Figura 4.5(b)). A receita mínima de entrada é de R\$ 76 mil/(MW·ano) e a receita necessária para ofertar toda a potência do BESS é de R\$ 895 mil/(MW·ano).

::: {custom-style="Legenda"}
Figura 4.5 – Curva de oferta no LRCAP para os casos de contrato de hidrogênio e de importação: (a) perda de lucro operacional esperado; (b) custo de oportunidade marginal; (c) potência ótima em função da receita fixa
:::

::: {custom-style="Figura"}
![](figuras/curva_oferta.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

O formato da curva decorre da divisão do BESS entre os módulos. Até cerca de 37,5 MW contratados, o módulo mercantil retém energia e potência suficientes para deslocar a geração FV excedente para o eletrolisador nas horas noturnas, e a contratação adicional retira apenas a capacidade de menor valor. A partir desse ponto, cada MW contratado reduz em 4,8 MWh a energia e em 1 MW a potência do módulo mercantil, que se aproxima de zero quando $P^{cap}$ tende a 60 MW, e o eletrolisador deixa de operar à noite. A Figura 4.5(c) traduz essa relação em uma curva de oferta escalonada: para receitas entre R\$ 80 mil e R\$ 300 mil/(MW·ano), o empreendedor ofertaria entre 35 e 42,5 MW; para R\$ 600 mil, 55 MW; e somente acima de cerca de R\$ 900 mil ofertaria toda a capacidade.

Esse resultado tem duas implicações para o proponente. A decisão de participar do leilão é robusta, pois o limiar de entrada é baixo em todos os casos avaliados (R\$ 76 mil a R\$ 96 mil/(MW·ano)), muito inferior a qualquer receita fixa plausível para sistemas de armazenamento. Por outro lado, a quantidade a ofertar acima de cerca de 40 MW é sensível tanto ao preço quanto às hipóteses sobre o hidrogênio, como mostra a subseção seguinte.

### 4.3.4 Contrato de hidrogênio e importação de energia

A Tabela 4.7 resume, para a receita fixa de referência, a potência ótima, o lucro e a operação média de cada caso.

::: {custom-style="Legenda"}
Tabela 4.7 – Potência ótima, lucro e operação média nos casos de contrato de hidrogênio e de importação (receita fixa de R\$ 600 mil/(MW·ano))
:::

| Indicador | Referência | Contrato 2 t/dia | Contrato 3 t/dia | Importação | Importação e contrato 3 t/dia |
|------------------------------|------------|------------|------------|------------|------------|
| Potência ótima (MW) | 55 | 60 | 55 | 60 | 60 |
| Lucro esperado (R\$ mi/ano) | 68,1 | 61,8 | 65,5 | 88,5 | 68,9 |
| Receita no MCP (R\$ mi/ano) | 5,1 | 6,2 | 3,0 | 6,1 | 4,0 |
| Receita de H₂ (R\$ mi/ano) | 36,0 | 25,4 | 37,0 | 89,4 | 38,3 |
| Custo de importação (R\$ mi/ano) | – | – | – | 34,7 | 3,4 |
| Energia exportada (GWh/ano) | 19,4 | 36,9 | 18,1 | 28,2 | 25,4 |
| Energia importada (GWh/ano) | – | – | – | 91,8 | 8,7 |
| H₂ vendido (t/ano) | 1.029 | 727 | 1.056 | 2.553 | 1.096 |
| Déficit contratual de H₂ (t/ano) | – | 3,6 | 39,6 | – | 0 |
| Fator de capacidade do eletrolisador | 0,37 | 0,26 | 0,38 | 0,92 | 0,39 |
| Receita mínima de entrada (R\$ mil/MW·ano) | 76 | 84 | 95 | 96 | 86 |
| Custo marginal do último MW (R\$ mil/MW·ano) | 895 | 172 | 2.037 | 474 | 406 |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

**Contrato de 2 t/dia.** Com um volume diário inferior à produção do caso de referência, o hidrogênio excedente não encontra comprador e a energia correspondente é exportada ao MCP, cuja energia praticamente dobra (de 19,4 para 36,9 GWh). O módulo mercantil perde a função de abastecer o eletrolisador à noite, e seu valor passa a ser o da arbitragem de preços no MCP, muito inferior. O custo de oportunidade do último MW cai de R\$ 895 mil para R\$ 172 mil/(MW·ano), e o ótimo passa a ser contratar toda a potência. O lucro diminui R\$ 6,3 milhões por ano em relação ao caso de referência, refletindo a menor venda de hidrogênio.

**Contrato de 3 t/dia.** Com um volume próximo da produção média do caso de referência, porém firme em todos os dias, o BESS passa a garantir a entrega nos dias e nas horas de menor geração. Mesmo assim, há um déficit de 40 t por ano (3,6% do volume contratado), concentrado nos períodos de menor irradiância, e a multa correspondente, de R\$ 1,4 milhão por ano, responde por cerca de metade da redução do lucro em relação ao caso de referência (R\$ 2,6 milhões por ano). A curva de custo de oportunidade torna-se ainda mais íngreme no extremo superior: o último MW custa cerca de R\$ 2,0 milhões/(MW·ano) — entre R\$ 1,9 milhão e R\$ 2,1 milhões, considerados os limites inferior e superior do lucro (Subseção 4.1) —, pois sua contratação eliminaria a potência do módulo mercantil e aumentaria o déficit. A potência ótima permanece em 55 MW.

**Importação de energia.** Quando a importação é permitida, o eletrolisador é suprido pela rede nas horas de PLD baixo, inclusive à noite, e seu fator de capacidade sobe de 0,37 para 0,92. A produção de hidrogênio mais que dobra e o lucro aumenta R\$ 20,4 milhões por ano, mesmo com o custo adicional de R\$ 250/MWh sobre a energia importada. Como a rede substitui o BESS no suprimento noturno do eletrolisador, o módulo mercantil perde valor e o ótimo passa a ser contratar toda a potência. Cerca de 65% da energia consumida pelo eletrolisador provém da rede nesse caso, o que torna a qualificação do hidrogênio dependente do critério regulatório adotado — de intensidade de emissões ou de origem física da energia.

**Importação com contrato de 3 t/dia.** A combinação das duas hipóteses mostra que o ganho da importação depende da existência de demanda: com o volume limitado pelo contrato, a importação restringe-se a 8,7 GWh por ano, usados para eliminar o déficit de entrega, e o lucro supera o do caso de referência em apenas R\$ 0,8 milhão por ano.

Esses resultados indicam que a troca entre o LRCAP e o MCP só se manifesta plenamente quando a demanda de hidrogênio é limitada. Sem limite de volume, a troca relevante é entre o LRCAP e a produção de hidrogênio, mediada pelo módulo mercantil do BESS; a regra de suprimento do eletrolisador é, entre as hipóteses avaliadas, a de maior efeito sobre o lucro.

### 4.3.5 Frequência do despacho do ONS

A Figura 4.6 e a Tabela 4.8 apresentam a curva de oferta do caso de referência para 50, 150 e 365 despachos por ano.

::: {custom-style="Legenda"}
Figura 4.6 – Curva de oferta no LRCAP para diferentes frequências de despacho do ONS: (a) perda de lucro operacional esperado; (b) custo de oportunidade marginal; (c) potência ótima em função da receita fixa
:::

::: {custom-style="Figura"}
![](figuras/curva_oferta_ciclos.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

::: {custom-style="Legenda"}
Tabela 4.8 – Efeito da frequência do despacho do ONS (receita fixa de R\$ 600 mil/(MW·ano))
:::

| Despachos por ano | Potência ótima (MW) | Lucro esperado (R\$ mi/ano) | Degradação do BESS (R\$ mi/ano) | Receita mínima de entrada (R\$ mil/MW·ano) |
|--------------------|--------------------|--------------------|--------------------|--------------------|
| 50 | 55 | 71,6 | 1,0 | 13 |
| 150 | 55 | 70,5 | 2,1 | 33 |
| 365 | 55 | 68,1 | 4,4 | 76 |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

As receitas no MCP e com hidrogênio são idênticas nos três casos, de modo que a frequência do despacho não altera a operação do lado mercantil. A única diferença está no custo de degradação do módulo LRCAP, e as curvas de custo de oportunidade marginal da Figura 4.6(b) são deslocadas em paralelo por exatamente $c^{deg} H^{cap} \Delta N^{ons}$: R\$ 43 mil/(MW·ano) entre 150 e 365 despachos e R\$ 63 mil/(MW·ano) entre 50 e 365 despachos, como previsto pela Equação (3.43). O efeito do ponto de conexão compartilhado mostrou-se, portanto, desprezível.

Em consequência, a frequência do despacho, embora desconhecida, não altera a potência ótima para a receita de referência e afeta apenas o limiar de entrada e o lucro. Como seu efeito é linear e pode ser calculado diretamente, sem simulação, essa incerteza pode ser incorporada à análise como um custo por MW contratado — por exemplo, como componente do lance mínimo —, sem a necessidade de cenários adicionais no modelo de operação.

### 4.3.6 Custo de degradação e dimensionamento

Esta subseção avalia duas hipóteses que poderiam alterar as conclusões anteriores: o custo de degradação do BESS e o dimensionamento do eletrolisador e do tanque de hidrogênio.

**Custo de degradação.** A Figura 4.7 e a Tabela 4.9 apresentam a curva de oferta para custos de degradação de R\$ 50, R\$ 100 e R\$ 200/MWh, os dois últimos próximos da faixa estimada a partir do custo de reposição dos módulos (Seção 3.5).

::: {custom-style="Legenda"}
Figura 4.7 – Curva de oferta no LRCAP para diferentes custos de degradação do BESS: (a) perda de lucro operacional esperado; (b) custo de oportunidade marginal; (c) potência ótima em função da receita fixa
:::

::: {custom-style="Figura"}
![](figuras/curva_oferta_degradacao.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

::: {custom-style="Legenda"}
Tabela 4.9 – Efeito do custo de degradação do BESS (receita fixa de R\$ 600 mil/(MW·ano))
:::

| Custo de degradação (R\$/MWh) | Potência ótima (MW) | Lucro esperado (R\$ mi/ano) | Receita mínima de entrada (R\$ mil/MW·ano) | Custo marginal do último MW (R\$ mil/MW·ano) |
|------------------|------------------|------------------|------------------|------------------|
| 50 | 55 | 68,1 | 76 | 895 |
| 100 | 55 | 63,7 | 149 | 881 |
| 200 | 52,5 | 54,9 | 295 | 854 |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

Quadruplicar o custo de degradação reduz o lucro em R\$ 13,2 milhões por ano e quase quadruplica a receita mínima de entrada, mas desloca a potência ótima em apenas 2,5 MW. A razão está na Figura 4.7(b): o custo maior eleva o custo de oportunidade na faixa inferior da curva, onde predomina o desgaste do módulo LRCAP, despachado diariamente; na faixa superior, porém, também torna mais caro o uso mercantil da bateria, que é justamente o uso perdido ao se contratar mais potência, e os dois efeitos praticamente se compensam. A decisão de quanto ofertar é, portanto, robusta ao custo de degradação, enquanto a decisão de participar e o lucro esperado são sensíveis a ele.

**Tamanho do eletrolisador.** A Figura 4.8 e a Tabela 4.10 comparam eletrolisadores de 10, 17,5 e 25 MW, mantida a usina FV de 50 MWp.

::: {custom-style="Legenda"}
Figura 4.8 – Curva de oferta no LRCAP para diferentes potências do eletrolisador: (a) perda de lucro operacional esperado; (b) custo de oportunidade marginal; (c) potência ótima em função da receita fixa
:::

::: {custom-style="Figura"}
![](figuras/curva_oferta_eletrolisador.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

::: {custom-style="Legenda"}
Tabela 4.10 – Efeito da potência do eletrolisador (receita fixa de R\$ 600 mil/(MW·ano))
:::

| Eletrolisador (MW) | Potência ótima (MW) | Lucro esperado (R\$ mi/ano) | H₂ vendido (t/ano) | Fator de capacidade do eletrolisador | Energia exportada (GWh/ano) |
|------------------|------------------|------------------|------------------|------------------|------------------|
| 10 | 50 | 60,4 | 850 | 0,53 | 28,4 |
| 17,5 | 55 | 68,1 | 1.029 | 0,37 | 19,4 |
| 25 | 57,5 | 73,5 | 1.175 | 0,30 | 11,9 |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

O tamanho do eletrolisador altera a forma da curva de oferta. Com 25 MW, o eletrolisador absorve durante o dia a maior parte da geração FV, e o módulo mercantil tem pouco a deslocar para a noite: o custo de oportunidade permanece em torno de R\$ 77 mil/(MW·ano) até 45 MW, e o ótimo para a receita de referência sobe para 57,5 MW. Com 10 MW, a geração FV excedente ao meio-dia é muito maior, a bateria mercantil é valiosa desde o mínimo regulatório e o custo de oportunidade já parte de R\$ 330 mil/(MW·ano); o ótimo cai para 50 MW. A relação entre as potências do eletrolisador e da usina FV, herdada da planta da UNIFEI (0,35), é, portanto, uma hipótese de projeto com efeito relevante sobre a curva de oferta, e não apenas um parâmetro de escala.

**Tamanho do tanque.** No caso com contrato de 3 t/dia, a ampliação do tanque de hidrogênio de 2 t para 10 t reduz o déficit anual de entrega, com 55 MW contratados, de 40 t para 11 t, e eleva o lucro operacional esperado em R\$ 1,6 milhão por ano. O tanque maior guarda o hidrogênio produzido nos dias de alta irradiância para os dias nublados, função que, com o tanque de 2 t, cabia ao módulo mercantil do BESS. Por isso, o custo de oportunidade marginal entre 30 e 50 MW cai de R\$ 100–169 mil para R\$ 85–126 mil/(MW·ano), e o lance mínimo para construir o BESS cai de R\$ 795 mil para R\$ 765 mil/(MW·ano) (Tabela 4.4). A potência ótima para a receita de referência permanece em 55 MW. Com 60 MW contratados, porém, os dois tanques produzem o mesmo resultado: sem o módulo mercantil, o eletrolisador opera apenas nas horas de sol, a entrega de 3 t/dia exige cerca de 9,4 h diárias na potência nominal, e raramente sobra hidrogênio para guardar. Esse efeito do tanque só aparece com a fronteira da relaxação linear (Subseção 4.1): com a condição cíclica semanal, o tanque era esvaziado no início de cada semana e sua ampliação não tinha efeito.

### 4.3.7 Sensibilidade à receita fixa e ao preço do hidrogênio

Como a receita fixa do LRCAP e o preço do hidrogênio não possuem referências consolidadas, o caso determinístico de 2025 foi resolvido para 48 combinações desses parâmetros: seis valores de receita fixa, entre R\$ 330 mil e R\$ 2,33 milhões/(MW·ano), e oito preços de hidrogênio, entre R\$ 10 e R\$ 45/kg. Os valores de receita fixa foram escolhidos a partir das quatro referências discutidas na Seção 3.5, sintetizadas no Quadro 4.1.

::: {custom-style="Legenda"}
Quadro 4.1 – Referências para a faixa de receita fixa avaliada
:::

| Receita fixa (R\$/MW·ano) | Referência | Observação |
|------------------|------------------------------------|------------------------------------|
| 330 mil | Primeiro leilão do MACSE, Itália, 30/09/2025: preço médio de € 12.959/(MWh·ano) para sistemas de baterias de íons de lítio, contratos de 15 anos (TERNA, 2025) | Convertido para um sistema de 4 h (€ 51.836/(MW·ano)) com a PTAX de 30/09/2025 (R\$ 6,2396/€), o que resulta em R\$ 323 mil; arredondado na grade |
| 830 mil | Leilão nº 3/2026-ANEEL (LRCAP), 20/03/2026: 501,3 MW de termelétricas existentes a óleo e biodiesel, preço médio de R\$ 831.251,52/(MW·ano), deságio de 50,1% (CCEE, 2026c) | Usinas existentes, sem investimento novo: piso de referência para o produto potência |
| 1,0 e 1,5 mi | CAPEX de referência de sistemas de baterias de R\$ 5.000 a 6.000/kW (BRASIL; EPE, 2025) | A anualização do CAPEX a 10% a.a. em 15 anos resulta em R\$ 657 mil a R\$ 789 mil/(MW·ano); os valores da grade acrescentam O&M, encargos, tributos e reposição de módulos para manter a disponibilidade |
| 2,33 mi | Leilão nº 2/2026-ANEEL (LRCAP), 18/03/2026: 18,97 GW de termelétricas a gás natural, biometano e carvão e ampliações de hidrelétricas, novas e existentes, preço médio de R\$ 2,334 milhões/(MW·ano), deságio de 5,5% (CCEE, 2026b) | Custo de atender à mesma necessidade de potência com a expansão térmica e hidrelétrica: teto de referência |

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

O valor de R\$ 600 mil/(MW·ano), adotado no caso de referência, situa-se, portanto, abaixo do preço obtido por usinas existentes no LRCAP de 2026 e abaixo do custo anualizado de investimento em baterias, e deve ser interpretado como hipótese conservadora para a receita fixa. Cada combinação foi resolvida pelo método de Benders, com *gap* máximo de 0,11%. Os resultados são apresentados na Figura 4.9.

::: {custom-style="Legenda"}
Figura 4.9 – Potência ótima no LRCAP e lucro anual em função da receita fixa e do preço do hidrogênio (caso determinístico de 2025)
:::

::: {custom-style="Figura"}
![](figuras/mapa_sensibilidade_potencia_lucro.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

Em nenhuma das combinações é vantajoso deixar de participar do leilão: a potência ótima varia entre 43,8 e 60 MW. Com receita fixa igual ou superior a R\$ 1,5 milhão/(MW·ano), o ótimo é contratar toda a potência do BESS para qualquer preço de hidrogênio da faixa avaliada. Para preços de hidrogênio de até R\$ 20/kg, o ótimo também é contratar toda a potência, independentemente da receita fixa, pois o valor da energia no eletrolisador, de até R\$ 336/MWh, já não justifica reservar o BESS para abastecê-lo. A região em que o ótimo é inferior a 60 MW concentra-se nas combinações de receita fixa baixa e preço de hidrogênio alto, e sua fronteira se desloca para preços maiores à medida que a receita fixa aumenta: a potência ótima deixa de ser 60 MW a partir de R\$ 25/kg com receita de R\$ 330 mil, de R\$ 30/kg com R\$ 600 mil, de R\$ 40/kg com R\$ 830 mil e de R\$ 45/kg com R\$ 1,0 milhão/(MW·ano).

O fator de capacidade do eletrolisador acompanha esse comportamento: com hidrogênio a R\$ 10/kg, o eletrolisador opera apenas com a geração FV que não encontra uso mais valioso no MCP (fator de capacidade de 0,17); a partir de R\$ 25/kg, ele absorve praticamente toda a geração FV (0,34) e, quando parte do BESS permanece no lado mercantil, também opera à noite (até 0,46).

Para avaliar o custo de uma decisão tomada sob incerteza quanto a esses parâmetros, calculou-se o arrependimento de contratar 54,4 MW — o ótimo do caso de referência —, definido como a diferença entre o lucro ótimo de cada combinação e o lucro obtido com essa potência (Figura 4.10).

::: {custom-style="Legenda"}
Figura 4.10 – Arrependimento de contratar 54,4 MW em função da receita fixa e do preço do hidrogênio (caso determinístico de 2025)
:::

::: {custom-style="Figura"}
![](figuras/mapa_sensibilidade_arrependimento.png){width=16cm}
:::

::: {custom-style="Fonte"}
Fonte: elaborado pelo autor.
:::

O arrependimento é nulo ou inferior a R\$ 0,4 milhão por ano na vizinhança do caso de referência (receita de R\$ 600 mil e hidrogênio entre R\$ 30 e R\$ 45/kg), mas cresce para até R\$ 11,6 milhões por ano quando a receita fixa é elevada, situação em que contratar toda a potência seria ótimo. O arrependimento é assimétrico: subestimar a potência a contratar custa mais do que superestimá-la. Com receita de R\$ 330 mil e hidrogênio a R\$ 45/kg, por exemplo, contratar 54,4 MW em vez do ótimo de 43,8 MW custa R\$ 2,5 milhões por ano, enquanto, com receita de R\$ 1,5 milhão e hidrogênio a R\$ 35/kg, contratar 54,4 MW em vez de 60 MW custa R\$ 4,4 milhões por ano. Diante da incerteza sobre a receita fixa — que, no leilão, é o próprio lance —, essa assimetria favorece decisões de contratação mais próximas da potência máxima.

Os resultados das Figuras 4.5 e 4.6 são coerentes com a curva de oferta da Subseção 4.3.3, obtida com o modelo estocástico: a potência ótima para R\$ 600 mil e hidrogênio a R\$ 35/kg (54,4 MW no caso determinístico) e a receita a partir da qual se oferta toda a potência (cerca de R\$ 900 mil, contra a fronteira entre R\$ 830 mil e R\$ 1,0 milhão no mapa) são compatíveis entre as duas análises.

## 4.4 Síntese

Os resultados permitem distinguir duas decisões e hierarquizar os fatores que determinam cada uma.

**Proponente que precisa construir o BESS (resultado principal):**

a) **a oferta é do tipo "tudo ou nada":** abaixo do lance mínimo, o BESS não é construído; acima dele, ofertam-se 57,5 a 60 MW, praticamente toda a potência da bateria;

b) **o lance mínimo é de cerca de R\$ 855 mil/(MW·ano) no caso central** e varia de R\$ 780 mil a R\$ 1,25 milhão/(MW·ano) conforme o custo de investimento, a taxa de desconto e a degradação; ele é bem aproximado pelo custo anual equivalente do BESS por MW acrescido do custo de degradação imposto pelo despacho do ONS (Equação (3.44)) e é próximo do preço obtido por termelétricas existentes no LRCAP de 2026;

c) **as hipóteses sobre o hidrogênio alteram pouco o lance mínimo** (de R\$ 765 mil a R\$ 855 mil/(MW·ano); a maior redução ocorre com o contrato firme de 3 t/dia, em que a bateria mercantil restante reduz o déficit de entrega), mas determinam a viabilidade do empreendimento como um todo: com os parâmetros adotados, nenhum caso se paga com investimento central, e o preço de equilíbrio do hidrogênio no caso de referência é de cerca de R\$ 68/kg;

d) **sem a receita do leilão, o BESS agrega pouco** (R\$ 9,7 milhões por ano, contra custo anual equivalente de R\$ 46,8 milhões): é o LRCAP que pode viabilizar a bateria, e a receita de referência de R\$ 600 mil/(MW·ano) é insuficiente para isso.

**Proponente que dispõe do BESS:**

e) **participar do leilão é robusto:** até cerca de 37,5 MW, o custo de oportunidade marginal situa-se entre R\$ 77 mil e R\$ 111 mil/(MW·ano) nos casos de contrato de hidrogênio e de importação, e a receita mínima de entrada permanece abaixo de R\$ 300 mil/(MW·ano) em todos os casos;

f) **a quantidade a ofertar acima de cerca de 40 MW depende do hidrogênio e do dimensionamento:** o custo de oportunidade do último MW varia de R\$ 172 mil a cerca de R\$ 2,0 milhões/(MW·ano) conforme o contrato de fornecimento, e a potência ótima varia de 50 a 57,5 MW com o tamanho do eletrolisador, porque o módulo mercantil do BESS tem como principal função abastecer o eletrolisador fora do período solar;

g) **a regra de suprimento do eletrolisador é a hipótese de maior efeito sobre o lucro:** permitir a importação de energia eleva o lucro em cerca de 30% e torna o BESS desnecessário para a produção de hidrogênio;

h) **o custo de degradação e a frequência do despacho afetam o lucro e o limiar de entrada, mas pouco a potência ótima**, e a receita fixa e o preço do hidrogênio definem a fronteira entre contratar parte ou toda a potência, com arrependimento assimétrico que favorece contratar mais.

**Método e incertezas:**

i) **a variação histórica de preço e de geração e a aproximação da decomposição têm efeito pequeno sobre a decisão:** os modelos determinístico e estocástico conduzem à mesma potência ótima, o VSS é nulo e o EVPI é de 0,2% do lucro esperado. A condição cíclica semanal da decomposição é inofensiva sem contrato de hidrogênio, mas, com contrato firme, subestima o lucro em até 4% (9% com o tanque de 10 t); com os estados de fronteira da relaxação linear do ano, a decomposição fica, na maior parte das avaliações, a menos de 0,1% do ótimo anual.

Em conjunto, os resultados indicam que, para um BESS novo, a arbitragem relevante não se dá entre o LRCAP e o mercado de curto prazo na operação, mas na decisão de investimento: a bateria é construída para o leilão, e o lance é determinado pelo seu custo. A produção de hidrogênio, por sua vez, define se o empreendimento híbrido como um todo é viável, e as condições de sua comercialização — preço, volume e critério de qualificação — são as informações prioritárias para essa avaliação.

## REFERÊNCIAS

::: {custom-style="Referencia"}
BRASIL. Ministério de Minas e Energia; EPE – EMPRESA DE PESQUISA ENERGÉTICA. **Caderno de parâmetros de custos**: geração e transmissão – PDE 2035. Brasília: MME/EPE, nov. 2025.
:::

::: {custom-style="Referencia"}
CCEE – CÂMARA DE COMERCIALIZAÇÃO DE ENERGIA ELÉTRICA. **InfoLeilão Expresso**: 04º LRCAP 2026 – Leilão nº 2/2026-ANEEL. São Paulo: CCEE, mar. 2026b. Disponível em: https://www.ccee.org.br. Acesso em: 3 out. 2026.
:::

::: {custom-style="Referencia"}
CCEE – CÂMARA DE COMERCIALIZAÇÃO DE ENERGIA ELÉTRICA. **InfoLeilão Expresso**: 05º LRCAP 2026 – Leilão nº 3/2026-ANEEL. São Paulo: CCEE, mar. 2026c. Disponível em: https://www.ccee.org.br. Acesso em: 3 out. 2026.
:::

::: {custom-style="Referencia"}
TERNA. **Terna completes first MACSE auction**: 10 GWh of energy storage capacity awarded. Roma: Terna S.p.A., 1 out. 2025. Comunicado de imprensa. Disponível em: https://www.terna.it. Acesso em: 3 out. 2026.
:::
