# Verificação regulatória das hipóteses de rede e mercado (cap3, Seções 3.5 e 3.8.4)

Data da verificação: 18/11/2026. Regra adotada: só se afirma o que foi lido no texto de uma fonte; o que não foi lido consta como **não encontrado** ou **não verificado**, sem preenchimento de memória.

## 0. Limitações de acesso (leia primeiro)

- Todo o domínio `www2.aneel.gov.br` (REN 1.000/2021, REN 1.162/2026 e demais RENs) respondeu **HTTP 403** a acessos automatizados, também por `curl`. O texto oficial das RENs da ANEEL **não** foi lido. O domínio `planalto.gov.br` não resolveu (DNS bloqueado) e `leis.org` também não, de modo que as leis e decretos não foram lidos.
- A REN 1.000/2021 foi lida numa cópia consolidada **secundária** (legisweb), não no texto oficial. Os trechos dela aparecem marcados como *fonte secundária*.
- A REN 1.162/2026 **não foi lida**. Tudo o que a respeito dela aparece abaixo vem de páginas oficiais da ANEEL que não trazem o corpo da norma, ou de notícias (secundárias), e está marcado como tal.
- Fontes lidas integralmente por extração de texto dos PDFs: Portaria Normativa MME nº 136/2026 (gov.br/mme) e os cadernos de Regras de Comercialização da CCEE, módulos 02 (Medição Contábil, v. 2026.5.2), 09 (Encargos, v. 2026.6.4) e 20 (Votos e Contribuição Associativa, v. 2026.2.0).

## 1. Posto tarifário ponta / fora de ponta

**Fonte secundária** (cópia consolidada da REN ANEEL nº 1.000/2021, Art. 2º, inciso XXXVIII; o texto oficial retornou 403): <https://www.legisweb.com.br/legislacao/?id=490988>

- Inciso XXXVIII: "posto tarifário: período em horas para aplicação das tarifas de forma diferenciada ao longo do dia".
- Alínea a (ponta): "posto tarifário ponta: período composto por 3 horas diárias consecutivas definidas pela distribuidora", conforme a curva de carga do sistema e aprovado pela ANEEL, sem aplicação a sábados, domingos e feriados nacionais listados.
- Alínea b (intermediário): "posto tarifário intermediário: período de duas horas, sendo uma hora imediatamente anterior e outra imediatamente posterior ao horário de ponta"; a mesma alínea limita o posto intermediário ao grupo B.
- Alínea c: "posto tarifário fora de ponta: período composto pelo conjunto das horas diárias consecutivas e complementares àquelas definidas nos postos ponta".
- Definições de grupo (Art. 2º): grupo A = tensão ≥ 2,3 kV; grupo B = tensão < 2,3 kV.

Conclusão: os postos são definidos por distribuidora para a aplicação de tarifas ao consumo (modalidades horárias dos grupos A e B). Nenhuma das definições lidas menciona geradores ou central geradora. Que o posto não se aplica a geradores é inferência da ausência no texto, não regra expressa.

## 2. TUST e TUSD de geração

**Não encontrado em texto oficial.** Do que foi lido (fonte secundária, REN 1.000/2021):

- Art. 2º, XLIX, b (TUSD): "valor monetário unitário determinado pela ANEEL, em R$/MWh (reais por megawatt-hora) ou em R$/kW (reais por quilowatt)".
- Art. 109, § 7º: "TUSDG Fio B = a parcela da TUSD aplicável a geradores conforme nível de tensão", em "Reais por quilowatt (R$/kW)". A definição lida de TUSDg Fio B **não** traz qualificador de posto tarifário, ao contrário da TUSD Fio B do consumo, definida "no posto tarifário fora de ponta".
- Art. 216, caput (lido na leitura completa, seção 7): modalidade geração "é caracterizada por tarifas de demanda, independentemente das horas de utilização do dia", aplicada à central geradora. Sem posto tarifário.
- Regras de MUST/MUSD e valores da TUST: não encontrados.

Sobre TUST (rede básica): a cobrança por montante de uso em R$/kW·mês **não foi confirmada em texto oficial**. A cobrança em R$/kW consta do texto secundário sobre a TUSDg, e a Portaria MME 136/2026, art. 9º, § 13, exige "contratação de Montantes de Uso do Sistema de Transmissão ou de Distribuição" (seção 6).

