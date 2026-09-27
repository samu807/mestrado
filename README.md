# Otimização da Operação de um Sistema Híbrido PV-BESS com Produção de Hidrogênio Verde

**Arbitragem entre o Leilão de Reserva de Capacidade (LRCAP) e o Mercado de Curto Prazo (MCP)**

Repositório do modelo de otimização da dissertação de mestrado. O modelo é um MILP
implementado em Python/[Pyomo](https://www.pyomo.org/) e resolvido com o
[HiGHS](https://highs.dev/) (gratuito e de código aberto).

```
PV ──┐                         ┌──► Rede (MCP, liquidado ao PLD)
     ├──► Barramento ──────────┼──► Eletrolisador ──► Tanque H₂ ──► Venda de H₂
BESS ◄┘   (balanço de potência) └──► LRCAP (reserva de capacidade do BESS)
```

## Estrutura

```
config/caso_base.yaml      parâmetros do caso (valores PLACEHOLDER — substituir por dados reais)
docs/formulacao.md         formulação matemática completa (conjuntos, parâmetros, variáveis, restrições)
src/pvbess_h2/
  parametros.py            leitura/validação do YAML
  dados.py                 séries de entrada (PV, PLD, janelas LRCAP) — reais via CSV ou sintéticas
  modelo.py                construção do modelo Pyomo e chamada do solver
  resultados.py            série horária de resultados, indicadores e gráfico
scripts/
  rodar_caso.py            resolve um caso e salva CSV + indicadores + gráfico em resultados/
  varredura_lrcap.py       sensibilidade: lucro × potência contratada no LRCAP
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

### Usando dados reais

- **PLD horário**: CSV com colunas `timestamp,pld` (ex.: dados abertos da CCEE) e
  `mercado.arquivo: data/pld_2025.csv`.
- **Geração PV**: CSV com colunas `timestamp,fator_capacidade` (0–1; ex.: PVGIS/INMET) e
  `pv.arquivo: data/pv_local.csv`.

## Primeiros resultados (dados sintéticos, apenas ilustrativos)

No caso base (7 dias), o modelo contrata ~25,7 MW no LRCAP — o máximo que a reserva de
4 h de energia permite com um BESS de 120 MWh. O custo dessa escolha aparece na operação:
o BESS precisa ficar carregado na janela de ponta (17h–21h) e deixa de fazer arbitragem
justamente nas horas de PLD mais alto, descarregando depois para alimentar o
eletrolisador durante a noite. Com os parâmetros atuais, o H₂ a R\$ 35/kg equivale a
~R\$ 636/MWh consumido, acima de quase todo PLD sintético, por isso o eletrolisador
opera com fator de capacidade de ~80%. **Os preços de H₂ e a receita do LRCAP são os
parâmetros mais sensíveis**: vale priorizar a coleta desses dados.

## Próximos passos sugeridos

1. Levantar as regras do LRCAP aplicáveis a armazenamento (duração, acionamento,
   apuração de disponibilidade, penalidades) e ajustar as restrições em `modelo.py`.
2. Substituir as séries sintéticas por PLD histórico e geração PV do local de estudo.
3. Definir parâmetros técnico-econômicos com base na literatura (eletrolisador PEM/alcalino, BESS Li-ion).
4. Estender para ano completo com dias representativos e depois para a versão estocástica
   (ver `docs/formulacao.md`, seção 7).
