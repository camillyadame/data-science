"""Testes das regras de limpeza e do índice de conforto.

Rodar a partir da pasta do projeto:
    python -m pytest tests
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import indice_turismo as it  # noqa: E402
import processar as pr  # noqa: E402


# ---------- _nota: faixas viram notas ----------

def test_nota_chuva_por_faixa():
    chuva = pd.Series([0.0, 0.2, 1.0, 3.0, 5.0, 10.0, 50.0])
    assert it._nota(chuva, it.FAIXAS_CHUVA).tolist() == [10, 10, 8, 8, 5, 2, 0]


def test_nota_mantem_ausente():
    notas = it._nota(pd.Series([np.nan, 0.0]), it.FAIXAS_CHUVA)
    assert np.isnan(notas.iloc[0])
    assert notas.iloc[1] == 10


def test_faixa_ideal_de_cada_perfil():
    sensacao = pd.Series([30.0, 25.0])
    praia = it._nota(sensacao, it.FAIXAS_TERMICAS["praia"]).tolist()
    passeio = it._nota(sensacao, it.FAIXAS_TERMICAS["passeio"]).tolist()
    assert praia == [10, 6]    # praia gosta de 28 a 33 °C
    assert passeio == [8, 10]  # passeio gosta de 22 a 28 °C


def test_pesos_somam_10():
    # cada nota vai de 0 a 10, então o índice vai de 0 a 100
    assert sum(it.PESOS.values()) == 10


# ---------- sensação térmica ----------

def test_sensacao_abaixo_de_27_e_a_propria_temperatura():
    t = pd.Series([20.0, 26.9])
    ur = pd.Series([90.0, 90.0])
    assert pr.sensacao_termica(t, ur).tolist() == [20.0, 26.9]


def test_sensacao_com_calor_e_umidade():
    # 30 °C com 70% de umidade: índice de calor da NOAA perto de 35 °C
    valor = pr.sensacao_termica(pd.Series([30.0]), pd.Series([70.0])).iloc[0]
    assert valor == pytest.approx(35.0, abs=0.5)


def test_sensacao_sem_umidade_usa_temperatura():
    valor = pr.sensacao_termica(pd.Series([32.0]), pd.Series([np.nan])).iloc[0]
    assert valor == 32.0


# ---------- limpeza e agregação ----------

def _leituras(horas, temp=25.0, **extra):
    inicio = pd.Timestamp("2024-01-10 00:00")
    base = {
        "estacao": "A759",
        "momento": [inicio + pd.Timedelta(hours=h) for h in range(horas)],
        "temp": temp, "temp_max": temp, "temp_min": temp, "umidade": 60.0,
        "chuva_mm": 0.0, "radiacao_kj": 500.0, "vento_ms": 2.0, "sensacao": temp,
    }
    base.update(extra)
    return pd.DataFrame(base)


def test_limpar_remove_valores_impossiveis():
    df = _leituras(3)
    df.loc[0, "temp"] = 60.0          # sensor quebrado
    df.loc[1, "radiacao_kj"] = -3.0   # ruído noturno
    df.loc[2, "umidade"] = 150.0
    limpo = pr.limpar(df)
    assert np.isnan(limpo.loc[0, "temp"])
    assert limpo.loc[1, "radiacao_kj"] == 0
    assert np.isnan(limpo.loc[2, "umidade"])


def test_dia_incompleto_vira_ausente():
    completo = pr.agregar_diario(_leituras(24))
    incompleto = pr.agregar_diario(_leituras(10))
    assert completo["temp_max"].iloc[0] == 25.0
    assert np.isnan(incompleto["temp_max"].iloc[0])


def test_dia_sem_chuva_medida_nao_vira_zero():
    diario = pr.agregar_diario(_leituras(24, chuva_mm=np.nan))
    assert np.isnan(diario["chuva_mm"].iloc[0])
