"""Fator de emissão horário do SIN a partir da geração por usina do ONS (dados abertos).

Para cada hora, fator = soma das térmicas fósseis (geração x fator do combustível) dividida
pela geração total do SIN, sem a micro e minigeração distribuída (MMGD). Fator de cada
combustível = fator de emissão do IPCC (2006) [tCO2/TJ] x 3,6 / rendimento da usina:
    gás natural 56,1 / 45%   -> 449 kg/MWh
    carvão      96,1 / 35%   -> 988 kg/MWh
    óleo diesel 74,1 / 38%   -> 702 kg/MWh
    óleo comb.  77,4 / 38%   -> 733 kg/MWh
Biomassa, resíduos industriais (licor negro da celulose, gases de siderurgia), nuclear e
renováveis entram com zero. Só emissões de operação, como o fator médio do MCTI.

Validação: em jan–abr/2025 a média mensal fica 2% a 5% abaixo dos fatores do MCTI (23,7;
24,8; 21,5; 28,9 kg/MWh), cuja base passou a incluir os novos empreendimentos renováveis em
2025. Pela metodologia anterior, os fatores anuais do MCTI de 2021–2023 (126,4; 42,6; 38,5)
são 34% a 42% maiores que os daqui.

Uso:  python scripts/importar_emissoes.py [--anos 2021 2022 2023 2024 2025]
Requer pyarrow. Os arquivos do ONS (~250 MB) são baixados para data/brutos/ons/.
"""

import argparse
import sys
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
URL = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/geracao_usina_2_ho"
BRUTOS = RAIZ / "data" / "brutos" / "ons"

IPCC = {"Gás": (56.1, 0.45), "Carvão": (96.1, 0.35), "Óleo Diesel": (74.1, 0.38),
        "Óleo Combustível": (77.4, 0.38), "Multi-Combustível Diesel/Óleo": (75.75, 0.38)}
FATOR = {c: f * 3.6 / eta for c, (f, eta) in IPCC.items()}     # kgCO2/MWh gerado


def arquivos(ano: int) -> list[Path]:
    # Até 2021 o ONS publica um arquivo por ano; a partir de 2022, um por mês.
    nomes = ([f"GERACAO_USINA-2_{ano}.parquet"] if ano <= 2021
             else [f"GERACAO_USINA-2_{ano}_{m:02d}.parquet" for m in range(1, 13)])
    BRUTOS.mkdir(parents=True, exist_ok=True)
    for n in nomes:
        if not (BRUTOS / n).exists():
            print(f"baixando {n}", flush=True)
            urllib.request.urlretrieve(f"{URL}/{n}", BRUTOS / n)
    return [BRUTOS / n for n in nomes]


def fator_horario(ano: int) -> pd.DataFrame:
    """Fator horário [kg/MWh] e geração do SIN sem MMGD [MWmed] em cada hora do ano."""
    cols = ["din_instante", "nom_tipousina", "nom_tipocombustivel", "cod_modalidadeoperacao", "val_geracao"]
    d = pd.concat([pd.read_parquet(f, columns=cols) for f in arquivos(ano)])
    d = d[~d.cod_modalidadeoperacao.str.contains("MMGD", na=False)]
    g = pd.to_numeric(d.val_geracao, errors="coerce").fillna(0.0)
    e = g * d.nom_tipocombustivel.map(FATOR).fillna(0.0) * (d.nom_tipousina == "TÉRMICA")
    h = pd.DataFrame({"g": g, "e": e, "t": d.din_instante}).groupby("t")[["g", "e"]].sum()
    idx = pd.date_range(f"{ano}-01-01", f"{ano}-12-31 23:00", freq="h")
    h = h.reindex(idx)
    if h.g.isna().any():
        print(f"{ano}: {int(h.g.isna().sum())} horas sem dados, preenchidas pela hora anterior")
        h = h.ffill().bfill()
    h["fe"] = h.e / h.g
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="+", type=int, default=[2021, 2022, 2023, 2024, 2025])
    args = ap.parse_args()
    print("Fatores por combustível [kg/MWh]:", {c: round(v) for c, v in FATOR.items()})
    for ano in args.anos:
        h = fator_horario(ano)
        saida = RAIZ / "data" / f"fator_emissao_sin_{ano}.csv"
        pd.DataFrame({"timestamp": h.index, "fator_kg_mwh": h.fe.round(2).values}).to_csv(saida, index=False)
        # médias ponderadas pela geração, como as do MCTI
        mes = h.groupby(h.index.month)[["e", "g"]].sum()
        mensal = (mes.e / mes.g).round(1).tolist()
        print(f"{ano}: média {h.e.sum() / h.g.sum():.1f} kg/MWh (horas: p5 {h.fe.quantile(.05):.1f}, "
              f"p95 {h.fe.quantile(.95):.1f}); mensal {mensal} -> {saida.relative_to(RAIZ)}")


if __name__ == "__main__":
    sys.exit(main())
