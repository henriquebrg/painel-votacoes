"""Deputados que se afastam do próprio partido: direção do afastamento e ranking."""
import numpy as np
import pandas as pd

CHAVE = ["modo", "janela"]


def classificar(ind: pd.DataFrame, n_min: int = 30) -> pd.DataFrame:
    """Acrescenta direcao, elegivel_ranking e posicao_ranking a `ind` (mediana e ranking por modo e janela)."""
    r = ind.copy()
    mediana = r.groupby(CHAVE + ["partido"])["alinh_gov"].transform("median")
    direcao = np.where(r.alinh_gov > mediana, "rumo ao governo", "rumo à oposição").astype(object)
    direcao[r.alinh_gov.isna().to_numpy()] = None
    r["direcao"] = pd.Series(direcao, index=r.index, dtype=object)
    r["elegivel_ranking"] = r.n_maioria >= n_min

    pos = pd.Series(np.nan, index=r.index)
    for _, idx in r[r.elegivel_ranking].groupby(CHAVE).groups.items():
        ordem = r.loc[idx].sort_values(["ic_maioria_sup", "alinh_maioria"], kind="stable").index
        pos[ordem] = np.arange(1, len(ordem) + 1)
    r["posicao_ranking"] = pos
    return r
