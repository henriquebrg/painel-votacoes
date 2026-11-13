"""Mapa de posições: PCA (SVD) da matriz deputado x votação, com sinal fixo."""
import numpy as np
import pandas as pd

_CODIGO = {"sim": 1.0, "nao": -1.0}


def _orientar(dim: np.ndarray, partido: pd.Series, sigla: str, negativo: bool) -> np.ndarray:
    """Inverte `dim` para que a média de `sigla` fique < 0 (negativo) ou >= 0.

    Se o partido não está na janela, o sinal calculado é mantido.
    """
    m = dim[(partido == sigla).to_numpy()]
    if len(m) == 0:
        return dim
    media = m.mean()
    if negativo and media > 0:
        return -dim
    if not negativo and media < 0:
        return -dim
    return dim


def posicoes(
    marcado: pd.DataFrame,
    janelas_movel: dict[str, list[str]],
    min_votos_dep: int = 50,
    min_votantes: int = 50,
    var_min: float = 0.15,
) -> tuple[pd.DataFrame, dict[str, list[float]]]:
    """Posições (dim1, dim2) por janela e variância explicada [dim1, dim2].

    sim=+1, nao=-1, demais categorias = ausente. Colunas centradas e ausentes
    preenchidos com 0. dim1 tem PT com média < 0; dim2 tem PL com média >= 0
    (se PT/PL ausente na janela, o sinal da SVD é mantido).
    """
    cod = marcado["categoria"].map(_CODIGO)
    base = marcado.assign(_x=cod)
    saidas, variancias = [], {}
    for chave, trims in janelas_movel.items():
        j = base[base["trimestre"].isin(trims)]
        mat = j.pivot_table(index="deputado_id", columns="id_votacao", values="_x", aggfunc="last")
        mat = mat.loc[:, mat.notna().sum() >= min_votantes]
        media = mat.mean()
        mat = mat.loc[:, (1 - media**2) > var_min]
        mat = mat.loc[mat.notna().sum(axis=1) >= min_votos_dep]
        if mat.shape[0] < 2 or mat.shape[1] < 2:
            continue
        x = (mat - mat.mean()).fillna(0.0).to_numpy()
        u, s, _ = np.linalg.svd(x, full_matrices=False)
        total = (s**2).sum()
        if total == 0:
            continue
        d1, d2 = u[:, 0] * s[0], u[:, 1] * s[1]
        part = (
            j.sort_values("id_votacao").groupby("deputado_id")["partido"].last().reindex(mat.index)
        )
        d1 = _orientar(d1, part, "PT", negativo=True)
        d2 = _orientar(d2, part, "PL", negativo=False)
        variancias[chave] = [float(s[0] ** 2 / total), float(s[1] ** 2 / total)]
        saidas.append(
            pd.DataFrame({"janela": chave, "deputado_id": mat.index, "dim1": d1, "dim2": d2})
        )
    cols = ["janela", "deputado_id", "dim1", "dim2"]
    pos = pd.concat(saidas, ignore_index=True) if saidas else pd.DataFrame(columns=cols)
    return pos, variancias
