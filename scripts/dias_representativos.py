"""Comparação dos blocos semanais com blocos diários e com dias representativos.

Muitos trabalhos reduzem o ano a K dias representativos, obtidos por agrupamento (clustering)
das séries diárias, e resolvem o modelo só para esses dias, com pesos iguais ao número de dias de
cada grupo. Este script mede o erro dessa abordagem em relação aos blocos semanais da Seção 3.6:

  1. resolve, para cada cenário (ano), cada dia do ano e cada potência da grade da curva de
     oferta, o MILP de 24 h com condição cíclica diária (módulo mercantil e tanque voltam ao
     estado inicial no fim do dia), isto é, blocos de um dia: Q_dia(P);
  2. agrupa os dias de cada ano por k-medoids sobre os perfis horários de PLD e de fator de
     capacidade FV (padronizados), para K = 6, 12, 24 e 48, e estima o lucro do ano pela soma dos
     lucros dos medoides ponderados pelo tamanho dos grupos;
  3. compara as curvas Q(P) resultantes com a dos blocos semanais (resultados/curva_oferta/<caso>.csv):
     potência ótima com a receita de referência, receita mínima de entrada e custo marginal.

O passo 1 isola o efeito de perder a cronologia entre dias; o passo 2 soma a ele o erro do
agrupamento.

Saída: resultados/dias_representativos/<caso>_diario.csv (Q por cenário, dia e potência) e
       resultados/dias_representativos/<caso>_resumo.csv

Uso:  python scripts/dias_representativos.py [--casos base contrato_3t] [--processos 4]
"""

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from curva_oferta import CASOS, aplicar  # noqa: E402
from pvbess_h2 import carregar_parametros, montar_series  # noqa: E402
from pvbess_h2.decomposicao import avaliar_bloco  # noqa: E402
from pvbess_h2.estocastico import dias_cenario, parametros_cenario  # noqa: E402

SAIDA = RAIZ / "resultados" / "dias_representativos"
KS = (6, 12, 24, 48)
GAP = 1e-4


def _dia(args):
    q, inicio, potencias = args
    warnings.filterwarnings("ignore")
    return [avaliar_bloco((q, inicio, 1, float(x), GAP, True)).q for x in potencias]


def lucro_diario(p, potencias, processos):
    tarefas, chaves = [], []
    for c in p.estocastico.cenarios:
        q = parametros_cenario(p, c)
        for d in pd.date_range(f"{c.ano}-01-01", periods=dias_cenario(p, c), freq="D"):
            tarefas.append((q, d.strftime("%Y-%m-%d 00:00"), potencias))
            chaves.append((c.nome, d.strftime("%Y-%m-%d")))
    with ProcessPoolExecutor(processos) as ex:
        res = list(ex.map(_dia, tarefas, chunksize=8))
    idx = pd.MultiIndex.from_tuples(chaves, names=["cenario", "dia"])
    return pd.DataFrame(res, index=idx, columns=[f"{x:g}" for x in potencias])


def atributos(p, c):
    """Vetor diário (48 valores) com PLD e fator de capacidade FV horários do cenário."""
    q = parametros_cenario(p, c)
    q.horizonte.inicio, q.horizonte.dias = f"{c.ano}-01-01 00:00", dias_cenario(p, c)
    s = montar_series(q)
    pld = s["pld_rs_mwh"].to_numpy().reshape(-1, 24)
    pv = (s["pv_disp_mw"] / q.pv.potencia_pico_mw).to_numpy().reshape(-1, 24)
    return pld, pv


def k_medoids(x, k, semente=0, iteracoes=100):
    """k-medoids (alternado), com inicialização k-means++. Retorna medoides e rótulos."""
    rng = np.random.default_rng(semente)
    d = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2)
    med = [int(rng.integers(len(x)))]
    for _ in range(1, k):
        dmin = d[:, med].min(axis=1) ** 2
        med.append(int(rng.choice(len(x), p=dmin / dmin.sum())))
    med = np.array(med)
    for _ in range(iteracoes):
        rot = np.argmin(d[:, med], axis=1)
        novo = np.array([np.flatnonzero(rot == j)[np.argmin(d[np.ix_(rot == j, rot == j)].sum(axis=0))]
                         for j in range(k)])
        if np.array_equal(np.sort(novo), np.sort(med)):
            break
        med = novo
    return med, np.argmin(d[:, med], axis=1)


def resumo(p, diario, semanal, potencias, receita):
    """Curvas Q(P) esperadas por método e indicadores da decisão."""
    curvas = {"Blocos semanais": semanal}
    curvas["Blocos diários (365 dias)"] = diario.groupby(level="cenario").sum().mean().to_numpy()
    for k in KS:
        anual = []
        for c in p.estocastico.cenarios:
            pld, pv = atributos(p, c)
            x = np.hstack([(pld - pld.mean()) / pld.std(), (pv - pv.mean()) / pv.std()])
            med, rot = k_medoids(x, k)
            pesos = np.bincount(rot, minlength=k)
            dq = diario.loc[c.nome].to_numpy()
            anual.append((pesos[:, None] * dq[med]).sum(axis=0))
        curvas[f"{k} dias representativos"] = np.mean(anual, axis=0)
    P = np.asarray(potencias)
    linhas = []
    for nome, q in curvas.items():
        v = receita * P + q
        i = int(np.argmax(v))
        linhas.append({
            "metodo": nome,
            "lucro_operacional_0_mw_rs": q[0],
            "erro_medio_q_pct": float(np.mean(np.abs(q - semanal) / semanal) * 100),
            "erro_perda_pct": float(np.mean(np.abs((q[0] - q[1:]) - (semanal[0] - semanal[1:]))
                                            / (semanal[0] - semanal[1:])) * 100),
            "p_otima_mw": P[i], "lucro_total_rs": v[i],
            "entrada_rs_mw": (q[0] - q[1]) / P[1],
            "marginal_ultimo_rs_mw": (q[-2] - q[-1]) / (P[-1] - P[-2]),
            **{f"q_{x:g}": y for x, y in zip(P, q)},
        })
    return pd.DataFrame(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--casos", nargs="+", default=["base", "contrato_3t"])
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    SAIDA.mkdir(parents=True, exist_ok=True)
    base = carregar_parametros(args.config)
    for caso in args.casos:
        p = aplicar(base, CASOS[caso][1])
        semanal = pd.read_csv(RAIZ / "resultados" / "curva_oferta" / f"{caso}.csv")
        potencias = semanal.p_cap_mw.tolist()
        arq = SAIDA / f"{caso}_diario.csv"
        if arq.exists():
            diario = pd.read_csv(arq, index_col=[0, 1])
            diario.index = diario.index.set_levels(diario.index.levels[0].astype(str), level=0)
        else:
            print(f"{caso}: resolvendo blocos diários...", flush=True)
            diario = lucro_diario(p, potencias, args.processos)
            diario.to_csv(arq)
        r = resumo(p, diario, semanal.q_rs.to_numpy(), potencias, p.lrcap.receita_fixa_rs_mw_ano)
        r.to_csv(SAIDA / f"{caso}_resumo.csv", index=False)
        print(f"\n{caso}:")
        print(r[["metodo", "erro_medio_q_pct", "erro_perda_pct", "p_otima_mw", "entrada_rs_mw",
                 "marginal_ultimo_rs_mw"]].round(2).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
