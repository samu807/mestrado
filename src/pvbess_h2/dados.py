"""Montagem das séries temporais de entrada (PV, PLD e despacho do ONS no módulo LRCAP).

Quando não há arquivo de dados informado, são geradas séries SINTÉTICAS apenas para
testar o modelo. Para a dissertação, substitua por dados reais, por exemplo:
  - PLD horário: CCEE (https://dadosabertos.ccee.org.br)
  - Irradiância / geração PV: PVGIS, INMET, NSRDB ou medição local
"""

from __future__ import annotations

import warnings
from functools import lru_cache
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


def _perfil_pld(p: Parametros, idx: pd.DatetimeIndex, pld: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Despacho do ONS ligado ao PLD do cenário (proxy do despacho de menor custo).

    Por dia: descarga a potência plena no bloco de `duracao_h` horas consecutivas de maior
    PLD médio após a janela solar (rampa noturna); recarga nas horas de menor PLD dentro de
    `janela_recarga`, com a energia necessária para repor uma descarga completa. A ordem
    (recarga de dia, descarga à noite) garante no máximo 1 ciclo por dia.
    """
    b, lr, d = p.bess, p.lrcap, p.lrcap.despacho_ons
    dt = p.horizonte.dt_h
    h_desc = int(round(lr.duracao_h / dt))
    janela = sorted(d.janela_recarga)
    q = lr.duracao_h / (b.eficiencia_descarga * b.eficiencia_carga) / dt  # p.u.·passo a recarregar
    desc = np.zeros(len(idx))
    rec = np.zeros(len(idx))
    dia = (idx.normalize() - idx[0].normalize()).days
    for dd in np.unique(dia):
        pos = np.flatnonzero(dia == dd)
        horas = idx.hour[pos]
        noite = pos[horas > janela[-1]]
        if len(noite) >= h_desc:
            medias = [pld[noite[i:i + h_desc]].mean() for i in range(len(noite) - h_desc + 1)]
            i0 = int(np.argmax(medias))
            desc[noite[i0:i0 + h_desc]] = 1.0
        dentro = pos[np.isin(horas, janela)]
        restante = q
        for k in dentro[np.argsort(pld[dentro], kind="stable")]:
            if restante <= 1e-9:
                break
            rec[k] = min(1.0, restante)
            restante -= rec[k]
    return desc, rec


def _regra(p: Parametros) -> tuple:
    """Campos que definem o período de descarga usado para ranquear os dias."""
    d = p.lrcap.despacho_ons
    return (d.modo, max(d.janela_recarga), tuple(d.horas_descarga),
            int(round(p.lrcap.duracao_h / p.horizonte.dt_h)))


def _nota_dia(regra: tuple, pld: pd.Series) -> pd.Series:
    """PLD médio de cada dia no período em que o ONS descarregaria (critério de seleção)."""
    modo, fim_janela, horas_descarga, h = regra
    if modo == "pld":   # melhor bloco de h horas após a janela solar, como em _perfil_pld
        noite = pld[pld.index.hour > fim_janela]
        return noite.groupby(noite.index.normalize()).agg(
            lambda x: x.rolling(h).mean().max() if len(x) >= h else -np.inf)
    sel = pld[pld.index.hour.isin(horas_descarga)]
    return sel.groupby(sel.index.normalize()).mean()


def _van_der_corput(k: np.ndarray) -> np.ndarray:
    """Sequência de baixa discrepância em [0, 1) (base 2)."""
    k, v, den = np.asarray(k, dtype=np.int64) + 1, np.zeros(len(k)), 1.0
    while (k > 0).any():
        den *= 2
        v += (k % 2) / den
        k //= 2
    return v


def _maiores(nota: pd.Series, n: float) -> set:
    """Os n dias de maior nota. Empates (ex.: PLD no piso o dia todo) são desfeitos por uma
    sequência de baixa discrepância no dia do ano, que espalha os escolhidos pelo ano em
    vez de favorecer os primeiros dias."""
    desempate = _van_der_corput(nota.index.dayofyear.to_numpy() - 1)
    ordem = np.lexsort((desempate, -nota.round(6).to_numpy()))
    return set(nota.index[ordem[:int(round(min(n, len(nota))))]])


@lru_cache(maxsize=32)
def _dias_selecionados_ano(arquivo: str, fator: float, regra: tuple, ciclos: float) -> frozenset:
    """Dias de despacho de cada ano civil do arquivo de PLD: os N de maior nota."""
    df = pd.read_csv(arquivo, parse_dates=["timestamp"]).set_index("timestamp")
    nota = _nota_dia(regra, df["pld"].astype(float) * fator)
    dias = set()
    for _, g in nota.groupby(nota.index.year):
        dias |= _maiores(g, ciclos)
    return frozenset(dias)


def dias_despacho(p: Parametros, idx: pd.DatetimeIndex, pld: np.ndarray) -> np.ndarray:
    """Máscara horária dos dias com despacho do ONS quando `ciclos_ano` é informado.

    Com PLD de arquivo, a seleção é feita sobre o ano civil inteiro (os N dias de maior
    PLD no período de descarga), de modo que blocos semanais vejam a mesma escolha que o
    ano completo. Com PLD sintético, N é rateado no horizonte.
    """
    n = p.lrcap.despacho_ons.ciclos_ano
    if p.mercado.arquivo:
        arq = Path(p.mercado.arquivo)
        arq = arq if arq.is_absolute() else p.base_dir / arq
        escolhidos = _dias_selecionados_ano(str(arq), float(p.mercado.fator_preco), _regra(p), float(n))
    else:
        nota = _nota_dia(_regra(p), pd.Series(np.asarray(pld, dtype=float), index=idx))
        escolhidos = _maiores(nota, n * len(nota) / 365)
    return np.isin(idx.normalize(), list(escolhidos))


def despacho_ons(p: Parametros, idx: pd.DatetimeIndex, pld: np.ndarray | None = None) -> pd.DataFrame:
    """Perfil de despacho do ONS no módulo LRCAP, por MW contratado (p.u. de P_cap).

    Retorna `descarga_pu`, `recarga_pu` e `soc_pu` (energia armazenada em MWh por MW
    contratado, ao fim de cada intervalo). O módulo começa cheio. Sem arquivo, o
    perfil é gerado assim: descarga a potência plena nas `horas_descarga` dos dias
    selecionados e recarga, nas `horas_recarga`, até encher (limitada à potência
    nominal). O perfil é exógeno ao empreendedor (Portaria MME 136/2026, art. 5º §2º).
    """
    b, lr, d = p.bess, p.lrcap, p.lrcap.despacho_ons
    dt = p.horizonte.dt_h
    e_max = b.soc_max_frac * lr.energia_por_mw_h
    e_min = b.soc_min_frac * lr.energia_por_mw_h
    dia = (idx.normalize() - idx[0].normalize()).days

    if d.arquivo:
        desc = _ler_serie(d.arquivo, p.base_dir, "descarga_pu", idx).to_numpy()
        rec = _ler_serie(d.arquivo, p.base_dir, "recarga_pu", idx).to_numpy()
    elif d.modo == "pld":
        desc, rec_pld = _perfil_pld(p, idx, np.asarray(pld, dtype=float))
        rec = None
    else:
        ativo = np.ones(len(idx), bool) if d.dias is None else np.isin(dia, d.dias)
        desc = (idx.hour.isin(d.horas_descarga) & ativo).astype(float)
        rec = None
    if d.ciclos_ano is not None and not d.arquivo:
        desc = desc * dias_despacho(p, idx, pld)   # sem descarga, o módulo fica cheio e não recarrega

    soc = np.empty(len(idx))
    rec_calc = np.zeros(len(idx))
    e = e_max
    for t in range(len(idx)):
        if rec is None:
            limite = rec_pld[t] if d.modo == "pld" and not d.arquivo else float(idx[t].hour in d.horas_recarga)
            if limite > 0:
                rec_calc[t] = min(limite, max(0.0, (e_max - e) / (b.eficiencia_carga * dt)))
        else:
            rec_calc[t] = rec[t]
        e += (b.eficiencia_carga * rec_calc[t] - desc[t] / b.eficiencia_descarga) * dt
        if e < e_min - 1e-9 or e > e_max + 1e-9:
            raise ValueError(
                f"Despacho ONS inviável em {idx[t]}: SOC do módulo LRCAP = {e:.3f} MWh/MW fora de "
                f"[{e_min:.3f}, {e_max:.3f}]. Revise horas de descarga/recarga ou lrcap.energia_por_mw_h.")
        soc[t] = e

    if np.any(desc > 1 + 1e-9) or np.any(rec_calc > 1 + 1e-9) or np.any(desc * rec_calc > 1e-9):
        raise ValueError("Despacho ONS: potências acima de 1 p.u. ou carga e descarga simultâneas")

    # Limites de ciclos (art. 4º §3º): um ciclo completo = duracao_h horas a P_cap.
    ciclos_dia = pd.Series(desc * dt, index=dia).groupby(level=0).sum() / lr.duracao_h
    if (ciclos_dia > lr.ciclos_max_dia + 1e-9).any():
        warnings.warn(f"Despacho ONS excede {lr.ciclos_max_dia} ciclos completos/dia (art. 4º §3º)")
    horas = len(idx) * dt
    if ciclos_dia.sum() > lr.ciclos_max_ano * horas / 8760 + 1e-9:
        warnings.warn("Despacho ONS excede o limite anual de ciclos, rateado no horizonte (art. 4º §3º)")

    return pd.DataFrame({"descarga_pu": desc, "recarga_pu": rec_calc, "soc_pu": soc}, index=idx)


def montar_series(p: Parametros) -> pd.DataFrame:
    """Retorna DataFrame horário com as séries exógenas do modelo."""
    idx = indice_temporal(p)
    rng = np.random.default_rng(p.mercado.semente)

    if p.pv.arquivo:
        fc = _ler_serie(p.pv.arquivo, p.base_dir, "fator_capacidade", idx)
    else:
        fc = perfil_pv_sintetico(p, idx, rng)

    if p.mercado.arquivo:
        pld = _ler_serie(p.mercado.arquivo, p.base_dir, "pld", idx) * p.mercado.fator_preco
    else:
        pld = pld_sintetico(p, idx, rng)

    ons = despacho_ons(p, idx, pld.to_numpy())
    return pd.DataFrame(
        {
            "pv_disp_mw": p.pv.potencia_pico_mw * fc.values,
            "pld_rs_mwh": pld.values,
            "ons_descarga_pu": ons["descarga_pu"].values,
            "ons_recarga_pu": ons["recarga_pu"].values,
            "ons_soc_pu": ons["soc_pu"].values,
            "dia": (idx.normalize() - idx[0].normalize()).days,
        },
        index=idx,
    )
