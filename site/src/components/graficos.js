import * as Plot from "npm:@observablehq/plot";
import {html, svg} from "npm:htl";
import {ordenarRanking} from "./estado.js";
import {pct, rotuloGrupo, governoRanking, formatarJanela, N_MIN, ROTULO_SEM_GRUPO} from "./formato.js";
import {termo, partidoUf, legenda} from "./termos.js";
import {EXPLICA, explicaGrupo} from "./explicacoes.js";
import {nomePartido} from "./siglas.js";

export {pct, ROTULO_SEM_GRUPO};

// Uma cor por grupo, a mesma em todas as páginas: goiaba, mostarda e petróleo.
// Validada para daltonismo (ΔE ≥ 8 entre todos os pares) com a skill de dataviz.
// O mostarda tem contraste baixo contra o fundo: os grupos sempre levam rótulo escrito.
export const CORES_GRUPO = {Base: "#e5576b", Independentes: "#c99418", "Oposição": "#00688f"};
export const COR_SEM_GRUPO = "#9aa0a6";
// Fundo da página (style.css), para o contorno dos rótulos sobre os pontos.
const FUNDO = "#f5f6f4";
// Ordem de leitura, da oposição à base (a mesma do eixo do governo).
export const ORDEM_GRUPOS = ["Oposição", "Independentes", "Base"];

// Uma cor por partido (os maiores); os demais em cinza.
export const CORES_PARTIDO = {
  PT: "#c0392b", PL: "#1f4e9e", "UNIÃO": "#17a2b8", PSD: "#e67e22", MDB: "#27ae60",
  PP: "#8e44ad", REPUBLICANOS: "#2c3e50", PSOL: "#f1c40f", NOVO: "#ff7f50"
};
export const COR_OUTRO_PARTIDO = "#bbb";
const corPartido = (p) => CORES_PARTIDO[p] ?? COR_OUTRO_PARTIDO;
export const PARTIDOS_SEM_ORIENTACAO = ["PT", "PL", "PP", "UNIÃO", "PSD", "MDB", "REPUBLICANOS"];

const num = (x) => (x ?? 0).toLocaleString("pt-BR");
// "votou com o governo em 26% de 38 votações"
const deVotacoes = (valor, n) => `${pct(valor)} de ${num(n)} ${n === 1 ? "votação" : "votações"}`;

/** Legenda dos grupos, com a explicação de cada um. `comSemGrupo` acrescenta o cinza. */
export function legendaGrupos(grupos, {comSemGrupo = true} = {}) {
  const itens = ORDEM_GRUPOS.filter((g) => !grupos?.rotulos || grupos.rotulos.includes(g))
    .map((g) => ({rotulo: g, cor: CORES_GRUPO[g], explicacao: explicaGrupo(g, grupos)}));
  if (comSemGrupo) itens.push({rotulo: ROTULO_SEM_GRUPO, cor: COR_SEM_GRUPO, explicacao: EXPLICA.semGrupo});
  return legenda(itens, {rotulo: "Grupos"});
}

/** Legenda de partidos, com o nome por extenso de cada sigla. */
export function legendaPartidos(partidos, {outros = false} = {}) {
  const itens = partidos.map((p) => ({rotulo: p, cor: corPartido(p), explicacao: nomePartido(p)}));
  if (outros) itens.push({rotulo: "Outros", cor: COR_OUTRO_PARTIDO, explicacao: "Os demais partidos, todos em cinza."});
  return legenda(itens, {rotulo: "Partidos"});
}

export const ROTULO_EIXO_PARTIDO = {
  maioria: "Alinhamento à maioria da bancada",
  orientacao: "Alinhamento à orientação do partido"
};

const campoPartido = (eixoPartido) => (eixoPartido === "orientacao" ? "alinh_par" : "alinh_maioria");
const campoNPartido = (eixoPartido) => (eixoPartido === "orientacao" ? "n_par" : "n_maioria");

