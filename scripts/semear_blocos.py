"""Gera o rascunho da tabela de blocos e federações da 57ª legislatura.

Uso: uv run python scripts/semear_blocos.py SAIDA.csv [ARQUIVOS_DE_ORIENTACOES...]

- Consulta a API v2 da Câmara (/blocos e /blocos/{id}/partidos). A API só traz
  os blocos vigentes, sem datas: as linhas saem com `inicio` vazio.
- Acrescenta as três federações da legislatura (fixas desde 2023-02-01).
- Se forem passados arquivos votacoesOrientacoes-*.json, lista as bancadas
  "BL ..." observadas com primeira e última aparição, em linhas sem partido,
  como evidência para completar à mão os blocos já encerrados.

O rascunho é revisado à mão e salvo em data/curado/blocos.csv.
"""
import csv
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from painel.carregar import carregar_orientacoes, normalizar_sigla  # noqa: E402

API = "https://dadosabertos.camara.leg.br/api/v2"
CABECALHO = {"Accept": "application/json"}
INICIO_LEGISLATURA = "2023-02-01"
FEDERACOES = {
    "FDR PT-PCDOB-PV": ["PT", "PCDOB", "PV"],
    "FDR PSOL-REDE": ["PSOL", "REDE"],
    "FDR PSDB-CIDADANIA": ["PSDB", "CIDADANIA"],
}
COLUNAS = ["bancada_prefixo", "partido", "inicio", "fim", "observacao"]


def _get(caminho: str) -> list[dict]:
    resp = requests.get(f"{API}{caminho}", headers=CABECALHO, timeout=60)
    resp.raise_for_status()
    time.sleep(0.5)
    return resp.json()["dados"]


def linhas_api() -> list[dict]:
    linhas = []
    for bloco in _get("/blocos?idLegislatura=57&itens=100"):
        if bloco["federacao"]:
            continue  # federações entram pela lista fixa
        partidos = _get(f"/blocos/{bloco['id']}/partidos")
        for p in partidos:
            linhas.append({
                "bancada_prefixo": "",
                "partido": normalizar_sigla(p["sigla"]),
                "inicio": "",
                "fim": "",
                "observacao": f"API /blocos/{bloco['id']} ({bloco['nome']}); prefixo e datas a completar",
            })
    return linhas


def linhas_federacoes() -> list[dict]:
    return [
        {
            "bancada_prefixo": prefixo,
            "partido": partido,
            "inicio": INICIO_LEGISLATURA,
            "fim": "",
            "observacao": "federação fixa na 57ª legislatura (API /blocos, federacao=true)",
        }
        for prefixo, partidos in FEDERACOES.items()
        for partido in partidos
    ]


def linhas_evidencia(arquivos_orientacoes: list[Path], arquivos_votacoes: list[Path]) -> list[dict]:
    import pandas as pd

    from painel.carregar import carregar_votacoes, filtrar_plenario

    o = carregar_orientacoes(arquivos_orientacoes)
    v = filtrar_plenario(carregar_votacoes(arquivos_votacoes))[["id_votacao", "data"]]
    o = o[o.bancada.str.startswith("BL")].merge(v, on="id_votacao")
    g = o.groupby("bancada").agg(inicio=("data", "min"), fim=("data", "max"), n=("id_votacao", "nunique"))
    return [
        {
            "bancada_prefixo": bancada,
            "partido": "",
            "inicio": pd.Timestamp(r.inicio).date().isoformat(),
            "fim": pd.Timestamp(r.fim).date().isoformat(),
            "observacao": f"observado nas orientações: {r.n} votações; membros a completar",
        }
        for bancada, r in g.sort_values("inicio").iterrows()
    ]


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        sys.exit(__doc__)
    saida = Path(argv[1])
    orientacoes = [Path(a) for a in argv[2:]]
    votacoes = [p.with_name(p.name.replace("votacoesOrientacoes", "votacoes")) for p in orientacoes]
    linhas = linhas_api() + linhas_federacoes()
    if orientacoes:
        linhas += linhas_evidencia(orientacoes, votacoes)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} linhas em {saida}")


if __name__ == "__main__":
    main(sys.argv)
