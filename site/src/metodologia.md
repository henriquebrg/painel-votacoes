---
title: Metodologia
---

# Metodologia

Esta página explica, em linguagem simples, como cada número do painel é calculado. Os dados vêm dos arquivos abertos da Câmara dos Deputados e cobrem a 57ª legislatura (de 01/02/2023 a 31/01/2027).

```js
const meta = FileAttachment("data/meta.json").json();
const grupos = FileAttachment("data/grupos.json").json();
```

```js
import {pct, faixaPct} from "./components/formato.js";
```

```js
const num = (x) => x.toLocaleString("pt-BR");
const mapa = FileAttachment("data/mapa.json").json();
```

```js
const faixa = (i) => faixaPct(Object.values(mapa.variancia).map((p) => p[i]).filter(Number.isFinite));
// trimestres da legislatura já iniciados na data da atualização
const d = new Date(meta.atualizado_em);
const trimestresPassados = Math.min(meta.janelas.length, (d.getUTCFullYear() - 2023) * 4 + Math.floor(d.getUTCMonth() / 3) + 1);
const votosPorTrimestre = Math.round(meta.n_votacoes_com_orientacao_governo / trimestresPassados);
```

## 1. Quais votações entram

Entram apenas as **votações nominais do Plenário**, aquelas em que o voto de cada deputado fica registrado. Votações simbólicas (sem registro individual) e votações de comissões ficam de fora. Na última atualização, o painel tinha **${num(meta.n_votacoes_plenario)}** votações nominais no Plenário, das quais **${num(meta.n_votacoes_com_orientacao_governo)}** com orientação do governo.

## 2. A regra de alinhamento

Para cada voto, comparamos o que o deputado votou com a orientação dada pela liderança. O índice é o percentual de votos que coincidem com a orientação.

| Situação | O que acontece |
|---|---|
| A orientação foi "Liberado", ficou em branco ou não existe | O voto não entra na conta |
| O deputado votou "Artigo 17" ou em branco | O voto não entra na conta e é contado numa categoria à parte |
| O deputado se absteve | Conta como divergência |
| Qualquer outro caso | Alinhado apenas se o voto for igual à orientação (Sim com Sim, Não com Não, Obstrução com Obstrução) |

Ausências nunca entram. Se o governo orientou "Obstrução", obstruir é seguir a orientação. Se a orientação foi Sim ou Não e o deputado obstruiu ou se absteve, isso conta como divergência. Os votos "Artigo 17" (voto do presidente da sessão) e em branco aparecem contados no detalhe do deputado, mas não mexem no índice.

## 3. O eixo do partido

O índice principal de fidelidade ao partido é **"votou com a maioria dos outros deputados do mesmo partido"**. Em cada votação, olhamos o que os demais colegas de partido votaram e tomamos a categoria mais votada como posição da bancada. Valem estas regras:

- é preciso haver pelo menos 3 colegas de partido com voto registrado na votação;
- se houver empate entre as categorias mais votadas, a votação não entra;
- se a maioria dos colegas se absteve, a abstenção conta como uma posição;
- o deputado está alinhado quando seu voto é igual a essa categoria. O partido considerado é o que ele tinha **na data da votação**.

Por que não usar a orientação do líder? Porque em 2025 o bloco grande e os partidos do centrão (PP, União, PSD, MDB e Republicanos) deixaram a maior parte das votações sem orientação. Na verificação de novembro de 2026, o bloco grande havia orientado apenas 26 de 168 votações de 2025. O índice pela orientação do líder ou do bloco continua disponível como **visão secundária**, mas não é comparável entre os anos. A cobertura dele, isto é, a fatia das votações com orientação válida para o partido, foi:

```js
display(html`<table>
  <thead><tr><th>Ano</th><th>Cobertura da orientação de partido ou bloco</th></tr></thead>
  <tbody>${meta.anos.map((a) => html`<tr><td>${a}</td><td>${pct(meta.cobertura_orientacao_partido[a])}</td></tr>`)}</tbody>
</table>`);
```

Como o índice pela maioria da bancada não depende de a liderança ter orientado, ele é usado nos grupos, no ranking e como eixo padrão dos gráficos.

## 4. A janela móvel de 12 meses

Cada trimestre mostra os índices **acumulados nos últimos 12 meses** (os 4 trimestres que terminam naquele). Um trimestre isolado tem, em média, cerca de ${votosPorTrimestre} votações com orientação do governo (total de ${num(meta.n_votacoes_com_orientacao_governo)} dividido por ${trimestresPassados} trimestres), pouco para um número estável. A janela móvel suaviza o ruído sem esconder as mudanças de rumo. Também é possível ver o trimestre isolado ou a legislatura inteira.

## 5. A margem de erro

Todo índice vem com um **intervalo de Wilson a 95%**. É a faixa em que o valor "verdadeiro" provavelmente está, dado o número de votos contados: quanto menos votos, mais larga a faixa. Para o deputado entrar nos rankings, ele precisa ter **pelo menos 30 votos contados** na janela.

## 6. Os grupos

