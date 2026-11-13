"""Regra de alinhamento, janelas de tempo e índices por deputado."""
from itertools import product
from math import sqrt

import numpy as np
import pandas as pd

from painel.carregar import CATEGORIAS_VOTO, ORIENTACOES, REGIOES
from painel.orientacao_partido import CATEGORIAS_BASE

BANCADA_GOVERNO = "GOVERNO"
ORIENTACOES_VALIDAS = {"sim", "nao", "obstrucao"}
CATEGORIAS_FORA = {"artigo17", "branco"}
MODOS = ("movel", "trimestre", "legislatura")
TRIMESTRES_MOVEL = 4
MIN_COLEGAS_MAIORIA = 3
_ORDEM_BASE = ["sim", "nao", "abstencao", "obstrucao"]

COLUNAS_INDICES = [
    "janela", "modo", "deputado_id", "nome", "partido", "uf", "regiao",
    "n_gov", "alinh_gov", "ic_gov_inf", "ic_gov_sup",
    "n_par", "alinh_par", "ic_par_inf", "ic_par_sup",
    "n_maioria", "alinh_maioria", "ic_maioria_inf", "ic_maioria_sup",
    "n_artigo17", "n_branco",
]
COLUNAS_NAO_ORIENTACAO = ["janela", "modo", "partido", "n_votacoes", "n_sem_orientacao", "taxa_sem_orientacao"]


def seguiu(categoria: str, orientacao: str | None) -> bool | None:
    """True/False se o voto conta para o alinhamento; None se é excluído."""
    if orientacao not in ORIENTACOES_VALIDAS:
        return None
    if categoria in CATEGORIAS_FORA:
        return None
    return categoria == orientacao


# Tabela (categoria, orientação) → resultado, derivada de `seguiu` para aplicá-la de forma vetorizada.
_TABELA_SEGUIU = {
    (c, o): seguiu(c, o)
    for c, o in product(set(CATEGORIAS_VOTO.values()), set(ORIENTACOES.values()))
}


def _seguiu_vetor(categoria: pd.Series, orientacao: pd.Series) -> pd.Series:
    oris = [None if pd.isna(o) else o for o in orientacao.astype(object)]
    valores = [_TABELA_SEGUIU.get(par) for par in zip(categoria, oris)]
    return pd.Series(valores, index=categoria.index, dtype=object)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centro = (p + z2 / (2 * n)) / denom
    meia = z * sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (max(0.0, centro - meia), min(1.0, centro + meia))


def trimestre(d) -> str:
    d = pd.Timestamp(d)
    return f"{d.year}T{d.quarter}"


def _anteriores(t: str, n: int) -> list[str]:
    """Os n trimestres de calendário terminando em t, do mais antigo ao mais recente."""
    ano, q = int(t[:4]), int(t[5:])
    indice = ano * 4 + (q - 1)
    return [f"{i // 4}T{i % 4 + 1}" for i in range(indice - n + 1, indice + 1)]


def janelas(trimestres: list[str], modo: str) -> dict[str, list[str]]:
    if modo not in MODOS:
        raise ValueError(f"modo desconhecido: {modo!r}")
    ordenados = sorted(set(trimestres))
    if modo == "legislatura":
        return {"legislatura": ordenados}
    if modo == "trimestre":
        return {t: [t] for t in ordenados}
    presentes = set(ordenados)
    return {t: [x for x in _anteriores(t, TRIMESTRES_MOVEL) if x in presentes] for t in ordenados}


def _como_objeto(s: pd.Series) -> pd.Series:
    s = s.astype(object)
    return s.where(s.notna(), None)


def _maioria_dos_colegas(votos: pd.DataFrame) -> pd.Series:
    """Voto mais comum entre os outros deputados do mesmo partido na votação (None se < 3 colegas ou empate)."""
    contaveis = votos[votos.categoria.isin(CATEGORIAS_BASE)]
    contagem = (
        pd.crosstab([contaveis.id_votacao, contaveis.partido], contaveis.categoria)
        .reindex(columns=_ORDEM_BASE, fill_value=0)
    )
    chaves = pd.MultiIndex.from_frame(votos[["id_votacao", "partido"]])
    colegas = contagem.reindex(chaves, fill_value=0).to_numpy(dtype=int)
    proprio = np.stack([(votos.categoria == c).to_numpy() for c in _ORDEM_BASE], axis=1)
    colegas = colegas - proprio.astype(int)
    total = colegas.sum(axis=1)
    maximo = colegas.max(axis=1)
    empates = (colegas == maximo[:, None]).sum(axis=1)
    escolha = np.array(_ORDEM_BASE, dtype=object)[colegas.argmax(axis=1)]
    valida = (total >= MIN_COLEGAS_MAIORIA) & (empates == 1)
    return pd.Series(np.where(valida, escolha, None), index=votos.index, dtype=object)


