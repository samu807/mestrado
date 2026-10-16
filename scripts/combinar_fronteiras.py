"""Combina as curvas de oferta obtidas com as duas fronteiras de bloco.

As fronteiras "lp" (estados da relaxação linear do ano) e "ciclica" (condição cíclica semanal)
produzem, cada uma, uma operação viável do ano inteiro e, portanto, um limite inferior do lucro
operacional ótimo. Para cada caso, potência e cenário, adota-se o maior dos dois; o limite superior
é o da relaxação linear. A operação média é a da fronteira com maior lucro esperado no ponto em que
foi avaliada.

A recarga do módulo LRCAP acima da custeada pela CONCAP (injetada / RTE de referência) é apurada
por bloco no modelo. Com poucos despachos, a recarga de um despacho no fim de um bloco cai no bloco
seguinte, sem a injeção correspondente, e é cobrada como excedente. A combinação devolve essa parcela,
apurando o excedente no ano inteiro (correção linear em P, nula com despacho diário).

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
from pvbess_h2 import carregar_parametros, montar_series  # noqa: E402
from pvbess_h2.decomposicao import dividir_em_blocos  # noqa: E402
from pvbess_h2.estocastico import dias_cenario, parametros_cenario  # noqa: E402

sys.path.insert(0, str(RAIZ / "scripts"))
from curva_oferta import CASOS, aplicar  # noqa: E402

DIR = RAIZ / "resultados" / "curva_oferta"
BASE = carregar_parametros(str(RAIZ / "config" / "estocastico_unifei.yaml"))
PROBS = BASE.estocastico.probabilidades()


def correcao_recarga(caso):
    """Por cenário: custo da recarga excedente do módulo LRCAP somado por bloco menos o apurado no
    ano inteiro, em R$/(MW·ano)."""
    p = aplicar(BASE, CASOS[caso][1])
    out = []
    for c in p.estocastico.cenarios:
        q = parametros_cenario(p, c)
        dias = dias_cenario(p, c)
        q.horizonte.inicio, q.horizonte.dias = f"{c.ano}-01-01 00:00", dias
        s = montar_series(q)
        dt, rte = q.horizonte.dt_h, q.lrcap.rte_referencia

        def custo(x):
            er, ei = float((x.ons_recarga_pu * dt).sum()), float((x.ons_descarga_pu * dt).sum())
            f = max(0.0, er - ei / rte) / er if er > 0 else 0.0
            return f * float((x.pld_rs_mwh * x.ons_recarga_pu * dt).sum())
        blocos = 0.0
        for ini, d in dividir_em_blocos(f"{c.ano}-01-01", dias, p.estocastico.dias_bloco):
            i0 = pd.Timestamp(ini)
            blocos += custo(s[(s.index >= i0) & (s.index < i0 + pd.Timedelta(days=d))])
        out.append(blocos - custo(s))
    return np.asarray(out)


def combinar(caso):
    lp = pd.read_csv(DIR / "fronteira_lp" / f"{caso}.csv")
    ci = pd.read_csv(DIR / "fronteira_ciclica" / f"{caso}.csv")
    assert np.allclose(lp.p_cap_mw, ci.p_cap_mw), caso
    cen = [c for c in lp.columns if c.startswith("q_") and c != "q_rs"]
    q = np.maximum(lp[cen].to_numpy(), ci[cen].to_numpy())
    corr = correcao_recarga(caso)
    q = q + np.outer(lp.p_cap_mw.to_numpy(), corr)
    pi = np.asarray(PROBS, float)
    assert np.allclose(lp[cen].to_numpy() @ pi, lp.q_rs), caso
    out = pd.DataFrame({"p_cap_mw": lp.p_cap_mw, "q_rs": q @ pi})
    out[cen] = q
    out["q_lp_rs"], out["q_ciclica_rs"], out["ub_rs"] = lp.q_rs, ci.q_rs, lp.ub_rs
    out["correcao_recarga_rs_mw"] = float(corr @ pi)
    out.to_csv(DIR / f"{caso}.csv", index=False)
    # operação: a da fronteira com maior lucro esperado no ponto avaliado
    escolhas = {}
    for f, c in (("fronteira_lp", lp), ("fronteira_ciclica", ci)):
        op = pd.read_csv(DIR / f / f"{caso}_operacao.csv", index_col=0)["valor"]
        escolhas[f] = (float(np.interp(op["p_cap_mw"], c.p_cap_mw, c.q_rs)), op)
    f = max(escolhas, key=lambda k: escolhas[k][0])
    shutil.copy(DIR / f / f"{caso}_operacao.csv", DIR / f"{caso}_operacao.csv")
    ganho = (out.q_rs - lp.q_rs).max()
    print(f"{caso}: máx(lp, cíclica); ganho sobre lp até R$ {ganho / 1e3:.0f} mil; correção da recarga "
          f"R$ {float(corr @ pi) / 1e3:.1f} mil/MW; operação de {f}")


if __name__ == "__main__":
    casos = sys.argv[1:] or sorted(p.stem for p in (DIR / "fronteira_lp").glob("*.csv")
                                   if not p.stem.endswith("_operacao")
                                   and (DIR / "fronteira_ciclica" / p.name).exists())
    for c in casos:
        combinar(c)
