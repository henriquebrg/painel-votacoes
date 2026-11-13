"""Pipeline completo: python -m painel.cli [--anos ...] [--raw ...] [--saida ...] [--sem-download]."""
import argparse
import sys
from pathlib import Path

import pandas as pd

from painel.baixar import ANO_OPCIONAL, TIPOS, DownloadFalhou, baixar_todos
from painel.carregar import carregar_orientacoes, carregar_votacoes, carregar_votos, filtrar_plenario
from painel.desgarrados import classificar
from painel.exportar import exportar
from painel.grupos import ajustar_grupos, atribuir
from painel.mapa import posicoes
from painel.metricas import BANCADA_GOVERNO, MODOS, ORIENTACOES_VALIDAS, indices, janelas, marcar_alinhamento, nao_orientacao
from painel.orientacao_partido import carregar_tabela_blocos, cobertura, orientacao_aplicavel
from painel.validacao import (
    CAMINHO_REFERENCIA,
    COLUNAS_REFERENCIA,
    checar_placar,
    checar_referencia,
    checar_sanidade,
    ids_nominais_plenario,
    marcar_regra_radar,
)

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_BLOCOS = RAIZ / "data" / "curado" / "blocos.csv"
ANOS_PADRAO = [2023, 2024, 2025, 2026, 2027]
INICIO_LEGISLATURA, FIM_LEGISLATURA = pd.Timestamp("2023-02-01"), pd.Timestamp("2027-01-31")


class ArquivoAusente(Exception):
    pass


def _argumentos(argv):
    p = argparse.ArgumentParser(prog="python -m painel.cli", description="Pipeline do painel de votações.")
    p.add_argument("--anos", type=int, nargs="+", default=ANOS_PADRAO)
    p.add_argument("--raw", type=Path, default=RAIZ / "data" / "raw")
    p.add_argument("--saida", type=Path, default=RAIZ / "site" / "src" / "data")
    p.add_argument("--sem-download", action="store_true", help="usa os arquivos já presentes em --raw")
    return p.parse_args(argv)


def _arquivos(raw: Path, anos: list[int]) -> dict[str, list[Path]]:
    """Arquivos por tipo; só o ano opcional (2027) pode faltar."""
    por_tipo = {tipo: [] for tipo in TIPOS}
    for tipo in TIPOS:
        for ano in anos:
            caminho = raw / f"{tipo}-{ano}.json"
            if caminho.exists():
                por_tipo[tipo].append(caminho)
            elif ano != ANO_OPCIONAL:
                raise ArquivoAusente(f"arquivo ausente: {caminho}")
    return por_tipo


def _ler_referencia() -> pd.DataFrame:
    if not CAMINHO_REFERENCIA.exists():
        return pd.DataFrame(columns=COLUNAS_REFERENCIA)
    return pd.read_csv(CAMINHO_REFERENCIA, dtype=str, keep_default_na=False, encoding="utf-8")


def _cobertura_ou_nulo(aplicavel, votos) -> float | None:
    """Cobertura arredondada; None (null no JSON) quando o ano não tem votos que entrem na conta."""
    c = cobertura(aplicavel, votos)
    return None if pd.isna(c) else round(c, 4)


def _meta(votacoes, orientacoes, votos, aplicavel, marcado) -> dict:
    gov = orientacoes[(orientacoes.bancada == BANCADA_GOVERNO) & orientacoes.orientacao.isin(ORIENTACOES_VALIDAS)]
    ano_votacao = dict(zip(votacoes.id_votacao, votacoes.data.dt.year))
    ano_voto = votos.id_votacao.map(ano_votacao)
    ano_aplicavel = aplicavel.id_votacao.map(ano_votacao)
    anos = sorted(int(a) for a in votacoes.data.dt.year.unique())
    return {
        "anos": anos,
        "n_votacoes_plenario": len(ids_nominais_plenario(votos, votacoes)),
        "n_votacoes_com_orientacao_governo": int(gov.id_votacao.nunique()),
        "cobertura_orientacao_partido": {
            str(a): _cobertura_ou_nulo(aplicavel[ano_aplicavel == a], votos[ano_voto == a]) for a in anos
        },
        "janelas": list(janelas(marcado.trimestre.dropna().tolist(), "movel")),
    }


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        if not args.sem_download:
            print(f"baixando {args.anos} para {args.raw}")
            baixar_todos(args.anos, args.raw)
        arquivos = _arquivos(args.raw, args.anos)
    except (DownloadFalhou, ArquivoAusente) as exc:
        print(f"ERRO: {exc}")
        return 1
    try:
        blocos = carregar_tabela_blocos(CAMINHO_BLOCOS)
    except ValueError as exc:
        print(f"ERRO em {CAMINHO_BLOCOS.name}: {exc}")
        return 1

    # Todos os órgãos na legislatura: só para a checagem pela regra do Radar. O resto usa só o Plenário.
    votacoes_todas = carregar_votacoes(arquivos["votacoes"])
    votacoes_todas = votacoes_todas[votacoes_todas.data.between(INICIO_LEGISLATURA, FIM_LEGISLATURA)]
    votos_todos = carregar_votos(arquivos["votacoesVotos"])
    orientacoes_todas = carregar_orientacoes(arquivos["votacoesOrientacoes"])
    marcado_radar = marcar_regra_radar(votos_todos, votacoes_todas, orientacoes_todas)

    votacoes = filtrar_plenario(votacoes_todas)
    plenario = set(votacoes.id_votacao)
    votos = votos_todos[votos_todos.id_votacao.isin(plenario)].reset_index(drop=True)
    orientacoes = orientacoes_todas[orientacoes_todas.id_votacao.isin(plenario)].reset_index(drop=True)
    print(f"{len(votacoes)} votações do Plenário ({len(ids_nominais_plenario(votos, votacoes))} nominais), "
          f"{len(votos)} votos")

    aplicavel = orientacao_aplicavel(orientacoes, votacoes, votos, blocos)
    marcado = marcar_alinhamento(votos, votacoes, orientacoes, aplicavel)
    por_modo = {modo: indices(marcado, modo) for modo in MODOS}

    # Validações antes das etapas caras: qualquer erro encerra sem publicar.
    erros = (
        checar_placar(votos, votacoes)
        + checar_sanidade(por_modo["movel"])
        + checar_referencia(marcado, _ler_referencia(), marcado_radar=marcado_radar)
    )
    if erros:
        print("VALIDAÇÃO FALHOU — nada foi exportado:")
        for e in erros:
            print(f"  - {e}")
        return 1

    modelo = ajustar_grupos(por_modo["legislatura"])
    ind = classificar(atribuir(modelo, pd.concat(por_modo.values(), ignore_index=True)))
    mapa, variancia = posicoes(marcado, janelas(marcado.trimestre.dropna().tolist(), "movel"))
    sem_orientacao = pd.concat(
        [nao_orientacao(marcado, aplicavel, votacoes, modo) for modo in ("movel", "trimestre")], ignore_index=True
    )
    meta = _meta(votacoes, orientacoes, votos, aplicavel, marcado)
    exportar(args.saida, ind, modelo, mapa, variancia, sem_orientacao, meta)
    print(f"exportado para {args.saida}; cobertura da orientação partidária por ano: "
          f"{meta['cobertura_orientacao_partido']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
