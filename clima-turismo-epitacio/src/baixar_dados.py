"""Baixa os dados históricos do INMET e guarda só as estações usadas no projeto.

O INMET publica um .zip por ano com todas as estações automáticas do Brasil
(cerca de 100 MB cada). Este script baixa ano a ano, extrai apenas as estações
de interesse e apaga o .zip.

Uso:
    python src/baixar_dados.py 2003 2025
"""
import sys
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip"
ESTACOES = ("A759", "A707")  # Bataguassu (MS) e Presidente Prudente (SP)
PASTA_BRUTOS = Path(__file__).resolve().parents[1] / "dados" / "brutos"


def baixar_ano(ano: int, tentativas: int = 3) -> Path:
    destino = PASTA_BRUTOS / f"{ano}.zip"
    for tentativa in range(1, tentativas + 1):
        try:
            req = Request(URL.format(ano=ano), headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=300) as resp, open(destino, "wb") as f:
                while bloco := resp.read(1 << 20):
                    f.write(bloco)
            zipfile.ZipFile(destino).testzip()
            return destino
        except Exception as erro:  # rede instável: tenta de novo
            print(f"  {ano}: tentativa {tentativa} falhou ({erro})")
            time.sleep(5)
    raise RuntimeError(f"Não foi possível baixar {ano}")


def extrair(zip_path: Path) -> list[str]:
    salvos = []
    with zipfile.ZipFile(zip_path) as z:
        for nome in z.namelist():
            if any(f"_{cod}_" in nome for cod in ESTACOES):
                destino = PASTA_BRUTOS / Path(nome).name
                destino.write_bytes(z.read(nome))
                salvos.append(destino.name)
    zip_path.unlink()
    return salvos


if __name__ == "__main__":
    inicio, fim = (int(a) for a in sys.argv[1:3]) if len(sys.argv) > 2 else (2003, 2025)
    PASTA_BRUTOS.mkdir(parents=True, exist_ok=True)
    for ano in range(inicio, fim + 1):
        arquivos = extrair(baixar_ano(ano))
        print(f"{ano}: {len(arquivos)} arquivo(s)")
