// Termos com explicação: siglas e conceitos sublinhados que mostram uma caixa ao passar o mouse,
// ao receber foco pelo teclado ou ao serem tocados (celular). Uma só caixa serve a página toda.
import {html} from "npm:htl";
import {explicaPartidoUf, nomePartido} from "./siglas.js";

/** Texto sublinhado que explica a si mesmo. `explicacao` é texto simples. */
export function termo(texto, explicacao) {
  if (!explicacao) return texto;
  // O clique só serve para ler: não seleciona a linha ou o ponto em que o termo está.
  return html`<span class="termo" tabindex="0" data-explica=${explicacao} onclick=${(ev) => ev.stopPropagation()}>${texto}</span>`;
}

/** "PSD-PR" com o nome do partido e do estado por extenso. */
export const partidoUf = (partido, uf) => termo(`${partido}-${uf}`, explicaPartidoUf(partido, uf));

/** Sigla de partido com o nome por extenso. */
export const sigla = (partido) => termo(partido, nomePartido(partido) === partido ? null : nomePartido(partido));

/**
 * Legenda em HTML (a do Plot não aceita explicações): uma amostra de cor e um termo por item.
 * `itens`: [{rotulo, cor, explicacao}]
 */
export function legenda(itens, {rotulo = "Legenda"} = {}) {
  return html`<ul class="legenda" aria-label=${rotulo}>${itens.map(({rotulo, cor, explicacao}) => html`<li>
    <span class="amostra" style=${`background:${cor}`}></span>${termo(rotulo, explicacao)}
  </li>`)}</ul>`;
}

/**
 * Liga a caixa de explicação na página. Devolve a função que a desliga.
 * Mouse: aparece ao entrar e some ao sair. Teclado: aparece com o foco, some com Esc ou ao sair.
 * Toque: o toque dá foco ao termo; tocar fora tira o foco.
 */
export function iniciarTermos(raiz = document) {
  const caixa = document.createElement("div");
  caixa.className = "explica";
  caixa.id = "explica-termo";
  caixa.setAttribute("role", "tooltip");
  caixa.hidden = true;
  document.body.append(caixa);
  let atual = null;

  const mostrar = (el) => {
    atual?.removeAttribute("aria-describedby");
    atual = el;
    caixa.textContent = el.dataset.explica;
    caixa.hidden = false;
    el.setAttribute("aria-describedby", caixa.id);
    // Abaixo do termo, sem sair da tela; se não couber embaixo, vai para cima.
    const r = el.getBoundingClientRect();
    const larg = caixa.offsetWidth;
    const alt = caixa.offsetHeight;
    const margem = 8;
    const x = Math.min(Math.max(margem, r.left), window.innerWidth - larg - margem);
    const abaixo = r.bottom + 6;
    const y = abaixo + alt + margem > window.innerHeight ? Math.max(margem, r.top - alt - 6) : abaixo;
    caixa.style.left = `${x}px`;
    caixa.style.top = `${y}px`;
  };
  const esconder = () => {
    atual?.removeAttribute("aria-describedby");
    atual = null;
    caixa.hidden = true;
  };
  const alvo = (ev) => ev.target instanceof Element ? ev.target.closest(".termo[data-explica]") : null;

  const aoEntrar = (ev) => { const el = alvo(ev); if (el) mostrar(el); };
  const aoSair = (ev) => {
    const el = alvo(ev);
    if (el && el === atual && !el.contains(ev.relatedTarget) && document.activeElement !== el) esconder();
  };
  const aoFocar = (ev) => { const el = alvo(ev); if (el) mostrar(el); };
  const aoDesfocar = (ev) => { if (alvo(ev) === atual) esconder(); };
  const aoTeclar = (ev) => { if (ev.key === "Escape" && atual) esconder(); };
  const aoRolar = () => atual && (document.activeElement === atual ? mostrar(atual) : esconder());

  raiz.addEventListener("pointerover", aoEntrar);
  raiz.addEventListener("pointerout", aoSair);
  raiz.addEventListener("focusin", aoFocar);
  raiz.addEventListener("focusout", aoDesfocar);
  document.addEventListener("keydown", aoTeclar);
  window.addEventListener("scroll", aoRolar, {passive: true});
  window.addEventListener("resize", esconder);

  return () => {
    raiz.removeEventListener("pointerover", aoEntrar);
    raiz.removeEventListener("pointerout", aoSair);
    raiz.removeEventListener("focusin", aoFocar);
    raiz.removeEventListener("focusout", aoDesfocar);
    document.removeEventListener("keydown", aoTeclar);
    window.removeEventListener("scroll", aoRolar);
    window.removeEventListener("resize", esconder);
    caixa.remove();
  };
}
