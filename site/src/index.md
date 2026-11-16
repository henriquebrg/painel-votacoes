---
title: Explorar
toc: false
---

# Como votam os deputados

<p class="lead">Cada traço é um deputado, do que menos vota com o governo ao que mais vota. A cor é o grupo em que os votos dele o colocam. Use os filtros para recortar por estado, partido ou grupo, e o trimestre para voltar no tempo.</p>

```js
import {carregarFonte} from "./components/fonte.js";
carregarFonte();
```

```js
import {lerEstado, escreverEstado, filtrar, rastro, DIRECOES} from "./components/estado.js";
import {dispersao, mapaPosicoes, rankingDesgarrados, semOrientacao, regua, contagemGrupos, CORES_GRUPO, COR_SEM_GRUPO, ROTULO_EIXO_PARTIDO, pct} from "./components/graficos.js";
import {rotuloGrupo} from "./components/formato.js";
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
const ROTULO_MODO = {movel: "Últimos 12 meses", trimestre: "Só o trimestre", legislatura: "Legislatura inteira"};
const REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"];
const formatarJanela = (j) => (/^\d{4}T\d$/.test(j) ? `${j.slice(5)}º tri ${j.slice(0, 4)}` : j);
const decimal = (x) => (x == null ? "—" : x.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2}));
const ordenar = (xs) => [...xs].sort((a, b) => a.localeCompare(b, "pt-BR"));
const opcoes = (rows, campo) => ordenar(new Set(rows.map((r) => r[campo]).filter(Boolean)));

// Filtro de múltipla escolha compacto: um botão que abre uma lista de caixas de marcar.
// O valor é a lista marcada (vazia = sem filtro), como no Inputs.select múltiplo que substitui.
function filtroMultiplo(rotulo, opts, valorInicial) {
  const marcados = new Set(valorInicial.filter((v) => opts.includes(v)));
  const resumo = html`<span class="filtro-resumo"></span>`;
  const caixas = opts.map((o) => {
    const cb = html`<input type="checkbox" value=${o}>`;
    cb.checked = marcados.has(o);
    return html`<label>${cb}<span>${o}</span></label>`;
  });
  const limpar = html`<button type="button" class="filtro-limpar">Limpar</button>`;
  const el = html`<details class="filtro">
    <summary><span class="filtro-rotulo">${rotulo}</span>${resumo}</summary>
    <div class="filtro-painel" role="group" aria-label=${rotulo}>${limpar}<div class="filtro-lista">${caixas}</div></div>
  </details>`;
  const atualizar = () => {
    el.value = opts.filter((o) => marcados.has(o));
    const k = el.value.length;
    resumo.textContent = k === 0 ? "todos" : k <= 2 ? el.value.join(", ") : `${k} marcados`;
    el.classList.toggle("ativo", k > 0);
    limpar.disabled = k === 0;
  };
  // Registrado antes do Generators.input: o valor já está certo quando ele lê o evento.
  el.addEventListener("input", (ev) => {
    if (ev.target.type !== "checkbox") return;
    ev.target.checked ? marcados.add(ev.target.value) : marcados.delete(ev.target.value);
    atualizar();
  });
  limpar.onclick = () => {
    marcados.clear();
    for (const l of caixas) l.querySelector("input").checked = false;
    atualizar();
    el.dispatchEvent(new Event("input", {bubbles: true}));
  };
  el.addEventListener("keydown", (ev) => ev.key === "Escape" && el.open && ((el.open = false), el.querySelector("summary").focus()));
  atualizar();
  return el;
}

function seletorJanela(janelas, valorInicial) {
  let i = janelas.includes(valorInicial) ? janelas.indexOf(valorInicial) : janelas.length - 1;
  let relogio = null;
  const faixa = html`<input type="range" min="0" max=${janelas.length - 1} step="1" aria-label="Trimestre">`;
  const rotulo = html`<output></output>`;
  const botao = html`<button type="button" class="tocar" aria-label="Percorrer os trimestres">▶</button>`;
  const el = html`<div class="seletor-janela">${botao}${faixa}${rotulo}</div>`;
  const mostrar = () => { faixa.value = i; rotulo.textContent = formatarJanela(janelas[i]); el.value = janelas[i]; };
  const definir = (k) => { i = k; mostrar(); el.dispatchEvent(new Event("input", {bubbles: true})); };
  el.parar = () => { clearInterval(relogio); relogio = null; botao.textContent = "▶"; botao.setAttribute("aria-label", "Percorrer os trimestres"); };
  botao.onclick = () => {
    if (relogio) return el.parar();
    if (i === janelas.length - 1) definir(0);
    botao.textContent = "❚❚";
    botao.setAttribute("aria-label", "Pausar");
    relogio = setInterval(() => (i < janelas.length - 1 ? definir(i + 1) : el.parar()), 1500);
  };
  faixa.oninput = (ev) => { ev.stopPropagation(); el.parar(); definir(+faixa.value); };
  mostrar();
  return el;
}
```

