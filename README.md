# Otimização da Operação de um Sistema Híbrido PV-BESS com Produção de Hidrogênio Verde

**Arbitragem entre o Leilão de Reserva de Capacidade (LRCAP) e o Mercado de Curto Prazo (MCP)**

Repositório do modelo de otimização da dissertação de mestrado. O modelo é um MILP
implementado em Python/[Pyomo](https://www.pyomo.org/) e resolvido com o
[HiGHS](https://highs.dev/) (gratuito e de código aberto).

```
 Lado mercantil (operado pelo empreendedor)
   PV ────────────┐
   BESS mercantil ◄┼─► Eletrolisador ─► Tanque H₂ ─► venda de H₂
                   └─► exportação ao MCP (PLD) ──┐
                                                 ├─► ponto de conexão compartilhado ◄─► SIN
 BESS módulo LRCAP ◄─► despacho do ONS ──────────┘   (receita fixa; energia liquidada na CONCAP)
```

As regras do LRCAP seguem a **Portaria Normativa MME nº 136/2026** (LRCAP de 2026 —
Armazenamento). O ponto central: a potência contratada é operada pelo ONS e não pode
gerar receita no MCP (art. 9º §5º, IV e §6º). Por isso a arbitragem é modelada como a
**divisão do BESS** entre um módulo LRCAP e um módulo mercantil. Detalhes em
`docs/formulacao.md`.

## Estrutura

```
config/caso_base.yaml      parâmetros do caso (valores PLACEHOLDER — substituir por dados reais)
config/itajuba_2025.yaml   mesmo caso com PLD SE/CO e PV de Itajubá (requer data/ gerado pelo importador)
docs/formulacao.md         formulação matemática completa (conjuntos, parâmetros, variáveis, restrições)
src/pvbess_h2/
  parametros.py            leitura/validação do YAML
  dados.py                 séries de entrada (PV, PLD, despacho do ONS) — reais via CSV ou sintéticas
  modelo.py                construção do modelo Pyomo e chamada do solver
  resultados.py            série horária de resultados, indicadores e gráfico
  importacao.py            leitura dos formatos da CCEE e do PVGIS
  decomposicao.py          Benders com cortes reforçados (P_cap no mestre, semanas nos subproblemas)
scripts/
  rodar_caso.py            resolve um caso e salva CSV + indicadores + gráfico em resultados/
  varredura_lrcap.py       sensibilidade: lucro × potência contratada no LRCAP
  importar_dados.py        converte CSVs brutos da CCEE (PLD) e do PVGIS (PV) para data/
  anual_benders.py         ano completo por decomposição de Benders (blocos semanais em paralelo)
tests/                     testes (modelo, importação de dados, decomposição)
```

## Como rodar

```bash
pip install -r requirements.txt
python scripts/rodar_caso.py                     # caso base (7 dias)
python scripts/varredura_lrcap.py --passos 11    # curva de arbitragem LRCAP x MCP
python scripts/anual_benders.py                  # ano completo de Itajubá (≈ 75 s em 4 núcleos)
python -m pytest                                 # testes
```

Para criar um novo cenário, copie `config/caso_base.yaml` (ex.: `config/cenario_h2_barato.yaml`),
altere os parâmetros e rode `python scripts/rodar_caso.py config/cenario_h2_barato.yaml`.
Os resultados vão para `resultados/<nome_do_cenario>/`.

### Usando dados reais — caso Itajubá (MG), submercado SE/CO

1. **PLD horário** — [dados abertos da CCEE](https://dadosabertos.ccee.org.br), conjunto
   "PLD horário": baixe o CSV do ano (ex.: 2025).
2. **Geração PV** — [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/pt/), aba *Dados horários*:
   lat. `-22.4256`, long. `-45.4528`, marque *Potência FV* com 1 kWp, perdas 14%,
   inclinação/azimute otimizados, último ano disponível; baixe em CSV.
3. Converta para o formato do modelo (o PV é reposicionado no ano do PLD e passado para UTC-3):

   ```bash
   python scripts/importar_dados.py --pld pld_horario_2025.csv --submercado SE \
       --pv Timeseries_-22.426_-45.453_*.csv --ano 2025
   python scripts/rodar_caso.py config/itajuba_2025.yaml
   ```

Formatos aceitos diretamente pelo modelo (para outras fontes):
`timestamp,pld`, `timestamp,fator_capacidade` e, para o despacho do ONS,
`timestamp,descarga_pu,recarga_pu` (em `lrcap.despacho_ons.arquivo`).

## Resultados — Itajubá (MG), ano de 2025

PLD horário SE/CO de 2025 (CCEE), PV do PVGIS-ERA5 (50 MWp, fator de capacidade 16,9%),
BESS de 60 MW / 300 MWh, eletrolisador de 10 MW, despacho diário do ONS (descarga
18h–21h, recarga 10h–14h). **Parâmetros econômicos ainda provisórios** (receita fixa de
R\$ 600 mil/MW·ano; H₂ a R\$ 35/kg).

Ótimo anual por Benders (3 iterações, *gap* 0,04%): **P_cap = 50,8 MW**, lucro de
**R\$ 60,1 mi/ano**.

![Convergência de Benders e função valor](docs/figuras/benders_itajuba_2025.png)

| Potência no LRCAP | Lucro anual | MCP | H₂ | Receita fixa |
|---|---|---|---|---|
| 0 MW | R\$ 41,0 mi | 0,9 | 43,8 | 0 |
| 30 MW (mínimo) | R\$ 56,5 mi | 0,7 | 43,6 | 18,0 |
| **50,8 MW (ótimo)** | **R\$ 60,1 mi** | 3,8 | 31,7 | 30,5 |
| 60 MW (BESS inteiro) | R\$ 58,6 mi | 6,5 | 21,5 | 36,0 |

- Participar do LRCAP aumenta o lucro em cerca de R\$ 19 mi/ano em relação a não participar.
- O ótimo é **plano** entre 45 e 55 MW (variação < 0,5%): a escolha exata depende mais dos
  parâmetros econômicos provisórios do que da operação.
- Semanas isoladas levam a ótimos de 35 a 56 MW. Por isso a decisão, que vale por 15 anos
  de contrato, precisa ser tomada sobre o ano inteiro.
- A troca central é **H₂ × receita fixa**: cada MW contratado tira bateria que alimentaria
  o eletrolisador à noite (fator de capacidade do eletrolisador: 0,57 no ótimo).

## Próximos passos sugeridos

1. Quando o edital da ANEEL sair: incluir penalidades e abatimento da receita fixa por
   indisponibilidade, e o preço inicial do leilão.
2. Definir parâmetros técnico-econômicos com base na literatura (eletrolisador PEM/alcalino, BESS Li-ion).
3. Versão estocástica em dois estágios com CVaR (cenários de despacho do ONS, PLD e PV),
   reaproveitando a decomposição de Benders (ver `docs/formulacao.md`, seções 6 e 8).
4. Eletrolisador: custo de partida, tempos mínimos ligado/desligado e *standby*.
