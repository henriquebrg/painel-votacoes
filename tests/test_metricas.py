from datetime import date
from itertools import product

import numpy as np
import pandas as pd
import pytest

from painel.metricas import (
    _seguiu_vetor,
    indices,
    janelas,
    marcar_alinhamento,
    nao_orientacao,
    seguiu,
    trimestre,
    wilson,
)


@pytest.mark.parametrize("cat,ori,esp", [
    ("sim", "sim", True), ("nao", "sim", False), ("abstencao", "sim", False), ("obstrucao", "sim", False),
    ("obstrucao", "obstrucao", True), ("sim", "obstrucao", False), ("sim", "liberado", None), ("sim", None, None),
    ("artigo17", "sim", None), ("branco", "nao", None), ("abstencao", "nao", False)])
def test_seguiu(cat, ori, esp):
    assert seguiu(cat, ori) is esp


def test_seguiu_vetor_equivale_a_funcao():
    cats = ["sim", "nao", "abstencao", "obstrucao", "artigo17", "branco"]
    oris = ["sim", "nao", "obstrucao", "liberado", None]
    pares = list(product(cats, oris))
    res = _seguiu_vetor(pd.Series([c for c, _ in pares]), pd.Series([o for _, o in pares], dtype=object))
    assert list(res) == [seguiu(c, o) for c, o in pares]


def test_wilson():
    lo, hi = wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)
    assert wilson(0, 0) == (0.0, 1.0)


def test_trimestre_e_janelas():
    assert trimestre(date(2023, 2, 1)) == "2023T1" and trimestre(date(2026, 10, 1)) == "2026T4"
    t = ["2023T1", "2023T2", "2023T3", "2023T4", "2024T1"]
    assert janelas(t, "movel")["2024T1"] == ["2023T2", "2023T3", "2023T4", "2024T1"]
    assert janelas(t, "movel")["2023T2"] == ["2023T1", "2023T2"]
    assert janelas(t, "trimestre")["2023T3"] == ["2023T3"]
    assert janelas(t, "legislatura") == {"legislatura": t}
    with pytest.raises(ValueError):
        janelas(t, "anual")


# ---------- helpers para DataFrames pequenos ----------

def _votacoes(*pares):
    return pd.DataFrame(
        [{"id_votacao": i, "data": pd.Timestamp(d), "sigla_orgao": "PLEN"} for i, d in pares]
    )


def _votos(*linhas):
    return pd.DataFrame(
        [{"id_votacao": i, "deputado_id": dep, "nome": f"Dep {dep}", "partido": p, "uf": uf, "categoria": c}
         for i, dep, p, uf, c in linhas],
        columns=["id_votacao", "deputado_id", "nome", "partido", "uf", "categoria"],
    )


def _orientacoes(*linhas):
    return pd.DataFrame(linhas, columns=["id_votacao", "bancada", "orientacao"])


def _aplicavel(*linhas):
    return pd.DataFrame(
        [{"id_votacao": i, "partido": p, "orientacao": o, "fonte": "partido" if o else None} for i, p, o in linhas],
        columns=["id_votacao", "partido", "orientacao", "fonte"], dtype=object,
    )


def _dep(df, dep, id_votacao=None):
    sel = df[df.deputado_id == dep]
    if id_votacao is not None:
        sel = sel[sel.id_votacao == id_votacao]
    assert len(sel) == 1
    return sel.iloc[0]


def test_marcar_alinhamento_colunas():
    votacoes = _votacoes(("v1", "2023-03-01"))
    votos = _votos(("v1", "1", "PT", "SP", "sim"), ("v1", "2", "PL", "RJ", "nao"))
    orient = _orientacoes(("v1", "GOVERNO", "sim"), ("v1", "PT", "sim"))
    apl = _aplicavel(("v1", "PT", "sim"), ("v1", "PL", None))
    m = marcar_alinhamento(votos, votacoes, orient, apl)
    assert list(m.columns) == list(votos.columns) + [
        "data", "trimestre", "orient_gov", "seguiu_gov", "orient_partido", "seguiu_partido", "seguiu_maioria"]
    assert len(m) == 2
    pt, pl = _dep(m, "1"), _dep(m, "2")
    assert pt.trimestre == "2023T1" and pt.orient_gov == "sim" and pt.seguiu_gov is True
    assert pt.seguiu_partido is True
    assert pl.seguiu_gov is False and pl.orient_partido is None and pl.seguiu_partido is None