```js
// Fecha o filtro aberto ao clicar fora dele.
const fecharFiltros = (ev) => {
  for (const d of document.querySelectorAll("details.filtro[open]")) if (!d.contains(ev.target)) d.open = false;
};
document.addEventListener("click", fecharFiltros);
invalidation.then(() => document.removeEventListener("click", fecharFiltros));
```

```js
const modoInput = Inputs.select(Object.keys(ROTULO_MODO), {label: "Período", value: inicial.modo, format: (m) => ROTULO_MODO[m]});
const modo = Generators.input(modoInput);
const seletor = seletorJanela(meta.janelas, inicial.janela);
const janela = Generators.input(seletor);
invalidation.then(() => seletor.parar());
const regioesInput = filtroMultiplo("Região", REGIOES, inicial.regioes);
const regioes = Generators.input(regioesInput);
const gruposInput = filtroMultiplo("Grupo", grupos.rotulos, inicial.grupos);
const gruposSel = Generators.input(gruposInput);
const eixoInput = Inputs.select(Object.keys(ROTULO_EIXO_PARTIDO), {
  label: "Eixo vertical", value: inicial.eixoPartido,
  format: (e) => (e === "maioria" ? "Maioria da bancada" : "Orientação do partido")
});
const eixoPartido = Generators.input(eixoInput);
```

```js
const deputado = Mutable(inicial.deputado);
// A régua se abre uma vez, na chegada; depois só muda de lugar.
const reguaAnimada = {feito: false};
const selecionar = (id) => (deputado.value = id == null ? null : String(id));
```

```js
const indices = ARQUIVOS_INDICES[modo].json();
```

```js
const ufsInput = filtroMultiplo("UF", opcoes(indices, "uf"), naUrl().ufs);
const ufs = Generators.input(ufsInput);
const partidosInput = filtroMultiplo("Partido", opcoes(indices, "partido"), naUrl().partidos);
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
const copiar = html`<button type="button" class="botao">Copiar link desta visão</button>`;
copiar.onclick = async () => {
  try {
    await navigator.clipboard.writeText(location.href);
    copiar.textContent = "Link copiado";
  } catch {
    copiar.textContent = "Não foi possível copiar. Use a barra de endereço";
  }
  setTimeout(() => (copiar.textContent = "Copiar link desta visão"), 2500);
};
```

<section class="placar" aria-label="Deputados por grupo">
  <p class="placar-titulo"><strong>${visiveis.length.toLocaleString("pt-BR")}</strong> deputados, ${legislatura ? "na legislatura inteira" : modo === "movel" ? `nos 12 meses até o ${formatarJanela(janela)}` : `no ${formatarJanela(janela)}`}</p>
  ${resize((width) => {
    const g = regua(visiveis, {destaque: deputado, width, animar: !reguaAnimada.feito});
    reguaAnimada.feito = true;
    g.addEventListener("click", () => g.value && selecionar(g.value.deputado_id));
    return g;
  })}
  <div class="regua-pontas" aria-hidden="true"><span>← vota menos com o governo</span><span>vota mais com o governo →</span></div>
  ${contagemGrupos(visiveis)}
</section>

<div class="barra-filtros">
  <div class="filtros-tempo">${modoInput}${seletor}</div>
  <div class="filtros-recorte">${ufsInput}${regioesInput}${partidosInput}${gruposInput}</div>
  ${copiar}
</div>

