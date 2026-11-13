import numpy as np
import pandas as pd

from painel.mapa import posicoes


def _marcado(n_pt=20, n_pl=20, n_vot=60, seed=0, ordem_inversa=False, extra=None):
    rng = np.random.default_rng(seed)
    gov = rng.choice(["sim", "nao"], n_vot)
    linhas = []
    for v in range(n_vot):
        for i in range(n_pt + n_pl):
            pt = i < n_pt
            c = gov[v] if pt else ("nao" if gov[v] == "sim" else "sim")
            if rng.random() < 0.05:
                c = "nao" if c == "sim" else "sim"
            linhas.append(("v%03d" % v, i, "PT" if pt else "PL", "2025T4", c))
    df = pd.DataFrame(linhas, columns=["id_votacao", "deputado_id", "partido", "trimestre", "categoria"])
    if extra is not None:
        df = pd.concat([df, extra], ignore_index=True)
    if ordem_inversa:
        df = df.iloc[::-1].reset_index(drop=True)
    return df


JAN = {"2025T4": ["2025T4"]}


def test_dois_blocos_separados_em_dim1():
    pos, var = posicoes(_marcado(), JAN, min_votantes=10)
    pos = pos.set_index("deputado_id")
    assert (pos.loc[range(0, 20), "dim1"] < 0).all()
    assert (pos.loc[range(20, 40), "dim1"] > 0).all()
    assert var["2025T4"][0] > 0.5


def _negado(df):
    return df.assign(categoria=df["categoria"].map({"sim": "nao", "nao": "sim"}))


def test_sinal_estavel():
    # votos originais e negados forçam sinais brutos opostos da SVD
    for marcado in (_marcado(), _negado(_marcado())):
        pos, _ = posicoes(marcado, JAN, min_votantes=10)
        pos = pos.set_index("deputado_id")
        assert pos.loc[range(0, 20), "dim1"].mean() < 0
        assert pos.loc[range(20, 40), "dim2"].mean() >= 0


def test_sem_pt_mantem_sinal():
    m = _marcado()
    m = m.assign(partido=m["partido"].replace("PT", "PSOL"))
    pos, var = posicoes(m, JAN, min_votantes=10)
    assert len(pos) > 0
    assert "2025T4" in var


def test_filtra_deputados_com_poucos_votos():
    # deputado 999 vota em apenas 10 votações
    extra = pd.DataFrame(
        [("v%03d" % v, 999, "PT", "2025T4", "sim") for v in range(10)],
        columns=["id_votacao", "deputado_id", "partido", "trimestre", "categoria"],
    )
    pos, _ = posicoes(_marcado(extra=extra), JAN, min_votantes=10)
    assert 999 not in set(pos["deputado_id"])
    assert len(pos) == 40
