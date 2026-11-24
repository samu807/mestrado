"""Valor mercantil da energia da bateria: operação anual sem leilão (P = 0) para várias capacidades de energia.

Para cada capacidade E (MWh), com a potência de 60 MW mantida, resolve a operação anual de cada cenário (2021 a 2025) e
salva o lucro operacional, a descarga e o estado de carga. A diferença de lucro entre capacidades mede o valor de cada MWh
adicional no mercado (MCP e hidrogênio), sem a receita fixa do LRCAP.

Uso:  python scripts/dimensionamento_bess.py config/estocastico_unifei_faixas.yaml --energia 50 100 150 200 250 \
          [--potencia 60] [--subdir curva_oferta/dimensionamento_bess]
"""

import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.decomposicao import operacao_anual  # noqa: E402
from pvbess_h2.estocastico import dias_cenario, parametros_cenario  # noqa: E402

COLUNAS = ["pv_disp_mw", "pld_rs_mwh", "p_eletrolisador_mw", "p_exportacao_mw", "p_carga_bess_mw", "p_descarga_bess_mw",
           "soc_mwh", "venda_h2_kg_h"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--energia", type=float, nargs="+", required=True)
    ap.add_argument("--potencia", type=float, default=60.0)
    ap.add_argument("--subdir", default="curva_oferta/dimensionamento_bess")
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    saida = RAIZ / "resultados" / args.subdir
    saida.mkdir(parents=True, exist_ok=True)
    for e in args.energia:
        p = carregar_parametros(args.config)
        p.lrcap.receita_fixa_rs_mw_ano = 0.0
        p.bess.energia_mwh = float(e)
        p.bess.potencia_carga_mw = args.potencia
        p.bess.potencia_descarga_mw = args.potencia
        p.validar()
        linhas = []
        for c in p.estocastico.cenarios:
            parcial = saida / f"parcial_E{e:g}_P{args.potencia:g}_{c.ano}.csv"
            if parcial.exists():          # retomada após interrupção
                linhas.append(pd.read_csv(parcial).iloc[0].to_dict())
                print(f"[E={e:g} MWh] {c.ano}: retomado", flush=True)
                continue
            q = parametros_cenario(p, c)
            df, k = operacao_anual(q, f"{c.ano}-01-01", dias_cenario(p, c), 0.0, processos=args.processos)
            df[[col for col in COLUNAS if col in df]].to_csv(saida / f"op_E{e:g}_P{args.potencia:g}_{c.ano}.csv", index_label="timestamp")
            linhas.append({"ano": c.ano, "lucro_operacional_rs": k["lucro_rs"], "h2_vendido_t": k["h2_vendido_kg"] / 1e3,
                           "exportacao_gwh": k["energia_exportada_mwh"] / 1e3,
                           "descarga_gwh": float(df["p_descarga_bess_mw"].sum() / 1e3)})
            pd.DataFrame([linhas[-1]]).to_csv(parcial, index=False)
            print(f"[E={e:g} MWh, {args.potencia:g} MW] {c.ano}: lucro R$ {linhas[-1]['lucro_operacional_rs'] / 1e6:.3f} mi", flush=True)
        t = pd.DataFrame(linhas)
        t.to_csv(saida / f"resumo_E{e:g}_P{args.potencia:g}.csv", index=False)
        print(f"[E={e:g} MWh] média: lucro R$ {t.lucro_operacional_rs.mean() / 1e6:.3f} mi", flush=True)


if __name__ == "__main__":
    main()
