"""Cortes de geração solar impostos pelo ONS (constrained-off) como perfil de redução da geração FV.

Dados abertos do ONS, conjunto `restricao_coff_fotovoltaica_tm` (todas as usinas e conjuntos solares, a cada
meia hora, desde abril/2024): geração verificada, geração limitada pelo ONS em tempo real e geração de
referência (a que a usina teria sem a limitação). Para o subsistema Sudeste/Centro-Oeste, o corte de cada
meia hora é a geração de referência menos a verificada nas usinas com limitação, e a fração cortada é a
razão entre o corte e a geração de referência de todas as usinas do subsistema.

Como o perfil horário de um dia específico não corresponde ao tempo meteorológico que a série de irradiância do
modelo tem naquele dia, a fração é tabelada por mês e hora do dia (razão das somas) e aplicada a todos os dias:

  observado  cada ano com a sua tabela (2024: abril a dezembro; 2025: ano completo); anos sem dado e meses sem
             dado ficam com fração zero (2021 a 2023 e janeiro a março de 2024)
  recente    a tabela dos últimos 12 meses completos (nov/2025 a out/2026), aplicada a todos os anos

Saída: data/ons_corte_fv_<perfil>_<ano>.csv (timestamp, fracao_corte) para 2021 a 2025, lidos por
`pv.corte_arquivo`, e resultados/cortes_fv/resumo.csv.

Uso:  python scripts/importar_cortes_fv.py [--subsistema "Sudeste/Centro-Oeste"]
Requer pyarrow. Os arquivos do ONS são baixados para data/brutos/ons/.
"""

import argparse
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BASE = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_fotovoltaica_tm"
BRUTOS = RAIZ / "data" / "brutos" / "ons"
SAIDA = RAIZ / "resultados" / "cortes_fv"
ANOS = [2021, 2022, 2023, 2024, 2025]
RECENTE = ("2025-11", "2026-10")      # 12 meses completos


def meses_disponiveis() -> list[str]:
    with urllib.request.urlopen(f"https://ons-aws-prod-opendata.s3.amazonaws.com/?list-type=2&prefix=dataset/"
                                f"restricao_coff_fotovoltaica_tm/RESTRICAO", timeout=60) as r:
        texto = r.read().decode()
    return sorted(set(re.findall(r"RESTRICAO_COFF_FOTOVOLTAICA_(\d{4}_\d{2})\.parquet", texto)))


def arquivo(mes: str) -> Path:
    arq = BRUTOS / f"RESTRICAO_COFF_FOTOVOLTAICA_{mes}.parquet"
    if not arq.exists():
        BRUTOS.mkdir(parents=True, exist_ok=True)
        print(f"baixando {arq.name}", flush=True)
        urllib.request.urlretrieve(f"{BASE}/{arq.name}", arq)
    return arq


def carregar(subsistema: str) -> pd.DataFrame:
    cols = ["nom_subsistema", "din_instante", "val_geracao", "val_geracaolimitada", "val_geracaoreferencia"]
    partes = []
    for mes in meses_disponiveis():
        d = pd.read_parquet(arquivo(mes), columns=cols)
        d = d[d.nom_subsistema == subsistema]
        corte = (d.val_geracaoreferencia - d.val_geracao).clip(lower=0).where(d.val_geracaolimitada.notna(), 0.0)
        partes.append(pd.DataFrame({"t": d.din_instante, "ref": d.val_geracaoreferencia, "corte": corte}))
    d = pd.concat(partes)
    d = d[d.t < d.t.max().normalize()]            # descarta o último dia, que pode estar incompleto
    return d


def tabela(d: pd.DataFrame) -> pd.Series:
    """Fração cortada por (mês, hora): razão entre a soma dos cortes e a das gerações de referência."""
    g = d.groupby([d.t.dt.month, d.t.dt.hour])[["ref", "corte"]].sum()
    return (g.corte / g.ref.where(g.ref > 0)).fillna(0.0).rename("fracao")


def perfil(ano: int, tab: pd.Series | None) -> pd.DataFrame:
    idx = pd.date_range(f"{ano}-01-01", f"{ano + 1}-01-01", freq="h", inclusive="left")
    if tab is None:
        f = pd.Series(0.0, index=idx)
    else:
        chave = pd.MultiIndex.from_arrays([idx.month, idx.hour])
        f = pd.Series(tab.reindex(chave).fillna(0.0).to_numpy(), index=idx)
    return pd.DataFrame({"timestamp": idx, "fracao_corte": f.round(5).to_numpy()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subsistema", default="Sudeste/Centro-Oeste")
    args = ap.parse_args()
    d = carregar(args.subsistema)
    SAIDA.mkdir(parents=True, exist_ok=True)

    resumo = []
    rec = d[(d.t >= RECENTE[0]) & (d.t < pd.Timestamp(RECENTE[1]) + pd.offsets.MonthBegin(1))]
    tab_rec = tabela(rec)
    for ano in ANOS:
        da = d[d.t.dt.year == ano]
        obs = perfil(ano, tabela(da) if len(da) else None)
        obs.to_csv(RAIZ / "data" / f"ons_corte_fv_observado_{ano}.csv", index=False)
        perfil(ano, tab_rec).to_csv(RAIZ / "data" / f"ons_corte_fv_recente_{ano}.csv", index=False)
        resumo.append({"ano": ano, "meses_com_dado": int(da.t.dt.month.nunique()),
                       "corte_pct_da_referencia": 100 * da.corte.sum() / da.ref.sum() if len(da) else 0.0})
    r = pd.DataFrame(resumo).astype({"ano": object})
    r.loc[len(r)] = {"ano": "recente", "meses_com_dado": 12, "corte_pct_da_referencia": 100 * rec.corte.sum() / rec.ref.sum()}
    r.to_csv(SAIDA / "resumo.csv", index=False)
    por_hora = tab_rec.unstack().mul(100).round(1)
    por_hora.to_csv(SAIDA / "tabela_recente_mes_hora_pct.csv")
    pd.set_option("display.width", 220)
    print(r.round(2).to_string(index=False))
    print("\nFração cortada (%) por mês (linhas) e hora (colunas), 'recente':")
    print(por_hora.loc[:, 7:17].to_string())


if __name__ == "__main__":
    sys.exit(main())
