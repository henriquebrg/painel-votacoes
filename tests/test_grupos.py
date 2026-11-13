import numpy as np
import pandas as pd

from painel.grupos import ajustar_grupos, atribuir

CENTROS = [(0.95, 0.95), (0.55, 0.7), (0.2, 0.95)]


def _amostra():
    rng = np.random.default_rng(0)
    pts = np.vstack([rng.normal(c, 0.03, size=(50, 2)) for c in CENTROS])
    return pd.DataFrame({
        "deputado_id": range(len(pts)),
        "alinh_gov": pts[:, 0], "alinh_maioria": pts[:, 1],
        "n_gov": 100, "n_maioria": 100,
    }), pts


def test_tres_nuvens_rotuladas():
    df, pts = _amostra()
    m = ajustar_grupos(df, k=3, seed=0)
    assert m.rotulos == ["Base", "Independentes", "Oposição"]
    for i, centro in enumerate(m.centros):
        media = pts[i * 50:(i + 1) * 50].mean(axis=0)
        assert np.allclose(centro, media, atol=0.05)
    assert set(m.bic) == {2, 3, 4, 5}


def test_atribuir_nan_sem_grupo():
    df, _ = _amostra()
    m = ajustar_grupos(df, seed=0)
    novo = pd.DataFrame({"alinh_gov": [np.nan, 0.9], "alinh_maioria": [0.9, np.nan], "n_gov": 100, "n_maioria": 100})
    r = atribuir(m, novo)
    assert r["grupo"].isna().all()


def test_dist_centro_zero_no_centro():
    df, _ = _amostra()
    m = ajustar_grupos(df, seed=0)
    pts = pd.DataFrame(m.centros, columns=["alinh_gov", "alinh_maioria"]).assign(n_gov=100, n_maioria=100)
    r = atribuir(m, pts)
    assert list(r["grupo"]) == m.rotulos
    assert np.allclose(r["dist_centro"], 0)


def test_atribuir_poucos_votos_sem_grupo():
    df, _ = _amostra()
    m = ajustar_grupos(df, seed=0)
    c = m.centros[0]
    novo = pd.DataFrame({
        "alinh_gov": [c[0]] * 4, "alinh_maioria": [c[1]] * 4,
        "n_gov": [29, 30, 100, 30], "n_maioria": [100, 29, 100, 30],
    })
    r = atribuir(m, novo)
    assert r["grupo"].iloc[:2].isna().all()
    assert np.isnan(r["dist_centro"].iloc[0]) and np.isnan(r["dist_centro"].iloc[1])
    assert list(r["grupo"].iloc[2:]) == ["Base", "Base"]
    assert atribuir(m, novo, n_min=10)["grupo"].notna().all()
