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
CHAVES_META = ["n_votacoes_plenario", "n_votacoes_com_orientacao_governo", "anos",
               "cobertura_orientacao_partido", "janelas"]


def _registros(df: pd.DataFrame) -> list[dict]:
    """Registros JSON com floats arredondados a 4 casas e NaN como null."""
    return json.loads(df.to_json(orient="records", double_precision=CASAS, force_ascii=False))


def _gravar(caminho: Path, dados) -> None:
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, caminho)


def exportar(saida: Path, ind: pd.DataFrame, modelo: ModeloGrupos, mapa: pd.DataFrame,
             variancia: dict, sem_orientacao: pd.DataFrame, meta: dict) -> None:
    meta_completa = {
        "atualizado_em": datetime.now(FUSO).isoformat(timespec="seconds"),
        "fonte": FONTE,
        **{chave: meta[chave] for chave in CHAVES_META},
    }
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    _gravar(saida / "indices.json", _registros(ind))
    _gravar(saida / "grupos.json", asdict(modelo))
    _gravar(saida / "mapa.json", {"posicoes": _registros(mapa), "variancia": variancia})
    _gravar(saida / "sem_orientacao.json", _registros(sem_orientacao))
    _gravar(saida / "meta.json", meta_completa)