<section class="secao">
  <h2>Com o governo e com a própria bancada</h2>
  <p class="dica">Cada ponto é um deputado. Para a direita, vota mais com a orientação do governo; para cima, mais com a sua bancada. Os anéis marcam o centro de cada grupo. Clique num ponto para ver o deputado e o caminho dele no tempo.</p>
  <div class="grid grid-cols-3 explorar">
    <div class="grid-colspan-2">
      ${eixoInput}
      ${resize((width) => {
        const g = dispersao(visiveis, {grupos, rastro: trilha, eixoPartido, destaque: deputado, width});
        g.addEventListener("click", () => g.value && selecionar(g.value.deputado_id));
        return g;
      })}
      ${eixoPartido === "orientacao" ? html`<p class="nota">A orientação partidária nem sempre é dada. Cobertura por ano: ${Object.entries(meta.cobertura_orientacao_partido).map(([ano, c]) => `${ano} ${pct(c)}`).join(", ")}. Por isso o eixo padrão é a maioria da bancada.</p>` : ""}
    </div>
    <aside class="painel-deputado" aria-live="polite">${painelDeputado()}</aside>
  </div>
</section>

```js
// Célula própria: o filtro de direção não volta a "todas" quando a janela muda.
const direcaoInput = Inputs.radio(DIRECOES, {label: "Direção", value: "todas"});
const direcao = Generators.input(direcaoInput);
```

<section class="secao ranking-secao">
  <h2>Desgarrados: quem mais se afasta da própria bancada</h2>
  <p class="dica">Fidelidade é a parcela das votações em que o deputado votou com a maioria dos colegas de partido. A faixa cinza é o intervalo de 95%. Só entram deputados com ao menos 30 votações contadas. Clique numa linha para destacar o deputado.</p>
  ${direcaoInput}
  <div class="tabela-rolavel">${rankingDesgarrados(visiveis, {limite: 20, direcao, destaque: deputado, aoSelecionar: selecionar})}</div>
</section>

```js
// O mapa só existe para janelas móveis: no trimestre usa a janela móvel que termina nele;
// na legislatura, a última janela móvel com mapa.
const janelasMapa = [...new Set(mapa.posicoes.map((p) => p.janela))].sort();
const janelaMapa = legislatura ? janelasMapa.at(-1) : janela;
const posicoesMapa = mapa.posicoes.filter((p) => p.janela === janelaMapa);
const notaMapa = janelaMapa == null
  ? "Ainda não há mapa de posições."
  : posicoesMapa.length === 0
  ? `Sem mapa de posições para ${formatarJanela(janelaMapa)}.`
  : modo === "trimestre"
    ? `O mapa usa os 12 meses até o ${formatarJanela(janelaMapa)}; um trimestre sozinho tem poucas votações.`
    : legislatura
      ? `O mapa usa os últimos 12 meses (até o ${formatarJanela(janelaMapa)}).`
      : null;
// Sem orientação: a série do modo atual; na legislatura, a série móvel.
const modoSemOrientacao = legislatura ? "movel" : modo;
const serieSemOrientacao = semOrientacaoRows.filter((r) => r.modo === modoSemOrientacao);
```

<div class="grid grid-cols-2 explorar secao">
  <section>
    <h2>Mapa de posições</h2>
    <p class="dica">Usa todos os votos, sem olhar orientações: deputados que votam de forma parecida ficam perto. A cor é o partido.</p>
    ${posicoesMapa.length ? resize((width) => {
      const g = mapaPosicoes(posicoesMapa, visiveis, {destaque: deputado, variancia: mapa.variancia[janelaMapa], width});
      g.addEventListener("click", () => g.value && selecionar(g.value.deputado_id));
      return g;
    }) : ""}
    ${notaMapa ? html`<p class="nota">${notaMapa}</p>` : ""}
  </section>
  <section>
    <h2>Quando os partidos deixam de orientar</h2>
    <p class="dica">Parcela das votações em que o partido não deu orientação à bancada. Quanto mais alta, menos dá para medir fidelidade pela orientação.</p>
    ${resize((width) => semOrientacao(serieSemOrientacao, {janela: legislatura ? null : janela, width}))}
    ${legislatura ? html`<p class="nota">Na legislatura inteira, a série mostra janelas de 12 meses.</p>` : ""}
  </section>
</div>

