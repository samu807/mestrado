"""Erro da decomposição em blocos com condição cíclica.

A decomposição impõe que os estados de armazenamento (BESS mercantil e tanque de H2)
voltem ao valor inicial ao fim de cada bloco. Isso restringe o problema anual: o lucro
com blocos mais longos é maior ou igual. Este script mede o efeito avaliando a operação
anual com P_cap fixo para blocos de 7, 14 e 28 dias e, opcionalmente, refazendo o
Benders com blocos de 14 dias.

Uso:  python scripts/erro_decomposicao.py [config/unifei_escalonada.yaml] [--p-cap 54.44]
          [--blocos 7 14 28] [--benders 14]
"""

import argparse
import sys
import time
import warnings
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.decomposicao import operacao_anual, resolver_benders  # noqa: E402

COLS = ["lucro_rs", "receita_mcp_rs", "receita_h2_rs", "custo_degradacao_rs", "h2_produzido_kg",
        "energia_exportada_mwh"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "unifei_escalonada.yaml"))
    ap.add_argument("--p-cap", type=float, default=54.44)
    ap.add_argument("--inicio", default="2025-01-01")
    ap.add_argument("--dias", type=int, default=365)
    ap.add_argument("--blocos", type=int, nargs="+", default=[7, 14, 28])
    ap.add_argument("--benders", type=int, nargs="*", default=[14], help="tamanhos de bloco para refazer o Benders")
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    p = carregar_parametros(args.config)
    saida = RAIZ / "resultados" / (Path(args.config).stem + "_decomposicao")
    saida.mkdir(parents=True, exist_ok=True)

    linhas = []
    for b in args.blocos:
        t0 = time.time()
        _, k = operacao_anual(p, args.inicio, args.dias, args.p_cap, dias_bloco=b, processos=args.processos)
        linhas.append({"dias_bloco": b, "p_cap_mw": args.p_cap, **k[COLS].to_dict(), "tempo_s": time.time() - t0})
        print(f"blocos de {b:2d} dias: lucro = R$ {k.lucro_rs / 1e6:.4f} mi  [{time.time() - t0:.0f} s]", flush=True)
    fixo = pd.DataFrame(linhas)
    ref = fixo.lucro_rs.iloc[0]
    fixo["dif_rel_lucro"] = (fixo.lucro_rs - ref) / ref
    fixo.to_csv(saida / "potencia_fixa.csv", index=False)

    ots = []
    for b in args.benders:
        t0 = time.time()
        x, lb, hist, _ = resolver_benders(p, args.inicio, args.dias, dias_bloco=b, processos=args.processos)
        ub = hist.tabela().limite_superior_rs.iloc[-1]
        ots.append({"dias_bloco": b, "p_cap_mw": x, "lucro_rs": lb, "limite_superior_rs": ub,
                    "tempo_s": time.time() - t0})
        print(f"Benders com blocos de {b} dias: P_cap = {x:.2f} MW, lucro = R$ {lb / 1e6:.4f} mi", flush=True)
    if ots:
        pd.DataFrame(ots).to_csv(saida / "benders.csv", index=False)
    print(fixo.to_string(index=False))
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
