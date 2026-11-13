import json

import numpy as np
import pandas as pd
import pytest

from painel.carregar import carregar_votacoes, carregar_votos
from painel.exportar import exportar
from painel.grupos import ModeloGrupos
from painel.validacao import (
    COLUNAS_REFERENCIA,
    checar_placar,
    checar_referencia,
    checar_sanidade,
)


# ---------- placar ----------

def _placar(fixtures):
    return (carregar_votos([fixtures / "votacoesVotos-2025.json"]),
            carregar_votacoes([fixtures / "votacoes-2025.json"]))


def test_placar_confere(fixtures):
    votos, votacoes = _placar(fixtures)
    assert checar_placar(votos, votacoes) == []


def test_placar_divergente(fixtures):
    votos, votacoes = _placar(fixtures)
    votacoes.loc[votacoes.id_votacao == "2494086-7", "votos_sim"] = 99
    erros = checar_placar(votos, votacoes)
    assert len(erros) == 1 and "2494086-7" in erros[0]


def test_placar_ignora_fora_do_plenario(fixtures):
    votos, votacoes = _placar(fixtures)
    votacoes.loc[votacoes.sigla_orgao == "CCJC", "votos_sim"] = 99
    assert checar_placar(votos, votacoes) == []


# ---------- sanidade ----------

def _ind_movel(janelas=("2023T2", "2023T3"), n_pt=60, n_pl=90, n_outros=360, alinh_pt=0.95, alinh_pl=0.3):
    linhas = []
    for j in janelas:
        for i in range(n_pt):
            linhas.append({"janela": j, "deputado_id": f"pt{i}", "partido": "PT", "n_gov": 100,
                           "alinh_gov": alinh_pt, "alinh_par": 0.9, "alinh_maioria": 0.9})
        for i in range(n_pl):
            linhas.append({"janela": j, "deputado_id": f"pl{i}", "partido": "PL", "n_gov": 100,
                           "alinh_gov": alinh_pl, "alinh_par": 0.9, "alinh_maioria": 0.9})
        for i in range(n_outros):
            linhas.append({"janela": j, "deputado_id": f"o{i}", "partido": "PSD", "n_gov": 100,
                           "alinh_gov": 0.7, "alinh_par": np.nan, "alinh_maioria": 0.8})
    return pd.DataFrame(linhas)


def test_sanidade_ok():
    assert checar_sanidade(_ind_movel()) == []


def test_sanidade_pt_baixo_falha():
    erros = checar_sanidade(_ind_movel(alinh_pt=0.6))
    assert erros and all("PT" in e for e in erros)


def test_sanidade_pl_alto_falha():
    erros = checar_sanidade(_ind_movel(alinh_pl=0.7))
    assert erros and all("PL" in e for e in erros)


def test_sanidade_contagem_de_deputados():
    assert any("deputados" in e for e in checar_sanidade(_ind_movel(n_outros=100)))
    assert any("deputados" in e for e in checar_sanidade(_ind_movel(n_outros=500)))
    # 2023T1 fica fora das checagens de contagem e de medianas
    assert checar_sanidade(_ind_movel(janelas=("2023T1",), n_outros=10, alinh_pl=0.6)) == []


def test_sanidade_alinhamento_fora_de_0_1():
    ind = _ind_movel()
    ind.loc[0, "alinh_maioria"] = 1.2
    assert any("alinh_maioria" in e for e in checar_sanidade(ind))


def test_sanidade_ignora_partido_com_menos_de_10():
    assert checar_sanidade(_ind_movel(n_pt=9, alinh_pt=0.1, n_outros=411)) == []


# ---------- referência externa ----------

def _marcado():
    # Deputado 1: 20 votos em 2024 com orientação do governo, 15 seguidos (0,75).
    linhas = [{"deputado_id": "1", "data": pd.Timestamp("2024-03-01") + pd.Timedelta(days=i),
               "seguiu_gov": i < 15} for i in range(20)]
    linhas.append({"deputado_id": "1", "data": pd.Timestamp("2024-05-01"), "seguiu_gov": None})
    linhas.append({"deputado_id": "1", "data": pd.Timestamp("2025-01-10"), "seguiu_gov": False})
    return pd.DataFrame(linhas).astype({"seguiu_gov": object})


def _ref(alinhamento, metodo="igual"):
    return pd.DataFrame([{"fonte": "Teste", "url": "https://exemplo", "metodo": metodo, "deputado_id": "1",
                          "nome": "Dep 1", "inicio": "2024-01-01", "fim": "2024-12-31",
                          "alinhamento_governo": alinhamento}], columns=COLUNAS_REFERENCIA)


def test_referencia_tolerancia():
    m = _marcado()
    assert checar_referencia(m, _ref(0.79)) == []  # 4 pp
    erros = checar_referencia(m, _ref(0.81))  # 6 pp
    assert len(erros) == 1 and "Dep 1" in erros[0]
    assert checar_referencia(m, _ref(0.81, metodo="diferente")) == []


def test_referencia_vazia_e_noop():
    assert checar_referencia(_marcado(), pd.DataFrame(columns=COLUNAS_REFERENCIA)) == []


def test_referencia_csv_do_repositorio_tem_colunas():
    from painel.validacao import CAMINHO_REFERENCIA

    ref = pd.read_csv(CAMINHO_REFERENCIA, dtype=str)
    assert list(ref.columns) == COLUNAS_REFERENCIA