## 3. Armazenamento (BESS): TUST/TUSD

**Texto da REN 1.162/2026 não lido. Não há confirmação oficial de se a cobrança é só na injeção ou nas duas parcelas.**

O que as fontes lidas sustentam:

- Página oficial da ANEEL, "Armazenamento de Energia: ANEEL encerra Consulta Pública e aprova regras sobre a cobrança pelo uso da rede", publicada em 02/06/2026 (modificada em 03/07/2026): <https://www.gov.br/aneel/pt-br/assuntos/noticias/2026/armazenamento-de-energia-aneel-encerra-consulta-publica-e-aprova-regras-sobre-a-cobranca-pelo-uso-da-rede>. Só o subtítulo foi legível: "Voto-Vista do Diretor Willamy Frota foi aprovado pela maioria do colegiado" e "O assunto fez parte da segunda fase da Consulta Pública nº 39/2023". O corpo da notícia não foi obtido.
- Página oficial da ANEEL sobre SAE colocalizado (publicada em 20/07/2026): <https://www.gov.br/aneel/pt-br/centrais-de-conteudos/manuais-modelos-e-instrucoes/armazeamento-de-energia/sae-colocalizado-a-centrais-geradoras>. Diz: "A ANEEL, em 2 de junho de 2026, regulamentou procedimentos e requisitos para inclusão de sistemas de armazenamento em centrais geradoras" e "A Resolução Normativa 1.162/2026 inseriu o art. 16-A na Resolução Normativa 1.071/2023". Não trata de TUST/TUSD.
- Fontes **secundárias**, não verificadas na norma e **conflitantes entre si**: o Cenário Energia (<https://cenarioenergia.com.br/2026/06/02/aneel-aprova-marco-de-baterias-com-tarifacao-dupla-para-sistemas-sem-despacho-do-ons/>) relata, por resumo de busca, "tarifação dupla" (consumo e injeção) para sistemas sem despacho do ONS e isenção de encargos de rede na fase de carregamento para os vinculados à operação centralizada; um resultado do Canal Solar de 27/07/2026 diz que a regulação "permanece sem definição". Um documento da EPE (FAQ do LRCAP) foi citado por resumo de busca como dizendo que a REN 1.162/2026 incluiu o art. 149-A na REN 1.000/2021 e que, para o LRCAP, "deve ser considerada apenas a parcela de geração (MUSTg)". Não li o texto desses documentos.
- Texto oficial lido: Portaria MME 136/2026, art. 9º, §§ 6º a 8º e 13 (seção 6), que liquida a carga e a injeção ao PLD na CONCAP e exige contratar montantes de uso "para permitir a descarga e a recarga total do SAE, conforme regulamentação da ANEEL".

O art. 149-A da REN 1.000/2021 não consta da cópia consolidada lida (seção 7).

## 4. Importação de energia da rede: encargos de consumo

**Não encontrado em texto oficial** para TUST de consumo, CDE, Proinfa e ICMS (leis e decretos inacessíveis; REN da ANEEL com 403). Nenhuma dependência horária foi verificada.

Do que foi lido, ESS: CCEE, Regras de Comercialização, módulo 09 Encargos v. 2026.6.4 (Despacho ANEEL nº 3.382, de 27/08/2026), item 1.1.7 "Forma de rateio dos encargos":
"Rateado na proporção do consumo atendido pelo SIN (Consumo atendido pelo SIN: consumo total subtraído da energia elétrica autoproduzida no SIN, ...)". Não há, nessa tabela, dependência de posto horário. URL: <https://www.ccee.org.br/documents/80415/36296802/09%20-%20Encargos_2026.6.4_JUN.pdf/ac1beaf1-21e9-e607-c2a8-1feeb2d57165>

A Portaria MME 136/2026, art. 9º, § 4º, II, k, inclui entre os custos da receita fixa "os encargos setoriais pela energia consumida e injetada, conforme regulamentação da ANEEL", sem dizer quais.

## 5. Liquidação de gerador no MCP (CCEE)

- **Perdas na Rede Básica**: módulo 02 Medição Contábil v. 2026.5.2, item 1.1.5: "essas perdas são absorvidas na proporção de 50% para os consumidores e 50% para os geradores participantes do rateio de perdas da Rede Básica". Item 1.1.6: "As usinas não interligadas à Rede Básica, à exceção daquelas consideradas quando do estabelecimento dos montantes dos Contratos Iniciais, deverão ser desconsideradas no rateio das perdas elétricas apuradas na Rede Básica" e "todas as parcelas de carga participam do rateio de perdas da Rede Básica". Cálculo: "O Fator de Rateio de Perdas de Geração é calculado de modo a contemplar a metade das Perdas da Rede Básica ao gerador" (fórmula em figura). URL: <https://www.ccee.org.br/documents/80415/36296900/02%20-%20Medi%C3%A7%C3%A3o%20Cont%C3%A1bil_2026.5.2_MAI.pdf/b78996a2-5271-82ad-28b3-1889768896db>. Ajuste ao centro de gravidade: **não encontrado** no texto extraído do módulo 02 (a expressão não aparece).
- **Perdas internas**: módulo 02 trata de "perdas internas" por usina com abatimento (F_PDI), e a mesma matéria aparece no módulo 09 (ESS). Não verifiquei se isso se aplica a este projeto.
- **Quem paga o ESS**: módulo 09, tabela de rateio acima: rateio sobre o consumo atendido pelo SIN, para restrição de operação, compensação síncrona, reativos, importação, segurança energética e deslocamento hidráulico. Geradores aparecem no módulo como **recebedores** de encargos (ex.: restrição de operação para eólicas e solares). Exceção literal: "referente ao encargo de deslocamento hidráulico por inflexibilidade, seu custo será pago pela usina que deu origem". O módulo 09 não menciona armazenamento/baterias (não encontrado).
- **Contribuição associativa**: módulo 20 Votos e Contribuição Associativa v. 2026.2.0, "Este módulo envolve: Todos os agentes da CCEE", categorias "Geração, Distribuição, Comercialização e Consumo"; "A contribuição associativa mensal terá como componentes: i) parcela mínima ... de mesmo valor para todos os agentes, e ii) parcela adicional ... proporcional ao volume de energia contabilizado pelo agente nos 12 (doze) meses anteriores". Logo, agentes da categoria Geração pagam. Valores em R$: **não encontrado**. URL: <https://www.ccee.org.br/documents/80415/36295943/20%20-%20Votos%20e%20Contribui%C3%A7%C3%A3o%20Associativa_2026.2.0_FEV.pdf/0f1b2f65-4d49-a0db-9e89-a1056146e21c>
- **TFSEE (taxa de fiscalização da ANEEL)**: não encontrado.

## 6. Portaria Normativa MME nº 136, de 1º de junho de 2026

Fonte: <https://www.gov.br/mme/pt-br/acesso-a-informacao/legislacao/portarias/2026/portaria-normativa-mme-n-136-2026.pdf> (texto extraído do PDF oficial). Observações: (i) a expressão "custos de conexão e de uso do sistema" **não existe com essas palavras**; o texto traz itens separados (§ 4º, II, d e e). (ii) Os §§ 5º a 8º e o § 13 de que se trata são os do **art. 9º**; no art. 4º, os §§ 5º a 8º tratam de ciclo completo, PMI e profundidade de descarga.

**Art. 9º, § 4º, II** (a receita fixa "deverá abranger, entre outros"):
- "d) os custos de conexão ao Sistema de Transmissão e Distribuição;"
- "e) o custo de Uso do Sistema de Transmissão ou Distribuição;"
- "h) tributos e encargos diretos e indiretos;"
- "k) os encargos setoriais pela energia consumida e injetada, conforme regulamentação da ANEEL."

**Art. 9º, § 1º**: "A ANEEL deverá disciplinar as regras aplicáveis para o acesso ao sistema de transmissão e de distribuição de energia elétrica, compreendendo os aspectos de conexão e de uso, assim como outros ajustes regulatórios necessários à integração dos SAEs ao sistema elétrico."

**Art. 9º, § 5º, IV**: "a receita fixa associada à contratação dos sistemas de armazenamento ..., prevista pelo vendedor, seja suficiente para remunerar integralmente todo e qualquer uso que o ONS fizer dos empreendimentos vencedores destes Leilões com observância dos compromissos de disponibilidade definidos no art. 4º, sem geração de receitas adicionais fora do CRCAP."

**Art. 9º, § 6º**: "A energia utilizada no carregamento e a injetada pelos SAEs serão liquidadas no Mercado de Curto Prazo - MCP ao Preço da Liquidação das Diferenças - PLD, e os resultados positivos e negativos dessa liquidação serão destinados à Conta de Potência para Reserva de Capacidade - CONCAP, observado o limite de custeio estabelecido no § 8º."

**Art. 9º, § 7º**: "O montante de energia utilizada no carregamento a ser custeada pela CONCAP ficará limitado ao quociente entre a energia injetada e a eficiência total de que trata o inciso VI do art. 7º."

**Art. 9º, § 8º**: "O montante de energia utilizada no carregamento que exceder aquele de que trata o § 7º será custeado pelo empreendedor."

**Art. 9º, § 9º**: "O custeio da energia relativa às perdas elétricas do sistema de interesse restrito do PMI até o barramento da subestação de conexão do empreendimento ao SIN é de exclusiva responsabilidade do empreendedor."

**Art. 9º, § 13**: "É exigida a contratação de Montantes de Uso do Sistema de Transmissão ou de Distribuição para permitir a descarga e a recarga total do SAE, conforme regulamentação da ANEEL."

**Art. 4º, § 1º**: "Poderão participar novos SAEs: I - que venham a ser conectados diretamente ao ponto de conexão do SIN, sem compartilhamento de instalações de interesse restrito com outros agentes; ou II - que venham a ser instalados no mesmo ponto de conexão ao SIN de outros agentes, compartilhando as respectivas instalações de interesse restrito."

**Art. 4º, § 5º**: "Considera-se ciclo completo a soma de um ou mais ciclos parciais cujo total de energia descarregada do SAE corresponda à potência contratada no [CRCAP], em MW, multiplicada por quatro horas, consideradas as perdas declaradas e verificadas no Ponto de Medição Individual - PMI."

**Art. 4º, § 6º**: "O Ponto de Medição Individual - PMI corresponde ao primeiro ponto do sistema de interesse restrito no qual é possível a identificação individualizada da injeção e do consumo do empreendimento, ..."

**Art. 4º, § 7º**: "O PMI poderá não coincidir com o ponto de conexão conforme configuração das instalações e critérios do ONS e CCEE."

**Art. 4º, § 8º**: "A totalidade da potência efetivamente contratada deverá ser integralmente disponibilizada para despacho do ONS, sendo a definição da profundidade de descarga (Depth of Discharge - DoD) de exclusiva responsabilidade do empreendedor."

**Art. 4º, § 13**: "Os SAEs deverão manter disponíveis e de forma contínua os recursos estabelecidos na Nota Técnica do ONS e da EPE referente aos Requisitos Técnicos Mínimos para a Conexão de Sistemas de Armazenamento de Energia via Baterias e suas revisões, inclusive quanto às funcionalidades de grid-forming, ..."

**Art. 5º**: "Pela disponibilidade da potência contratada, o titular do empreendimento fará jus à Receita Fixa, em R$/ano, a ser paga em doze parcelas mensais, ..."; § 2º: "Fica alocado ao empreendedor o risco relativo à incerteza de despacho do seu empreendimento pelo ONS, ..."

## 7. Art. 149-A e regras de geração na REN 1.000/2021 (cópia consolidada, fonte secundária)

Fonte: <https://www.legisweb.com.br/legislacao/?id=490988> (cópia com alterações até a REN 1.174/2026, de 27/10/2026; lida quase toda, com duas lacunas de ~58 caracteres e fórmulas em imagem não lidas).

- **Art. 149-A: não existe nessa cópia** (o art. 149 é seguido direto pelo art. 150). A cópia não mostra nenhuma alteração da REN 1.162/2026 na REN 1.000. Isso contradiz o que um documento da EPE teria dito (resumo de busca) e é coerente com a página da ANEEL, que só cita o art. 16-A da REN 1.071/2023. Não resolvo a divergência: só o texto oficial da REN 1.162/2026 (DOU) resolve.
- **Art. 216, caput**: a modalidade tarifária geração "é caracterizada por tarifas de demanda, independentemente das horas de utilização do dia" e se aplica à central geradora. Isso responde à pergunta 2 (por demanda, sem diferenciação por posto), mas em fonte secundária.
- **Art. 149, caput**: "A demanda contratada por central geradora deve ser o valor por ela declarado de sua máxima potência injetável".
- **Art. 150**: demanda de importador/exportador "sem diferenciação por posto tarifário".
- **Art. 127, § 3º**: gerador despachado centralizadamente pelo ONS firma também CUST com o ONS.
- **Art. 156**: cita o MUST contratado pela supridora, só sobre prazo; nenhum valor ou fórmula de MUST/TUST foi encontrado. **MUSD, MUSTg e "SAE": ausentes** do texto lido.
- **Encargos (CDE, Proinfa) sobre energia consumida por gerador ou armazenador**: nada encontrado na REN 1.000.
- Armazenamento na REN 1.000 aparece só em regras de micro e minigeração (incluídas pela REN 1.059/2023), sem cobrança específica.

## 8. Tabela-resumo

| Item | O que a fonte diz | URL | Muda hipótese do modelo? |
|---|---|---|---|
| 1. Postos ponta/fora de ponta | REN 1.000, art. 2º, XXXVIII (cópia secundária): ponta = 3 h diárias consecutivas definidas pela distribuidora; fora de ponta = horas complementares; intermediário só no grupo B. Sem menção a geradores. | <https://www.legisweb.com.br/legislacao/?id=490988> | Não, desde que a TUST de geração seja anual. Aplicável ao consumo, não confirmado para geração. Texto oficial não lido (403). |
| 2. TUST/TUSD de geração | REN 1.000, art. 216 (secundária): modalidade geração "caracterizada por tarifas de demanda, independentemente das horas de utilização do dia"; art. 149: demanda contratada = máxima potência injetável. Valor da TUST de rede básica: não confirmado. | idem | Não contradiz a TUST em R$/kW·mês sem posto horário (3.5). Falta confirmação oficial. |
| 3. BESS: injeção e recarga | REN 1.162 não lida. Portaria art. 9º, § 13: contratar MUST/MUSD "para permitir a descarga e a recarga total". Fontes secundárias divergem (dupla cobrança × só geração). Art. 149-A não consta da cópia consolidada da REN 1.000. | URLs da seção 3 | Sim, em aberto. A sensibilidade "TUST de consumo também" (3.8.4) é plausível, e a base de cálculo deve ser confirmada na REN 1.162. |
| 4. Importação da rede | TUST consumo, CDE, Proinfa, ICMS: não encontrado. ESS rateado no consumo atendido pelo SIN, sem dependência horária no módulo 09. | CCEE módulo 09 | O adicional de R$ 250/MWh continua sem fonte. Já é declarado hipótese do autor em 3.5. |
| 5. Perdas na rede básica | 50% consumo, 50% geração, só para usinas na Rede Básica; centro de gravidade não encontrado. | CCEE módulo 02 | Sim: o modelo não tem fator de perdas. O efeito é sobre a energia de usina ligada à Rede Básica. |
| 5. ESS | Rateado no consumo atendido pelo SIN; geração recebe. Exceção: deslocamento por inflexibilidade. | CCEE módulo 09 | A venda ao MCP não paga ESS. A compra da rede e a recarga do BESS pagam, como consumo. Hipótese do modelo mantida para venda. |
| 5. Contribuição CCEE | Todos os agentes pagam, inclusive geração (parcela mínima + adicional pelo volume). Valor não encontrado. | CCEE módulo 20 | Item não modelado (3.5/3.8.2 já avisam que o lance é piso). Confirma a omissão. |
| 6. Portaria 136/2026 | art. 9º, § 4º, II, d, e, k: conexão, uso e "encargos setoriais pela energia consumida e injetada" fazem parte da RF. § 6º: carga e injeção ao PLD na CONCAP. §§ 7º/8º: limite de custeio. § 9º: perdas até a subestação são do empreendedor. | gov.br/mme (seção 6) | §§ 6º-8º coincidem com a modelagem de cap3. Novidades: § 9º (perdas do PMI) não está no modelo; encargos setoriais já declarados fora. |
