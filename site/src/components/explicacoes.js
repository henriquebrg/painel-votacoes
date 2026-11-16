// Textos das explicações (caixas que aparecem sobre os termos sublinhados).
// Ficam todos aqui para serem revisados juntos. Sem dependências: testável no Node.
import {pct, N_MIN} from "./formato.js";

export const EXPLICA = {
  orientacaoGoverno:
    "Antes de cada votação, o líder do governo na Câmara indica como os deputados governistas devem votar: Sim, Não, Obstrução ou Liberado. O alinhamento ao governo é a parcela das votações com essa indicação em que o deputado votou igual a ela.",
  maioriaBancada:
    "Em cada votação, olhamos como votou a maioria dos outros deputados do mesmo partido. O alinhamento à bancada é a parcela das votações em que o deputado votou junto com essa maioria. Não depende de o líder do partido ter orientado, por isso é o eixo padrão.",
  orientacaoPartido:
    "O voto indicado pelo líder do partido ou do bloco de que o partido faz parte. Em 2025 muitos partidos deixaram de orientar, então este eixo conta menos votações e não é comparável entre os anos.",
  ic:
    "Intervalo de confiança de 95%: a faixa em que o valor verdadeiro provavelmente está, dado o número de votações contadas. Com poucos votos a faixa fica larga e o número merece cautela.",
  n: "Número de votações contadas para calcular o índice no período escolhido.",
  artigo17:
    "“Artigo 17” é o registro de quem preside a sessão, que pelo Regimento Interno da Câmara não vota (salvo para desempatar). Esses registros não entram na conta.",
  branco: "Votos registrados em branco. Também não entram na conta.",
  distancia:
    "Distância, no gráfico de dispersão, entre o deputado e o centro do grupo dele (o anel), com os dois eixos medidos de 0 a 1. Quanto menor, mais típico do grupo; valores altos indicam alguém na fronteira com outro grupo.",
  semGrupo:
    `Deputados com menos de ${N_MIN} votações contadas no período, com o governo ou com a bancada. São poucos votos para classificar com segurança, como no caso de suplentes que exerceram o mandato por pouco tempo.`,
  fidelidade:
    "Fidelidade à bancada: parcela das votações em que o deputado votou com a maioria dos colegas de partido. 100% é sempre junto; 50% é metade das vezes.",
  direcao:
    `Para que lado o deputado se afasta. “Rumo ao governo”: ele vota com o governo mais do que a maioria dos colegas de partido (acima da mediana do partido). “Rumo à oposição”: vota com o governo menos do que eles. Só aparece com ao menos ${N_MIN} votações com orientação do governo.`,
  governoRanking:
    "Alinhamento do deputado ao governo no período, com a margem de erro entre parênteses. Ajuda a ver se o afastamento do partido é em direção ao governo ou contra ele.",
  ordemRanking:
    "A lista é ordenada pelo limite de cima da margem de erro, e não pelo valor medido: assim só aparece no topo quem se afasta do partido com segurança, e não quem teve poucos votos.",
  periodo:
    "Últimos 12 meses: os índices somam as votações dos 4 trimestres que terminam no trimestre escolhido; é o padrão, porque um trimestre sozinho tem poucas votações. Só o trimestre: só as votações daquele trimestre. Legislatura inteira: tudo desde fevereiro de 2023.",
  trimestre: "Escolha o trimestre final. O botão ▶ percorre a legislatura trimestre a trimestre.",
  semOrientacao:
    "Orientar é o líder do partido (ou do bloco) indicar à bancada como votar. Contamos as votações em que o governo orientou e o partido não: ficou em branco, liberou a bancada ou não se manifestou.",
  mapa:
    "O mapa é feito por análise de componentes principais (PCA), uma técnica que resume milhares de votos em poucas medidas. Votações quase unânimes são descartadas, porque não distinguem ninguém.",
  grupoMetodo:
    "Os grupos são calculados por um método estatístico a partir dos votos, e não pela filiação: deputados do mesmo partido podem cair em grupos diferentes."
};

const DESCRICAO_GRUPO = {
  Base: "Votam com o governo na maior parte das vezes.",
  Independentes: "Ora votam com o governo, ora contra.",
  "Oposição": "Votam contra a orientação do governo na maior parte das vezes."
};

/** Explicação de um grupo, com a posição do centro dele (grupos.json). */
export function explicaGrupo(rotulo, grupos) {
  const i = grupos?.rotulos?.indexOf(rotulo) ?? -1;
  const centro = i >= 0 ? grupos.centros[i] : null;
  const posicao = centro
    ? ` O deputado típico do grupo segue o governo em ${pct(centro[0])} das votações e a própria bancada em ${pct(centro[1])}.`
    : "";
  return `${DESCRICAO_GRUPO[rotulo] ?? ""}${posicao} ${EXPLICA.grupoMetodo}`.trim();
}

/** Explicação de uma dimensão do mapa de posições, com a parcela da variação que ela resume. */
export function explicaDimensao(i, variancia) {
  const parte = variancia?.[i] != null ? ` Resume ${pct(variancia[i])} das diferenças entre os votos.` : "";
  return i === 0
    ? `O padrão mais forte de divergência nos votos: separa governo (à esquerda) e oposição (à direita).${parte}`
    : `O segundo padrão mais forte, independente do primeiro. Não tem uma leitura política fixa.${parte}`;
}
