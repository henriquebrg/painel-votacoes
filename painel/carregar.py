"""Carga e normalização dos arquivos anuais da Câmara."""
import json
import re
from pathlib import Path

import pandas as pd

ALIAS_SIGLAS = {
    "REPUBLICAN": "REPUBLICANOS",
    "SOLIDARIED": "SOLIDARIEDADE",
    "PODEMOS": "PODE",
    "FDR PSDB-CIDADAN": "FDR PSDB-CIDADANIA",
}

CATEGORIAS_VOTO = {
    "Sim": "sim",
    "Não": "nao",
    "Abstenção": "abstencao",
    "Obstrução": "obstrucao",
    "Artigo 17": "artigo17",
    "": "branco",
}

ORIENTACOES = {
    "Sim": "sim",
    "Não": "nao",
    "Obstrução": "obstrucao",
    "Liberado": "liberado",
    "": None,
}

REGIOES = {
    **dict.fromkeys(["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MS", "MT"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}


def normalizar_sigla(s: str) -> str:
    s = s.strip().upper()
    s = re.sub(r"\.\.\.$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIAS_SIGLAS.get(s, s)


def _registros(paths: list[Path]) -> list[dict]:
    registros: list[dict] = []
    for p in paths:
        registros.extend(json.loads(Path(p).read_text(encoding="utf-8"))["dados"])
    return registros


def _mapear(valor: str | None, tabela: dict, rotulo: str):
    chave = valor or ""
    if chave not in tabela:
        raise ValueError(f"{rotulo} desconhecido: {valor!r}")
    return tabela[chave]


def carregar_votacoes(paths: list[Path]) -> pd.DataFrame:
    df = pd.DataFrame(_registros(paths))
    df = df.rename(columns={
        "id": "id_votacao",
        "siglaOrgao": "sigla_orgao",
        "votosSim": "votos_sim",
        "votosNao": "votos_nao",
        "votosOutros": "votos_outros",
    })
    df["data"] = pd.to_datetime(df["data"])
    return df[["id_votacao", "data", "sigla_orgao", "votos_sim", "votos_nao", "votos_outros", "descricao"]]


def filtrar_plenario(votacoes: pd.DataFrame) -> pd.DataFrame:
    return votacoes[votacoes["sigla_orgao"] == "PLEN"].reset_index(drop=True)


def carregar_votos(paths: list[Path]) -> pd.DataFrame:
    linhas = []
    for r in _registros(paths):
        d = r["deputado_"]
        linhas.append({
            "id_votacao": r["idVotacao"],
            "deputado_id": str(d["id"]),
            "nome": d["nome"],
            "partido": normalizar_sigla(d["siglaPartido"]),
            "uf": d["siglaUf"],
            "categoria": _mapear(r["voto"], CATEGORIAS_VOTO, "voto"),
        })
    return pd.DataFrame(linhas, columns=["id_votacao", "deputado_id", "nome", "partido", "uf", "categoria"])


def carregar_orientacoes(paths: list[Path]) -> pd.DataFrame:
    linhas = [
        {
            "id_votacao": r["idVotacao"],
            "bancada": normalizar_sigla(r["siglaBancada"]),
            "orientacao": _mapear(r["orientacao"], ORIENTACOES, "orientação"),
        }
        for r in _registros(paths)
    ]
    return pd.DataFrame(linhas, columns=["id_votacao", "bancada", "orientacao"])
