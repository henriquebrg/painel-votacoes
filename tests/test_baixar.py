import pytest

from painel.baixar import DownloadFalhou, baixar


def test_baixar_salva_arquivo(tmp_path):
    corpo = b'{"dados":[{"id":"1"}]}'
    p = baixar("votacoes", 2025, tmp_path, obter=lambda url: (200, corpo))
    assert p == tmp_path / "votacoes-2025.json" and p.read_bytes() == corpo


def test_baixar_url_correta(tmp_path):
    urls = []
    baixar("votacoesVotos", 2023, tmp_path, obter=lambda u: (urls.append(u), (200, b'{"dados":[1]}'))[1])
    assert urls == ["https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/json/votacoesVotos-2023.json"]


def test_baixar_404_2027_retorna_none(tmp_path):
    assert baixar("votacoes", 2027, tmp_path, obter=lambda u: (404, b"")) is None


def test_baixar_404_outro_ano_falha(tmp_path):
    with pytest.raises(DownloadFalhou):
        baixar("votacoes", 2026, tmp_path, obter=lambda u: (404, b""))


def test_baixar_json_invalido_falha(tmp_path):
    for corpo in (b'{"dados":[]}', b'{"dad', b'{}'):
        with pytest.raises(DownloadFalhou):
            baixar("votacoes", 2025, tmp_path, obter=lambda u, c=corpo: (200, c))
    assert not (tmp_path / "votacoes-2025.json").exists()


def test_baixar_2027_vazio_retorna_none(tmp_path):
    assert baixar("votacoes", 2027, tmp_path, obter=lambda u: (200, b'{"dados":[]}')) is None
    assert not (tmp_path / "votacoes-2027.json").exists()