def test_maioria_exclui_o_proprio():
    votacoes = _votacoes(("v1", "2023-03-01"))
    votos = _votos(
        ("v1", "1", "PL", "SP", "sim"),
        ("v1", "2", "PL", "SP", "nao"), ("v1", "3", "PL", "SP", "nao"), ("v1", "4", "PL", "SP", "nao"),
    )
    m = marcar_alinhamento(votos, votacoes, _orientacoes(), _aplicavel())
    assert _dep(m, "1").seguiu_maioria is False
    assert _dep(m, "2").seguiu_maioria is True  # colegas: sim, nao, nao → maioria nao


def test_maioria_exige_tres_colegas_e_empate_e_none():
    votacoes = _votacoes(("v1", "2023-03-01"), ("v2", "2023-03-02"))
    votos = _votos(
        # v1: só 2 colegas contáveis (o artigo17 não conta)
        ("v1", "1", "PL", "SP", "sim"), ("v1", "2", "PL", "SP", "sim"), ("v1", "3", "PL", "SP", "sim"),
        ("v1", "4", "PL", "SP", "artigo17"),
        # v2: deputado 1 vê colegas sim, sim, nao, nao → empate
        ("v2", "1", "PL", "SP", "sim"), ("v2", "2", "PL", "SP", "sim"), ("v2", "3", "PL", "SP", "sim"),
        ("v2", "4", "PL", "SP", "nao"), ("v2", "5", "PL", "SP", "nao"),
    )
    m = marcar_alinhamento(votos, votacoes, _orientacoes(), _aplicavel())
    assert _dep(m, "1", "v1").seguiu_maioria is None
    assert _dep(m, "4", "v1").seguiu_maioria is None  # artigo17 nunca é avaliado
    assert _dep(m, "1", "v2").seguiu_maioria is None  # empate 2 x 2
    assert _dep(m, "4", "v2").seguiu_maioria is False  # votou nao; colegas sim x3, nao x1 → maioria sim


def test_indices_poucos_votos():
    votacoes = _votacoes(("v1", "2023-03-01"), ("v2", "2023-03-02"))
    votos = _votos(("v1", "1", "PT", "SP", "sim"), ("v2", "1", "PT", "SP", "nao"))
    orient = _orientacoes(("v1", "GOVERNO", "sim"), ("v2", "GOVERNO", "sim"))
    m = marcar_alinhamento(votos, votacoes, orient, _aplicavel())
    r = indices(m, "trimestre")
    assert list(r.columns) == [
        "janela", "modo", "deputado_id", "nome", "partido", "uf", "regiao",
        "n_gov", "alinh_gov", "ic_gov_inf", "ic_gov_sup",
        "n_par", "alinh_par", "ic_par_inf", "ic_par_sup",
        "n_maioria", "alinh_maioria", "ic_maioria_inf", "ic_maioria_sup",
        "n_artigo17", "n_branco"]
    linha = r.iloc[0]
    assert linha.janela == "2023T1" and linha.modo == "trimestre" and linha.regiao == "Sudeste"
    assert linha.n_gov == 2 and linha.alinh_gov == pytest.approx(0.5)
    assert linha.ic_gov_sup - linha.ic_gov_inf > 0.5
    assert linha.n_par == 0 and np.isnan(linha.alinh_par)
    assert (linha.ic_par_inf, linha.ic_par_sup) == (0.0, 1.0)
    assert linha.n_maioria == 0 and np.isnan(linha.alinh_maioria)


def test_troca_de_partido_na_janela():
    votacoes = _votacoes(("v1", "2023-02-10"), ("v2", "2023-05-10"))
    votos = _votos(
        ("v1", "1", "PL", "SP", "sim"),
        ("v2", "1", "PSD", "SP", "nao"),
    )
    apl = _aplicavel(("v1", "PL", "sim"), ("v1", "PSD", "nao"), ("v2", "PL", "nao"), ("v2", "PSD", "nao"))
    m = marcar_alinhamento(votos, votacoes, _orientacoes(), apl)
    assert _dep(m, "1", "v1").orient_partido == "sim" and _dep(m, "1", "v1").seguiu_partido is True
    assert _dep(m, "1", "v2").orient_partido == "nao" and _dep(m, "1", "v2").seguiu_partido is True
    r = indices(m, "movel")
    linha = r[r.janela == "2023T2"].iloc[0]
    assert linha.partido == "PSD" and linha.n_par == 2 and linha.alinh_par == 1.0
    assert r[r.janela == "2023T1"].iloc[0].partido == "PL"


