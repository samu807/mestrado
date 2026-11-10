"""Despacho do ONS como grandeza estocástica: verificação com despachos sintéticos.

Não há histórico de baterias contratadas no LRCAP. No caso de referência, o despacho do ONS em cada cenário
segue o PLD do ano (descarga no bloco de 4 h de maior PLD após a janela solar, recarga nas horas de menor PLD
da janela). Este script mede quanto o resultado depende dessa hipótese: sorteia perfis de despacho
INDEPENDENTES do preço, dentro dos limites da Portaria MME 136/2026 (art. 4º, § 3º: ciclos de 4 h, até 2 por
dia e 366 por ano), e recalcula a curva de oferta Q(P) e o lance mínimo do BESS.

Famílias de perfis (o horário de início de cada descarga é sorteado):
  horario      1 ciclo todo dia, descarga com início entre 16 h e 20 h
  dias_150     150 dias sorteados no ano, 1 ciclo, início entre 16 h e 20 h
  dias_50      50 dias sorteados no ano, 1 ciclo, início entre 16 h e 20 h
  dois_ciclos  183 dias sorteados (366 ciclos no ano), com descarga de manhã (início às 5 h ou 6 h) e à
               noite (início entre 17 h e 20 h)
Em todas, a recarga repõe a energia de cada descarga nas horas de menor PLD entre a descarga anterior e a
seguinte, a até 1 p.u. (o ONS minimiza o custo da recarga, art. 4º, § 14).

A recarga do módulo LRCAP acima da custeada pela CONCAP é apurada no ano civil pelo próprio modelo
(dados.despacho_ons), e não por bloco semanal: nos perfis sorteados, a recarga pode cair no bloco anterior ao da
descarga correspondente, e a apuração por bloco a cobraria como excedente.

A potência P = 0 não depende do despacho (não há módulo LRCAP); Q(0) vem de resultados/curva_oferta/base.csv,
assim como a curva do caso de referência nas mesmas potências. O lance mínimo é recalculado com a rotina de
scripts/viabilidade.py, na grade reduzida, para os perfis sintéticos e para o caso de referência.

Saídas (resultados/despacho_sintetico/): perfis/<familia>_k<k>_<ano>.csv, pontos.csv (Q por amostra e
potência, gravado a cada ponto; a rodada retoma de onde parou) e resumo.csv.

Uso:  python scripts/despacho_sintetico.py [--familias horario dias_150 dias_50 dois_ciclos] [--amostras 3 2 2 2]
          [--potencias 30 50 55 57.5 60] [--processos 4]
"""

import argparse
import copy
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from pvbess_h2 import carregar_parametros  # noqa: E402
from pvbess_h2.estocastico import avaliar_potencia, dias_cenario  # noqa: E402
from viabilidade import decomposicao, info_despacho, premissas  # noqa: E402

SAIDA = RAIZ / "resultados" / "despacho_sintetico"
FAMILIAS = {   # dias com despacho no ano (None = todos) e horas de início de cada ciclo do dia
    "horario": (None, [range(16, 21)]),
    "dias_150": (150, [range(16, 21)]),
    "dias_50": (50, [range(16, 21)]),
    "dois_ciclos": (183, [range(5, 7), range(17, 21)]),
}
R_REF = 600e3


def gerar_perfil(familia, k, ano, p):
    """Perfil horário do ano (descarga_pu, recarga_pu), por MW contratado."""
    n_dias_ano, inicios = FAMILIAS[familia]
    dias = dias_cenario(p, next(c for c in p.estocastico.cenarios if c.ano == ano))
    idx = pd.date_range(f"{ano}-01-01", periods=dias * 24, freq="h")
    rng = np.random.default_rng([2026, list(FAMILIAS).index(familia), k, ano])
    chamados = np.arange(dias) if n_dias_ano is None else np.sort(rng.choice(dias, n_dias_ano, replace=False))
    h = int(round(p.lrcap.duracao_h))
    eventos = sorted(d * 24 + int(rng.choice(list(faixa))) for d in chamados for faixa in inicios)
    pld = pd.read_csv(RAIZ / "data" / f"pld_se_{ano}.csv", parse_dates=["timestamp"]).set_index("timestamp")["pld"]
    pld = pld.reindex(idx).to_numpy()
    desc, rec = np.zeros(len(idx)), np.zeros(len(idx))
    q = p.lrcap.duracao_h / (p.bess.eficiencia_carga * p.bess.eficiencia_descarga)   # p.u.·h a repor por ciclo
    fim_anterior = 0
    for t0 in eventos:
        desc[t0:t0 + h] = 1.0
        janela = np.arange(fim_anterior, t0)
        restante = q
        for t in janela[np.argsort(pld[janela], kind="stable")]:
            if restante <= 1e-9:
                break
            rec[t] = min(1.0, restante)
            restante -= rec[t]
        if restante > 1e-6:
            raise ValueError(f"{familia} k{k} {ano}: sem horas para recarregar antes de {idx[t0]}")
        fim_anterior = t0 + h
    return pd.DataFrame({"timestamp": idx, "descarga_pu": desc, "recarga_pu": rec})


