import * as Plot from "npm:@observablehq/plot";
import {html, svg} from "npm:htl";
import {ordenarRanking} from "./estado.js";

// Uma cor por grupo, a mesma em todas as páginas.
export const CORES_GRUPO = {Base: "#2f6690", Independentes: "#c08a2d", "Oposição": "#b8483a"};
export const COR_SEM_GRUPO = "#9aa0a6";

// Uma cor por partido (os maiores); os demais em cinza.
export const CORES_PARTIDO = {
  PT: "#c0392b", PL: "#1f4e9e", "UNIÃO": "#17a2b8", PSD: "#e67e22", MDB: "#27ae60",
  PP: "#8e44ad", REPUBLICANOS: "#2c3e50", PSOL: "#f1c40f", NOVO: "#ff7f50"
};
export const COR_OUTRO_PARTIDO = "#bbb";
const corPartido = (p) => CORES_PARTIDO[p] ?? COR_OUTRO_PARTIDO;
export const PARTIDOS_SEM_ORIENTACAO = ["PT", "PL", "PP", "UNIÃO", "PSD", "MDB", "REPUBLICANOS"];

export const pct = (x) => (x == null || Number.isNaN(x) ? "—" : `${Math.round(x * 100)}%`);
const num = (x) => (x ?? 0).toLocaleString("pt-BR");

export const ROTULO_EIXO_PARTIDO = {
  maioria: "Alinhamento à maioria da bancada",
  orientacao: "Alinhamento à orientação do partido"
};

const campoPartido = (eixoPartido) => (eixoPartido === "orientacao" ? "alinh_par" : "alinh_maioria");
const campoNPartido = (eixoPartido) => (eixoPartido === "orientacao" ? "n_par" : "n_maioria");

/**
 * Dispersão governo × partido: um ponto por deputado, cor pelo grupo.
 * Centros dos grupos como anéis pretos (só no eixo da maioria, onde foram ajustados) e
 * o rastro do deputado selecionado (linha com pontos ao longo das janelas).
 * O valor do gráfico (`.value`) é o deputado sob o ponteiro.
 */
export function dispersao(rows, {grupos, rastro = [], eixoPartido = "maioria", destaque = null, width = 640} = {}) {
  const y = campoPartido(eixoPartido);
  const nPartido = campoNPartido(eixoPartido);
  const pontos = rows.filter((r) => r.alinh_gov != null && r[y] != null);
  const selecionado = pontos.filter((r) => destaque != null && String(r.deputado_id) === String(destaque));
  const trilha = rastro.filter((r) => r.alinh_gov != null && r[y] != null);
  const centros = eixoPartido === "maioria" && grupos
    ? grupos.centros.map(([gov, par], i) => ({alinh_gov: gov, [y]: par, rotulo: grupos.rotulos[i]}))
    : [];
  const rotulos = grupos?.rotulos ?? Object.keys(CORES_GRUPO);

  return Plot.plot({
    width,
    height: Math.min(560, Math.max(360, width * 0.72)),
    marginLeft: 48,
    marginBottom: 44,
    style: {fontSize: "12px"},
    x: {domain: [0, 1], tickFormat: pct, grid: true, label: "Alinhamento ao governo →", labelAnchor: "right"},
    y: {domain: [0, 1], tickFormat: pct, grid: true, label: `↑ ${ROTULO_EIXO_PARTIDO[eixoPartido]}`},
    color: {
      domain: rotulos,
      range: rotulos.map((g) => CORES_GRUPO[g] ?? COR_SEM_GRUPO),
      unknown: COR_SEM_GRUPO,
      legend: true
    },
    marks: [
      Plot.frame({stroke: "#ddd"}),
      Plot.dot(pontos, {
        x: "alinh_gov", y, fill: "grupo", r: 3.5,
        fillOpacity: destaque == null ? 0.75 : 0.35, stroke: "white", strokeWidth: 0.5
      }),
      Plot.line(trilha, {x: "alinh_gov", y, stroke: "#222", strokeWidth: 1.5, marker: "dot"}),
      // início do rastro; o fim coincide com o ponto destacado
      Plot.text(trilha.length > 1 ? trilha.slice(0, 1) : [], {
        x: "alinh_gov", y, text: "janela", dy: -10, fontSize: 10, fill: "#444"
      }),
      Plot.dot(selecionado, {x: "alinh_gov", y, r: 7, stroke: "#111", strokeWidth: 2, fill: "grupo"}),
      Plot.text(selecionado, {
        x: "alinh_gov", y, text: (d) => d.nome, dy: -14, fontWeight: 600, fill: "#111",
        stroke: "white", strokeWidth: 3
      }),
      Plot.dot(centros, {x: "alinh_gov", y, r: 9, stroke: "black", strokeWidth: 1.5, fill: "none"}),
      Plot.text(centros, {
        x: "alinh_gov", y, text: "rotulo", dx: 13, textAnchor: "start", fontWeight: 600,
        fill: "black", stroke: "white", strokeWidth: 3
      }),
      Plot.tip(pontos, Plot.pointer({
        x: "alinh_gov", y,
        title: (d) => [
          `${d.nome} (${d.partido}-${d.uf})`,
          `Governo: ${pct(d.alinh_gov)}`,
          `Partido: ${pct(d[y])}`,
          `n: ${num(d.n_gov)} votações com orientação do governo · ${num(d[nPartido])} para o partido`
        ].join("\n")
      }))
    ]
  });
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
  const caption = variancia
    ? `A dimensão 1 resume ${pct(variancia[0])} da variação dos votos; a dimensão 2, ${pct(variancia[1])}.`
    : undefined;

  return Plot.plot({
    width,
    height: Math.min(520, Math.max(340, width * 0.62)),
    marginLeft: 44,
    marginBottom: 44,
    style: {fontSize: "12px"},
    caption,
    x: {label: "Dimensão 1 (governo ↔ oposição)", labelAnchor: "center", ticks: 0, grid: false},
    y: {label: "Dimensão 2", ticks: 0},
    color: {domain: partidos, range: partidos.map(corPartido), unknown: COR_OUTRO_PARTIDO, legend: true},
    marks: [
      Plot.frame({stroke: "#ddd"}),
      Plot.dot(pontos, {
        x: "dim1", y: "dim2", fill: (d) => (CORES_PARTIDO[d.partido] ? d.partido : "outro"), r: 3.5,
        fillOpacity: destaque == null ? 0.8 : 0.35, stroke: "white", strokeWidth: 0.5
      }),
      Plot.dot(selecionado, {x: "dim1", y: "dim2", r: 7, stroke: "#111", strokeWidth: 2, fill: (d) => corPartido(d.partido)}),
      Plot.text(selecionado, {
        x: "dim1", y: "dim2", text: "nome", dy: -14, fontWeight: 600, fill: "#111", stroke: "white", strokeWidth: 3
      }),
      Plot.tip(pontos, Plot.pointer({x: "dim1", y: "dim2", title: (d) => `${d.nome} (${d.partido}-${d.uf})`}))
    ]
  });
}

