# Painel de votações

Painel público do alinhamento dos deputados federais às orientações do governo nas votações nominais do Plenário da Câmara (2023–2027). Um pipeline em Python (`painel/`) baixa os dados abertos da Câmara, valida e calcula os índices; um site estático em Observable Framework (`site/`) mostra o resultado. Uma rotina diária no GitHub Actions atualiza tudo e publica no Cloudflare Pages.

## Rodar localmente

Requisitos: [uv](https://docs.astral.sh/uv/) e Node 20.

```sh
uv sync
uv run pytest                      # testes do pipeline
uv run python -m painel.cli        # baixa 2023–2027 em data/raw/ e grava site/src/data/
cd site
npm ci
npm test
npm run dev                        # site local com recarga automática
npm run build                      # gera site/dist/ (precisa de site/src/data/meta.json: rode o pipeline antes)
```

O pipeline sai com código 1 se qualquer validação falhar, e nesse caso não escreve nada em `site/src/data/`.

## Curadoria manual

### `data/curado/blocos.csv`

Bancadas (blocos e federações) por partido e período. Colunas:

- `bancada_prefixo`: nome da bancada, como aparece nas orientações (ex.: `FDR PT-PCDOB-PV`);
- `partido`: sigla do partido que integra a bancada;
- `inicio`, `fim`: período de vigência (`AAAA-MM-DD`); `fim` vazio significa em vigor;
- `observacao`: **a evidência** da linha (fonte, endpoint da API, motivo). Toda linha nova precisa dela.

`bancada_prefixo`, `partido`, `inicio` e `observacao` são obrigatórios: uma linha com qualquer um deles vazio faz o pipeline parar com erro indicando a linha.

### `data/referencia/externa.csv`

Números de fontes externas usados para conferir os nossos cálculos. Colunas:

- `fonte`, `url`: de onde veio o número (a `url` pode trazer notas após ` | `);
- `metodo`: como comparar (veja abaixo);
- `deputado_id`, `nome`: deputado (id da API da Câmara);
- `inicio`, `fim`: período coberto pelo número;
- `alinhamento_governo`: fração entre 0 e 1 (ex.: `0.9698`).

Valores de `metodo`:

- `igual`: a fonte usa a mesma regra do painel (só Plenário); o valor é comparado ao nosso e a diferença deve ser de até 5 pontos percentuais;
- `regra_radar`: a fonte usa a regra do Radar do Congresso (inclui votos em comissões); recalculamos pela regra do Radar e comparamos, também com tolerância de 5 pp;
- `diferente`: a metodologia da fonte não é comparável; a linha fica registrada, mas não é conferida.

Qualquer outro valor de `metodo` é erro de validação.

## Quando a rotina diária falha

1. Abra a aba **Actions** do repositório e entre na execução `atualizar` que falhou.
2. Veja qual passo ficou vermelho:
   - `Testes Python` ou `Testes e build do site`: um teste quebrou; a mensagem diz qual.
   - `Baixar dados, validar e gerar...`: o download falhou ou uma validação reprovou os dados. A mensagem descreve o caso, que é um destes:
     - download: erro de rede ou HTTP, JSON inválido ou `dados` vazio em um arquivo de 2023–2026 (só 2027 pode faltar);
     - `blocos.csv`: linha com `bancada_prefixo`, `partido`, `inicio` ou `observacao` vazio;
     - placar: mais de 2% das votações nominais do Plenário com contagem Sim/Não diferente do placar oficial;
     - sanidade: janela (a partir de 2023T2) com menos de 400 ou mais de 620 deputados, índice fora de 0–100%, mediana de alinhamento ao governo do PT abaixo de 85% ou do PL acima de 50%;
     - referência externa: diferença acima de 5 pp, nenhum voto com orientação do governo no período, ou `metodo` desconhecido.

     Corrija o CSV de `data/curado/` ou `data/referencia/` se o erro for nosso, ou investigue a API da Câmara se o dado mudou.
   - `Publicar no Cloudflare Pages`: normalmente token expirado ou secret errado.
3. Depois de corrigir, faça commit/push e rode de novo em Actions, **Run workflow**, ou `gh workflow run atualizar`.

Como o deploy é o último passo, **uma falha em qualquer etapa mantém no ar a versão anterior do site**.

## Configuração inicial (uma vez)

1. Juntar o trabalho na branch `main` e deixá-la ativa antes de criar o repositório (o `--push` envia a branch atual, e a rotina só publica a partir da `main`):
   ```sh
   git checkout main
   git merge fase1            # se o trabalho estiver em outra branch
   gh repo create painel-votacoes --private --source . --push
   ```
2. Criar o projeto do Pages `painel-votacoes` (upload direto, sem Git) com `main` como branch de produção:
   ```sh
   npx wrangler pages project create painel-votacoes --production-branch=main
   ```
   O deploy da rotina usa `--branch=main`; se a branch de produção do projeto for outra, o site sai só como prévia.
3. Criar um token de API no Cloudflare com a permissão **Cloudflare Pages: Edit** e anotar também o Account ID.
4. Salvar os secrets (o comando pede o valor):
   ```sh
   gh secret set CLOUDFLARE_API_TOKEN
   gh secret set CLOUDFLARE_ACCOUNT_ID
   ```
5. Rodar a primeira vez: `gh workflow run atualizar && gh run watch`. Depois, a rotina roda todo dia às 07:00 (Brasília).
