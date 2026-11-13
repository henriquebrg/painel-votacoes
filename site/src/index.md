---
title: Explorar
toc: false
---

# Como votam os deputados

<p class="lead">Cada ponto é um deputado: o quanto ele vota com o governo (eixo horizontal) e com a própria bancada (eixo vertical), nas votações nominais do Plenário da Câmara.</p>

```js
import {lerEstado, escreverEstado, filtrar, rastro, DIRECOES} from "./components/estado.js";
import {dispersao, mapaPosicoes, rankingDesgarrados, semOrientacao, CORES_GRUPO, COR_SEM_GRUPO, ROTULO_EIXO_PARTIDO, pct} from "./components/graficos.js";
```

```js
const meta = FileAttachment("data/meta.json").json();
const grupos = FileAttachment("data/grupos.json").json();
const mapa = FileAttachment("data/mapa.json").json();
const semOrientacaoRows = FileAttachment("data/sem_orientacao.json").json();
// FileAttachment exige nomes literais: um arquivo por modo, carregado só quando o modo é ativado.
const ARQUIVOS_INDICES = {
  movel: FileAttachment("data/indices-movel.json"),
  trimestre: FileAttachment("data/indices-trimestre.json"),
  legislatura: FileAttachment("data/indices-legislatura.json")
};
const inicial = lerEstado(location.search);
// Inputs recriados ao trocar de modo partem do estado que já está na URL.
const naUrl = () => lerEstado(location.search);
```

```js
const ROTULO_MODO = {movel: "Móvel (4 trimestres)", trimestre: "Trimestre", legislatura: "Legislatura inteira"};
const REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"];
const formatarJanela = (j) => (/^\d{4}T\d$/.test(j) ? `${j.slice(5)}º tri ${j.slice(0, 4)}` : j);
const decimal = (x) => (x == null ? "—" : x.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2}));
const ordenar = (xs) => [...xs].sort((a, b) => a.localeCompare(b, "pt-BR"));
const opcoes = (rows, campo) => ordenar(new Set(rows.map((r) => r[campo]).filter(Boolean)));
const multipla = (label, opts, valor) =>
  Inputs.select(opts, {label, multiple: true, size: 5, value: valor.filter((v) => opts.includes(v))});

function seletorJanela(janelas, valorInicial) {
  let i = janelas.includes(valorInicial) ? janelas.indexOf(valorInicial) : janelas.length - 1;
  let relogio = null;
  const faixa = html`<input type="range" min="0" max=${janelas.length - 1} step="1" aria-label="Trimestre">`;
  const rotulo = html`<output></output>`;
  const botao = html`<button type="button" class="tocar" title="Percorrer os trimestres">▶</button>`;
  const el = html`<div class="seletor-janela"><span class="rotulo">Trimestre</span>${botao}${faixa}${rotulo}</div>`;
  const mostrar = () => { faixa.value = i; rotulo.textContent = formatarJanela(janelas[i]); el.value = janelas[i]; };
  const definir = (k) => { i = k; mostrar(); el.dispatchEvent(new Event("input", {bubbles: true})); };
  el.parar = () => { clearInterval(relogio); relogio = null; botao.textContent = "▶"; };
  botao.onclick = () => {
    if (relogio) return el.parar();
    if (i === janelas.length - 1) definir(0);
    botao.textContent = "❚❚";
    relogio = setInterval(() => (i < janelas.length - 1 ? definir(i + 1) : el.parar()), 1500);
  };
  faixa.oninput = (ev) => { ev.stopPropagation(); el.parar(); definir(+faixa.value); };
  mostrar();
  return el;
}
```

```js
const modoInput = Inputs.radio(Object.keys(ROTULO_MODO), {label: "Janela", value: inicial.modo, format: (m) => ROTULO_MODO[m]});
const modo = Generators.input(modoInput);
const seletor = seletorJanela(meta.janelas, inicial.janela);
const janela = Generators.input(seletor);
invalidation.then(() => seletor.parar());
const regioesInput = multipla("Região", REGIOES, inicial.regioes);
const regioes = Generators.input(regioesInput);
const gruposInput = multipla("Grupo", grupos.rotulos, inicial.grupos);
const gruposSel = Generators.input(gruposInput);
const eixoInput = Inputs.radio(Object.keys(ROTULO_EIXO_PARTIDO), {
  label: "Eixo do partido", value: inicial.eixoPartido,
  format: (e) => (e === "maioria" ? "Maioria da bancada" : "Orientação do partido")
});
const eixoPartido = Generators.input(eixoInput);
```

