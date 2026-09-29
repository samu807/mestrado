import copy
import warnings
from pathlib import Path

import numpy as np
import pytest

from pvbess_h2 import carregar_parametros, montar_series
from pvbess_h2.estocastico import avaliar_potencia, cvar, parametros_cenario, resolver_estocastico

CONFIG = Path(__file__).resolve().parents[1] / "config" / "estocastico_unifei.yaml"
warnings.filterwarnings("ignore", category=UserWarning)


def caso_pequeno(beta=0.0):
    p = carregar_parametros(CONFIG)
    p.estocastico.cenarios = p.estocastico.cenarios[:2]      # 2021 e 2022
    p.estocastico.dias_por_cenario = 4
    p.estocastico.dias_bloco = 2
    p.estocastico.beta = beta
    return p


def test_cvar_com_cenarios_equiprovaveis():
    v, pr = [10, 20, 30, 40, 50], [0.2] * 5
    assert cvar(v, pr, 0.8) == pytest.approx(10)          # pior cenário
    assert cvar(v, pr, 0.6) == pytest.approx(15)          # média dos 2 piores
    assert cvar(v, pr, 0.95) == pytest.approx(10)


def test_despacho_ligado_ao_pld():
    p = carregar_parametros(CONFIG)
    q = parametros_cenario(p, p.estocastico.cenarios[4])
    q.horizonte.inicio, q.horizonte.dias = "2025-08-04", 3
    s = montar_series(q)
    for _, dia in s.groupby("dia"):
        desc = dia[dia.ons_descarga_pu > 0]
        assert len(desc) == 4 and (desc.index.hour > 16).all()
        # descarga no bloco de 4 h de maior PLD médio após a janela solar
        noite = dia[dia.index.hour > 16].pld_rs_mwh.to_numpy()
        melhor = max(noite[i:i + 4].mean() for i in range(len(noite) - 3))
        assert desc.pld_rs_mwh.mean() == pytest.approx(melhor)
        assert (dia[dia.ons_recarga_pu > 0].index.hour.isin(range(8, 17))).all()


def test_fator_preco_corrige_pld():
    p = carregar_parametros(CONFIG)
    q = parametros_cenario(p, p.estocastico.cenarios[0])
    q.horizonte.inicio, q.horizonte.dias = "2021-03-01", 1
    s1 = montar_series(q)
    q.mercado.fator_preco = 1.0
    s0 = montar_series(q)
    assert np.allclose(s1.pld_rs_mwh, s0.pld_rs_mwh * 1.2097)


def test_benders_estocastico_certifica_e_bate_com_avaliacao():
    p = caso_pequeno(beta=1.0)
    av, hist, _ = resolver_estocastico(p, tol=1e-3, processos=2, verbose=False)
    ub = hist.limite_superior_rs.iloc[-1]
    assert ub >= av.objetivo - 1e-6
    assert av.p_cap == 0 or av.p_cap >= 30 - 1e-6
    # a avaliação direta no P ótimo reproduz o lucro dos cenários
    direto = avaliar_potencia(p, av.p_cap, processos=2)
    assert np.allclose(direto.lucro_cenarios, av.lucro_cenarios, rtol=1e-3)
    # nenhum ponto de uma grade supera o limite superior certificado
    for x in [30, 45, 60]:
        assert avaliar_potencia(p, x, processos=2).objetivo <= ub + 1e-3 * abs(ub)


def test_memoria_reaproveita_cortes_entre_betas():
    memoria = {}
    resolver_estocastico(caso_pequeno(0.0), processos=2, verbose=False, memoria=memoria)
    n = len(memoria["cortes"])
    av, _, _ = resolver_estocastico(caso_pequeno(2.0), processos=2, verbose=False, memoria=memoria)
    assert len(memoria["cortes"]) >= n and av.objetivo == pytest.approx(
        np.mean(av.lucro_cenarios) + 2.0 * cvar(av.lucro_cenarios, [0.5, 0.5], 0.8))
