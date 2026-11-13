"""Exportação dos resultados do pipeline em JSON para o site."""
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from painel.grupos import ModeloGrupos

FONTE = "Câmara dos Deputados — Dados Abertos"
FUSO = ZoneInfo("America/Sao_Paulo")
CASAS = 4
MODOS = ("movel", "trimestre", "legislatura")
ANTIGOS = ("indices.json",)  # formato anterior, um arquivo só para todos os modos
CHAVES_META = ["n_votacoes_plenario", "n_votacoes_com_orientacao_governo", "anos",
               "cobertura_orientacao_partido", "janelas"]


def _registros(df: pd.DataFrame) -> list[dict]:
    """Registros JSON com floats arredondados a 4 casas e NaN como null."""
    return json.loads(df.to_json(orient="records", double_precision=CASAS, force_ascii=False))


def exportar(saida: Path, ind: pd.DataFrame, modelo: ModeloGrupos, mapa: pd.DataFrame,
             variancia: dict, sem_orientacao: pd.DataFrame, meta: dict) -> None:
    """Grava os 7 arquivos como conjunto: serializa tudo, grava os .tmp e só então troca os definitivos.

    Os índices vão em um arquivo por modo de janela (`indices-{modo}.json`), para o site carregar
    só o modo ativo. Uma falha de serialização não toca a pasta; uma falha de escrita remove os
    .tmp já gravados.
    """
    meta_completa = {
        "atualizado_em": datetime.now(FUSO).isoformat(timespec="seconds"),
        "fonte": FONTE,
        **{chave: meta[chave] for chave in CHAVES_META},
    }
    conteudos = {
        nome: json.dumps(dados, ensure_ascii=False)
        for nome, dados in (
            *((f"indices-{modo}.json", _registros(ind[ind["modo"] == modo])) for modo in MODOS),
            ("grupos.json", asdict(modelo)),
            ("mapa.json", {"posicoes": _registros(mapa), "variancia": variancia}),
            ("sem_orientacao.json", _registros(sem_orientacao)),
            ("meta.json", meta_completa),
        )
    }
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    temporarios = {nome: saida / f"{nome}.tmp" for nome in conteudos}
    try:
        for nome, texto in conteudos.items():
            temporarios[nome].write_text(texto, encoding="utf-8")
    except OSError:
        for tmp in temporarios.values():
            tmp.unlink(missing_ok=True)
        raise
    for nome, tmp in temporarios.items():
        os.replace(tmp, saida / nome)
    for nome in ANTIGOS:
        (saida / nome).unlink(missing_ok=True)