# ---------- exportação ----------

CHAVES_META = {"atualizado_em", "fonte", "anos", "n_votacoes_plenario", "n_votacoes_com_orientacao_governo",
               "cobertura_orientacao_partido", "janelas"}


def test_exportar_arquivos(tmp_path):
    ind = pd.DataFrame([{"janela": "2023T1", "modo": "movel", "deputado_id": "1", "alinh_gov": 0.123456789,
                         "alinh_maioria": np.nan, "n_gov": 10}])
    modelo = ModeloGrupos(centros=[(0.9, 0.9), (0.5, 0.8), (0.2, 0.9)],
                          rotulos=["Base", "Independentes", "Oposição"], k=3, bic={2: 10.0, 3: 5.0})
    mapa = pd.DataFrame([{"janela": "2023T1", "deputado_id": "1", "dim1": -1.0, "dim2": 0.5}])
    sem = pd.DataFrame([{"janela": "2023T1", "modo": "movel", "partido": "PL", "n_votacoes": 4,
                         "n_sem_orientacao": 1, "taxa_sem_orientacao": 0.25}])
    meta = {"anos": [2023], "n_votacoes_plenario": 4, "n_votacoes_com_orientacao_governo": 3,
            "cobertura_orientacao_partido": {"2023": 0.9}, "janelas": ["2023T1"]}
    saida = tmp_path / "saida"
    exportar(saida, ind, modelo, mapa, {"2023T1": [0.4, 0.1]}, sem, meta)

    nomes = {"indices.json", "grupos.json", "mapa.json", "sem_orientacao.json", "meta.json"}
    assert {p.name for p in saida.iterdir()} == nomes
    lidos = {n: json.loads((saida / n).read_text(encoding="utf-8")) for n in nomes}
    assert CHAVES_META <= set(lidos["meta.json"])
    assert lidos["meta.json"]["fonte"] == "Câmara dos Deputados — Dados Abertos"
    assert lidos["meta.json"]["atualizado_em"].endswith("-03:00")
    assert lidos["indices.json"][0]["alinh_gov"] == 0.1235
    assert lidos["indices.json"][0]["alinh_maioria"] is None
    assert set(lidos["grupos.json"]) == {"centros", "rotulos", "k", "bic"}
    assert set(lidos["mapa.json"]) == {"posicoes", "variancia"}
    assert lidos["mapa.json"]["variancia"] == {"2023T1": [0.4, 0.1]}
    assert lidos["sem_orientacao.json"][0]["partido"] == "PL"


def test_meta_sem_chave_obrigatoria_falha(tmp_path):
    modelo = ModeloGrupos(centros=[], rotulos=[], k=3, bic={})
    with pytest.raises(KeyError):
        exportar(tmp_path, pd.DataFrame(), modelo, pd.DataFrame(), {}, pd.DataFrame(), {"anos": [2023]})


def test_placar_votacoes_simbolicas_nao_diluem():
    nominais = [f"n{i}" for i in range(10)]
    simbolicas = [f"s{i}" for i in range(100)]
    votacoes = pd.DataFrame(
        [{"id_votacao": i, "sigla_orgao": "PLEN", "votos_sim": 2, "votos_nao": 1} for i in nominais]
        + [{"id_votacao": i, "sigla_orgao": "PLEN", "votos_sim": 0, "votos_nao": 0} for i in simbolicas]
    )
    votacoes.loc[0, "votos_sim"] = 3  # 1 de 10 nominais diverge
    votos = pd.DataFrame(
        [{"id_votacao": i, "deputado_id": d, "categoria": c} for i in nominais
         for d, c in (("1", "sim"), ("2", "sim"), ("3", "nao"))]
    )
    erros = checar_placar(votos, votacoes, tolerancia=0.02)
    assert len(erros) == 1 and "1 de 10" in erros[0]


def _exportar_args(meta_extra=None):
    ind = pd.DataFrame([{"janela": "2023T1", "deputado_id": "1", "alinh_gov": 0.5}])
    modelo = ModeloGrupos(centros=[(0.9, 0.9)], rotulos=["Base"], k=1, bic={1: 1.0})
    mapa = pd.DataFrame([{"janela": "2023T1", "deputado_id": "1", "dim1": 0.0, "dim2": 0.0}])
    sem = pd.DataFrame([{"janela": "2023T1", "partido": "PL", "taxa_sem_orientacao": 0.1}])
    meta = {"anos": [2023], "n_votacoes_plenario": 1, "n_votacoes_com_orientacao_governo": 1,
            "cobertura_orientacao_partido": {"2023": 0.9}, "janelas": ["2023T1"], **(meta_extra or {})}
    return ind, modelo, mapa, {"2023T1": [0.4, 0.1]}, sem, meta


def test_exportar_falha_de_serializacao_preserva_arquivos_anteriores(tmp_path):
    saida = tmp_path / "saida"
    exportar(saida, *_exportar_args())
    antes = {p.name: p.read_bytes() for p in saida.iterdir()}
    ind, modelo, mapa, var, sem, meta = _exportar_args({"janelas": {"2023T1"}})  # set: não serializável
    ind.loc[0, "alinh_gov"] = 0.9
    with pytest.raises(TypeError):
        exportar(saida, ind, modelo, mapa, var, sem, meta)
    assert {p.name: p.read_bytes() for p in saida.iterdir()} == antes
