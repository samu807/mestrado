import warnings
from pathlib import Path

import numpy as np
import pytest

from pvbess_h2 import carregar_parametros
from pvbess_h2.decomposicao import avaliar_bloco, dividir_em_blocos, resolver_benders

CONFIG = Path(__file__).resolve().parents[1] / "config" / "caso_base.yaml"
warnings.filterwarnings("ignore", category=UserWarning)


def test_divisao_em_blocos():
    bl = dividir_em_blocos("2025-01-01", 365, 7)
    assert len(bl) == 52 and sum(d for _, d in bl) == 365 and bl[-1][1] == 8


def test_corte_reforcado_e_valido():
    """O corte deve limitar superiormente o lucro do bloco em qualquer P_cap."""
    p = carregar_parametros(CONFIG)
    r30 = avaliar_bloco((p, "2025-01-06", 2, 30.0, 1e-6))
    for x in [0.0, 40.0, 60.0]:
        q = avaliar_bloco((p, "2025-01-06", 2, x, 1e-6)).q
        assert r30.c + r30.lam * x >= q - 1e-3 * abs(q)
    assert r30.c + r30.lam * 30.0 == pytest.approx(r30.q, rel=1e-3)


def test_benders_certifica_otimo():
    p = carregar_parametros(CONFIG)
    x, lucro, hist, _ = resolver_benders(p, "2025-01-06", 4, dias_bloco=2, tol=1e-3,
                                         processos=2, verbose=False)
    tab = hist.tabela()
    assert tab.limite_superior_rs.iloc[-1] >= lucro - 1e-6
    assert (tab.limite_superior_rs.iloc[-1] - lucro) / lucro <= 1e-3 + 1e-9
    assert x == 0 or x >= p.lrcap.potencia_min_mw - 1e-6
    # Nenhum ponto de uma grade pode superar o limite superior certificado
    r_cap = p.lrcap.receita_fixa_rs_mw_ano * 4 * 24 / 8760
    for xg in np.linspace(30, 60, 4):
        v = r_cap * xg + sum(avaliar_bloco((p, i, d, xg, 1e-6)).q
                             for i, d in dividir_em_blocos("2025-01-06", 4, 2))
        assert v <= tab.limite_superior_rs.iloc[-1] + 1e-3 * abs(v)


def test_correcao_partidas():
    from pvbess_h2.decomposicao import correcao_partidas
    # Blocos cíclicos: o 2º começa ligado e termina ligado (não conta partida), mas o 1º terminou
    # desligado: na sequência do ano há uma partida a mais na fronteira.
    assert correcao_partidas(500.0, [(0, 0, True), (1, 1, True)]) == 500.0
    # O 2º começa ligado e termina desligado (conta uma partida), e o 1º terminou ligado: uma a menos;
    # o 1º começa desligado: nada muda na volta do ano.
    assert correcao_partidas(500.0, [(0, 1, True), (1, 0, True)]) == -500.0
    # Fronteira imposta (desligado antes do início): cada bloco que começa ligado conta uma partida,
    # mas o anterior terminou ligado em dois dos três casos.
    assert correcao_partidas(500.0, [(1, 1, False), (1, 0, False), (1, 1, False)]) == -1000.0
    assert correcao_partidas(0.0, [(0, 0, True), (1, 1, True)]) == 0.0
    assert correcao_partidas(500.0, [(None, None, True)]) == 0.0


def test_operacao_anual_conta_partidas_da_sequencia():
    # O custo de H2 da operação concatenada usa as partidas da sequência do ano (condição cíclica no ano),
    # e não as contadas bloco a bloco, nas duas fronteiras; e os picos de fluxo são máximos, não somas.
    import numpy as np
    from pvbess_h2 import carregar_parametros
    from pvbess_h2.decomposicao import operacao_anual
    p = carregar_parametros(Path(__file__).resolve().parents[1] / "config" / "referencia_2025.yaml")
    el = p.eletrolisador
    for fronteira in ("ciclica", "lp"):
        df, k = operacao_anual(p, "2025-03-03", 21, 55.0, processos=2, fronteira=fronteira)
        z = (df["p_eletrolisador_mw"].to_numpy() > 1e-6).astype(int)
        partidas = int(np.maximum(z - np.roll(z, 1), 0).sum())
        esperado = el.custo_variavel_rs_kg * df["producao_h2_kg_h"].sum() + el.custo_partida_rs * partidas
        assert k["custo_h2_rs"] == pytest.approx(esperado, abs=1.0)
        assert k["injecao_max_mw"] == pytest.approx(df["fluxo_conexao_mw"].max(), abs=1e-3)
        assert k["injecao_max_mw"] <= p.rede.exportacao_max_mw + 1e-6
