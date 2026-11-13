// Estado da página Explorar e sua forma na URL (?m=&j=&uf=&rg=&p=&g=&d=&ep=).

export const MODOS = ["movel", "trimestre", "legislatura"];
export const EIXOS_PARTIDO = ["maioria", "orientacao"];

// janela: null = última janela de meta.janelas
export const ESTADO_PADRAO = Object.freeze({
  modo: "movel", janela: null, ufs: [], regioes: [], partidos: [], grupos: [], deputado: null, eixoPartido: "maioria"
});

// chave do estado -> parâmetro da URL, na ordem em que são escritos
const LISTAS = {ufs: "uf", regioes: "rg", partidos: "p", grupos: "g"};

export function lerEstado(search) {
  const q = new URLSearchParams(search);
  const texto = (k) => q.get(k) || null;
  const lista = (k) => (q.get(k) || "").split(",").filter(Boolean);
  const opcao = (k, validas, padrao) => (validas.includes(q.get(k)) ? q.get(k) : padrao);
  return {
    modo: opcao("m", MODOS, ESTADO_PADRAO.modo),
    janela: texto("j"),
    ...Object.fromEntries(Object.entries(LISTAS).map(([chave, k]) => [chave, lista(k)])),
    deputado: texto("d"),
    eixoPartido: opcao("ep", EIXOS_PARTIDO, ESTADO_PADRAO.eixoPartido)
  };
}

export function escreverEstado(e) {
  const pares = [];
  const incluir = (k, v) => pares.push(`${k}=${encodeURIComponent(v)}`);
  if (e.modo !== ESTADO_PADRAO.modo) incluir("m", e.modo);
  if (e.janela) incluir("j", e.janela);
  for (const [chave, k] of Object.entries(LISTAS)) {
    if (e[chave]?.length) pares.push(`${k}=${e[chave].map(encodeURIComponent).join(",")}`);
  }
  if (e.deputado) incluir("d", e.deputado);
  if (e.eixoPartido !== ESTADO_PADRAO.eixoPartido) incluir("ep", e.eixoPartido);
  return pares.length ? `?${pares.join("&")}` : "";
}

const contem = (lista, valor) => !lista?.length || lista.includes(valor);

export function filtrar(rows, e) {
  const doModo = rows.filter((r) => r.modo === e.modo);
  // no modo legislatura só existe uma janela ("legislatura")
  const janela = e.modo === "legislatura" ? null
    : e.janela ?? doModo.reduce((max, r) => (r.janela > max ? r.janela : max), "");
  return doModo.filter((r) =>
    (janela === null || r.janela === janela)
    && contem(e.ufs, r.uf) && contem(e.regioes, r.regiao)
    && contem(e.partidos, r.partido) && contem(e.grupos, r.grupo));
}

export function rastro(rows, deputadoId, modo, ateJanela, janelasOrdem) {
  const posicao = new Map(janelasOrdem.map((j, i) => [j, i]));
  const limite = ateJanela == null ? Infinity : posicao.get(ateJanela) ?? -1;
  return rows
    .filter((r) => r.modo === modo && String(r.deputado_id) === String(deputadoId)
      && posicao.has(r.janela) && posicao.get(r.janela) <= limite)
    .sort((a, b) => posicao.get(a.janela) - posicao.get(b.janela))
    .map(({janela, alinh_gov, alinh_maioria, alinh_par}) => ({janela, alinh_gov, alinh_maioria, alinh_par}));
}

export const DIRECOES = ["todas", "rumo ao governo", "rumo à oposição"];

// Só deputados elegíveis ao ranking, na ordem de posicao_ranking (1 = mais desgarrado).
export function ordenarRanking(rows, direcao = "todas") {
  return rows
    .filter((r) => r.elegivel_ranking && r.posicao_ranking != null
      && (direcao === "todas" || r.direcao === direcao))
    .sort((a, b) => a.posicao_ranking - b.posicao_ranking);
}
