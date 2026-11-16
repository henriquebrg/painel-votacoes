import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync, existsSync} from "node:fs";
import {PARTIDOS, UFS, nomePartido, nomeUf, explicaPartidoUf} from "../src/components/siglas.js";

test("siglas desconhecidas voltam como vieram", () => {
  assert.equal(nomePartido("XYZ"), "XYZ");
  assert.equal(nomeUf("ZZ"), "ZZ");
});

test("explicaPartidoUf junta partido e estado por extenso", () => {
  assert.equal(explicaPartidoUf("PSD", "PR"), "Partido Social Democrático. Estado: Paraná.");
});

test("as 27 unidades da federação têm nome", () => {
  assert.equal(Object.keys(UFS).length, 27);
});

// Com os dados gerados presentes, toda sigla usada pelo painel precisa ter nome por extenso.
// Só roda localmente: no CI, um partido novo não deve travar a atualização diária
// (no site, a sigla sem nome aparece sem explicação).
const arquivo = new URL("../src/data/indices-movel.json", import.meta.url);
const pular = process.env.CI ? "no CI" : !existsSync(arquivo) && "sem dados gerados";
test("todo partido e UF dos dados têm nome por extenso", {skip: pular}, () => {
  const rows = JSON.parse(readFileSync(arquivo, "utf8"));
  const semNome = [...new Set(rows.map((r) => r.partido))].filter((p) => !(p in PARTIDOS));
  assert.deepEqual(semNome, []);
  assert.deepEqual([...new Set(rows.map((r) => r.uf))].filter((u) => !(u in UFS)), []);
});
