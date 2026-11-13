"""Validações bloqueantes: placar oficial, sanidade dos índices e referência externa."""
from pathlib import Path

import pandas as pd

CAMINHO_REFERENCIA = Path(__file__).resolve().parent.parent / "data" / "referencia" / "externa.csv"
COLUNAS_REFERENCIA = ["fonte", "url", "metodo", "deputado_id", "nome", "inicio", "fim", "alinhamento_governo"]
MAX_LISTADOS = 10
# 2023T1 tem só 8 votações com orientação do governo (mediana n_gov = 6): fica fora das checagens por janela.
JANELA_INICIAL = "2023T2"
DEPUTADOS_MIN, DEPUTADOS_MAX = 400, 620
COLUNAS_ALINH = ["alinh_gov", "alinh_par", "alinh_maioria"]
PT_MIN, PL_MAX = 0.85, 0.50
MIN_DEPUTADOS_PARTIDO = 10


class ValidacaoFalhou(Exception):
    pass


def checar_placar(votos, votacoes, tolerancia: float = 0.02) -> list[str]:
    """Compara, em cada votação nominal do Plenário, as contagens sim/não dos votos com votos_sim/votos_nao.

    Nominal = placar oficial não nulo ou ao menos um voto registrado. As simbólicas (0/0, sem votos)
    ficam fora do denominador para não diluir a tolerância.
    """
    plen = votacoes[votacoes.sigla_orgao == "PLEN"].set_index("id_votacao")[["votos_sim", "votos_nao"]]
    nominal = (plen.votos_sim + plen.votos_nao > 0) | plen.index.isin(votos.id_votacao)
    plen = plen[nominal]
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


def checar_referencia(marcado, ref: pd.DataFrame, tolerancia_pp: float = 5.0) -> list[str]:
    """Recalcula alinh_gov no período de cada linha de `ref` e aponta diferenças > tolerancia_pp.

    `alinhamento_governo` é uma fração em [0, 1]. Linhas com metodo == "diferente" não geram erro.
    """
    erros = []
    for r in ref.itertuples(index=False):
        if str(r.metodo).strip() == "diferente":
            continue
        inicio, fim = pd.Timestamp(r.inicio), pd.Timestamp(r.fim)
        sel = marcado[
            (marcado.deputado_id == str(r.deputado_id)) & (marcado.data >= inicio) & (marcado.data <= fim)
        ].seguiu_gov.dropna()
        if sel.empty:
            erros.append(f"referência {r.nome} ({r.fonte}, {r.inicio} a {r.fim}): nenhum voto com orientação do governo")
            continue
        nosso = float(sel.astype(float).mean())
        diferenca = abs(nosso - float(r.alinhamento_governo)) * 100
        if diferenca > tolerancia_pp:
            erros.append(
                f"referência {r.nome} ({r.fonte}, {r.inicio} a {r.fim}): externo {float(r.alinhamento_governo):.3f}, "
                f"calculado {nosso:.3f} (diferença {diferenca:.1f} pp > {tolerancia_pp} pp)"
            )
    return erros
