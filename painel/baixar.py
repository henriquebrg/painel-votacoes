"""Download dos arquivos anuais de dados abertos da Câmara dos Deputados."""

import json
import os
import time
from collections.abc import Callable
from pathlib import Path

import requests

URL_BASE = "https://dadosabertos.camara.leg.br/arquivos"
TIPOS = ("votacoes", "votacoesVotos", "votacoesOrientacoes")
ANO_OPCIONAL = 2027
TENTATIVAS = 3
TIMEOUT = 120


class DownloadFalhou(Exception):
    pass


def _obter_http(url: str) -> tuple[int, bytes]:
    """GET com timeout de 120 s e 3 tentativas com backoff (erros de rede e 5xx)."""
    ultimo: Exception | None = None
    for tentativa in range(TENTATIVAS):
        if tentativa:
            time.sleep(2**tentativa)
        try:
            resp = requests.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            ultimo = exc
            continue
        if resp.status_code >= 500:
            ultimo = DownloadFalhou(f"HTTP {resp.status_code}")
            continue
        return resp.status_code, resp.content
    raise DownloadFalhou(f"falha ao baixar {url}: {ultimo}")


def _validar(corpo: bytes, url: str) -> None:
    try:
        dados = json.loads(corpo).get("dados")
    except (ValueError, AttributeError) as exc:
        raise DownloadFalhou(f"JSON inválido em {url}: {exc}") from exc
    if not isinstance(dados, list) or not dados:
        raise DownloadFalhou(f"'dados' ausente ou vazio em {url}")


def baixar(
    tipo: str,
    ano: int,
    destino: Path,
    obter: Callable[[str], tuple[int, bytes]] | None = None,
) -> Path | None:
    """Baixa `{tipo}-{ano}.json` para `destino`, de forma atômica.

    Retorna None apenas em 404 quando ano == 2027 (arquivo ainda não publicado).
    """
    obter = obter or _obter_http
    url = f"{URL_BASE}/{tipo}/json/{tipo}-{ano}.json"
    status, corpo = obter(url)
    if status == 404 and ano == ANO_OPCIONAL:
        return None
    if status != 200:
        raise DownloadFalhou(f"HTTP {status} em {url}")
    _validar(corpo, url)
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    final = destino / f"{tipo}-{ano}.json"
    tmp = final.with_name(final.name + ".tmp")
    tmp.write_bytes(corpo)
    os.replace(tmp, final)
    return final


def baixar_todos(anos: list[int], destino: Path) -> dict[tuple[str, int], Path]:
    """Baixa todos os tipos para todos os anos; omite os arquivos 2027 inexistentes."""
    resultado: dict[tuple[str, int], Path] = {}
    for tipo in TIPOS:
        for ano in anos:
            caminho = baixar(tipo, ano, destino)
            if caminho is not None:
                resultado[(tipo, ano)] = caminho
    return resultado
