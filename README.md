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
scripts/
  rodar_caso.py            resolve um caso e salva CSV + indicadores + gráfico em resultados/
  varredura_lrcap.py       sensibilidade: lucro × potência contratada no LRCAP
  importar_dados.py        converte CSVs brutos da CCEE (PLD) e do PVGIS (PV) para data/
tests/test_modelo.py       testes de consistência (balanço, SOC, H₂ verde, LRCAP...)
```

## Como rodar

```bash
pip install -r requirements.txt
python scripts/rodar_caso.py                     # caso base (7 dias)
python scripts/varredura_lrcap.py --passos 11    # curva de arbitragem LRCAP x MCP
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

## Primeiros resultados (dados sintéticos, apenas ilustrativos)

Caso base (7 dias), com BESS de 60 MW / 300 MWh e despacho diário do ONS (descarga
18h–21h, recarga 10h–14h):

| Potência no LRCAP | Lucro no horizonte |
|---|---|
| 0 MW (só mercantil) | R\$ 1,04 mi |
| **31,4 MW (ótimo)** | **R\$ 1,31 mi** |
| 60 MW (BESS inteiro) | R\$ 1,19 mi |

O ótimo fica perto do mínimo de 30 MW. Com os parâmetros atuais, cada MW deixado no
módulo mercantil rende mais alimentando o eletrolisador à noite (H₂ a R\$ 35/kg ≈
R\$ 636/MWh) do que a receita fixa de R\$ 600 mil/MW·ano. **O preço do H₂ e a receita
fixa do LRCAP continuam sendo os parâmetros decisivos.** O preço inicial do leilão
ainda será definido pelo MME.

## Próximos passos sugeridos

1. Quando o edital da ANEEL sair: incluir penalidades e abatimento da receita fixa por
   indisponibilidade, e o preço inicial do leilão.
2. Substituir as séries sintéticas por PLD histórico e geração PV do local de estudo.
3. Definir parâmetros técnico-econômicos com base na literatura (eletrolisador PEM/alcalino, BESS Li-ion).
4. Estender para ano completo com dias representativos e depois para a versão estocástica,
   com cenários de despacho do ONS (ver `docs/formulacao.md`, seção 7).