/**
 * Dispersão governo × partido: um ponto por deputado, cor pelo grupo.
 * Deputados sem grupo (poucos votos) ficam em cinza, esmaecidos e atrás dos demais.
 * Centros dos grupos como anéis pretos (só no eixo da maioria, onde foram ajustados) e
 * o rastro do deputado selecionado (linha com pontos ao longo das janelas).
 * O valor do gráfico (`.value`) é o deputado sob o ponteiro.
 */
export function dispersao(rows, {grupos, rastro = [], eixoPartido = "maioria", destaque = null, width = 640} = {}) {
  const y = campoPartido(eixoPartido);
  const nPartido = campoNPartido(eixoPartido);
  // sem grupo primeiro: desenhados atrás
  const pontos = rows.filter((r) => r.alinh_gov != null && r[y] != null)
    .sort((a, b) => (a.grupo == null ? 0 : 1) - (b.grupo == null ? 0 : 1));
  const selecionado = pontos.filter((r) => destaque != null && String(r.deputado_id) === String(destaque));
  const trilha = rastro.filter((r) => r.alinh_gov != null && r[y] != null);
  const centros = eixoPartido === "maioria" && grupos
    ? grupos.centros.map(([gov, par], i) => ({alinh_gov: gov, [y]: par, rotulo: grupos.rotulos[i]}))
    : [];
  const rotulos = [
    ...ORDEM_GRUPOS.filter((g) => !grupos?.rotulos || grupos.rotulos.includes(g)),
    ...(pontos.some((r) => r.grupo == null) ? [ROTULO_SEM_GRUPO] : [])
  ];
  const opacidade = destaque == null ? 0.75 : 0.35;

  return Plot.plot({
    width,
    height: Math.min(560, Math.max(360, width * 0.72)),
    marginLeft: 48,
    marginBottom: 44,
    style: {fontSize: "12px"},
    x: {domain: [0, 1], tickFormat: pct, grid: true, label: "Alinhamento ao governo →", labelAnchor: "right"},
    y: {domain: [0, 1], ticks: 10, tickFormat: pct, grid: true, label: `↑ ${ROTULO_EIXO_PARTIDO[eixoPartido]}`},
    color: {
      domain: rotulos,
      range: rotulos.map((g) => CORES_GRUPO[g] ?? COR_SEM_GRUPO),
      unknown: COR_SEM_GRUPO
    },
    marks: [
      Plot.frame({stroke: "#ddd"}),
      Plot.dot(pontos, {
        x: "alinh_gov", y, fill: rotuloGrupo, r: 3.5,
        fillOpacity: {value: (d) => (d.grupo == null ? opacidade * 0.4 : opacidade), scale: null}, stroke: FUNDO, strokeWidth: 0.75
      }),
      Plot.line(trilha, {x: "alinh_gov", y, stroke: "#222", strokeWidth: 1.5, marker: "dot"}),
      // início do rastro; o fim coincide com o ponto destacado
      Plot.text(trilha.length > 1 ? trilha.slice(0, 1) : [], {
        x: "alinh_gov", y, text: "janela", dy: -10, fontSize: 10, fill: "#444"
      }),
      Plot.dot(selecionado, {x: "alinh_gov", y, r: 7, stroke: "#111", strokeWidth: 2, fill: rotuloGrupo}),
      Plot.text(selecionado, {
        x: "alinh_gov", y, text: (d) => d.nome, dy: -14, fontWeight: 600, fill: "#111",
        stroke: FUNDO, strokeWidth: 3
      }),
      Plot.dot(centros, {x: "alinh_gov", y, r: 9, stroke: "black", strokeWidth: 1.5, fill: "none"}),
      Plot.text(centros, {
        x: "alinh_gov", y, text: "rotulo", dx: 13, textAnchor: "start", fontWeight: 600,
        fill: "black", stroke: FUNDO, strokeWidth: 3
      }),
      Plot.tip(pontos, Plot.pointer({
        x: "alinh_gov", y,
        title: (d) => [
          `${d.nome} (${d.partido}-${d.uf}), ${nomePartido(d.partido)}`,
          `Grupo: ${rotuloGrupo(d)}`,
          `Votou com o governo em ${deVotacoes(d.alinh_gov, d.n_gov)}`,
          `Votou com ${eixoPartido === "orientacao" ? "a orientação do partido" : "a maioria da bancada"} em ${deVotacoes(d[y], d[nPartido])}`,
          "Clique para ver o caminho no tempo"
        ].join("\n")
      }))
    ]
  });
}

