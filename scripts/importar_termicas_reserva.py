"""Operação horária das termelétricas de reserva de capacidade (LRCAP), a partir dos dados abertos do ONS.

Não há histórico de baterias contratadas no LRCAP. O análogo brasileiro mais próximo são as termelétricas
contratadas como reserva de capacidade, cujo suprimento começou em agosto de 2026. O ONS publica, por usina e
por hora, a geração programada e a verificada, separadas por motivo de despacho (ordem de mérito,
inflexibilidade, razão elétrica, unit commitment, garantia energética, reserva de potência etc.), no conjunto
"geracao_termica_despacho_2_ho" (bucket público ons-aws-prod-opendata).

O ONS identifica explicitamente parte dessas unidades pelo sufixo "LRC" no nome (ex.: "UTE Linhares LRC1"). As
demais precisam ser confirmadas na lista oficial de vencedores (EPE, Informe Vencedores LRC 2021; ANEEL, Leilão
nº 11/2021). A lista USINAS abaixo reúne as unidades com sufixo LRC e as citadas como vencedoras na imprensa que
entraram em operação no período; edite-a quando a lista oficial for conferida.

Saídas: data/ons_termicas_reserva.csv (hora, usina, disponibilidade, geração verificada total e por motivo) e
        resultados/termicas_reserva/resumo.csv (dias acionados, horas, duração dos acionamentos, perfil horário).

Uso:  python scripts/importar_termicas_reserva.py [--inicio 2026-08] [--fim 2026-11]
"""

import argparse
import io
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
URL = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/geracao_termica_despacho_2_ho/GERACAO_TERMICA_DESPACHO-2_{a}_{m:02d}.parquet"
USINAS = {   # nome no ONS -> como a usina foi identificada
    "UTE Linhares LRC1": "sufixo LRC no cadastro do ONS",
    "UTE Linhares LRC4": "sufixo LRC no cadastro do ONS",
    "Azulão": "vencedora do LRCAP 2021 (Eneva); entrada em ago/2026",
}
MOTIVOS = ["ordemmerito", "inflexibilidade", "razaoeletrica", "unitcommitment", "garantiaenergetica",
           "reservapotencia", "gsub", "exportacao", "constrainedoff"]
LIGADA_MW = 1.0


def baixar(inicio, fim):
    partes = []
    for per in pd.period_range(inicio, fim, freq="M"):
        url = URL.format(a=per.year, m=per.month)
        with urllib.request.urlopen(url, timeout=120) as r:
            x = pd.read_parquet(io.BytesIO(r.read()))
        partes.append(x[x.nom_usina.isin(USINAS)])
        print(f"{per}: {partes[-1].nom_usina.nunique()} usinas", flush=True)
    x = pd.concat(partes)
    out = pd.DataFrame({"timestamp": pd.to_datetime(x.din_instante), "usina": x.nom_usina, "ceg": x.ceg,
                        "disponibilidade_mw": pd.to_numeric(x.val_progdisponibilidade, errors="coerce"),
                        "geracao_mw": pd.to_numeric(x.val_verifgeracao, errors="coerce")})
    for m in MOTIVOS:
        out[f"ger_{m}_mw"] = pd.to_numeric(x[f"val_verif{m}"], errors="coerce")
    return out.sort_values(["usina", "timestamp"]).reset_index(drop=True)


def resumo(d):
    linhas = []
    for u, g in d.groupby("usina"):
        g = g.set_index("timestamp")
        on = g.geracao_mw > LIGADA_MW
        dias = on.groupby(g.index.normalize()).any()
        blocos = on.groupby((on != on.shift()).cumsum()).sum()
        blocos = blocos[blocos > 0]
        motivos = {m: g[f"ger_{m}_mw"].sum() for m in MOTIVOS}
        total = max(sum(motivos.values()), 1e-9)
        linhas.append({
            "usina": u, "identificacao": USINAS[u], "inicio": g.index.min().date(), "fim": g.index.max().date(),
            "disponibilidade_max_mw": g.disponibilidade_mw.max(), "geracao_gwh": g.geracao_mw.sum() / 1e3,
            "dias": len(dias), "dias_acionada": int(dias.sum()), "acionamentos": len(blocos),
            "duracao_mediana_h": float(blocos.median()) if len(blocos) else 0.0,
            "duracao_max_h": float(blocos.max()) if len(blocos) else 0.0,
            **{f"motivo_{m}_pct": 100 * v / total for m, v in motivos.items()},
            **{f"ligada_h{h:02d}": v for h, v in on.groupby(g.index.hour).mean().items()},
        })
    return pd.DataFrame(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", default="2026-08")
    ap.add_argument("--fim", default="2026-11")
    args = ap.parse_args()
    d = baixar(args.inicio, args.fim)
    d.to_csv(RAIZ / "data" / "ons_termicas_reserva.csv", index=False)
    saida = RAIZ / "resultados" / "termicas_reserva"
    saida.mkdir(parents=True, exist_ok=True)
    r = resumo(d)
    r.to_csv(saida / "resumo.csv", index=False)
    print(r[["usina", "inicio", "fim", "disponibilidade_max_mw", "dias", "dias_acionada", "acionamentos",
             "duracao_mediana_h", "motivo_razaoeletrica_pct", "motivo_unitcommitment_pct"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
