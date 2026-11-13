"""Validações bloqueantes: placar oficial, sanidade dos índices e referência externa."""
from pathlib import Path

import pandas as pd

from painel.metricas import BANCADA_GOVERNO, _seguiu_vetor

CAMINHO_REFERENCIA = Path(__file__).resolve().parent.parent / "data" / "referencia" / "externa.csv"
COLUNAS_REFERENCIA = ["fonte", "url", "metodo", "deputado_id", "nome", "inicio", "fim", "alinhamento_governo"]
MAX_LISTADOS = 10
# 2023T1 tem só 8 votações com orientação do governo (mediana n_gov = 6): fica fora das checagens por janela.
JANELA_INICIAL = "2023T2"
DEPUTADOS_MIN, DEPUTADOS_MAX = 400, 620
COLUNAS_ALINH = ["alinh_gov", "alinh_par", "alinh_maioria"]
PT_MIN, PL_MAX = 0.85, 0.50
MIN_DEPUTADOS_PARTIDO = 10
METODOS = {"igual", "diferente", "regra_radar"}
ORIENTACOES_RADAR = {"sim", "nao"}


class ValidacaoFalhou(Exception):
    pass


def ids_nominais_plenario(votos, votacoes) -> set:
    """ids das votações nominais do Plenário: placar oficial sim+não não nulo ou ao menos um voto registrado."""
    plen = votacoes[votacoes.sigla_orgao == "PLEN"]
    nominal = (plen.votos_sim + plen.votos_nao > 0) | plen.id_votacao.isin(votos.id_votacao)
    return set(plen.id_votacao[nominal])


def checar_placar(votos, votacoes, tolerancia: float = 0.02) -> list[str]:
    """Compara, em cada votação nominal do Plenário, as contagens sim/não dos votos com votos_sim/votos_nao.

    Nominal: ver `ids_nominais_plenario`. As simbólicas (0/0, sem votos) ficam fora do denominador
    para não diluir a tolerância.
    """
    plen = votacoes[votacoes.sigla_orgao == "PLEN"].set_index("id_votacao")[["votos_sim", "votos_nao"]]
    plen = plen[plen.index.isin(ids_nominais_plenario(votos, votacoes))]
    if plen.empty:
        return []
    sn = votos[votos.categoria.isin(["sim", "nao"])]
    contagem = (
        pd.crosstab(sn.id_votacao, sn.categoria)
        .reindex(index=plen.index, columns=["sim", "nao"], fill_value=0)
    )
    diverge = (plen.votos_sim != contagem.sim) | (plen.votos_nao != contagem.nao)
    taxa = float(diverge.mean())
    if taxa <= tolerancia:
        return []
    exemplos = [
        f"{i}: oficial {plen.at[i, 'votos_sim']} sim/{plen.at[i, 'votos_nao']} não, "
        f"votos {contagem.at[i, 'sim']} sim/{contagem.at[i, 'nao']} não"
        for i in plen.index[diverge][:MAX_LISTADOS]
    ]
    return [f"placar divergente em {int(diverge.sum())} de {len(plen)} votações nominais do Plenário "
            f"({taxa:.1%} > {tolerancia:.1%}); exemplos: " + "; ".join(exemplos)]


def checar_sanidade(ind_movel) -> list[str]:
    """Contagem de deputados por janela, faixa [0, 1] dos índices e medianas de PT e PL.

    Contagem e medianas valem a partir de 2023T2 e as medianas só para partidos com >= 10 deputados
    com n_gov > 0 na janela.
    """
    erros = []
    ativos = ind_movel[ind_movel.n_gov > 0]
    contagem = ativos.groupby("janela").deputado_id.nunique()
    for janela, n in contagem[contagem.index >= JANELA_INICIAL].items():
        if not DEPUTADOS_MIN <= n <= DEPUTADOS_MAX:
            erros.append(f"janela {janela}: {n} deputados com n_gov > 0 (esperado {DEPUTADOS_MIN}–{DEPUTADOS_MAX})")

    for col in COLUNAS_ALINH:
        if col not in ind_movel:
            continue
        valores = ind_movel[col].dropna()
        fora = valores[(valores < 0) | (valores > 1)]
        if len(fora):
            erros.append(f"{col}: {len(fora)} valores fora de [0, 1]")

    partidos = ativos[ativos.partido.isin(["PT", "PL"]) & (ativos.janela >= JANELA_INICIAL)]
    for (janela, partido), g in partidos.groupby(["janela", "partido"]):
        if g.deputado_id.nunique() < MIN_DEPUTADOS_PARTIDO:
            continue
        mediana = float(g.alinh_gov.median())
        if partido == "PT" and mediana < PT_MIN:
            erros.append(f"janela {janela}: mediana de alinh_gov do PT = {mediana:.3f} < {PT_MIN}")
        if partido == "PL" and mediana > PL_MAX:
            erros.append(f"janela {janela}: mediana de alinh_gov do PL = {mediana:.3f} > {PL_MAX}")
    return erros