def marcar_alinhamento(votos, votacoes, orientacoes, aplicavel) -> pd.DataFrame:
    """votos + data, trimestre e o resultado de cada comparação (governo, partido, maioria da bancada).

    seguiu_gov e seguiu_partido aplicam `seguiu` (regra para orientações). seguiu_maioria NÃO usa
    `seguiu`: a maioria dos colegas não é uma orientação. É True quando a categoria do deputado é igual
    à categoria mais votada pelos colegas, inclusive quando essa maioria é abstencao ou obstrucao
    (abstenção é tratada como posição deliberada). None se o deputado não votou sim/nao/abstencao/obstrucao,
    se há menos de 3 colegas contáveis ou se há empate.
    """
    m = votos.merge(votacoes[["id_votacao", "data"]], on="id_votacao", how="left")
    m["trimestre"] = m.data.dt.year.astype("Int64").astype(str) + "T" + m.data.dt.quarter.astype("Int64").astype(str)
    m.loc[m.data.isna(), "trimestre"] = None

    gov = (
        orientacoes[orientacoes.bancada == BANCADA_GOVERNO]
        .drop_duplicates("id_votacao")[["id_votacao", "orientacao"]]
        .rename(columns={"orientacao": "orient_gov"})
    )
    m = m.merge(gov, on="id_votacao", how="left")
    m["orient_gov"] = _como_objeto(m.orient_gov)
    m["seguiu_gov"] = _seguiu_vetor(m.categoria, m.orient_gov)

    par = aplicavel[["id_votacao", "partido", "orientacao"]].rename(columns={"orientacao": "orient_partido"})
    m = m.merge(par, on=["id_votacao", "partido"], how="left")
    m["orient_partido"] = _como_objeto(m.orient_partido)
    m["seguiu_partido"] = _seguiu_vetor(m.categoria, m.orient_partido)

    maioria = _maioria_dos_colegas(m)
    # Igualdade de categorias, não `seguiu`: a maioria não é orientação (abstencao da maioria é posição).
    sm = pd.Series(
        np.where(m.categoria.to_numpy(object) == maioria.to_numpy(object), True, False), index=m.index, dtype=object
    )
    sm[maioria.isna() | ~m.categoria.isin(CATEGORIAS_BASE)] = None
    m["seguiu_maioria"] = sm
    return m


def _indice(grupos, coluna: str, prefixo: str) -> pd.DataFrame:
    n = grupos[coluna].count().astype(int)
    k = grupos[coluna].sum().astype(int)
    ic = [wilson(ki, ni) for ki, ni in zip(k, n)]
    return pd.DataFrame({
        f"n_{prefixo}": n,
        f"alinh_{prefixo}": np.where(n > 0, k / n.where(n > 0, 1), np.nan),
        f"ic_{prefixo}_inf": [lo for lo, _ in ic],
        f"ic_{prefixo}_sup": [hi for _, hi in ic],
    })


def indices(marcado: pd.DataFrame, modo: str) -> pd.DataFrame:
    """Uma linha por (janela, deputado) com os índices de alinhamento e intervalos de Wilson."""
    base = marcado.sort_values(["data", "id_votacao"], kind="stable").copy()
    for c in ("seguiu_gov", "seguiu_partido", "seguiu_maioria"):
        base[c] = base[c].map({True: 1.0, False: 0.0})
    base["artigo17"] = (base.categoria == "artigo17").astype(int)
    base["branco"] = (base.categoria == "branco").astype(int)

    partes = []
    for janela, trims in janelas(base.trimestre.dropna().tolist(), modo).items():
        na_janela = base[base.trimestre.isin(trims)]
        g = na_janela.groupby("deputado_id", sort=True)
        # Linha do último voto (não GroupBy.last, que pula valores ausentes coluna a coluna).
        ultimo = na_janela.groupby("deputado_id").tail(1).set_index("deputado_id")[["nome", "partido", "uf"]]
        r = pd.concat([
            ultimo,
            _indice(g, "seguiu_gov", "gov"),
            _indice(g, "seguiu_partido", "par"),
            _indice(g, "seguiu_maioria", "maioria"),
            g["artigo17"].sum().rename("n_artigo17"),
            g["branco"].sum().rename("n_branco"),
        ], axis=1).reset_index()
        r["janela"] = janela
        r["modo"] = modo
        r["regiao"] = r.uf.map(REGIOES)
        partes.append(r)
    if not partes:
        return pd.DataFrame(columns=COLUNAS_INDICES)
    return pd.concat(partes, ignore_index=True)[COLUNAS_INDICES]


def nao_orientacao(marcado, aplicavel, votacoes, modo) -> pd.DataFrame:
    """Taxa de votações do Plenário com orientação do governo em que o partido ficou sem orientação aplicável."""
    plenario = set(votacoes.loc[votacoes.sigla_orgao == "PLEN", "id_votacao"])
    base = marcado[
        marcado.id_votacao.isin(plenario)
        & marcado.orient_gov.isin(ORIENTACOES_VALIDAS)
        & marcado.categoria.isin(CATEGORIAS_BASE)
    ][["id_votacao", "partido", "trimestre"]].drop_duplicates()
    base = base.merge(aplicavel[["id_votacao", "partido", "orientacao"]], on=["id_votacao", "partido"], how="left")
    base["sem_orientacao"] = base.orientacao.isna().astype(int)

    partes = []
    for janela, trims in janelas(marcado.trimestre.dropna().tolist(), modo).items():
        g = base[base.trimestre.isin(trims)].groupby("partido", sort=True)
        r = pd.DataFrame({
            "n_votacoes": g.id_votacao.nunique().astype(int),
            "n_sem_orientacao": g.sem_orientacao.sum().astype(int),
        }).reset_index()
        r["taxa_sem_orientacao"] = r.n_sem_orientacao / r.n_votacoes
        r["janela"] = janela
        r["modo"] = modo
        partes.append(r)
    if not partes:
        return pd.DataFrame(columns=COLUNAS_NAO_ORIENTACAO)
    return pd.concat(partes, ignore_index=True)[COLUNAS_NAO_ORIENTACAO]