```js
const deputado = Mutable(inicial.deputado);
const selecionar = (id) => (deputado.value = id == null ? null : String(id));
```

```js
const indices = ARQUIVOS_INDICES[modo].json();
```

```js
const ufsInput = multipla("UF", opcoes(indices, "uf"), naUrl().ufs);
const ufs = Generators.input(ufsInput);
const partidosInput = multipla("Partido", opcoes(indices, "partido"), naUrl().partidos);
const partidos = Generators.input(partidosInput);
```

```js
const legislatura = modo === "legislatura";
for (const c of seletor.querySelectorAll("input, button")) c.disabled = legislatura;
seletor.classList.toggle("inativo", legislatura);
if (legislatura) seletor.parar();
```

```js
const estado = {
  modo, janela: janela === meta.janelas.at(-1) ? null : janela,
  ufs, regioes, partidos, grupos: gruposSel, deputado, eixoPartido
};
history.replaceState(history.state, "", location.pathname + escreverEstado(estado) + location.hash);
const visiveis = filtrar(indices, {...estado, janela});
const trilha = deputado ? rastro(indices, deputado, modo, janela, meta.janelas) : [];
const doDeputado = deputado ? indices.filter((r) => String(r.deputado_id) === deputado) : [];
const linhaDep = doDeputado.find((r) => legislatura || r.janela === janela) ?? null;
```

```js
const copiar = html`<button type="button" class="botao-link">Copiar link desta visão</button>`;
copiar.onclick = async () => {
  try {
    await navigator.clipboard.writeText(location.href);
    copiar.textContent = "Link copiado";
  } catch {
    copiar.textContent = "Não foi possível copiar — use a barra de endereço";
  }
  setTimeout(() => (copiar.textContent = "Copiar link desta visão"), 2500);
};
```

<div class="filtros">
  <div class="filtros-tempo">${modoInput}${seletor}${eixoInput}</div>
  <div class="filtros-recorte">${ufsInput}${regioesInput}${partidosInput}${gruposInput}</div>
</div>

<div class="resumo">
  <span><strong>${visiveis.length.toLocaleString("pt-BR")}</strong> deputados · ${legislatura ? "toda a legislatura" : `${ROTULO_MODO[modo].toLowerCase()} até ${formatarJanela(janela)}`}</span>
  ${copiar}
</div>

<div class="grid grid-cols-3 explorar">
  <div class="card grid-colspan-2">${resize((width) => {
    const g = dispersao(visiveis, {grupos, rastro: trilha, eixoPartido, destaque: deputado, width});
    g.addEventListener("click", () => g.value && selecionar(g.value.deputado_id));
    return g;
  })}
  ${eixoPartido === "orientacao" ? html`<p class="nota">A orientação partidária nem sempre é dada. Cobertura por ano: ${Object.entries(meta.cobertura_orientacao_partido).map(([ano, c]) => `${ano} ${pct(c)}`).join(" · ")}. Por isso o eixo padrão é a maioria da bancada.</p>` : ""}
  </div>
  <div class="card painel-deputado">${painelDeputado()}</div>
</div>

```js
// O mapa só existe para janelas móveis: no trimestre usa a janela móvel que termina nele;
// na legislatura, a última janela móvel com mapa.
const janelasMapa = [...new Set(mapa.posicoes.map((p) => p.janela))].sort();
const janelaMapa = legislatura ? janelasMapa.at(-1) : janela;
const posicoesMapa = mapa.posicoes.filter((p) => p.janela === janelaMapa);
const notaMapa = posicoesMapa.length === 0
  ? `Sem mapa de posições para ${formatarJanela(janelaMapa)}.`
  : modo === "trimestre"
    ? `O mapa usa a janela móvel de 4 trimestres até ${formatarJanela(janelaMapa)}; um trimestre sozinho tem poucas votações.`
    : legislatura
      ? `O mapa usa a última janela móvel (4 trimestres até ${formatarJanela(janelaMapa)}).`
      : null;
// Sem orientação: a série do modo atual; na legislatura, a série móvel.
const modoSemOrientacao = legislatura ? "movel" : modo;
const serieSemOrientacao = semOrientacaoRows.filter((r) => r.modo === modoSemOrientacao);
```