```js
function linhaIndice(rotulo, valor, inf, sup, n) {
  return html`<tr><th scope="row">${rotulo}</th><td class="valor">${pct(valor)}</td>
    <td class="ic">${valor == null ? "—" : `${pct(inf)} a ${pct(sup)}`}</td><td class="n">${(n ?? 0).toLocaleString("pt-BR")}</td></tr>`;
}

function escolherNaLista() {
  const lista = [...visiveis].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  const sel = html`<select aria-label="Escolher deputado"><option value="">Escolher um deputado na lista</option>${lista.map(
    (r) => html`<option value=${r.deputado_id}>${r.nome} (${r.partido}-${r.uf})</option>`
  )}</select>`;
  sel.onchange = () => selecionar(sel.value || null);
  return sel;
}

function painelDeputado() {
  if (!deputado) {
    return html`<p class="painel-vazio">Clique num ponto do gráfico, num traço da régua ou numa linha do ranking para ver os índices do deputado.</p>
      ${escolherNaLista()}`;
  }
  const limpar = html`<button type="button" class="botao">Limpar seleção</button>`;
  limpar.onclick = () => selecionar(null);
  const r = linhaDep;
  if (!r) {
    const nome = doDeputado[0]?.nome ?? `Deputado ${deputado}`;
    return html`<h3 class="nome">${nome}</h3><p class="dica">Sem votações contadas neste período.</p>${limpar}`;
  }
  const cor = CORES_GRUPO[r.grupo] ?? COR_SEM_GRUPO;
  return html`<h3 class="nome">${r.nome}</h3>
    <p class="sub">${r.partido}-${r.uf}, ${r.regiao}</p>
    <p class="grupo"><span class="amostra" style="background:${cor}"></span><strong>${rotuloGrupo(r)}</strong>
      ${r.grupo ? html`<span class="dist">distância ao centro do grupo: ${decimal(r.dist_centro)}</span>` : ""}</p>
    <table class="indices">
      <thead><tr><th><span class="sr">Alinhamento a</span></th><th>Índice</th><th>IC 95%</th><th>n</th></tr></thead>
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
.lead { max-width: 62ch; color: var(--theme-foreground-muted); font-size: var(--t-3); line-height: 1.4; margin: 0 0 2rem; }
.dica, .nota { color: var(--theme-foreground-muted); font-size: var(--t-1); max-width: 72ch; }
.nota { font-size: var(--t-0); }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

