// Registra a Archivo (Omnibus-Type, licença OFL; ver fonts/OFL-Archivo.txt), variável em peso e largura.
// Só o subconjunto latino: cobre todo o português. Até ela carregar, vale a fonte do sistema.
import {FileAttachment} from "observablehq:stdlib";

const arquivo = FileAttachment("../fonts/archivo-latin-wdth-normal.woff2");

export async function carregarFonte() {
  if (typeof FontFace === "undefined" || [...document.fonts].some((f) => f.family === "Archivo")) return;
  const fonte = new FontFace("Archivo", `url(${await arquivo.url()}) format("woff2")`, {
    weight: "100 900", stretch: "62% 125%", display: "swap"
  });
  document.fonts.add(fonte);
  await fonte.load();
}