Os deputados são separados em grupos por uma **mistura gaussiana** (um método estatístico que encontra aglomerados) sobre dois eixos: alinhamento com o governo e alinhamento com a maioria do partido. O ajuste é feito **uma única vez, com a legislatura inteira**. Em cada janela, cada deputado entra no grupo cujo centro está mais próximo, desde que tenha pelo menos 30 votações contadas tanto com o governo quanto com a maioria do partido; com menos, ele aparece como "Sem grupo (poucos votos)", em cinza. Assim os grupos não trocam de nome de um período para outro. Os grupos são nomeados pela posição do centro no eixo do governo, do mais alto ao mais baixo: Base, Independentes e Oposição.

O número padrão é 3. O critério BIC (quanto menor, melhor o ajuste, descontada a complexidade do modelo) para cada número de grupos testado foi:

```js
display(html`<table>
  <thead><tr><th>Número de grupos</th><th>BIC</th></tr></thead>
  <tbody>${Object.entries(grupos.bic).map(([k, v]) => html`<tr><td>${k}${Number(k) === grupos.k ? " (adotado)" : ""}</td><td>${v.toFixed(1)}</td></tr>`)}</tbody>
</table>`);
```

O BIC continua caindo quando se aumenta o número de grupos; adotamos 3 porque é o número com leitura política clara (base, independentes e oposição). Os centros dos grupos ficam, em alinhamento com o governo e com a maioria do partido, respectivamente, em:

```js
display(html`<ul>${grupos.rotulos.map((r, i) => html`<li><strong>${r}</strong>: ${pct(grupos.centros[i][0])} e ${pct(grupos.centros[i][1])}</li>`)}</ul>`);
```

## 7. O mapa de posições

O mapa coloca cada deputado num plano a partir de seus votos, usando uma **análise de componentes principais (PCA)** sobre a matriz de votos. Votações quase unânimes são descartadas, porque não distinguem ninguém. Deputados que votam de modo parecido ficam próximos. A orientação do mapa é fixa (o PT fica à esquerda), para que ele não se inverta de um trimestre para outro.

Nas janelas calculadas, o primeiro eixo explica entre ${faixa(0)} da variação dos votos, e o segundo, entre ${faixa(1)}. O mapa resume bem a posição principal, mas não toda a diferença entre deputados. A posição no mapa descreve semelhança de votos, não ideologia.

## 8. Como funciona o ranking

O ranking de **desgarrados** considera quem tem pelo menos 30 votos contados na janela. A ordem usa o **limite superior do intervalo de Wilson** do alinhamento com a maioria do partido: assim, quem tem poucos votos não sobe só por sorte. Há duas direções, conforme o deputado se afasta da maioria do partido **para o lado do governo** (alinhamento com o governo acima da mediana do partido na janela) ou **para o lado da oposição** (abaixo da mediana). As duas situações têm leituras políticas diferentes, por isso são listadas separadamente. A direção só é indicada para quem tem pelo menos 30 votações com orientação do governo na janela; com menos, a coluna "Governo" do ranking mostra "poucos votos".

## 9. Conferências com fontes externas e com o placar oficial

Os números são conferidos todos os dias, e a publicação é **bloqueada** se algo não bater.

- **Radar do Congresso (Congresso em Foco).** O Radar calcula o governismo com a mesma comparação voto a voto com a orientação do líder do governo, sem contar ausências, mas sobre um universo diferente do deste painel: inclui votações nominais de comissões (sobretudo a CCJC) e desconsidera as votações em que o governo orientou "Obstrução". Este painel usa apenas votações do Plenário e conta a orientação "Obstrução". Como teste diário, o processo reproduz os números do Radar aplicando a regra do Radar aos mesmos dados abertos; isso valida a leitura dos dados e das orientações. Os índices publicados aqui seguem a regra deste painel. Na verificação de novembro de 2026, na reprodução, os números coincidiam exatamente em 99,6% dos deputado-trimestres de 2023 a 2025; com a regra do painel, a diferença anual típica era de até 1 ou 2 pontos percentuais, podendo passar de 10 pontos para deputados que votam muito em comissões.
- **Placar oficial.** Para as votações nominais do Plenário, o total de votos Sim e Não que contamos é comparado ao placar oficial de cada votação, com pequena tolerância.
- **Consistência interna.** Outros testes verificam, por exemplo, que os índices ficam entre 0 e 100% e que os totais de votos fecham.

## 10. Limitações conhecidas

- **Orientações em branco.** Quando a liderança não orienta, não há como medir fidelidade por orientação. Na verificação de novembro de 2026, o bloco grande havia orientado só 26 de 168 votações de 2025. Por isso o eixo principal é a maioria da bancada, que tem seus próprios limites: partidos pequenos têm poucos colegas para comparar.
- **Só votações nominais do Plenário.** Votações simbólicas e de comissões não aparecem. Um deputado muito ativo em comissões pode parecer diferente do que mostra o Radar do Congresso.
- **2023, primeiro trimestre.** Há poucas votações no período (a legislatura começou em fevereiro), então os números dessa janela são pouco estáveis, e as margens de erro são largas.
- **O mapa é uma PCA.** É simples e fácil de explicar, mas um método especializado (W-NOMINATE) está previsto para uma versão futura.
- **Ausência não é voto.** Quem falta não é contado, e isso pode esconder estratégias de ausência.