def marcar_regra_radar(votos, votacoes, orientacoes) -> pd.DataFrame:
    """deputado_id, data e seguiu_radar pela regra do Radar do Congresso, sobre votações de todos os órgãos.

    Igual a `seguiu` (abstenção diverge; artigo17/branco ficam fora), mas só conta orientação do governo
    sim ou não: votações em que o governo orientou Obstrução ficam fora. Reproduz o Radar em 99,6% dos
    deputado-trimestres de 2023 a 2025. Serve só para validar a carga; os índices publicados não usam esta regra.
    """
    gov = (
        orientacoes[(orientacoes.bancada == BANCADA_GOVERNO) & orientacoes.orientacao.isin(ORIENTACOES_RADAR)]
        .drop_duplicates("id_votacao")[["id_votacao", "orientacao"]]
    )
    m = votos[["id_votacao", "deputado_id", "categoria"]].merge(gov, on="id_votacao").merge(
        votacoes[["id_votacao", "data"]], on="id_votacao"
    )
    m["seguiu_radar"] = _seguiu_vetor(m.categoria, m.orientacao)
    return m[["deputado_id", "data", "seguiu_radar"]]


def _alinhamento_no_periodo(base: pd.DataFrame, coluna: str, deputado_id: str, inicio, fim) -> float | None:
    sel = base[(base.deputado_id == deputado_id) & (base.data >= inicio) & (base.data <= fim)][coluna].dropna()
    return None if sel.empty else float(sel.astype(float).mean())


def checar_referencia(marcado, ref: pd.DataFrame, tolerancia_pp: float = 5.0,
                      marcado_radar: pd.DataFrame | None = None) -> list[str]:
    """Recalcula o alinhamento ao governo no período de cada linha de `ref` e aponta diferenças > tolerancia_pp.

    `alinhamento_governo` é uma fração em [0, 1]. Por `metodo`:
    - "igual": nossa regra (seguiu_gov de `marcado`, só Plenário);
    - "regra_radar": regra do Radar sobre `marcado_radar` (de `marcar_regra_radar`, todos os órgãos);
    - "diferente": não comparada.
    Qualquer outro valor de `metodo` é erro.
    """
    erros = []
    for r in ref.itertuples(index=False):
        metodo = str(r.metodo).strip()
        rotulo = f"referência {r.nome} ({r.fonte}, {r.inicio} a {r.fim})"
        if metodo not in METODOS:
            erros.append(f"{rotulo}: metodo desconhecido {metodo!r} (esperado um de {sorted(METODOS)})")
            continue
        if metodo == "diferente":
            continue
        if metodo == "regra_radar":
            if marcado_radar is None:
                erros.append(f"{rotulo}: linha pela regra do Radar sem os dados de todos os órgãos")
                continue
            base, coluna, regra = marcado_radar, "seguiu_radar", "regra do Radar"
        else:
            base, coluna, regra = marcado, "seguiu_gov", "regra do painel"
        nosso = _alinhamento_no_periodo(base, coluna, str(r.deputado_id), pd.Timestamp(r.inicio), pd.Timestamp(r.fim))
        if nosso is None:
            erros.append(f"{rotulo}: nenhum voto com orientação do governo ({regra})")
            continue
        diferenca = abs(nosso - float(r.alinhamento_governo)) * 100
        if diferenca > tolerancia_pp:
            erros.append(
                f"{rotulo}: externo {float(r.alinhamento_governo):.3f}, calculado {nosso:.3f} pela {regra} "
                f"(diferença {diferenca:.1f} pp > {tolerancia_pp} pp)"
            )
    return erros
