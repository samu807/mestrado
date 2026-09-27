import numpy as np
import pandas as pd
import pytest

from pvbess_h2.importacao import importar_pld_ccee, importar_pvgis


def test_pld_ccee_separador_ponto_e_virgula_e_virgula_decimal(tmp_path):
    arq = tmp_path / "pld.csv"
    arq.write_text(
        "MES_REFERENCIA;SUBMERCADO;DIA;HORA;PLD_HORA\n"
        "202501;SUDESTE;1;0;123,45\n"
        "202501;SUDESTE;1;1;1.234,50\n"
        "202501;SUL;1;0;99,00\n", encoding="utf-8")
    df = importar_pld_ccee(arq, "SE")
    assert list(df.timestamp) == [pd.Timestamp("2025-01-01 00:00"), pd.Timestamp("2025-01-01 01:00")]
    assert np.allclose(df.pld, [123.45, 1234.50])


def test_pld_ccee_separador_virgula(tmp_path):
    arq = tmp_path / "pld.csv"
    arq.write_text("MES_REFERENCIA,SUBMERCADO,DIA,HORA,PLD_HORA\n202502,NORDESTE,28,23,58.6\n")
    df = importar_pld_ccee(arq, "NE")
    assert df.timestamp.iloc[0] == pd.Timestamp("2025-02-28 23:00")
    assert df.pld.iloc[0] == pytest.approx(58.6)


def _pvgis_csv(caminho, ano=2023):
    utc = pd.date_range(f"{ano}-01-01 00:10", f"{ano}-12-31 23:10", freq="h")
    # sol entre 9h e 21h UTC (6h-18h local)
    p = np.where((utc.hour >= 9) & (utc.hour < 21), 500.0, 0.0)
    linhas = ["Latitude (decimal degrees):\t-22.426", "Longitude (decimal degrees):\t-45.453", "",
              "time,P,G(i),H_sun,T2m,WS10m,Int"]
    linhas += [f"{t:%Y%m%d:%H%M},{v},0,0,20,1,0.0" for t, v in zip(utc, p)]
    linhas += ["", "P: PV system power (W)"]
    caminho.write_text("\n".join(linhas))


def test_pvgis_fuso_e_ano_destino(tmp_path):
    arq = tmp_path / "pvgis.csv"
    _pvgis_csv(arq)
    df = importar_pvgis(arq, ano_destino=2024).set_index("timestamp")
    assert len(df) == 8784  # 2024 é bissexto: 29/02 repetido de 28/02
    fc = df.fator_capacidade
    assert fc[pd.Timestamp("2024-03-10 05:00")] == 0.0
    assert fc[pd.Timestamp("2024-03-10 06:00")] == pytest.approx(0.5)  # 9h UTC = 6h local
    assert fc[pd.Timestamp("2024-02-29 12:00")] == pytest.approx(0.5)
