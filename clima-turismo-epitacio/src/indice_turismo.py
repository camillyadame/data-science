"""Índice de conforto climático para turismo de rio e praia.

Adaptação do Holiday Climate Index: Beach (Scott, Rutty, Amelung e Tang, 2016),
que combina quatro componentes avaliados de 0 a 10:

    ICT = 2 x conforto térmico + 4 x céu aberto + 3 x chuva + 1 x vento   (0 a 100)

O índice original usa cobertura de nuvens, que as estações automáticas do INMET
não medem. Aqui o "céu aberto" vem da radiação solar do dia comparada com um dia
limpo do mesmo mês (percentil 95). As faixas de cada nota são escolhas deste
projeto. Há dois perfis de visitante, que só diferem no conforto térmico:

- "praia": quem vem para nadar e curtir as praias do Rio Paraná (ideal: sensação
  máxima entre 28 e 33 °C);
- "passeio": quem vem para a orla, pescar, passear de barco ou ir a eventos
  (ideal: sensação máxima entre 22 e 28 °C).
"""
import numpy as np
import pandas as pd

PESOS = {"nota_termica": 2, "nota_sol": 4, "nota_chuva": 3, "nota_vento": 1}

# (limite superior da faixa, nota)
FAIXAS_TERMICAS = {
    "praia": [(18, 0), (21, 2), (24, 4), (26, 6), (28, 8), (33, 10),
              (35, 8), (37, 6), (39, 4), (41, 2), (np.inf, 0)],
    "passeio": [(12, 0), (15, 2), (18, 4), (20, 6), (22, 8), (28, 10),
                (30, 8), (32, 6), (34, 4), (36, 2), (38, 1), (np.inf, 0)],
}
FAIXAS_CHUVA = [(0.2, 10), (3, 8), (6, 5), (12, 2), (np.inf, 0)]
FAIXAS_VENTO = [(0.5, 8), (3, 10), (5, 7), (8, 4), (np.inf, 0)]

CLASSES = [(0, "Desfavorável"), (60, "Aceitável"), (70, "Bom"), (80, "Excelente")]


def _nota(valores: pd.Series, faixas) -> pd.Series:
    limites = [f[0] for f in faixas]
    notas = np.array([f[1] for f in faixas], dtype=float)
    idx = np.searchsorted(limites, valores.to_numpy(), side="left")
    resultado = notas[np.clip(idx, 0, len(notas) - 1)]
    return pd.Series(np.where(valores.isna(), np.nan, resultado), index=valores.index)


def calcular(diario: pd.DataFrame, perfil: str = "praia") -> pd.DataFrame:
    d = diario.copy()
    d["perfil"] = perfil
    d["mes"] = pd.to_datetime(d["dia"]).dt.month
    ceu_limpo = d.groupby(["estacao", "mes"])["radiacao_mj"].transform(lambda s: s.quantile(0.95))
    d["fracao_sol"] = (d["radiacao_mj"] / ceu_limpo).clip(upper=1)

    d["nota_termica"] = _nota(d["sensacao_max"], FAIXAS_TERMICAS[perfil])
    d["nota_sol"] = (d["fracao_sol"] * 10).round()
    d["nota_chuva"] = _nota(d["chuva_mm"], FAIXAS_CHUVA)
    d["nota_vento"] = _nota(d["vento_medio"], FAIXAS_VENTO)

    d["indice"] = sum(d[col] * peso for col, peso in PESOS.items())
    limites = [c[0] for c in CLASSES]
    rotulos = [c[1] for c in CLASSES]
    d["classe"] = pd.cut(d["indice"], bins=limites + [101], labels=rotulos, right=False)
    return d
