"""Preço do H2 de origem fóssil (cinza) por ano de cenário, para o excedente da curva de demanda por faixas.

O H2 cinza vem da reforma a vapor do gás natural; seu custo segue o preço do gás, que no Brasil acompanha o
Brent (contratos da Petrobras com as distribuidoras indexados ao petróleo). Para cada ano de 2021 a 2025:

  gás (US$/MMBtu)      = k_brent · Brent, com k_brent calibrado nas médias da Petrobras de 2023 (US$ 11,50) e
                         2024 (US$ 10,50), divulgadas pela Abegas;
  H2 cinza (US$/kg)    = consumo da reforma (0,165 MMBtu/kg) · gás + custo não combustível (US$ 1/kg);
  H2 cinza (R$/kg)     = US$/kg · PTAX média do ano · fator do IPCA para R$ de 2025 (o mesmo do PLD).

O índice resultante é normalizado para que a média dos cinco anos seja R$ 16/kg, o valor fixo usado no caso
faixas_*t: o caso faixas_*t_ano mede só o efeito da variação entre anos e da sua correlação com o PLD, sem
mudar o nível médio do preço.

Saída: data/preco_h2_cinza_anual.csv
Uso:   python scripts/preco_h2_cinza.py
"""

from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
MEDIA_RS_KG = 16.0
K_BRENT = (11.50 / 82.49 + 10.50 / 80.53) / 2     # US$/MMBtu de gás por US$/bbl de Brent
CONSUMO_MMBTU_KG = 0.165
NAO_COMBUSTIVEL_USD_KG = 1.0
# Brent spot, média anual (EIA, série RBRTE; 2025 aproximado) e PTAX de venda, média anual (BCB; 2025 aproximado)
BRENT = {2021: 70.86, 2022: 100.93, 2023: 82.49, 2024: 80.53, 2025: 69.0}
PTAX = {2021: 5.3956, 2022: 5.1655, 2023: 4.9953, 2024: 5.3920, 2025: 5.58}


def main():
    cfg = yaml.safe_load(open(RAIZ / "config" / "estocastico_unifei.yaml"))
    ipca = {c["ano"]: c.get("fator_preco", 1.0) for c in cfg["estocastico"]["cenarios"]}
    d = pd.DataFrame({"ano": sorted(BRENT)})
    d["brent_usd_bbl"] = d.ano.map(BRENT)
    d["gas_usd_mmbtu"] = K_BRENT * d.brent_usd_bbl
    d["h2_cinza_usd_kg"] = CONSUMO_MMBTU_KG * d.gas_usd_mmbtu + NAO_COMBUSTIVEL_USD_KG
    d["ptax"] = d.ano.map(PTAX)
    d["fator_ipca"] = d.ano.map(ipca)
    d["h2_cinza_rs2025_kg"] = d.h2_cinza_usd_kg * d.ptax * d.fator_ipca
    d["preco_excedente_rs_kg"] = MEDIA_RS_KG * d.h2_cinza_rs2025_kg / d.h2_cinza_rs2025_kg.mean()
    d.round(4).to_csv(RAIZ / "data" / "preco_h2_cinza_anual.csv", index=False)
    print(d.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
