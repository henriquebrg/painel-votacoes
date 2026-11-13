import test from "node:test";
import assert from "node:assert/strict";
import {ESTADO_PADRAO, lerEstado, escreverEstado, filtrar, rastro} from "../src/components/estado.js";

const UFS_NORDESTE = new Set(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"]);

const linha = (janela, modo, deputado_id, uf, regiao, partido, grupo, alinh_gov) => ({
  janela, modo, deputado_id, nome: `Dep ${deputado_id}`, uf, regiao, partido, grupo,
  alinh_gov, alinh_maioria: alinh_gov / 2, alinh_par: alinh_gov / 4
});

const linhas = [
  linha("2025T3", "movel", "1", "BA", "Nordeste", "PT", "Base", 0.9),
  linha("2025T4", "movel", "1", "BA", "Nordeste", "PT", "Base", 0.8),
  linha("2025T4", "movel", "2", "SP", "Sudeste", "PL", "Oposição", 0.2),
  linha("2025T4", "movel", "3", "PE", "Nordeste", "UNIÃO", "Independentes", 0.6),
  linha("2025T4", "movel", "4", "RS", "Sul", "UNIÃO", "Base", 0.7),
  linha("2025T4", "trimestre", "1", "BA", "Nordeste", "PT", "Base", 0.85),
  linha("2026T1", "movel", "1", "BA", "Nordeste", "PT", "Base", 0.7),
  linha("2025T2", "movel", "1", "BA", "Nordeste", "PT", "Base", 0.95),
  linha("legislatura", "legislatura", "1", "BA", "Nordeste", "PT", "Base", 0.88)
];
const ordem = ["2025T1", "2025T2", "2025T3", "2025T4", "2026T1"];

test("ida e volta pela URL preserva o estado, com acentos e deputado", () => {
  const e = {...ESTADO_PADRAO, modo: "trimestre", janela: "2024T2", ufs: ["BA", "SP"], regioes: ["Centro-Oeste"],
    partidos: ["UNIÃO", "PL"], grupos: ["Oposição"], deputado: "204379", eixoPartido: "orientacao"};
  assert.deepEqual(lerEstado(escreverEstado(e)), e);
  const so = {...ESTADO_PADRAO, partidos: ["UNIÃO"], deputado: "204379"};
  assert.deepEqual(lerEstado(escreverEstado(so)), so);
});

test("o estado padrão não escreve nada na URL e é o que se lê de uma URL vazia", () => {
  assert.equal(escreverEstado(ESTADO_PADRAO), "");
  assert.deepEqual(lerEstado(""), ESTADO_PADRAO);
  assert.deepEqual(lerEstado("?"), ESTADO_PADRAO);
});

test("só os valores diferentes do padrão vão para a URL", () => {
  assert.equal(escreverEstado({...ESTADO_PADRAO, janela: "2025T4", partidos: ["PL"]}), "?j=2025T4&p=PL");
  assert.deepEqual(lerEstado("?j=2025T4&p=PL"), {...ESTADO_PADRAO, janela: "2025T4", partidos: ["PL"]});
});

test("valores inválidos na URL voltam ao padrão", () => {
  assert.deepEqual(lerEstado("?m=semanal&ep=outro&uf=,,"), ESTADO_PADRAO);
});

test("filtrar por região devolve só UFs do Nordeste", () => {
  const r = filtrar(linhas, {...ESTADO_PADRAO, janela: "2025T4", regioes: ["Nordeste"]});
  assert.deepEqual(r.map((x) => x.deputado_id).sort(), ["1", "3"]);
  assert.ok(r.every((x) => UFS_NORDESTE.has(x.uf)));
});

test("filtrar aplica modo, janela, UF, partido e grupo; lista vazia não filtra", () => {
  const base = {...ESTADO_PADRAO, janela: "2025T4"};
  assert.equal(filtrar(linhas, base).length, 4);
  assert.deepEqual(filtrar(linhas, {...base, partidos: ["UNIÃO"]}).map((x) => x.deputado_id), ["3", "4"]);
  assert.deepEqual(filtrar(linhas, {...base, partidos: ["UNIÃO"], grupos: ["Base"]}).map((x) => x.deputado_id), ["4"]);
  assert.deepEqual(filtrar(linhas, {...base, ufs: ["SP"]}).map((x) => x.deputado_id), ["2"]);
  assert.deepEqual(filtrar(linhas, {...base, modo: "trimestre"}).map((x) => x.alinh_gov), [0.85]);
});

test("filtrar com janela nula usa a última janela do modo", () => {
  assert.deepEqual(filtrar(linhas, ESTADO_PADRAO).map((x) => x.janela), ["2026T1"]);
});

test("filtrar no modo legislatura ignora a janela", () => {
  const r = filtrar(linhas, {...ESTADO_PADRAO, modo: "legislatura", janela: "2025T4"});
  assert.deepEqual(r.map((x) => x.janela), ["legislatura"]);
});

test("rastro devolve as janelas em ordem e para em ateJanela", () => {
  const r = rastro(linhas, "1", "movel", "2025T4", ordem);
  assert.deepEqual(r, [
    {janela: "2025T2", alinh_gov: 0.95, alinh_maioria: 0.475, alinh_par: 0.2375},
    {janela: "2025T3", alinh_gov: 0.9, alinh_maioria: 0.45, alinh_par: 0.225},
    {janela: "2025T4", alinh_gov: 0.8, alinh_maioria: 0.4, alinh_par: 0.2}
  ]);
  assert.deepEqual(rastro(linhas, "1", "movel", null, ordem).map((x) => x.janela), ["2025T2", "2025T3", "2025T4", "2026T1"]);
  assert.deepEqual(rastro(linhas, "2", "movel", "2025T3", ordem), []);
});