/**
 * Taxa de votações sem orientação do partido, por janela, uma linha por partido.
 * `rows`: registros de sem_orientacao.json já do modo desejado.
 */
export function semOrientacao(rows, {partidos = PARTIDOS_SEM_ORIENTACAO, janela = null, width = 640} = {}) {
  const dados = rows.filter((r) => partidos.includes(r.partido) && r.taxa_sem_orientacao != null);
  const janelas = [...new Set(dados.map((r) => r.janela))].sort();
  return Plot.plot({
    title: "Com que frequência cada partido deixou de orientar",
    width,
    height: 320,
    marginLeft: 44,
    marginBottom: 40,
    style: {fontSize: "12px"},
    x: {type: "point", domain: janelas, label: null, tickFormat: (j, i) => (janelas.length > 8 && i % 2 ? "" : j)},
    y: {domain: [0, 1], tickFormat: pct, grid: true, label: "↑ Votações sem orientação"},
    color: {domain: partidos, range: partidos.map(corPartido), legend: true},
    marks: [
      Plot.ruleX(janela && janelas.includes(janela) ? [janela] : [], {stroke: "#999", strokeDasharray: "3,3"}),
      Plot.line(dados, {x: "janela", y: "taxa_sem_orientacao", stroke: "partido", strokeWidth: 1.8}),
      Plot.dot(dados, {x: "janela", y: "taxa_sem_orientacao", fill: "partido", r: 2}),
      Plot.tip(dados, Plot.pointerX({
        x: "janela", y: "taxa_sem_orientacao",
        title: (d) => `${d.partido} · ${d.janela}\n${pct(d.taxa_sem_orientacao)} sem orientação (${num(d.n_sem_orientacao)} de ${num(d.n_votacoes)} votações)`
      }))
    ]
  });
}

// Barra 0–100% da fidelidade à bancada, com a faixa do IC 95% e o ponto estimado.
function barraFidelidade(r, largura = 140) {
  const x = (v) => 4 + v * (largura - 8);
  return svg`<svg width=${largura} height="14" viewBox="0 0 ${largura} 14" role="img"
      aria-label=${`Fidelidade ${pct(r.alinh_maioria)}, IC ${pct(r.ic_maioria_inf)} a ${pct(r.ic_maioria_sup)}`}>
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
  if (!linhas.length) return html`<p class="dica">Nenhum deputado com ao menos 30 votações contadas nesta janela.</p>`;
  return html`<table class="ranking">
    <thead><tr><th>#</th><th>Deputado</th><th>Fidelidade à bancada</th><th>IC 95%</th><th>Governo</th><th>Direção</th></tr></thead>
    <tbody>${linhas.map((r) => {
      const tr = html`<tr class=${String(r.deputado_id) === String(destaque) ? "selecionado" : ""} tabindex="0">
        <td class="n">${r.posicao_ranking}</td>
        <td><strong>${r.nome}</strong> <span class="sub">(${r.partido}-${r.uf})</span></td>
        <td>${barraFidelidade(r)} <span class="valor">${pct(r.alinh_maioria)}</span></td>
        <td class="ic">${pct(r.ic_maioria_inf)} a ${pct(r.ic_maioria_sup)}</td>
        <td class="valor">${pct(r.alinh_gov)}</td>
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
