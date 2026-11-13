import test from "node:test";
import assert from "node:assert/strict";
import {pct, faixaPct, rotuloGrupo, governoRanking, ROTULO_SEM_GRUPO} from "../src/components/formato.js";

test("pct mostra — para valores ausentes ou não finitos", () => {
  assert.equal(pct(0.725), "73%");
  for (const x of [null, undefined, NaN, Infinity, -Infinity]) assert.equal(pct(x), "—");
});

test("faixaPct dá min e max, ou — sem valores", () => {
  assert.equal(faixaPct([0.3, 0.1, 0.2]), "10% e 30%");
  assert.equal(faixaPct([]), "—");
});

test("rotuloGrupo usa 'Sem grupo (poucos votos)' quando não há grupo", () => {
  assert.equal(ROTULO_SEM_GRUPO, "Sem grupo (poucos votos)");
  assert.equal(rotuloGrupo({grupo: "Base"}), "Base");
  assert.equal(rotuloGrupo({grupo: null}), ROTULO_SEM_GRUPO);
});

test("governoRanking mostra valor com IC, ou 'poucos votos' com n_gov < 30", () => {
  const r = {alinh_gov: 0.8, ic_gov_inf: 0.7, ic_gov_sup: 0.87};
  assert.equal(governoRanking({...r, n_gov: 30}), "80% (70% a 87%)");
  assert.equal(governoRanking({...r, n_gov: 12}), "poucos votos (12)");
  assert.equal(governoRanking({...r, n_gov: null}), "poucos votos (0)");
});
