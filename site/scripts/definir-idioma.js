// O Framework 1.13 não tem opção de idioma: marcamos o <html> de cada página gerada.
import {readdirSync, readFileSync, writeFileSync, statSync} from "node:fs";
import {join} from "node:path";
import {fileURLToPath} from "node:url";

function paginas(dir) {
  return readdirSync(dir).flatMap((nome) => {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) return nome.startsWith("_") ? [] : paginas(caminho);
    return nome.endsWith(".html") ? [caminho] : [];
  });
}

for (const arquivo of paginas(fileURLToPath(new URL("../dist", import.meta.url)))) {
  const html = readFileSync(arquivo, "utf8");
  writeFileSync(arquivo, html.replace(/<html(?![^>]*\blang=)/, '<html lang="pt-BR"'));
}
