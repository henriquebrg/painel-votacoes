import pandas as pd
import pytest

from painel.orientacao_partido import (
    carregar_tabela_blocos,
    cobertura,
    orientacao_aplicavel,
)

CSV_BLOCOS = """bancada_prefixo,partido,inicio,fim,observacao
Bl UniPpPsd,União,2025-02-01,,teste
BL UNIPPPSD,PP,2025-02-01,,teste
BL UNIPPPSD,PSD,2025-02-01,,teste
FDR PT-PCDOB-PV,PT,2023-02-01,,teste
FDR PT-PCDOB-PV,PCdoB,2023-02-01,,teste
FDR PT-PCDOB-PV,PV,2023-02-01,,teste
"""


@pytest.fixture
def blocos(tmp_path):
    p = tmp_path / "blocos.csv"
    p.write_text(CSV_BLOCOS, encoding="utf-8")
    return carregar_tabela_blocos(p)


def _votacoes(*pares):
    return pd.DataFrame(
        [{"id_votacao": i, "data": pd.Timestamp(d)} for i, d in pares]
    )


def _orientacoes(*linhas):
    return pd.DataFrame(linhas, columns=["id_votacao", "bancada", "orientacao"])


def _votos(*linhas):
    return pd.DataFrame(
        [{"id_votacao": i, "deputado_id": dep, "partido": p, "categoria": c} for i, dep, p, c in linhas]
    )


def _linha(aplicavel, id_votacao, partido):
    sel = aplicavel[(aplicavel.id_votacao == id_votacao) & (aplicavel.partido == partido)]
    assert len(sel) == 1
    return sel.iloc[0]


def test_carregar_tabela_blocos_normaliza(blocos):
    assert list(blocos.columns) == ["bancada_prefixo", "partido", "inicio", "fim", "observacao"]
    assert blocos.bancada_prefixo.iloc[0] == "BL UNIPPPSD"
    assert blocos.partido.iloc[0] == "UNIÃO"
    assert "PCDOB" in set(blocos.partido)
    assert blocos.inicio.iloc[0] == pd.Timestamp("2025-02-01")
    assert pd.isna(blocos.fim.iloc[0])


def test_orientacao_direta_tem_prioridade(blocos):
    ap = orientacao_aplicavel(
        _orientacoes(("v1", "PP", "nao"), ("v1", "BL UNIPPPSD", "sim")),
        _votacoes(("v1", "2025-03-10")),
        _votos(("v1", "d1", "PP", "nao")),
        blocos,
    )
    r = _linha(ap, "v1", "PP")
    assert r.orientacao == "nao"
    assert r.fonte == "partido"


def test_partido_herda_do_bloco_na_data(blocos):
    ap = orientacao_aplicavel(
        _orientacoes(("v1", "BL UNIPPPSD", "sim")),
        _votacoes(("v1", "2025-03-10")),
        _votos(("v1", "d1", "PSD", "sim")),
        blocos,
    )
    r = _linha(ap, "v1", "PSD")
    assert r.orientacao == "sim"
    assert r.fonte == "bloco"


def test_bloco_fora_da_vigencia_nao_vale(blocos):
    ap = orientacao_aplicavel(
        _orientacoes(("v1", "BL UNIPPPSD", "sim")),
        _votacoes(("v1", "2025-01-15")),
        _votos(("v1", "d1", "PSD", "sim")),
        blocos,
    )
    r = _linha(ap, "v1", "PSD")
    assert r.orientacao is None
    assert r.fonte is None


def test_federacao(blocos):
    ap = orientacao_aplicavel(
        _orientacoes(("v1", "FDR PT-PCDOB-PV", "obstrucao")),
        _votacoes(("v1", "2025-03-10")),
        _votos(("v1", "d1", "PCDOB", "obstrucao")),
        blocos,
    )
    r = _linha(ap, "v1", "PCDOB")
    assert r.orientacao == "obstrucao"
    assert r.fonte == "federacao"


def test_sem_bloco_nao_e_divergencia(blocos):
    ap = orientacao_aplicavel(
        _orientacoes(("v1", "BL UNIPPPSD", "nao"), ("v1", "GOVERNO", "nao")),
        _votacoes(("v1", "2025-03-10")),
        _votos(("v1", "d1", "NOVO", "sim"), ("v1", "d2", "PSD", "nao")),
        blocos,
    )
    assert list(ap.columns) == ["id_votacao", "partido", "orientacao", "fonte"]
    assert len(ap) == 2
    r = _linha(ap, "v1", "NOVO")
    assert r.orientacao is None
    assert r.fonte is None


def test_cobertura():
    aplicavel = pd.DataFrame([
        {"id_votacao": "v1", "partido": "PT", "orientacao": "sim", "fonte": "federacao"},
        {"id_votacao": "v1", "partido": "PL", "orientacao": "liberado", "fonte": "partido"},
        {"id_votacao": "v1", "partido": "NOVO", "orientacao": None, "fonte": None},
    ])
    votos = _votos(
        ("v1", "d1", "PT", "sim"),
        ("v1", "d2", "PT", "abstencao"),
        ("v1", "d3", "PL", "obstrucao"),
        ("v1", "d4", "NOVO", "nao"),
        ("v1", "d5", "NOVO", "artigo17"),  # fora da base
        ("v1", "d6", "NOVO", "branco"),    # fora da base
    )
    assert cobertura(aplicavel, votos) == pytest.approx(0.75)


def test_federacao_tem_prioridade_sobre_bloco(blocos):
    extra = pd.DataFrame([{
        "bancada_prefixo": "BL PLFDRPT", "partido": "PT", "inicio": pd.Timestamp("2025-02-01"),
        "fim": pd.NaT, "observacao": "teste",
    }])
    ap = orientacao_aplicavel(
        _orientacoes(("v1", "BL PLFDRPTUNIPP", "sim"), ("v1", "FDR PT-PCDOB-PV", "nao")),
        _votacoes(("v1", "2025-03-10")),
        _votos(("v1", "d1", "PT", "nao")),
        pd.concat([blocos, extra], ignore_index=True),
    )
    r = _linha(ap, "v1", "PT")
    assert (r.orientacao, r.fonte) == ("nao", "federacao")
