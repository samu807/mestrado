"""Montagem das séries temporais de entrada (PV, PLD, janelas/acionamentos do LRCAP).

Quando não há arquivo de dados informado, são geradas séries SINTÉTICAS apenas para
testar o modelo. Para a dissertação, substitua por dados reais, por exemplo:
  - PLD horário: CCEE (https://dadosabertos.ccee.org.br)
  - Irradiância / geração PV: PVGIS, INMET, NSRDB ou medição local
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .parametros import Parametros


def indice_temporal(p: Parametros) -> pd.DatetimeIndex:
    h = p.horizonte
    passos = int(round(24 * h.dias / h.dt_h))
    return pd.date_range(h.inicio, periods=passos, freq=pd.Timedelta(hours=h.dt_h))


def _ler_serie(caminho: str, base_dir: Path, coluna: str, idx: pd.DatetimeIndex) -> pd.Series:
    arq = Path(caminho)
    if not arq.is_absolute():
        arq = base_dir / arq
    df = pd.read_csv(arq, parse_dates=["timestamp"]).set_index("timestamp")
    serie = df[coluna].reindex(idx)
    if serie.isna().any():
        faltantes = serie[serie.isna()].index[:5].tolist()
        raise ValueError(f"{arq}: sem dados de '{coluna}' para {faltantes} ...")
    return serie.astype(float)


def perfil_pv_sintetico(p: Parametros, idx: pd.DatetimeIndex, rng: np.random.Generator) -> pd.Series:
    """Fator de capacidade PV sintético: senoide entre 6h e 18h com nebulosidade diária."""
    hora = idx.hour + idx.minute / 60 + p.horizonte.dt_h / 2  # ponto médio do intervalo
    forma = np.clip(np.sin(np.pi * (hora - 6) / 12), 0, None)
    dias = (idx.normalize() - idx[0].normalize()).days
    fator_dia = 1 - p.pv.nebulosidade * rng.uniform(0, 1, size=dias.max() + 1)
    ruido = np.clip(1 + 0.05 * rng.standard_normal(len(idx)), 0.8, 1.1)
    fc = p.pv.fator_capacidade_pico * forma * fator_dia[dias] * ruido
    return pd.Series(np.clip(fc, 0, 1), index=idx)


def pld_sintetico(p: Parametros, idx: pd.DatetimeIndex, rng: np.random.Generator) -> pd.Series:
    """PLD sintético com formato típico recente: vale ao meio-dia (excesso solar) e
    pico na rampa noturna (17h-21h)."""
    m = p.mercado
    forma = np.array([0.9, 0.85, 0.8, 0.8, 0.85, 0.9, 0.95, 0.9, 0.7, 0.55, 0.45, 0.4,
                      0.4, 0.45, 0.55, 0.7, 0.95, 1.5, 2.2, 2.4, 2.0, 1.5, 1.2, 1.0])
    forma = forma / forma.mean()
    dias = (idx.normalize() - idx[0].normalize()).days
    nivel_dia = m.pld_medio_rs_mwh * rng.lognormal(0, 0.2, size=dias.max() + 1)
    ruido = rng.lognormal(0, 0.1, size=len(idx))
    pld = nivel_dia[dias] * forma[idx.hour] * ruido
    return pd.Series(np.clip(pld, m.pld_min_rs_mwh, m.pld_max_rs_mwh), index=idx)


def montar_series(p: Parametros) -> pd.DataFrame:
    """Retorna DataFrame horário com as séries exógenas do modelo."""
    idx = indice_temporal(p)
    rng = np.random.default_rng(p.mercado.semente)

    if p.pv.arquivo:
        fc = _ler_serie(p.pv.arquivo, p.base_dir, "fator_capacidade", idx)
    else:
        fc = perfil_pv_sintetico(p, idx, rng)

    if p.mercado.arquivo:
        pld = _ler_serie(p.mercado.arquivo, p.base_dir, "pld", idx)
    else:
        pld = pld_sintetico(p, idx, rng)

    janela = idx.hour.isin(p.lrcap.janela_disponibilidade_h).astype(int)
    acion = np.zeros(len(idx), dtype=int)
    for t in p.lrcap.acionamentos:
        if not 0 <= t < len(idx):
            raise ValueError(f"lrcap.acionamentos: índice {t} fora do horizonte (0..{len(idx) - 1})")
        acion[t] = 1

    return pd.DataFrame(
        {
            "pv_disp_mw": p.pv.potencia_pico_mw * fc.values,
            "pld_rs_mwh": pld.values,
            "janela_lrcap": janela,
            "acionamento_lrcap": acion,
            "dia": (idx.normalize() - idx[0].normalize()).days,
        },
        index=idx,
    )
