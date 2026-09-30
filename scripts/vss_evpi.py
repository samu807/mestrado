"""Valor da solução estocástica (VSS) e valor esperado da informação perfeita (EVPI).

Problema de maximização (lucro), neutro ao risco (beta = 0):
    RP  = max_x E_s[Pi_s(x)]                 (problema estocástico, "recourse problem")
    WS  = E_s[max_x Pi_s(x)]                 (espera-e-vê: cada ano com a sua melhor potência)
    EEV = E_s[Pi_s(x_EV)]                    (x_EV = ótimo do ano médio)
    EVPI = WS - RP >= 0        VSS = RP - EEV >= 0

O ano médio é a média hora a hora dos 5 anos (PLD já corrigido pelo IPCA; 29/02 removido),
gerada em data/pld_se_medio_2021_2025.csv e data/pv_itajuba_sarah3_medio_2021_2025.csv.

Uso:  python scripts/vss_evpi.py [config/estocastico_unifei.yaml] [--tol 1e-4] [--processos 4]
"""

import argparse
import copy
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia, resolver_estocastico  # noqa: E402
from pvbess_h2.parametros import Cenario  # noqa: E402

MEDIO = Cenario(nome="médio", ano=2025, pld_arquivo="data/pld_se_medio_2021_2025.csv",
                pv_arquivo="data/pv_itajuba_sarah3_medio_2021_2025.csv", fator_preco=1.0)


def otimo(p, cenarios, args, rotulo):
    q = copy.deepcopy(p)
    q.estocastico.cenarios = cenarios
    print(f"\n=== {rotulo} ===", flush=True)
    av, hist, _ = resolver_estocastico(q, tol=args.tol, processos=args.processos)
    ub = hist.limite_superior_rs.iloc[-1]
    return av, ub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--tol", type=float, default=1e-4)
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)

    base = carregar_parametros(args.config)
    base.estocastico.beta = 0.0
    anos = base.estocastico.cenarios
    probs = np.array(base.estocastico.probabilidades())
    saida = RAIZ / "resultados" / (Path(args.config).stem + "_estocastico")
    saida.mkdir(parents=True, exist_ok=True)

    # RP: problema estocástico
    rp, rp_ub = otimo(base, anos, args, "RP (5 anos)")

    # WS: cada ano com a sua melhor potência
    ws_linhas = []
    for c in anos:
        av, ub = otimo(base, [c], args, f"WS: ano {c.nome}")
        ws_linhas.append({"cenario": c.nome, "p_cap_mw": av.p_cap, "lucro_rs": av.esperado, "limite_sup_rs": ub})
    ws = pd.DataFrame(ws_linhas)

    # EV: ano médio -> x_EV, avaliado nos 5 anos
    ev, ev_ub = otimo(base, [MEDIO], args, "EV (ano médio)")
    eev = avaliar_potencia(base, ev.p_cap, processos=args.processos)

    WS, WS_ub = float(probs @ ws.lucro_rs), float(probs @ ws.limite_sup_rs)
    RP, EEV = rp.esperado, eev.esperado
    nomes = [c.nome for c in anos]
    decisoes = pd.DataFrame(
        [{"decisao": "RP (estocástico)", "p_cap_mw": rp.p_cap, **dict(zip(nomes, rp.lucro_cenarios)),
          "esperado_rs": RP, "cvar_rs": rp.cvar},
         {"decisao": "EV (ano médio)", "p_cap_mw": ev.p_cap, **dict(zip(nomes, eev.lucro_cenarios)),
          "esperado_rs": EEV, "cvar_rs": eev.cvar},
         {"decisao": "WS (informação perfeita)", "p_cap_mw": np.nan, **dict(zip(nomes, ws.lucro_rs)),
          "esperado_rs": WS, "cvar_rs": np.nan}])
    resumo = pd.DataFrame([
        {"indicador": "RP", "valor_rs": RP, "limite_sup_rs": rp_ub},
        {"indicador": "WS", "valor_rs": WS, "limite_sup_rs": WS_ub},
        {"indicador": "EV (lucro do ano médio)", "valor_rs": ev.esperado, "limite_sup_rs": ev_ub},
        {"indicador": "EEV", "valor_rs": EEV, "limite_sup_rs": np.nan},
        {"indicador": "EVPI = WS - RP", "valor_rs": WS - RP, "limite_sup_rs": WS_ub - RP},
        {"indicador": "VSS = RP - EEV", "valor_rs": RP - EEV, "limite_sup_rs": rp_ub - EEV},
    ])
    ws.to_csv(saida / "ws_por_ano.csv", index=False)
    decisoes.to_csv(saida / "vss_evpi_decisoes.csv", index=False)
    resumo.to_csv(saida / "vss_evpi.csv", index=False)
    pd.set_option("display.float_format", lambda v: f"{v / 1e6:,.4f}" if abs(v) > 1e3 else f"{v:,.3f}")
    print("\n" + ws.to_string(index=False))
    print("\n" + decisoes.to_string(index=False))
    print("\n" + resumo.to_string(index=False))
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
