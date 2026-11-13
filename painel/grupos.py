"""Grupos de deputados por mistura gaussiana sobre (alinh_gov, alinh_maioria)."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

EIXOS = ["alinh_gov", "alinh_maioria"]
N_INIT = 5


@dataclass
class ModeloGrupos:
    centros: list[tuple[float, float]]
    rotulos: list[str]
    k: int
    bic: dict[int, float]


def _rotulos(k: int) -> list[str]:
    if k == 3:
        return ["Base", "Independentes", "Oposição"]
    meio = [f"Intermediário {i}" for i in range(1, k - 1)]
    return ["Base", *meio, "Oposição"]


def _ajustar(x: np.ndarray, k: int, seed: int) -> GaussianMixture:
    return GaussianMixture(
        n_components=k, covariance_type="full", n_init=N_INIT, random_state=seed
    ).fit(x)


def ajustar_grupos(ind_legislatura, k: int | None = 3, k_max: int = 5,
                   n_min: int = 30, seed: int = 0) -> ModeloGrupos:
    ok = ind_legislatura[
        (ind_legislatura["n_gov"] >= n_min) & (ind_legislatura["n_maioria"] >= n_min)
    ].dropna(subset=EIXOS)
    x = ok[EIXOS].to_numpy(dtype=float)
    modelos = {kk: _ajustar(x, kk, seed) for kk in range(2, k_max + 1)}
    bic = {kk: float(m.bic(x)) for kk, m in modelos.items()}
    if k is None:
        k = min(bic, key=bic.get)
    modelo = modelos[k] if k in modelos else _ajustar(x, k, seed)
    centros = sorted(
        ((float(c[0]), float(c[1])) for c in modelo.means_), key=lambda c: -c[0]
    )
    return ModeloGrupos(centros=centros, rotulos=_rotulos(k), k=k, bic=bic)


def atribuir(modelo: ModeloGrupos, ind, n_min: int = 30) -> pd.DataFrame:
    """Grupo do centro mais próximo; sem grupo (None, dist NaN) se faltar eixo ou n_gov/n_maioria < n_min."""
    saida = ind.copy()
    pts = saida[EIXOS].to_numpy(dtype=float)
    validos = (
        ~np.isnan(pts).any(axis=1)
        & (saida["n_gov"].to_numpy() >= n_min)
        & (saida["n_maioria"].to_numpy() >= n_min)
    )
    centros = np.array(modelo.centros)
    grupo = np.full(len(saida), None, dtype=object)
    dist = np.full(len(saida), np.nan)
    if validos.any():
        d = np.linalg.norm(pts[validos][:, None, :] - centros[None, :, :], axis=2)
        idx = d.argmin(axis=1)
        grupo[validos] = np.array(modelo.rotulos, dtype=object)[idx]
        dist[validos] = d[np.arange(len(idx)), idx]
    saida["grupo"] = grupo
    saida["dist_centro"] = dist
    return saida
