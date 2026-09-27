"""Conversão de dados brutos (CCEE, PVGIS) para os CSVs de entrada do modelo.

- PLD horário (CCEE, dados abertos, conjunto "PLD horário"): arquivo anual com colunas
  MES_REFERENCIA (AAAAMM), SUBMERCADO, DIA, HORA e PLD_HORA. Separador e vírgula
  decimal são detectados automaticamente.
- Geração PV (PVGIS, "Dados horários"/seriescalc, com cálculo de potência para 1 kWp):
  CSV ou JSON com a coluna `time` (AAAAMMDD:HHMM, em UTC) e `P` (W). O fator de
  capacidade é P / (1000 x kWp).

Saídas no formato lido por `dados.py`: `timestamp,pld` e `timestamp,fator_capacidade`,
em horário local (padrão UTC-3, sem horário de verão desde 2019).
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

SUBMERCADOS = {"SE": "SUDESTE", "SUDESTE": "SUDESTE", "S": "SUL", "SUL": "SUL",
               "NE": "NORDESTE", "NORDESTE": "NORDESTE", "N": "NORTE", "NORTE": "NORTE"}


def _normalizar(nome: str) -> str:
    return nome.strip().strip('"').upper().replace(" ", "_")


def _ler_tabela_ccee(arquivo: Path) -> pd.DataFrame:
    texto = arquivo.read_text(encoding="utf-8-sig", errors="replace")
    cabecalho = texto.splitlines()[0]
    sep = ";" if cabecalho.count(";") > cabecalho.count(",") else ","
    df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str)
    df.columns = [_normalizar(c) for c in df.columns]
    return df


def importar_pld_ccee(arquivo: str | Path, submercado: str = "SE") -> pd.DataFrame:
    """Lê o CSV anual de PLD horário da CCEE e retorna `timestamp,pld` do submercado."""
    df = _ler_tabela_ccee(Path(arquivo))
    faltando = {"MES_REFERENCIA", "SUBMERCADO", "DIA", "HORA", "PLD_HORA"} - set(df.columns)
    if faltando:
        raise ValueError(f"{arquivo}: colunas esperadas ausentes {sorted(faltando)}; "
                         f"encontradas {list(df.columns)}")
    alvo = SUBMERCADOS[submercado.upper()]
    df = df[df["SUBMERCADO"].str.strip().str.upper() == alvo]
    if df.empty:
        raise ValueError(f"{arquivo}: nenhum registro para o submercado {alvo}")

    mes = df["MES_REFERENCIA"].str.strip()
    ts = pd.to_datetime(mes.str[:4] + "-" + mes.str[4:6] + "-" + df["DIA"].str.strip().str.zfill(2)) \
        + pd.to_timedelta(df["HORA"].astype(int), unit="h")
    pld = pd.to_numeric(df["PLD_HORA"].str.strip().str.replace(".", "", regex=False)
                        .str.replace(",", ".", regex=False)
                        if df["PLD_HORA"].str.contains(",").any() else df["PLD_HORA"])
    out = pd.DataFrame({"timestamp": ts.values, "pld": pld.values}).sort_values("timestamp")
    if out["timestamp"].duplicated().any():
        raise ValueError(f"{arquivo}: horários duplicados para o submercado {alvo}")
    return out.reset_index(drop=True)


def _ler_pvgis(arquivo: Path) -> pd.DataFrame:
    texto = arquivo.read_text(encoding="utf-8", errors="replace")
    if texto.lstrip().startswith("{"):
        horas = json.loads(texto)["outputs"]["hourly"]
        return pd.DataFrame(horas)[["time", "P"]]
    # CSV: há linhas de metadados antes do cabeçalho e um rodapé de legendas
    linhas = texto.splitlines()
    ini = next(i for i, l in enumerate(linhas) if l.startswith("time,"))
    dados = [linhas[ini]]
    for l in linhas[ini + 1:]:
        if not l[:8].isdigit():
            break
        dados.append(l)
    return pd.read_csv(io.StringIO("\n".join(dados)))[["time", "P"]]


def importar_pvgis(arquivo: str | Path, kwp: float = 1.0, ano_destino: int | None = None,
                   fuso_h: int = -3) -> pd.DataFrame:
    """Lê a série horária do PVGIS e retorna `timestamp,fator_capacidade` em horário local.

    `ano_destino` recoloca a série em outro ano (mesmo mês/dia/hora), para combinar um
    ano de irradiância do PVGIS com o ano do PLD. 29/02 é descartado ou repetido de 28/02.
    """
    df = _ler_pvgis(Path(arquivo))
    utc = pd.to_datetime(df["time"], format="%Y%m%d:%H%M")
    local = (utc + pd.Timedelta(hours=fuso_h)).dt.floor("h")
    fc = (df["P"].astype(float) / (1000.0 * kwp)).clip(0, 1)
    serie = pd.Series(fc.values, index=local.values).groupby(level=0).mean()

    if ano_destino is not None:
        idx = pd.date_range(f"{ano_destino}-01-01", f"{ano_destino}-12-31 23:00", freq="h")
        chave = pd.Series(serie.values, index=pd.MultiIndex.from_arrays(
            [serie.index.month, serie.index.day, serie.index.hour]))
        chave = chave[~chave.index.duplicated()]
        dia_origem = np.where((idx.month == 2) & (idx.day == 29), 28, idx.day)
        valores = chave.reindex(pd.MultiIndex.from_arrays([idx.month, dia_origem, idx.hour])).to_numpy()
        serie = pd.Series(valores, index=idx)
        # Até |fuso_h| horas se perdem no deslocamento de fuso (noite: geração zero).
        # Mais lacunas que isso indicam série incompleta.
        if serie.isna().sum() > abs(fuso_h):
            raise ValueError(f"{arquivo}: série PVGIS incompleta ({serie.isna().sum()} horas sem dado)")
        serie = serie.fillna(0.0)
    return pd.DataFrame({"timestamp": serie.index, "fator_capacidade": serie.values})
