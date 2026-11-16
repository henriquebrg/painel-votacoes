import {readFileSync} from "node:fs";
import {textoRodape} from "./src/components/rodape.js";

// O rodapé do Framework é um texto fixo; lemos meta.json na hora do build
// para que toda página mostre a data da última atualização.
const meta = JSON.parse(readFileSync(new URL("./src/data/meta.json", import.meta.url), "utf8"));
const escapar = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const PAGINAS = [
  {name: "Explorar", path: "/"},
  {name: "Metodologia", path: "/metodologia"}
];
const normalizar = (p) => (p === "/index" ? "/" : p);

// Cabeçalho próprio no lugar da barra lateral: com duas páginas, a navegação cabe numa linha.
// Todas as páginas estão na raiz, então os links relativos valem em qualquer uma.
function cabecalho({path}) {
  const links = PAGINAS.map(({name, path: destino}) => {
    const atual = normalizar(path) === destino ? ' aria-current="page"' : "";
    return `<a href=".${destino === "/" ? "/" : destino}"${atual}>${name}</a>`;
  }).join("");
  return `<a class="marca" href="./">Votações na Câmara<span>57ª legislatura</span></a><nav aria-label="Páginas">${links}</nav>`;
}

export default {
  title: "Votações na Câmara — 57ª Legislatura",
  root: "src",
  pages: PAGINAS,
  sidebar: false,
  pager: false,
  toc: {label: "Nesta página"},
  style: "style.css",
  globalStylesheets: [],
  header: cabecalho,
  footer: `<span class="rodape-fonte">${escapar(textoRodape(meta))}</span>`,
  cleanUrls: true
};