/**
 * Régua do Plenário: um traço por deputado, do menos ao mais alinhado ao governo, cor pelo grupo.
 * A posição é a ordem (não o valor), como as cadeiras de um placar: a régua mostra quantos
 * deputados há em cada trecho do eixo. O valor do gráfico (`.value`) é o deputado sob o ponteiro.
 */
export function regua(rows, {destaque = null, width = 640, animar = false} = {}) {
  const pontos = rows
    .filter((r) => r.alinh_gov != null)
    .sort((a, b) => a.alinh_gov - b.alinh_gov || a.nome.localeCompare(b.nome, "pt-BR"))
    .map((r, i) => ({...r, pos: i}));
  const n = pontos.length;
  const passo = width / Math.max(n, 1);
  const selecionado = pontos.filter((r) => destaque != null && String(r.deputado_id) === String(destaque));
  const g = Plot.plot({
    width,
    height: 60,
    marginTop: 4,
    marginBottom: 2,
    marginLeft: 1,
    marginRight: 1,
    x: {domain: [-0.5, Math.max(n, 1) - 0.5], axis: null},
    y: {domain: [0, 1], axis: null},
    marks: [
      Plot.ruleX(pontos, {
        x: "pos", y1: 0.08, y2: 1,
        stroke: (d) => CORES_GRUPO[d.grupo] ?? COR_SEM_GRUPO,
        strokeWidth: Math.max(1, passo - (passo > 3 ? 1 : 0.4))
      }),
      Plot.ruleX(selecionado, {x: "pos", y1: -0.02, y2: 1.1, stroke: "#1c2321", strokeWidth: Math.max(2, passo)}),
      Plot.tip(pontos, Plot.pointerX({
        x: "pos", y: 1, anchor: "bottom",
        title: (d) => `${d.nome} (${d.partido}-${d.uf})\nGrupo: ${rotuloGrupo(d)}\nVotou com o governo em ${deVotacoes(d.alinh_gov, d.n_gov)}`
      }))
    ]
  });
  g.classList.add("regua");
  if (animar) g.classList.add("animar");
  g.setAttribute("aria-label", `Régua com ${n.toLocaleString("pt-BR")} deputados ordenados pelo alinhamento ao governo`);
  return g;
}

/**
 * Contagem de deputados por grupo, na ordem da régua; serve de legenda dela.
 */
export function contagemGrupos(rows, grupos) {
  const conta = new Map();
  for (const r of rows) {
    if (r.alinh_gov == null) continue;
    const g = r.grupo ?? ROTULO_SEM_GRUPO;
    conta.set(g, (conta.get(g) ?? 0) + 1);
  }
  const ordem = [...ORDEM_GRUPOS, ROTULO_SEM_GRUPO].filter((g) => conta.has(g));
  return html`<ul class="contagem">${ordem.map((g) => html`<li>
    <span class="amostra" style=${`background:${CORES_GRUPO[g] ?? COR_SEM_GRUPO}`}></span>
    ${termo(g, g === ROTULO_SEM_GRUPO ? EXPLICA.semGrupo : explicaGrupo(g, grupos))} <strong>${conta.get(g).toLocaleString("pt-BR")}</strong>
  </li>`)}</ul>`;
}

/**
 * Mapa de posições (redução de dimensão dos votos): um ponto por deputado, cor pelo partido.
 * `rows` dá nome e partido (junção por deputado_id); só entram deputados presentes em `rows`.
 * `variancia` = [v1, v2], fração da variação explicada por cada dimensão (vai para a legenda).
 * O valor do gráfico (`.value`) é o deputado sob o ponteiro.
 */
