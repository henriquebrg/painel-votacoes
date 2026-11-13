import numpy as np
import pandas as pd

from painel.desgarrados import classificar
from painel.metricas import wilson


def _linha(dep, partido="X", alinh_gov=0.5, n=100, alinh=0.5, sup=None, janela="legislatura", modo="movel",
           n_gov=100):
    return {"janela": janela, "modo": modo, "deputado_id": dep, "partido": partido,
            "alinh_gov": alinh_gov, "n_gov": n_gov, "n_maioria": n, "alinh_maioria": alinh,
            "ic_maioria_sup": alinh if sup is None else sup}


def test_direcao_por_mediana_do_partido():
    ind = pd.DataFrame([_linha(1, alinh_gov=0.2), _linha(2, alinh_gov=0.5), _linha(3, alinh_gov=0.9),
                        _linha(4, alinh_gov=np.nan), _linha(5, partido="Y", alinh_gov=0.1)])
    r = classificar(ind).set_index("deputado_id")
    assert r.loc[3, "direcao"] == "rumo ao governo"
    assert r.loc[1, "direcao"] == "rumo à oposição"
    assert r.loc[2, "direcao"] == "rumo à oposição"  # igual à mediana: não está acima
    assert r.loc[4, "direcao"] is None
    assert r.loc[5, "direcao"] == "rumo à oposição"  # mediana de Y é ele mesmo


def test_direcao_separa_modo_e_janela():
    ind = pd.DataFrame([_linha(1, alinh_gov=0.9, modo="movel"), _linha(2, alinh_gov=0.1, modo="movel"),
                        _linha(1, alinh_gov=0.9, modo="trimestre"), _linha(2, alinh_gov=0.1, modo="trimestre"),
                        _linha(3, alinh_gov=0.95, modo="trimestre")])
    r = classificar(ind)
    t = r[r.modo == "trimestre"].set_index("deputado_id")
    assert t.loc[3, "direcao"] == "rumo ao governo"
    assert t.loc[2, "direcao"] == "rumo à oposição"


def test_ranking_exclui_n_baixo():
    ind = pd.DataFrame([_linha(1, n=29, alinh=0.1), _linha(2, n=30, alinh=0.5)])
    r = classificar(ind).set_index("deputado_id")
    assert not r.loc[1, "elegivel_ranking"] and np.isnan(r.loc[1, "posicao_ranking"])
    assert r.loc[2, "elegivel_ranking"] and r.loc[2, "posicao_ranking"] == 1


def test_ranking_usa_limite_superior():
    _, sa = wilson(80, 200)
    _, sb = wilson(11, 31)  # 0.355
    ind = pd.DataFrame([_linha(2, n=31, alinh=0.35, sup=sb), _linha(1, n=200, alinh=0.40, sup=sa)])
    r = classificar(ind).set_index("deputado_id")
    assert r.loc[1, "posicao_ranking"] == 1 and r.loc[2, "posicao_ranking"] == 2


def test_ranking_por_janela_e_desempate():
    ind = pd.DataFrame([_linha(1, sup=0.5, alinh=0.4), _linha(2, sup=0.5, alinh=0.3),
                        _linha(3, sup=0.9, janela="outra")])
    r = classificar(ind).set_index("deputado_id")
    assert r.loc[2, "posicao_ranking"] == 1 and r.loc[1, "posicao_ranking"] == 2
    assert r.loc[3, "posicao_ranking"] == 1


def test_direcao_none_com_poucos_votos_do_governo():
    ind = pd.DataFrame([_linha(1, alinh_gov=0.9, n_gov=29), _linha(2, alinh_gov=0.1), _linha(3, alinh_gov=0.5),
                        _linha(4, alinh_gov=0.95, n_gov=30)])
    r = classificar(ind).set_index("deputado_id")
    assert r.loc[1, "direcao"] is None
    assert r.loc[4, "direcao"] == "rumo ao governo"