```js
// Célula própria: o filtro de direção não volta a "todas" quando a janela muda.
const direcaoInput = Inputs.radio(DIRECOES, {label: "Direção", value: "todas"});
const direcao = Generators.input(direcaoInput);
```

<div class="grid grid-cols-2 explorar">
  <div class="card">
    <h2>Mapa de posições</h2>
    <p class="dica">Deputados que votam de forma parecida ficam perto. Cor pelo partido.</p>
    ${posicoesMapa.length ? resize((width) => {
      const g = mapaPosicoes(posicoesMapa, visiveis, {destaque: deputado, variancia: mapa.variancia[janelaMapa], width});
      g.addEventListener("click", () => g.value && selecionar(g.value.deputado_id));
      return g;
    }) : ""}
    ${notaMapa ? html`<p class="nota">${notaMapa}</p>` : ""}
  </div>
  <div class="card">${resize((width) => semOrientacao(serieSemOrientacao, {janela: legislatura ? null : janela, width}))}
    ${legislatura ? html`<p class="nota">Na legislatura inteira, a série mostra as janelas móveis de 4 trimestres.</p>` : ""}
  </div>
</div>

<div class="card ranking-card">
  <h2>Desgarrados: quem mais se afasta da própria bancada</h2>
  <p class="dica">Fidelidade = parcela das votações em que o deputado votou com a maioria dos colegas de partido. A barra cinza é o intervalo de 95%; só entram deputados com ao menos 30 votações contadas. Clique numa linha para destacar o deputado.</p>
  ${direcaoInput}
  ${rankingDesgarrados(visiveis, {limite: 20, direcao, destaque: deputado, aoSelecionar: selecionar})}
</div>

```js
function linhaIndice(rotulo, valor, inf, sup, n) {
  return html`<tr><th scope="row">${rotulo}</th><td class="valor">${pct(valor)}</td>
    <td class="ic">${valor == null ? "—" : `${pct(inf)} a ${pct(sup)}`}</td><td class="n">${(n ?? 0).toLocaleString("pt-BR")}</td></tr>`;
}

function escolherNaLista() {
  const lista = [...visiveis].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  const sel = html`<select aria-label="Escolher deputado"><option value="">Ou escolha na lista…</option>${lista.map(
    (r) => html`<option value=${r.deputado_id}>${r.nome} (${r.partido}-${r.uf})</option>`
  )}</select>`;
  sel.onchange = () => selecionar(sel.value || null);
  return sel;
}

function painelDeputado() {
  if (!deputado) {
    return html`<h2>Deputado</h2>
      <p class="dica">Clique em um ponto para ver os índices do deputado e o caminho dele ao longo dos trimestres.</p>
      ${escolherNaLista()}`;
  }
  const limpar = html`<button type="button" class="limpar">Limpar seleção</button>`;
  limpar.onclick = () => selecionar(null);
  const r = linhaDep;
  if (!r) {
    const nome = doDeputado[0]?.nome ?? `Deputado ${deputado}`;
    return html`<h2>${nome}</h2><p class="dica">Sem votações contadas nesta janela.</p>${limpar}`;
  }
  const cor = CORES_GRUPO[r.grupo] ?? COR_SEM_GRUPO;
  return html`<h2>${r.nome}</h2>
    <p class="sub">${r.partido}-${r.uf} · ${r.regiao}</p>
    <p class="grupo"><span class="bolinha" style="background:${cor}"></span><strong>${r.grupo ?? "Sem grupo"}</strong>
      <span class="dist">distância ao centro do grupo: ${decimal(r.dist_centro)}</span></p>
    <table class="indices">
      <thead><tr><th></th><th>Índice</th><th>IC 95%</th><th>n</th></tr></thead>
      <tbody>
        ${linhaIndice("Governo", r.alinh_gov, r.ic_gov_inf, r.ic_gov_sup, r.n_gov)}
        ${linhaIndice("Maioria da bancada", r.alinh_maioria, r.ic_maioria_inf, r.ic_maioria_sup, r.n_maioria)}
        ${linhaIndice("Orientação do partido", r.alinh_par, r.ic_par_inf, r.ic_par_sup, r.n_par)}
      </tbody>
    </table>
    <p class="fora">Fora da conta: ${(r.n_artigo17 ?? 0).toLocaleString("pt-BR")} votos “Artigo 17” e ${(r.n_branco ?? 0).toLocaleString("pt-BR")} em branco.</p>
    ${trilha.length > 1 ? html`<p class="dica">A linha no gráfico mostra o caminho de ${formatarJanela(trilha[0].janela)} a ${formatarJanela(trilha.at(-1).janela)}.</p>` : ""}
    ${limpar}`;
}
```

