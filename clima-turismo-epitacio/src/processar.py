"""Lê os CSVs horários do INMET, limpa e agrega em dados diários."""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BRUTOS = RAIZ / "dados" / "brutos"
PROCESSADOS = RAIZ / "dados" / "processados"

# A ordem das colunas é a mesma em todos os anos, mas os nomes mudam
# (acentos, "DATA (YYYY-MM-DD)" x "Data"). Por isso lemos por posição.
COLUNAS = {
    0: "data", 1: "hora", 2: "chuva_mm", 6: "radiacao_kj", 7: "temp",
    9: "temp_max", 10: "temp_min", 15: "umidade", 18: "vento_ms",
}
NOMES_ESTACAO = {"A759": "Bataguassu", "A707": "Presidente Prudente"}
FUSO_LOCAL = -3  # horário de Brasília, o de Presidente Epitácio (sem horário de verão)


def ler_arquivo(caminho: Path) -> pd.DataFrame:
    df = pd.read_csv(
        caminho, sep=";", skiprows=8, header=0, encoding="latin1",
        usecols=list(COLUNAS), names=None, decimal=",", na_values=["-9999", ""],
        dtype=str,
    )
    df.columns = [COLUNAS[i] for i in sorted(COLUNAS)]
    for col in df.columns[2:]:
        df[col] = pd.to_numeric(df[col].str.replace(",", "."), errors="coerce")
    data = df["data"].str.replace("/", "-")
    hora = df["hora"].str.extract(r"(\d{2})")[0]
    utc = pd.to_datetime(data + " " + hora + ":00", format="%Y-%m-%d %H:%M")
    df["momento"] = utc + pd.Timedelta(hours=FUSO_LOCAL)
    df["estacao"] = caminho.name.split("_")[3]
    return df.drop(columns=["data", "hora"])


def limpar(df: pd.DataFrame) -> pd.DataFrame:
    """Remove leituras fisicamente impossíveis (sensor travado ou com defeito)."""
    df = df.copy()
    for col in ("temp", "temp_max", "temp_min"):
        df.loc[(df[col] < -5) | (df[col] > 46), col] = np.nan
    df.loc[(df["umidade"] < 3) | (df["umidade"] > 100), "umidade"] = np.nan
    df.loc[(df["chuva_mm"] < 0) | (df["chuva_mm"] > 120), "chuva_mm"] = np.nan
    df.loc[df["radiacao_kj"] < 0, "radiacao_kj"] = 0
    df.loc[(df["vento_ms"] < 0) | (df["vento_ms"] > 40), "vento_ms"] = np.nan
    return df.drop_duplicates(["estacao", "momento"])


def sensacao_termica(t: pd.Series, ur: pd.Series) -> pd.Series:
    """Índice de calor da NOAA (Rothfusz), em °C. Abaixo de 27 °C usa a própria temperatura."""
    f = t * 9 / 5 + 32
    hi = (-42.379 + 2.04901523 * f + 10.14333127 * ur - 0.22475541 * f * ur
          - 6.83783e-3 * f**2 - 5.481717e-2 * ur**2 + 1.22874e-3 * f**2 * ur
          + 8.5282e-4 * f * ur**2 - 1.99e-6 * f**2 * ur**2)
    hi_c = (hi - 32) * 5 / 9
    return t.where((t < 27) | ur.isna(), hi_c)


def carregar_horario() -> pd.DataFrame:
    arquivos = sorted(BRUTOS.glob("INMET_*.CSV"))
    df = limpar(pd.concat([ler_arquivo(a) for a in arquivos], ignore_index=True))
    df["sensacao"] = sensacao_termica(df["temp"], df["umidade"])
    return df.sort_values(["estacao", "momento"]).reset_index(drop=True)


def agregar_diario(h: pd.DataFrame, min_horas: int = 20) -> pd.DataFrame:
    h = h.assign(dia=h["momento"].dt.normalize())
    g = h.groupby(["estacao", "dia"])
    d = pd.DataFrame({
        "horas_temp": g["temp"].count(),
        "horas_chuva": g["chuva_mm"].count(),
        "temp_max": g["temp_max"].max(),
        "temp_min": g["temp_min"].min(),
        "temp_media": g["temp"].mean(),
        "sensacao_max": g["sensacao"].max(),
        "umidade_media": g["umidade"].mean(),
        "umidade_min": g["umidade"].min(),
        "chuva_mm": g["chuva_mm"].sum(min_count=1),
        "vento_medio": g["vento_ms"].mean(),
        "radiacao_mj": g["radiacao_kj"].sum(min_count=1) / 1000,
    }).reset_index()
    # Dia incompleto vira ausente: preferimos um buraco a uma média enganosa.
    temp_cols = ["temp_max", "temp_min", "temp_media", "sensacao_max", "umidade_media", "umidade_min", "radiacao_mj", "vento_medio"]
    d.loc[d["horas_temp"] < min_horas, temp_cols] = np.nan
    d.loc[d["horas_chuva"] < min_horas, "chuva_mm"] = np.nan
    d["nome"] = d["estacao"].map(NOMES_ESTACAO)
    return d.drop(columns=["horas_temp", "horas_chuva"])


if __name__ == "__main__":
    PROCESSADOS.mkdir(parents=True, exist_ok=True)
    horario = carregar_horario()
    diario = agregar_diario(horario)
    diario.to_csv(PROCESSADOS / "diario.csv", index=False, float_format="%.2f")
    print(diario.groupby("nome").agg(inicio=("dia", "min"), fim=("dia", "max"), dias=("temp_max", "count")))
