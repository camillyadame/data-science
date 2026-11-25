"""Exporta um resumo pequeno da análise para a página interativa do portfólio.

Lê dados/processados/diario.csv e gera dados/processados/resumo_web.json com:

- "mensal": por mês, % de dias bons nos dois perfis e as médias de clima
  (estação Bataguassu, A759);
- "anual": dias com máxima de 35 °C ou mais em Presidente Prudente (A707),
  só anos com pelo menos 330 dias válidos;
- "por_hora": sensação térmica média por mês e hora (12 x 24). Só é gerado
  quando os dados brutos horários estão em dados/brutos/ (baixar_dados.py).

Uso:
    python src/exportar_web.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import indice_turismo as it  # noqa: E402
import processar as pr  # noqa: E402

SAIDA = pr.PROCESSADOS / "resumo_web.json"


def _r(v, casas=1):
    return None if pd.isna(v) else round(float(v), casas)


def mensal(diario: pd.DataFrame) -> list[dict]:
    bata = diario[diario["estacao"] == "A759"].copy()
    datas = pd.to_datetime(bata["dia"])
    bata["mes"], bata["ano"] = datas.dt.month, datas.dt.year

    # Chuva mensal: só meses com pelo menos 25 dias medidos, como na análise.
    chuva = bata.groupby(["ano", "mes"])["chuva_mm"].agg(["sum", "count"])
    chuva = chuva[chuva["count"] >= 25]["sum"].groupby("mes").mean()

    bons = {}
    for perfil in ("praia", "passeio"):
        d = it.calcular(bata, perfil)
        d = d[d["indice"].notna()]
        bons[perfil] = d.groupby("mes")["indice"].apply(lambda s: (s >= 70).mean() * 100)
        bons[perfil + "_n"] = d.groupby("mes")["indice"].count()

    g = bata.groupby("mes")
    linhas = []
    for mes in range(1, 13):
        m = g.get_group(mes)
        linhas.append({
            "mes": mes,
            "bons_praia": _r(bons["praia"][mes], 0),
            "bons_passeio": _r(bons["passeio"][mes], 0),
            "dias_avaliados": int(bons["praia_n"][mes]),
            "temp_max": _r(m["temp_max"].mean()),
            "temp_min": _r(m["temp_min"].mean()),
            "sensacao_max": _r(m["sensacao_max"].mean()),
            "chuva_mm": _r(chuva.get(mes), 0),
            "dias_chuva": _r((m["chuva_mm"].dropna() >= 1).mean() * 30.4),
        })
    return linhas


def anual(diario: pd.DataFrame) -> list[dict]:
    pp = diario[diario["estacao"] == "A707"].copy()
    pp["ano"] = pd.to_datetime(pp["dia"]).dt.year
    a = pp.groupby("ano").agg(dias_validos=("temp_max", "count"),
                              dias_35=("temp_max", lambda s: int((s >= 35).sum())))
    return [{"ano": int(ano), "dias_validos": int(l.dias_validos),
             "dias_35": int(l.dias_35), "completo": bool(l.dias_validos >= 330)}
            for ano, l in a.iterrows()]


def por_hora() -> list[list[float]] | None:
    if not any(pr.BRUTOS.glob("INMET_*.CSV")):
        return None
    h = pr.carregar_horario()
    h = h[h["estacao"] == "A759"]
    tabela = h.pivot_table(index=h["momento"].dt.month, columns=h["momento"].dt.hour,
                           values="sensacao", aggfunc="mean")
    return [[_r(tabela.loc[m, hr]) for hr in range(24)] for m in range(1, 13)]


if __name__ == "__main__":
    diario = pd.read_csv(pr.PROCESSADOS / "diario.csv")
    resumo = {
        "fonte": "INMET, Dados Históricos. Bataguassu (A759) 2013–2025; Presidente Prudente (A707) 2003–2025.",
        "mensal": mensal(diario),
        "anual": anual(diario),
        "por_hora": por_hora(),
    }
    SAIDA.write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Salvo em {SAIDA.relative_to(pr.RAIZ)}"
          + ("" if resumo["por_hora"] else " (sem a tabela por hora: dados brutos ausentes)"))
