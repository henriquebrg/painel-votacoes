import {readFileSync} from "node:fs";
import {textoRodape} from "./src/components/rodape.js";

// O rodapé do Framework é um texto fixo; lemos meta.json na hora do build
// para que toda página mostre a data da última atualização.
const meta = JSON.parse(readFileSync(new URL("./src/data/meta.json", import.meta.url), "utf8"));
const escapar = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export default {
  title: "Votações na Câmara — 57ª Legislatura",
  root: "src",
  pages: [
    {name: "Explorar", path: "/"},
    {name: "Metodologia", path: "/metodologia"}
  ],
  footer: `<span class="rodape-fonte">${escapar(textoRodape(meta))}</span>`,
  cleanUrls: true
};
