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
