from painel.carregar import (
    REGIOES,
    carregar_orientacoes,
    carregar_votacoes,
    carregar_votos,
    filtrar_plenario,
    normalizar_sigla,
)


def test_normalizar_sigla_variantes():
    assert normalizar_sigla("União") == normalizar_sigla("UNIÃO") == "UNIÃO"
    assert normalizar_sigla("Republican") == "REPUBLICANOS"
    assert normalizar_sigla("Solidaried") == "SOLIDARIEDADE"
    assert normalizar_sigla("Podemos") == "PODE"
    assert normalizar_sigla("PCdoB") == "PCDOB"
    assert normalizar_sigla("Bl UniPpPsd...") == "BL UNIPPPSD"
    assert normalizar_sigla(" Fdr PSDB-CIDADAN ") == "FDR PSDB-CIDADANIA"


def test_categorias_de_voto(fixtures):
    v = carregar_votos([fixtures / "votacoesVotos-2025.json"])
    assert set(v.categoria) <= {"sim", "nao", "abstencao", "obstrucao", "artigo17", "branco"}
    assert {"abstencao", "obstrucao", "artigo17", "branco"} <= set(v.categoria)
    assert list(v.columns) == ["id_votacao", "deputado_id", "nome", "partido", "uf", "categoria"]
    assert v.deputado_id.map(type).eq(str).all()
    assert "PCDOB" in set(v.partido)


def test_voto_desconhecido_levanta(tmp_path):
    import json

    p = tmp_path / "v.json"
    p.write_text(json.dumps({"dados": [{
        "idVotacao": "1", "voto": "Talvez",
        "deputado_": {"id": "1", "nome": "X", "siglaPartido": "PT", "siglaUf": "BA"},
    }]}))
    import pytest

    with pytest.raises(ValueError, match="Talvez"):
        carregar_votos([p])


def test_carregar_votacoes(fixtures):
    vt = carregar_votacoes([fixtures / "votacoes-2025.json"])
    assert list(vt.columns) == [
        "id_votacao", "data", "sigla_orgao", "votos_sim", "votos_nao", "votos_outros", "descricao",
    ]
    assert str(vt.data.dtype).startswith("datetime64")
    assert len(vt) == 3


def test_filtrar_plenario(fixtures):
    vt = filtrar_plenario(carregar_votacoes([fixtures / "votacoes-2025.json"]))
    assert set(vt.sigla_orgao) == {"PLEN"} and len(vt) == 2


def test_orientacao_vazia_vira_none(fixtures):
    o = carregar_orientacoes([fixtures / "votacoesOrientacoes-2025.json"])
    assert o.orientacao.isna().any() and set(o.orientacao.dropna()) <= {"sim", "nao", "obstrucao", "liberado"}
    assert "REPUBLICANOS" in set(o.bancada) and "FDR PT-PCDOB-PV" in set(o.bancada)


def test_regioes_cobrem_27_ufs():
    assert len(REGIOES) == 27 and REGIOES["BA"] == "Nordeste" and REGIOES["DF"] == "Centro-Oeste"