def test_artigo17_contado_a_parte():
    votacoes = _votacoes(("v1", "2023-03-01"), ("v2", "2023-03-02"), ("v3", "2023-03-03"))
    votos = _votos(
        ("v1", "1", "PT", "SP", "sim"), ("v2", "1", "PT", "SP", "artigo17"), ("v3", "1", "PT", "SP", "branco"))
    orient = _orientacoes(*[(v, "GOVERNO", "sim") for v in ("v1", "v2", "v3")])
    m = marcar_alinhamento(votos, votacoes, orient, _aplicavel())
    linha = indices(m, "legislatura").iloc[0]
    assert linha.janela == "legislatura"
    assert linha.n_artigo17 == 1 and linha.n_branco == 1 and linha.n_gov == 1


def test_nao_orientacao():
    datas = [("v1", "2023-03-01"), ("v2", "2023-03-02"), ("v3", "2023-03-03"), ("v4", "2023-03-04"),
             ("v5", "2023-03-05"), ("v6", "2023-03-06")]
    votacoes = _votacoes(*datas)
    votos = _votos(*[(v, "1", "PL", "SP", "sim") for v, _ in datas], ("v1", "2", "PT", "BA", "sim"))
    orient = _orientacoes(
        ("v1", "GOVERNO", "sim"), ("v2", "GOVERNO", "nao"), ("v3", "GOVERNO", "obstrucao"),
        ("v4", "GOVERNO", "sim"), ("v5", "GOVERNO", "liberado"))  # v5 liberado e v6 sem orientação: fora da base
    apl = _aplicavel(
        ("v1", "PL", "liberado"), ("v2", "PL", None), ("v3", "PL", None), ("v4", "PL", None),
        ("v5", "PL", None), ("v6", "PL", None), ("v1", "PT", "sim"))
    m = marcar_alinhamento(votos, votacoes, orient, apl)
    r = nao_orientacao(m, apl, votacoes, "trimestre")
    assert list(r.columns) == ["janela", "modo", "partido", "n_votacoes", "n_sem_orientacao", "taxa_sem_orientacao"]
    pl = r[r.partido == "PL"].iloc[0]
    assert pl.janela == "2023T1" and pl.modo == "trimestre"
    assert pl.n_votacoes == 4 and pl.n_sem_orientacao == 3 and pl.taxa_sem_orientacao == pytest.approx(0.75)
    pt = r[r.partido == "PT"].iloc[0]
    assert pt.n_votacoes == 1 and pt.n_sem_orientacao == 0


def test_nao_orientacao_ignora_votacoes_fora_do_plenario():
    votacoes = _votacoes(("v1", "2023-03-01"), ("v2", "2023-03-02"))
    votacoes.loc[votacoes.id_votacao == "v2", "sigla_orgao"] = "CCJC"
    votos = _votos(("v1", "1", "PL", "SP", "sim"), ("v2", "1", "PL", "SP", "sim"))
    orient = _orientacoes(("v1", "GOVERNO", "sim"), ("v2", "GOVERNO", "sim"))
    apl = _aplicavel(("v1", "PL", None), ("v2", "PL", None))
    m = marcar_alinhamento(votos, votacoes, orient, apl)
    pl = nao_orientacao(m, apl, votacoes, "legislatura").iloc[0]
    assert pl.n_votacoes == 1 and pl.n_sem_orientacao == 1


def test_maioria_abstencao_e_posicao():
    votacoes = _votacoes(("v1", "2023-03-01"))
    votos = _votos(
        ("v1", "A", "PL", "SP", "abstencao"), ("v1", "B", "PL", "SP", "sim"),
        ("v1", "2", "PL", "SP", "abstencao"), ("v1", "3", "PL", "SP", "abstencao"), ("v1", "4", "PL", "SP", "abstencao"),
    )
    m = marcar_alinhamento(votos, votacoes, _orientacoes(), _aplicavel())
    assert _dep(m, "A").seguiu_maioria is True
    assert _dep(m, "B").seguiu_maioria is False
