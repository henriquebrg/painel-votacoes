"""Orientação aplicável a cada partido: própria, do bloco ou da federação."""
from pathlib import Path

import pandas as pd

from painel.carregar import normalizar_sigla

COLUNAS_BLOCOS = ["bancada_prefixo", "partido", "inicio", "fim", "observacao"]
COLUNAS_APLICAVEL = ["id_votacao", "partido", "orientacao", "fonte"]
CATEGORIAS_BASE = {"sim", "nao", "abstencao", "obstrucao"}
PREFIXO_FEDERACAO = "FDR "


COLUNAS_OBRIGATORIAS = ["bancada_prefixo", "partido", "inicio", "observacao"]


def carregar_tabela_blocos(path: Path) -> pd.DataFrame:
    """Lê blocos.csv; ValueError se uma linha tiver bancada_prefixo, partido, inicio ou observacao vazio."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    df = df[COLUNAS_BLOCOS].copy()
    for i, linha in df.iterrows():
        vazias = [c for c in COLUNAS_OBRIGATORIAS if not linha[c].strip()]
        if vazias:
            # linha do arquivo: +1 do cabeçalho, +1 por começar em 1
            raise ValueError(f"{path}, linha {i + 2}: campo(s) vazio(s) {', '.join(vazias)}")
    df["bancada_prefixo"] = df["bancada_prefixo"].map(normalizar_sigla)
    df["partido"] = df["partido"].map(normalizar_sigla)
    df["inicio"] = pd.to_datetime(df["inicio"])
    df["fim"] = pd.to_datetime(df["fim"].replace("", None))
    return df.reset_index(drop=True)


def _orientacao_herdada(partido, data, bancadas: dict, blocos: pd.DataFrame):
    """(orientação, fonte) vinda de federação ou bloco vigente na data; federação primeiro."""
    vigentes = blocos[
        (blocos.partido == partido)
        & (blocos.inicio <= data)
        & (blocos.fim.isna() | (blocos.fim >= data))
    ]
    candidatos = []
    for prefixo in vigentes.bancada_prefixo:
        fonte = "federacao" if prefixo.startswith(PREFIXO_FEDERACAO) else "bloco"
        for bancada, orientacao in bancadas.items():
            if bancada.startswith(prefixo):
                candidatos.append((fonte != "federacao", orientacao, fonte))
    if not candidatos:
        return None, None
    _, orientacao, fonte = min(candidatos, key=lambda c: c[0])
    return orientacao, fonte


def orientacao_aplicavel(
    orientacoes: pd.DataFrame,
    votacoes: pd.DataFrame,
    votos: pd.DataFrame,
    blocos: pd.DataFrame,
) -> pd.DataFrame:
    """Uma linha por (votação, partido com deputado presente).

    Sem orientação própria, de federação ou de bloco vigente, orientacao e fonte ficam None.
    """
    datas = dict(zip(votacoes.id_votacao, votacoes.data))
    validas = orientacoes[orientacoes.orientacao.notna()]
    por_votacao = {
        i: dict(zip(g.bancada, g.orientacao)) for i, g in validas.groupby("id_votacao")
    }
    linhas = []
    pares = votos[["id_votacao", "partido"]].drop_duplicates()
    for id_votacao, partido in pares.itertuples(index=False):
        bancadas = por_votacao.get(id_votacao, {})
        if partido in bancadas:
            orientacao, fonte = bancadas[partido], "partido"
        elif id_votacao in datas:
            orientacao, fonte = _orientacao_herdada(partido, datas[id_votacao], bancadas, blocos)
        else:
            orientacao, fonte = None, None
        linhas.append({"id_votacao": id_votacao, "partido": partido, "orientacao": orientacao, "fonte": fonte})
    return pd.DataFrame(linhas, columns=COLUNAS_APLICAVEL, dtype=object)


def cobertura(aplicavel: pd.DataFrame, votos: pd.DataFrame) -> float:
    """Fração dos pares (votação, deputado) com voto sim/não/abstenção/obstrução cujo partido recebeu orientação."""
    base = votos[votos.categoria.isin(CATEGORIAS_BASE)][["id_votacao", "partido"]]
    if base.empty:
        return float("nan")
    m = base.merge(aplicavel[["id_votacao", "partido", "orientacao"]], on=["id_votacao", "partido"], how="left")
    return float(m.orientacao.notna().mean())