def com_perfil(base, familia, k):
    p = copy.deepcopy(base)
    p.lrcap.despacho_ons.arquivo = str(SAIDA / "perfis" / f"{familia}_k{k}_{{ano}}.csv")
    return p


def lance(p, eco, curva, q_sem):
    pr = premissas(eco)
    return decomposicao(p, eco, pr, curva, info_despacho(p), q_sem)["lance_minimo_rs_mw_ano"]


def indicadores(P, Q):
    q0 = Q[0]
    v = R_REF * P + Q
    return {"q0_rs": q0, "entrada_rs_mw": float(((q0 - Q[1:]) / P[1:]).min()),
            "receita_60mw_rs_mw": float(((Q[:-1] - Q[-1]) / (P[-1] - P[:-1])).max()),
            "p_otima_600k_mw": float(P[int(np.argmax(v))])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(RAIZ / "config" / "estocastico_unifei.yaml"))
    ap.add_argument("--familias", nargs="+", default=list(FAMILIAS))
    ap.add_argument("--amostras", nargs="+", type=int, default=[3, 2, 2, 2])
    ap.add_argument("--potencias", nargs="+", type=float, default=[30, 50, 55, 57.5, 60])
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    (SAIDA / "perfis").mkdir(parents=True, exist_ok=True)
    base = carregar_parametros(args.config)
    base.lrcap.receita_fixa_rs_mw_ano = 0.0
    eco = yaml.safe_load(open(RAIZ / "config" / "economia.yaml", encoding="utf-8"))
    q_sem = float(pd.read_csv(RAIZ / "resultados" / "viabilidade" / "sem_bess.csv").lucro_sem_bess_rs.iloc[0])
    ref = pd.read_csv(RAIZ / "resultados" / "curva_oferta" / "base.csv").set_index("p_cap_mw")
    nomes = [c.nome for c in base.estocastico.cenarios]

    arq = SAIDA / "pontos.csv"
    pontos = pd.read_csv(arq).to_dict("records") if arq.exists() else []
    feitos = {(r["familia"], int(r["k"]), round(r["p_cap_mw"], 6)) for r in pontos}
    amostras = [(f, k) for f, n in zip(args.familias, args.amostras) for k in range(n)]
    for familia, k in amostras:
        for c in base.estocastico.cenarios:
            destino = SAIDA / "perfis" / f"{familia}_k{k}_{c.ano}.csv"
            if not destino.exists():
                gerar_perfil(familia, k, c.ano, base).to_csv(destino, index=False, date_format="%Y-%m-%d %H:%M:%S")
        p = com_perfil(base, familia, k)
        for x in args.potencias:
            if (familia, k, round(x, 6)) in feitos:
                continue
            av = avaliar_potencia(p, float(x), processos=args.processos)
            pontos.append({"familia": familia, "k": k, "p_cap_mw": x, "q_rs": av.esperado,
                           **{f"q_{n}": v for n, v in zip(nomes, av.lucro_cenarios)}})
            pd.DataFrame(pontos).to_csv(arq, index=False)
            print(f"[{familia} k{k}] P = {x:5.1f} MW  Q = R$ {av.esperado / 1e6:7.3f} mi  "
                  f"(referência {ref.q_rs.get(x, np.nan) / 1e6:7.3f})", flush=True)

    # Resumo: curva reduzida (P = 0 da referência) de cada amostra e da referência
    df = pd.DataFrame(pontos)
    P = np.array([0.0] + list(args.potencias))
    linhas = []
    q_ref = np.array([ref.q_rs.loc[x] for x in P])
    curva_ref = pd.DataFrame({"p_cap_mw": P, "q_rs": q_ref})
    linhas.append({"familia": "referencia_pld", "k": -1, **indicadores(P, q_ref),
                   "lance_rs_mw_ano": lance(base, eco, curva_ref, q_sem),
                   **{f"q_{x:g}": y for x, y in zip(P, q_ref)}})
    for (familia, k), g in df.groupby(["familia", "k"], sort=False):
        g = g.set_index("p_cap_mw")
        if not all(x in g.index for x in args.potencias):
            continue
        p = com_perfil(base, familia, k)
        Q = np.array([ref.q_rs.loc[0.0]] + [g.q_rs.loc[x] for x in args.potencias])
        linhas.append({"familia": familia, "k": k, **indicadores(P, Q),
                       "lance_rs_mw_ano": lance(p, eco, pd.DataFrame({"p_cap_mw": P, "q_rs": Q}), q_sem),
                       **{f"q_{x:g}": y for x, y in zip(P, Q)},
                       **{f"dq_{x:g}_pct": (y / r - 1) * 100 for x, y, r in zip(P[1:], Q[1:], q_ref[1:])}})
    res = pd.DataFrame(linhas)
    res.to_csv(SAIDA / "resumo.csv", index=False)
    cols = ["familia", "k", "entrada_rs_mw", "receita_60mw_rs_mw", "p_otima_600k_mw", "lance_rs_mw_ano"] + \
           [c for c in res.columns if c.startswith("dq_")]
    print(res[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