export function mapaPosicoes(posicoes, rows, {destaque = null, variancia = null, width = 640} = {}) {
  const porId = new Map(rows.map((r) => [String(r.deputado_id), r]));
  const pontos = posicoes
    .filter((p) => porId.has(String(p.deputado_id)))
    .map((p) => {
      const r = porId.get(String(p.deputado_id));
      return {...p, deputado_id: String(p.deputado_id), nome: r.nome, partido: r.partido, uf: r.uf};
    });
  const selecionado = pontos.filter((p) => destaque != null && p.deputado_id === String(destaque));
  const partidos = Object.keys(CORES_PARTIDO);

  return Plot.plot({
    width,
    height: Math.min(520, Math.max(340, width * 0.62)),
    marginLeft: 44,
    marginBottom: 44,
    style: {fontSize: "12px"},
    x: {label: "← governo · Dimensão 1 · oposição →", labelAnchor: "center", ticks: 0, grid: false},
    y: {label: "↑ Dimensão 2", ticks: 0},
    color: {domain: partidos, range: partidos.map(corPartido), unknown: COR_OUTRO_PARTIDO},
    marks: [
      Plot.frame({stroke: "#ddd"}),
      Plot.dot(pontos, {
        x: "dim1", y: "dim2", fill: (d) => (CORES_PARTIDO[d.partido] ? d.partido : "outro"), r: 3.5,
        fillOpacity: destaque == null ? 0.8 : 0.35, stroke: FUNDO, strokeWidth: 0.75
      }),
      Plot.dot(selecionado, {x: "dim1", y: "dim2", r: 7, stroke: "#111", strokeWidth: 2, fill: (d) => corPartido(d.partido)}),
      Plot.text(selecionado, {
        x: "dim1", y: "dim2", text: "nome", dy: -14, fontWeight: 600, fill: "#111", stroke: FUNDO, strokeWidth: 3
      }),
      Plot.tip(pontos, Plot.pointer({
        x: "dim1", y: "dim2",
        title: (d) => `${d.nome} (${d.partido}-${d.uf})\n${nomePartido(d.partido)}\nPerto dele, quem vota de forma parecida`
      }))
    ]
  });
}

/**
 * Taxa de votações sem orientação do partido, por janela, uma linha por partido.
 * `rows`: registros de sem_orientacao.json já do modo desejado.
 */
export function semOrientacao(rows, {partidos = PARTIDOS_SEM_ORIENTACAO, janela = null, modo = "movel", width = 640} = {}) {
  const dados = rows.filter((r) => partidos.includes(r.partido) && r.taxa_sem_orientacao != null);
  const janelas = [...new Set(dados.map((r) => r.janela))].sort();
  return Plot.plot({
    width,
    height: 320,
    marginLeft: 44,
    marginBottom: 40,
    style: {fontSize: "12px"},
    // Só o 1º trimestre de cada ano leva rótulo; os demais ficam como marcas.
    x: {type: "point", domain: janelas, label: null, tickFormat: (j) => (j.endsWith("T1") ? formatarJanela(j) : "")},
    y: {domain: [0, 1], tickFormat: pct, grid: true, label: "↑ Votações sem orientação"},
    color: {domain: partidos, range: partidos.map(corPartido)},
    marks: [
      Plot.ruleX(janela && janelas.includes(janela) ? [janela] : [], {stroke: "#999", strokeDasharray: "3,3"}),
      Plot.line(dados, {x: "janela", y: "taxa_sem_orientacao", stroke: "partido", strokeWidth: 1.8}),
      Plot.dot(dados, {x: "janela", y: "taxa_sem_orientacao", fill: "partido", r: 2}),
      Plot.tip(dados, Plot.pointerX({
        x: "janela", y: "taxa_sem_orientacao",
        title: (d) => `${d.partido} (${nomePartido(d.partido)})\n${modo === "movel" ? "Nos 12 meses até o" : "No"} ${formatarJanela(d.janela)}\nNão orientou em ${pct(d.taxa_sem_orientacao)} das votações (${num(d.n_sem_orientacao)} de ${num(d.n_votacoes)})`
      }))
    ]
  });
}

