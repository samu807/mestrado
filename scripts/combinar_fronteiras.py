"""Combina as curvas de oferta obtidas com as duas fronteiras de bloco.

As fronteiras "lp" (estados da relaxação linear do ano) e "ciclica" (condição cíclica semanal)
produzem, cada uma, uma operação viável do ano inteiro e, portanto, um limite inferior do lucro
operacional ótimo. Para cada caso, potência e cenário, adota-se o maior dos dois; o limite superior
é o da relaxação linear. A operação média é a da fronteira com maior lucro esperado no ponto em que
foi avaliada.

Entrada: resultados/curva_oferta/fronteira_lp/<caso>.csv e fronteira_ciclica/<caso>.csv
Saída:   resultados/curva_oferta/<caso>.csv e <caso>_operacao.csv

Uso:  python scripts/combinar_fronteiras.py [caso ...]
"""

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from pvbess_h2 import carregar_parametros  # noqa: E402

DIR = RAIZ / "resultados" / "curva_oferta"
PROBS = carregar_parametros(str(RAIZ / "config" / "estocastico_unifei.yaml")).estocastico.probabilidades()


def combinar(caso):
    lp = pd.read_csv(DIR / "fronteira_lp" / f"{caso}.csv")
    ci = pd.read_csv(DIR / "fronteira_ciclica" / f"{caso}.csv")
    assert np.allclose(lp.p_cap_mw, ci.p_cap_mw), caso
    cen = [c for c in lp.columns if c.startswith("q_") and c != "q_rs"]
    q = np.maximum(lp[cen].to_numpy(), ci[cen].to_numpy())
    pi = np.asarray(PROBS, float)
    assert np.allclose(lp[cen].to_numpy() @ pi, lp.q_rs), caso
    out = pd.DataFrame({"p_cap_mw": lp.p_cap_mw, "q_rs": q @ pi})
    out[cen] = q
    out["q_lp_rs"], out["q_ciclica_rs"], out["ub_rs"] = lp.q_rs, ci.q_rs, lp.ub_rs
    out.to_csv(DIR / f"{caso}.csv", index=False)
    # operação: a da fronteira com maior lucro esperado no ponto avaliado
    escolhas = {}
    for f, c in (("fronteira_lp", lp), ("fronteira_ciclica", ci)):
        op = pd.read_csv(DIR / f / f"{caso}_operacao.csv", index_col=0)["valor"]
        escolhas[f] = (float(np.interp(op["p_cap_mw"], c.p_cap_mw, c.q_rs)), op)
    f = max(escolhas, key=lambda k: escolhas[k][0])
    shutil.copy(DIR / f / f"{caso}_operacao.csv", DIR / f"{caso}_operacao.csv")
    ganho = (out.q_rs - lp.q_rs).max()
    print(f"{caso}: máx(lp, cíclica); ganho sobre lp até R$ {ganho / 1e3:.0f} mil; operação de {f}")


if __name__ == "__main__":
    casos = sys.argv[1:] or sorted(p.stem for p in (DIR / "fronteira_lp").glob("*.csv")
                                   if not p.stem.endswith("_operacao")
                                   and (DIR / "fronteira_ciclica" / p.name).exists())
    for c in casos:
        combinar(c)
