"""Validação da decomposição de Benders contra o MILP monolítico em horizontes intermediários.

Para um horizonte de N dias (padrão: 28) com as mesmas condições de contorno nas pontas, compara:
  1. o MILP monolítico do horizonte inteiro, com P_cap livre (ótimo exato, até o gap do solver);
  2. (opcional, --bloco-unico) Benders com um único bloco do tamanho do horizonte: mesmo problema,
     resolvido pelo método; com um bloco só, o MILP lagrangiano do corte reforçado é tão difícil quanto
     o monolítico, e a função valor não côncava impede o fechamento do gap;
  3. Benders com blocos semanais, como no restante do trabalho: acrescenta a aproximação das
     condições cíclicas em cada semana.

Uso:  python scripts/validacao_monolitico.py [--casos base contrato_3t] [--inicios 2025-01-06 2025-07-07]
          [--dias 28] [--tempo-max 3600]
"""

import argparse
import multiprocessing as mp
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
import pyomo.environ as pyo

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from curva_oferta import CASOS, aplicar  # noqa: E402
from pvbess_h2 import carregar_parametros, montar_series  # noqa: E402
from pvbess_h2.decomposicao import _solver, resolver_benders  # noqa: E402
from pvbess_h2.estocastico import parametros_cenario  # noqa: E402
from pvbess_h2.modelo import construir_modelo  # noqa: E402

SAIDA = RAIZ / "resultados" / "validacao_monolitico"
GAP = 1e-4
args_threads = 4   # o monolítico usa os mesmos núcleos que os processos do Benders


def monolitico(q, inicio, dias, tempo_max):
    q.horizonte.inicio, q.horizonte.dias = inicio, dias
    q.lrcap.potencia_fixa_mw = None
    s = montar_series(q)
    m = construir_modelo(q, s)
    opt = _solver(GAP, threads=args_threads)
    opt.config.time_limit = tempo_max
    t0 = time.time()
    r = opt.solve(m)
    t = time.time() - t0
    ok = r.best_feasible_objective is not None
    if ok:
        r.solution_loader.load_vars()
    nb = sum(1 for v in m.component_data_objects(pyo.Var) if v.domain is pyo.Binary)
    return {"p_cap_mw": float(pyo.value(m.P_cap)) if ok else float("nan"),
            "lucro_rs": r.best_feasible_objective if ok else float("nan"),
            "limite_superior_rs": r.best_objective_bound, "tempo_s": t,
            "status": str(r.termination_condition).split(".")[-1], "binarias": nb}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--casos", nargs="+", default=["base", "contrato_3t"])
    ap.add_argument("--inicios", nargs="+", default=["2025-01-06", "2025-07-07"])
    ap.add_argument("--dias", type=int, default=28)
    ap.add_argument("--tempo-max", type=float, default=3600)
    ap.add_argument("--sem-benders", action="store_true", help="só o monolítico (teste de escala)")
    ap.add_argument("--bloco-unico", action="store_true",
                    help="também Benders com um só bloco (lento: o MILP lagrangiano do horizonte é difícil)")
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    SAIDA.mkdir(parents=True, exist_ok=True)
    base = carregar_parametros(args.config)
    linhas = []
    for caso in args.casos:
        p0 = aplicar(base, CASOS[caso][1])
        for inicio in args.inicios:
            c = next(c for c in p0.estocastico.cenarios if c.ano == int(inicio[:4]))
            p = parametros_cenario(p0, c)
            ini = f"{inicio} 00:00"
            rot = {"caso": caso, "inicio": inicio, "dias": args.dias}
            # Em processo separado: o HiGHS fixa o número de threads do processo na primeira solução,
            # e o mestre do Benders usa uma só.
            with ProcessPoolExecutor(1, mp_context=mp.get_context("spawn")) as ex:
                r = ex.submit(monolitico, parametros_cenario(p0, c), ini, args.dias, args.tempo_max).result()
            linhas.append({**rot, "metodo": "MILP monolítico", **r})
            print(linhas[-1], flush=True)
            if args.sem_benders:
                continue
            metodos = [("Benders, blocos semanais", 7)]
            if args.bloco_unico:
                metodos.insert(0, ("Benders, bloco único", args.dias))
            for nome, db in metodos:
                t0 = time.time()
                x, lb, hist, _ = resolver_benders(p, ini, args.dias, dias_bloco=db, tol=GAP, gap_sub=GAP,
                                                  processos=args.processos, verbose=True)
                tab = hist.tabela()
                linhas.append({**rot, "metodo": nome, "p_cap_mw": x, "lucro_rs": lb,
                               "limite_superior_rs": tab.limite_superior_rs.iloc[-1], "tempo_s": time.time() - t0,
                               "status": f"{len(tab)} iterações", "binarias": float("nan")})
                print(linhas[-1], flush=True)
            pd.DataFrame(linhas).to_csv(SAIDA / f"validacao_{args.dias}d.csv", index=False)
    df = pd.DataFrame(linhas)
    df.to_csv(SAIDA / f"validacao_{args.dias}d.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
