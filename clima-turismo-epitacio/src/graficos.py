"""Gráficos do projeto, na identidade visual da adame.dev."""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

FIGURAS = Path(__file__).resolve().parents[1] / "figuras"

NAVY = "#1A1E5E"       # textos e títulos
MAGENTA = "#E31C79"    # perfil "praia" e destaque principal
INDIGO = "#3B44B8"     # perfil "passeio" (navy clareado para passar no teste de daltonismo)
AQUA = "#A3D7DF"
CINZA = "#6B6F8A"
GRADE = "#E4E6EF"
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Divergente: frio (índigo) -> confortável (cinza claro) -> quente (magenta)
MAPA_SENSACAO = LinearSegmentedColormap.from_list(
    "sensacao", ["#2A2F8F", "#7C84D6", "#EEEEF2", "#F08AB8", "#B0105C"])
MAPA_SEQ = LinearSegmentedColormap.from_list("seq", ["#F2F8FA", AQUA, "#4A8FB0", NAVY])


def estilo():
    mpl.rcParams.update({
        "font.family": ["Inter", "DejaVu Sans"], "font.size": 11,
        "axes.edgecolor": GRADE, "axes.labelcolor": CINZA, "axes.titlecolor": NAVY,
        "axes.titlesize": 15, "axes.titleweight": "regular", "axes.titlelocation": "left",
        "axes.titlepad": 14, "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": GRADE, "grid.linewidth": 0.8, "xtick.color": CINZA,
        "ytick.color": CINZA, "xtick.major.size": 0, "ytick.major.size": 0,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.3,
        "legend.frameon": False, "text.color": NAVY,
    })


def _fonte(fig, texto):
    """Nota de fonte abaixo do último gráfico, sem encostar nos rótulos do eixo x."""
    ax = [a for a in fig.axes if a.get_label() != "<colorbar>"][-1]
    ax.annotate(texto, xy=(0, 0), xycoords="axes fraction", xytext=(0, -42),
                textcoords="offset points", fontsize=8.5, color=CINZA, ha="left", va="top")


def calendario(resumo: pd.DataFrame, nome="01-calendario-do-visitante.png"):
    """Barras lado a lado: % de dias bons ou excelentes por mês, por perfil."""
    fig, ax = plt.subplots(figsize=(11, 4.8))
    x = np.arange(12)
    largura = 0.38
    for i, (perfil, cor, rotulo) in enumerate([("praia", MAGENTA, "Praia e rio"),
                                               ("passeio", INDIGO, "Passeio, pesca e eventos")]):
        v = resumo[perfil].to_numpy() * 100
        barras = ax.bar(x + (i - 0.5) * (largura + 0.02), v, largura, color=cor, label=rotulo,
                        zorder=3)
        melhor = np.argsort(v)[-3:]
        for j in melhor:
            ax.text(x[j] + (i - 0.5) * (largura + 0.02), v[j] + 1.5, f"{v[j]:.0f}%",
                    ha="center", va="bottom", fontsize=9, color=NAVY)
    ax.set_xticks(x, MESES)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter())
    ax.set_title("Quantos dias do mês têm clima bom para o visitante")
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.02), ncol=2, fontsize=10)
    _fonte(fig, "Dias com índice de conforto ≥ 70 (bom ou excelente). Estação INMET Bataguassu (A759), a 37 km do centro de Epitácio.")
    fig.savefig(FIGURAS / nome)
    return fig