<style>
.lead { max-width: 68ch; color: var(--theme-foreground-muted); font-size: 1.05rem; }
.filtros { display: flex; flex-direction: column; gap: 0.75rem; margin: 1.5rem 0 0.5rem; }
.filtros-tempo, .filtros-recorte { display: flex; flex-wrap: wrap; gap: 0.5rem 2rem; align-items: flex-start; }
.filtros-recorte form { width: auto; }
.filtros-recorte select { min-width: 9rem; }
.seletor-janela { display: flex; align-items: center; gap: 0.5rem; font: 13px var(--sans-serif); }
.seletor-janela .rotulo { min-width: 5.5rem; }
.seletor-janela input[type=range] { width: 14rem; }
.seletor-janela output { min-width: 6.5rem; font-variant-numeric: tabular-nums; }
.seletor-janela.inativo { opacity: 0.4; }
.tocar { width: 2rem; }
.resumo { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;
  font-size: 0.9rem; color: var(--theme-foreground-muted); margin: 0.5rem 0; }
.botao-link, .limpar { font: inherit; font-size: 0.85rem; padding: 0.3rem 0.8rem; border-radius: 4px; cursor: pointer;
  border: 1px solid var(--theme-foreground-faint); background: var(--theme-background); color: var(--theme-foreground); }
.botao-link:hover, .limpar:hover { border-color: var(--theme-foreground-muted); }
.explorar .card { margin: 0; }
.painel-deputado h2 { margin: 0 0 0.25rem; font-size: 1.15rem; }
.painel-deputado .sub, .painel-deputado .dica, .painel-deputado .fora, .nota { color: var(--theme-foreground-muted); font-size: 0.85rem; }
.painel-deputado .grupo { display: flex; align-items: baseline; gap: 0.4rem; flex-wrap: wrap; }
.painel-deputado .dist { color: var(--theme-foreground-muted); font-size: 0.8rem; }
.bolinha { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 50%; }
.indices { width: 100%; font-size: 0.85rem; font-variant-numeric: tabular-nums; }
.indices th[scope=row] { font-weight: normal; }
.indices .valor { font-weight: 600; }
.indices .ic, .indices .n { color: var(--theme-foreground-muted); }
.painel-deputado select { width: 100%; margin-top: 0.5rem; }
.explorar + .explorar, .ranking-card { margin-top: 1rem; }
.explorar h2, .ranking-card h2 { margin: 0 0 0.25rem; font-size: 1.05rem; }
.dica { color: var(--theme-foreground-muted); font-size: 0.85rem; }
.ranking { width: 100%; font-size: 0.85rem; font-variant-numeric: tabular-nums; max-width: none; }
.ranking td { vertical-align: middle; }
.ranking td svg { vertical-align: middle; }
.ranking tbody tr { cursor: pointer; }
.ranking tbody tr:hover { background: var(--theme-background-alt); }
.ranking tr.selecionado { background: var(--theme-background-alt); outline: 2px solid #111; }
.ranking .sub, .ranking .ic, .ranking .n { color: var(--theme-foreground-muted); }
.ranking .valor { font-weight: 600; }
</style>
