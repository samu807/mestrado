"""Perfil alternativo de despacho do ONS, ligado à carga líquida do SIN em vez do PLD.

A carga líquida (carga menos geração eólica e solar, inclusive a MMGD) é suprida pelas fontes
despacháveis: é a soma horária da geração hidrelétrica, térmica e nuclear, a partir dos dados de
geração por usina do ONS (os mesmos de scripts/importar_emissoes.py). Por dia:
  - descarga a potência plena no bloco de `duracao_h` horas consecutivas de maior carga líquida
    após a janela de recarga (a ponta da carga líquida, no fim da tarde e à noite);
  - recarga, dentro da janela, nas horas de menor carga líquida, com a energia que repõe a descarga.

Saída: data/ons_carga_liquida_<ano>.csv (timestamp, descarga_pu, recarga_pu, carga_liquida_mw).

Uso:  python scripts/importar_carga_liquida.py [anos ...]
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from importar_emissoes import arquivos  # noqa: E402
from pvbess_h2 import carregar_parametros  # noqa: E402

DESPACHAVEIS = ("HIDROELÉTRICA", "TÉRMICA", "NUCLEAR")


def carga_liquida(ano: int) -> pd.Series:
    cols = ["din_instante", "nom_tipousina", "val_geracao"]
    d = pd.concat([pd.read_parquet(f, columns=cols) for f in arquivos(ano)])
    d = d[d.nom_tipousina.isin(DESPACHAVEIS)]
    g = pd.to_numeric(d.val_geracao, errors="coerce").fillna(0.0)
    h = g.groupby(d.din_instante.values).sum()
    idx = pd.date_range(f"{ano}-01-01", f"{ano}-12-31 23:00", freq="h")
    return h.reindex(idx).ffill().bfill()


def perfil(cl: pd.Series, duracao_h: int, janela: list[int], eta_ch: float, eta_dis: float) -> pd.DataFrame:
    desc = np.zeros(len(cl))
    rec = np.zeros(len(cl))
    x = cl.to_numpy()
    q = duracao_h / (eta_ch * eta_dis)
    dia = cl.index.normalize()
    for dd in np.unique(dia):
        pos = np.flatnonzero(dia == dd)
        horas = cl.index.hour[pos]
        noite = pos[horas > max(janela)]
        if len(noite) >= duracao_h:
            medias = [x[noite[i:i + duracao_h]].mean() for i in range(len(noite) - duracao_h + 1)]
            i0 = int(np.argmax(medias))
            desc[noite[i0:i0 + duracao_h]] = 1.0
        dentro = pos[np.isin(horas, janela)]
        restante = q
        for k in dentro[np.argsort(x[dentro], kind="stable")]:
            if restante <= 1e-9:
                break
            rec[k] = min(1.0, restante)
            restante -= rec[k]
    return pd.DataFrame({"timestamp": cl.index, "descarga_pu": desc, "recarga_pu": rec.round(6),
                         "carga_liquida_mw": x.round(1)})


def main():
    anos = [int(a) for a in sys.argv[1:]] or [2021, 2022, 2023, 2024, 2025]
    p = carregar_parametros(str(RAIZ / "config" / "estocastico_unifei.yaml"))
    lr, b = p.lrcap, p.bess
    for ano in anos:
        cl = carga_liquida(ano)
        df = perfil(cl, int(round(lr.duracao_h)), sorted(lr.despacho_ons.janela_recarga),
                    b.eficiencia_carga, b.eficiencia_descarga)
        df.to_csv(RAIZ / "data" / f"ons_carga_liquida_{ano}.csv", index=False)
        hd = pd.Series(df.timestamp[df.descarga_pu > 0]).dt.hour.value_counts().sort_index()
        print(f"{ano}: carga líquida média {cl.mean():.0f} MW; horas de descarga mais frequentes: "
              f"{dict(hd.head(6))}", flush=True)


if __name__ == "__main__":
    main()