// Barra 0–100% da fidelidade à bancada, com a faixa do IC 95% e o ponto estimado.
function barraFidelidade(r, largura = 140) {
  const x = (v) => 4 + v * (largura - 8);
  return svg`<svg width=${largura} height="14" viewBox="0 0 ${largura} 14" role="img"
      aria-label=${`Fidelidade ${pct(r.alinh_maioria)}, margem de erro de ${pct(r.ic_maioria_inf)} a ${pct(r.ic_maioria_sup)}`}>
    <title>${`Fidelidade medida: ${pct(r.alinh_maioria)} (o ponto). Margem de erro: de ${pct(r.ic_maioria_inf)} a ${pct(r.ic_maioria_sup)} (a faixa cinza).`}</title>
    <line x1=${x(0)} x2=${x(1)} y1="7" y2="7" stroke="#e3e3e3" stroke-width="6" stroke-linecap="round"></line>
    <line x1=${x(r.ic_maioria_inf ?? 0)} x2=${x(r.ic_maioria_sup ?? 1)} y1="7" y2="7" stroke="#9aa0a6" stroke-width="6"></line>
    <circle cx=${x(r.alinh_maioria ?? 0)} cy="7" r="4" fill=${corPartido(r.partido)} stroke="#111" stroke-width="1"></circle>
  </svg>`;
}

/**
 * Tabela dos deputados que mais se afastam da própria bancada (fidelidade = alinh_maioria).
 * Só linhas elegíveis, na ordem de posicao_ranking; `direcao` filtra ("todas" não filtra).
 * Clicar numa linha chama `aoSelecionar(deputado_id)`.
 */
export function rankingDesgarrados(rows, {limite = 20, direcao = "todas", destaque = null, aoSelecionar = null} = {}) {
  const linhas = ordenarRanking(rows, direcao).slice(0, limite);
  if (!linhas.length) return html`<p class="dica">Nenhum deputado elegível com estes filtros.</p>`;
  return html`<table class="ranking">
    <thead><tr>
      <th>${termo("#", EXPLICA.ordemRanking)}</th><th>Deputado</th>
      <th>${termo("Fidelidade à bancada", EXPLICA.fidelidade)}</th><th>${termo("IC 95%", EXPLICA.ic)}</th>
      <th>${termo("Governo (IC 95%)", EXPLICA.governoRanking)}</th><th>${termo("Direção", EXPLICA.direcao)}</th>
    </tr></thead>
    <tbody>${linhas.map((r) => {
      const tr = html`<tr class=${String(r.deputado_id) === String(destaque) ? "selecionado" : ""} tabindex="0">
        <td class="n">${r.posicao_ranking}</td>
        <td><span class="nome-dep">${r.nome}</span> <span class="sub">(${partidoUf(r.partido, r.uf)})</span></td>
        <td>${barraFidelidade(r)} <span class="valor">${pct(r.alinh_maioria)}</span></td>
        <td class="ic">${pct(r.ic_maioria_inf)} a ${pct(r.ic_maioria_sup)}</td>
        <td class=${(r.n_gov ?? 0) >= N_MIN ? "governo" : "governo poucos"}>${governoRanking(r)}</td>
        <td>${r.direcao ?? "—"}</td>
      </tr>`;
      if (aoSelecionar) {
        tr.onclick = () => aoSelecionar(r.deputado_id);
        tr.onkeydown = (ev) => (ev.key === "Enter" || ev.key === " ") && (ev.preventDefault(), aoSelecionar(r.deputado_id));
      }
      return tr;
    })}</tbody>
  </table>`;
}
