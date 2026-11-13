import json
import shutil

from painel.cli import main


def _raw_corrompido(fixtures, destino):
    destino.mkdir()
    for f in fixtures.glob("*.json"):
        shutil.copy(f, destino / f.name)
    p = destino / "votacoes-2025.json"
    dados = json.loads(p.read_text(encoding="utf-8"))
    for v in dados["dados"]:
        if v["siglaOrgao"] == "PLEN":
            v["votosSim"] += 50
    p.write_text(json.dumps(dados), encoding="utf-8")


def test_cli_falha_sem_publicar(fixtures, tmp_path, capsys):
    raw, saida = tmp_path / "raw", tmp_path / "saida"
    _raw_corrompido(fixtures, raw)
    saida.mkdir()
    codigo = main(["--anos", "2025", "--raw", str(raw), "--saida", str(saida), "--sem-download"])
    assert codigo == 1
    assert list(saida.iterdir()) == []
    assert "placar" in capsys.readouterr().out.lower()


def test_cli_ano_ausente_sem_download_falha(fixtures, tmp_path, capsys):
    raw, saida = tmp_path / "raw", tmp_path / "saida"
    _raw_corrompido(fixtures, raw)
    codigo = main(["--anos", "2024", "--raw", str(raw), "--saida", str(saida), "--sem-download"])
    assert codigo == 1
    assert not saida.exists() or list(saida.iterdir()) == []


def _entradas_meta():
    import pandas as pd
    votacoes = pd.DataFrame({
        "id_votacao": ["n1", "n2", "s1", "x27"],
        "data": pd.to_datetime(["2025-03-01", "2025-04-01", "2025-05-01", "2027-01-10"]),
        "sigla_orgao": "PLEN",
        "votos_sim": [0, 300, 0, 0], "votos_nao": [0, 100, 0, 0],
    })
    votos = pd.DataFrame({"id_votacao": ["n1", "n1"], "deputado_id": ["a", "b"],
                          "categoria": ["sim", "nao"], "partido": ["PT", "PL"]})
    orientacoes = pd.DataFrame({"id_votacao": ["n1"], "bancada": ["GOVERNO"], "orientacao": ["sim"]})
    aplicavel = pd.DataFrame({"id_votacao": ["n1"], "partido": ["PT"], "orientacao": ["sim"]})
    marcado = pd.DataFrame({"trimestre": ["2025T1"]})
    return votacoes, orientacoes, votos, aplicavel, marcado


def test_meta_conta_so_votacoes_nominais():
    from painel.cli import _meta
    meta = _meta(*_entradas_meta())
    assert meta["n_votacoes_plenario"] == 2  # n1 (votos) e n2 (placar); s1 e x27 simbólicas


def test_meta_cobertura_sem_nan():
    from painel.cli import _meta
    meta = _meta(*_entradas_meta())
    json.dumps(meta, allow_nan=False)
    assert meta["cobertura_orientacao_partido"]["2025"] == 0.5
    assert meta["cobertura_orientacao_partido"].get("2027") is None


def test_cli_blocos_invalido_falha(fixtures, tmp_path, capsys, monkeypatch):
    import painel.cli
    ruim = tmp_path / "blocos.csv"
    ruim.write_text("bancada_prefixo,partido,inicio,fim,observacao\nFDR X,PT,2023-02-01,,\n", encoding="utf-8")
    monkeypatch.setattr(painel.cli, "CAMINHO_BLOCOS", ruim)
    saida = tmp_path / "saida"
    codigo = main(["--anos", "2025", "--raw", str(fixtures), "--saida", str(saida), "--sem-download"])
    assert codigo == 1
    assert not saida.exists()
    assert "observacao" in capsys.readouterr().out
