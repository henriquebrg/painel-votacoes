import * as Plot from "npm:@observablehq/plot";

// Uma cor por grupo, a mesma em todas as páginas.
export const CORES_GRUPO = {Base: "#2f6690", Independentes: "#c08a2d", "Oposição": "#b8483a"};
export const COR_SEM_GRUPO = "#9aa0a6";

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
