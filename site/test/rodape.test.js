import test from "node:test";
import assert from "node:assert/strict";
import {formatarData, textoRodape, rodape} from "../src/components/rodape.js";

const meta = {atualizado_em: "2026-11-13T06:05:00-03:00", fonte: "Câmara dos Deputados — Dados Abertos"};

test("formatarData usa o fuso de São Paulo", () => {
  assert.equal(formatarData("2026-11-13T06:05:00-03:00"), "13/11/2026 06:05");
  assert.equal(formatarData("2026-11-13T09:05:00Z"), "13/11/2026 06:05");
});

test("o rodapé cita a fonte e a data de atualização", () => {
  const texto = textoRodape(meta);
  assert.match(texto, /Câmara dos Deputados/);
  assert.equal(texto, "Fonte: Câmara dos Deputados — Dados Abertos · Atualizado em 13/11/2026 06:05");
});

test("rodape devolve um elemento com esse texto", () => {
  const el = {tag: null, textContent: "", className: ""};
  globalThis.document = {createElement: (tag) => Object.assign(el, {tag})};
  const r = rodape(meta);
  delete globalThis.document;
  assert.equal(r.tag, "footer");
  assert.match(r.textContent, /Câmara dos Deputados/);
});