def mapa_horario(tabela: pd.DataFrame, nome="02-melhor-horario-orla.png"):
    """Heatmap mês x hora da sensação térmica média."""
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.grid(False)
    im = ax.imshow(tabela.to_numpy(), aspect="auto", cmap=MAPA_SENSACAO, vmin=14, vmax=38,
                   origin="upper")
    ax.set_yticks(range(12), MESES)
    ax.set_xticks(range(0, 24, 2), [f"{h}h" for h in range(0, 24, 2)])
    for (i, j), v in np.ndenumerate(tabela.to_numpy()):
        if j % 3 == 0 and not np.isnan(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5,
                    color="white" if (v > 32 or v < 18) else NAVY)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cb.outline.set_visible(False)
    cb.set_label("Sensação térmica média (°C)", color=CINZA)
    ax.set_title("A que horas a orla é mais agradável, mês a mês")
    _fonte(fig, "Média da sensação térmica (índice de calor da NOAA) em cada hora, horário de Brasília. Estação INMET Bataguassu (A759).")
    fig.savefig(FIGURAS / nome)
    return fig


def clima_mensal(normais: pd.DataFrame, nome="03-clima-mes-a-mes.png"):
    """Dois painéis com o mesmo eixo x: temperatura e chuva (sem eixo duplo)."""
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.6), sharex=True,
                                 gridspec_kw={"height_ratios": [1.3, 1], "hspace": 0.35})
    x = np.arange(12)
    a1.fill_between(x, normais["temp_min"], normais["temp_max"], color=AQUA, alpha=0.5, lw=0)
    a1.plot(x, normais["temp_max"], color=MAGENTA, lw=2, marker="o", ms=5, label="Máxima média")
    a1.plot(x, normais["temp_min"], color=INDIGO, lw=2, marker="o", ms=5, label="Mínima média")
    for serie, cor, desloc in (("temp_max", MAGENTA, 8), ("temp_min", INDIGO, -14)):
        for j in (normais[serie].idxmax(), normais[serie].idxmin()):
            a1.annotate(f"{normais[serie][j]:.0f}°", (j, normais[serie][j]), xytext=(0, desloc),
                        textcoords="offset points", ha="center", fontsize=9, color=NAVY)
    a1.set_ylabel("°C")
    a1.set_ylim(5, 40)
    a1.legend(loc="lower left", ncol=2, fontsize=10)
    a1.set_title("Temperatura e chuva ao longo do ano")
    a2.bar(x, normais["chuva_mm"], 0.62, color=INDIGO, zorder=3)
    for j, v in enumerate(normais["chuva_mm"]):
        a2.text(j, v + 4, f"{v:.0f}", ha="center", fontsize=8.5, color=NAVY)
    a2.set_ylabel("Chuva (mm/mês)")
    a2.set_xticks(x, MESES)
    a2.set_ylim(0, normais["chuva_mm"].max() * 1.25)
    _fonte(fig, "Médias mensais 2013–2025. Estação INMET Bataguassu (A759).")
    fig.savefig(FIGURAS / nome)
    return fig


def tendencia_calor(anual: pd.DataFrame, nome="04-dias-de-calor-extremo.png"):
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.bar(anual.index, anual["dias_35"], 0.7, color=MAGENTA, zorder=3)
    ok = anual["dias_35"].notna()
    a, b = np.polyfit(anual.index[ok], anual["dias_35"][ok], 1)
    xs = np.array([anual.index.min(), anual.index.max()])
    ax.plot(xs, a * xs + b, color=NAVY, lw=2, ls="--", zorder=4)
    ax.text(xs[1] + 0.4, a * xs[1] + b, f"tendência:\n{a * 10:+.0f} dias por década",
            fontsize=9.5, color=NAVY, va="center")
    for ano in anual["dias_35"].nlargest(2).index:
        ax.text(ano, anual.loc[ano, "dias_35"] + 1, f"{anual.loc[ano, 'dias_35']:.0f}",
                ha="center", fontsize=9, color=NAVY)
    ax.set_xticks(range(2005, anual.index.max() + 1, 2))
    ax.set_title("Dias por ano com máxima de 35 °C ou mais")
    _fonte(fig, "Estação INMET Presidente Prudente (A707), a cerca de 80 km. Anos com menos de 330 dias válidos (2016 e 2022) ficam de fora.")
    fig.savefig(FIGURAS / nome)
    return fig