/* Placar: a régua é a peça principal da página. */
.placar { margin: 0 0 1.5rem; }
.placar-titulo { margin: 0 0 0.5rem; font-size: var(--t-1); color: var(--theme-foreground-muted); }
.placar-titulo strong { color: var(--theme-foreground); font-size: var(--t-2); }
.placar svg.regua { display: block; cursor: pointer; overflow: visible; }
.placar svg.regua.animar { animation: abrir-regua 700ms cubic-bezier(.2,.7,.2,1) both; }
@keyframes abrir-regua { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
.regua-pontas { display: flex; justify-content: space-between; font-size: var(--t-0); color: var(--theme-foreground-muted); margin-top: 0.3rem; }
.contagem { list-style: none; padding: 0; margin: 0.75rem 0 0; max-width: none; display: flex; flex-wrap: wrap; gap: 0.25rem 1.75rem; }
.contagem li { display: flex; align-items: center; gap: 0.4rem; font-size: var(--t-1); max-width: none; }
.contagem strong { font-size: var(--t-3); font-stretch: 80%; font-weight: 700; }
.amostra { display: inline-block; width: 0.75rem; height: 0.75rem; border-radius: 2px; flex: none; }

/* Filtros: uma faixa só, presa ao topo ao rolar. */
.barra-filtros {
  position: sticky; top: calc(var(--observablehq-header-height) + 1.5rem); z-index: 1;
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 1.5rem;
  padding: 0.6rem 0; margin: 0 0 2.5rem;
  background: var(--theme-background); border-bottom: 1px solid var(--linha);
}
.filtros-tempo, .filtros-recorte { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.75rem; }
.barra-filtros .botao { margin-left: auto; }
.barra-filtros form { width: auto; margin: 0; }
.barra-filtros form label { width: auto; margin-right: 0.4rem; }
.barra-filtros select { width: auto; }
.seletor-janela { display: flex; align-items: center; gap: 0.5rem; font-size: var(--t-1); }
.seletor-janela input[type=range] { width: 11rem; }
.seletor-janela output { min-width: 6.5rem; font-weight: 600; }
.seletor-janela.inativo { opacity: 0.4; }
.tocar { width: 2rem; height: 1.75rem; border: 1px solid var(--linha); border-radius: 4px; background: var(--theme-background-a); cursor: pointer; color: var(--theme-foreground); }

.filtro { position: relative; font-size: var(--t-1); }
.filtro summary {
  list-style: none; cursor: pointer; display: flex; gap: 0.35rem; align-items: baseline;
  padding: 0.3rem 0.65rem; border: 1px solid var(--linha); border-radius: 4px; background: #fff;
}
.filtro summary::-webkit-details-marker { display: none; }
.filtro summary::after { content: "▾"; color: var(--theme-foreground-muted); font-size: 0.8em; }
.filtro-rotulo { font-weight: 600; }
.filtro-resumo { color: var(--theme-foreground-muted); max-width: 12rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.filtro.ativo summary { border-color: var(--verde); box-shadow: inset 0 0 0 1px var(--verde); }
.filtro.ativo .filtro-resumo { color: var(--verde); }
.filtro-painel {
  position: absolute; top: calc(100% + 4px); left: 0; z-index: 3; min-width: 17rem; max-width: calc(100vw - 2rem);
  background: #fff; border: 1px solid var(--linha); border-radius: 6px; padding: 0.5rem;
  box-shadow: 0 6px 20px rgb(28 35 33 / 0.12);
}
.filtro-lista { max-height: 16rem; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(7.5rem, 1fr)); gap: 0.1rem 0.5rem; }
.filtro-lista label { display: flex; gap: 0.35rem; align-items: center; padding: 0.15rem 0.1rem; cursor: pointer; white-space: nowrap; }
.filtro-limpar { display: block; margin: 0 0 0.35rem auto; font: inherit; font-size: var(--t-0); color: var(--verde); background: none; border: 0; cursor: pointer; padding: 0.1rem 0.2rem; }
.filtro-limpar:disabled { color: var(--theme-foreground-faint); cursor: default; }

.botao { font: inherit; font-size: var(--t-1); font-weight: 600; padding: 0.35rem 0.85rem; border-radius: 4px; cursor: pointer;
  border: 1px solid var(--verde); background: transparent; color: var(--verde); }
.botao:hover { background: var(--verde); color: #fff; }

/* Seções sem moldura: o espaço separa. */
.secao { margin: 0 0 3.5rem; }
.secao h2 { margin: 0 0 0.25rem; }
.secao .dica { margin: 0 0 1rem; }
.explorar section > h2 + .dica { min-height: 3em; }
.explorar form { margin-bottom: 0.25rem; }

.painel-deputado { border-left: 3px solid var(--linha); padding-left: 1.25rem; font-size: var(--t-1); align-self: start; }
.painel-vazio { color: var(--theme-foreground-muted); margin-top: 0; }
.painel-deputado .nome { font-size: var(--t-4); font-weight: 800; font-stretch: 75%; line-height: 1.05; margin: 0 0 0.2rem; }
.painel-deputado .sub, .painel-deputado .fora { color: var(--theme-foreground-muted); }
.painel-deputado .sub { margin: 0; }
.painel-deputado .grupo { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.painel-deputado .dist { color: var(--theme-foreground-muted); font-size: var(--t-0); }
.painel-deputado select { width: 100%; max-width: none; margin: 0.5rem 0; font-size: var(--t-1); }
.indices { width: 100%; max-width: none; }
.indices th[scope=row] { font-weight: 400; }
.indices .valor { font-weight: 700; }
.indices .ic, .indices .n { color: var(--theme-foreground-muted); }

.tabela-rolavel { overflow-x: auto; }
.ranking { width: 100%; min-width: 46rem; max-width: none; font-size: var(--t-1); }
.ranking td { vertical-align: middle; }
.ranking td svg { vertical-align: middle; }
.ranking tbody tr { cursor: pointer; }
.ranking tbody tr:hover { background: #fff; }
.ranking tr.selecionado { background: #fff; box-shadow: inset 3px 0 0 var(--verde); }
.ranking .nome-dep { font-weight: 700; font-stretch: 82%; font-size: var(--t-2); }
.ranking .sub, .ranking .ic, .ranking .n { color: var(--theme-foreground-muted); }
.ranking .valor { font-weight: 700; }
.ranking .governo { white-space: nowrap; }
.ranking .governo.poucos { color: var(--theme-foreground-muted); font-style: italic; }

@media (max-width: 640px) {
  .barra-filtros { position: static; }
  .barra-filtros .botao { margin-left: 0; }
  .painel-deputado { border-left: 0; border-top: 3px solid var(--linha); padding: 1rem 0 0; }
}
</style>
