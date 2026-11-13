# Painel de Votações da Câmara (2023–2026) — Design

Data: 2026-11-13 · Status: rascunho para aprovação

## 1. Intenção e porquê

Painel web interativo sobre o comportamento de voto dos deputados federais na 57ª legislatura (de fevereiro de 2023 ao fim de 2026), alimentado direto pelos dados abertos da Câmara.

O projeto tem três funções:
1. **Aprendizado.** É o projeto do autor para aprender a usar o Claude Code.
2. **Ferramenta de trabalho.** Substitui a análise que o autor faz hoje no Power BI, de tempos em tempos e com dados atualizados à mão. A pergunta central é **quem é base forte do governo, quem é independente e quem é oposição forte**, e **quem se afasta da orientação do próprio partido**, porque esses deputados são candidatos a desfiliação.
3. **Portfólio e consultoria.** Fica publicado na web e mostra o método e a capacidade de análise do autor.

Hoje o autor usa um gráfico de dois eixos: alinhamento com o governo × alinhamento com o partido. Ele identifica os grupos no olho e filtra por UF, região e partido. Ele mesmo considera esse método amador e quer uma **base estatística mais sólida**.

## 2. Objetivos

- **G1.** Gráfico de dois eixos (governo × partido) com filtros de UF, região e partido. Os grupos são **calculados por algoritmo**, e cada deputado mostra a que distância está do centro do seu grupo.
- **G2.** **Mapa de posições** baseado em todos os votos, sem depender de orientações, para conferir os grupos do G1.
- **G3.** **Ranking de quem se afasta do partido, com margem de erro**, separando dois tipos: quem se afasta *em direção ao governo* e quem se afasta *em direção à oposição*.
- **G4.** **Evolução no tempo**, por trimestre, ao longo da legislatura: o gráfico de dois eixos pode ser animado, cada deputado deixa um rastro do caminho que fez e a linha do tempo mostra os marcos.
- **G5.** **Narrativa.** O autor escreve a história da relação do governo com a Câmara e depois a do centrão (PP, União, PSD, MDB e Republicanos), partidos que tiveram ministérios e ainda assim mantiveram muitos deputados independentes. Cada capítulo fica ligado a uma **visão salva** do painel, que serve de evidência visual.
- **G6.** **Validação pela janela partidária de 2026.** Conferir se os deputados que o método apontava como desgarrados em 2023 a 2025 de fato trocaram de partido.
- **G7.** Atualização **automática e diária**, com a data da última atualização e a fonte visíveis em todas as telas.

## 3. Não-objetivos (v1)

- Senado e votações em comissões. A v1 usa só votações nominais do Plenário.
- Login, contas de usuário ou edição da narrativa pelo navegador.
- Consultas à API da Câmara em tempo real.
- Previsão eleitoral.
- Publicar o código-fonte.

## 4. Anti-objetivos (seria um fracasso mesmo funcionando)

- **Publicar dado errado ou tela quebrada.** Para um portfólio, isso é pior que não ter o painel.
- **Chamar alguém de "rebelde" com base em poucos votos.** Toda métrica individual precisa mostrar a margem de erro e respeitar um número mínimo de votos.
- **Parecer uma ferramenta genérica** ou uma cópia do Power BI. O acabamento precisa ser de portfólio.
- **Expor o código ou rascunhos** que o autor não publicou.

## 5. Restrições e fatos sobre os dados (verificados em 12/11/2026)

**Fonte principal.** Arquivos anuais em lote, atualizados todo dia:
- `https://dadosabertos.camara.leg.br/arquivos/votacoes/json/votacoes-{ano}.json`, com cerca de 12 MB por ano.
- `.../votacoesVotos/json/votacoesVotos-{ano}.json`, com cerca de 79 MB (2023) e 108 MB (2025).
- `.../votacoesOrientacoes/json/votacoesOrientacoes-{ano}.json`, com cerca de 1,7 MB por ano.

**Limite da API.** O endpoint `/votacoes` da API v2 recusa períodos maiores que 3 meses. Por isso a API é usada só como complemento, por exemplo no histórico de partidos de cada deputado.

**Números de 2025:**
- 2.041 votações no Plenário, das quais 316 têm orientação "Governo" Sim ou Não.
- Cerca de 170 mil votos individuais Sim ou Não no Plenário.

**Votos no arquivo de 2025:** Sim, Não, Obstrução (375), Abstenção (347), "Artigo 17" (420, presidente da sessão) e vazio (421).

**Partido do deputado.** O campo `deputado_.siglaPartido` dos votos parece trazer o partido **na data do voto**: 14 deputados aparecem com mais de um partido no arquivo de 2025. *Ainda falta confirmar isso com o histórico da API.*

**Orientações:**
- `siglaBancada` traz "Governo", "Maioria", "Minoria", "Oposição", partidos, **federações** ("Fdr PT-PCdoB-PV") e **blocos com nomes cortados** ("Bl PlFdrPtUniPp...").
- A grafia varia: "UNIÃO" e "União", "Republican" e "REPUBLICANOS".
- Cerca de 25% das orientações vêm vazias. Também aparecem "Liberado" e "Obstrução".

**Ministérios.** A Câmara não informa quais partidos tiveram ministérios, nem quando. Isso precisa ser curado à mão.

**Custo.** Hospedagem gratuita e manutenção mínima.

**Privacidade.** Código e rascunhos ficam privados. O site publicado é público.

## 6. Abordagens consideradas

| | Abordagem | Vantagens | Desvantagens |
|---|---|---|---|
| **A (escolhida)** | Site estático, com os dados recalculados todo dia (Observable Framework, cálculos em Python, rotina diária no GitHub Actions) | Narrativa com rolagem fácil de fazer, acabamento de portfólio, gratuito, rápido, quase não quebra | Cortes totalmente novos precisam entrar no cálculo diário e não saem na hora |
| B | App em Python (Streamlit/Dash) | Filtros prontos rapidamente | Fraco para narrativa, cara genérica, o app "dorme" na hospedagem gratuita |
| C | Sistema completo (site, servidor e banco) | Login, editor da narrativa e consultas livres | Várias vezes mais trabalho e manutenção; exagero para um projeto pessoal |

O autor escolheu a **A**, seguindo a recomendação.

## 7. O que já está decidido

### 7.1 Infraestrutura
- Repositório **privado** no GitHub.
- Publicação no **Cloudflare Pages** (gratuito e compatível com repositório privado), a partir do GitHub Actions.
- **Rotina diária:**
  1. Baixar os arquivos anuais de 2023 a 2026.
  2. Calcular as métricas.
  3. Gerar dados agregados e compactos para o site.
  4. Gerar e publicar o site.
- Os arquivos brutos **não** são versionados no repositório.
- Site em português (pt-BR). Todas as telas mostram a fonte (Câmara dos Deputados, Dados Abertos) e a data da última atualização.

### 7.2 Telas
1. **Narrativa** (página inicial)
   - Texto em capítulos; o gráfico fica fixo ao lado e muda para a visão salva do capítulo atual.
   - Cada capítulo tem um link "abrir no modo Explorar".
   - Capítulos marcados como rascunho não são publicados.
2. **Explorar**
   - Gráfico de dois eixos com rastro no tempo e barra para escolher o trimestre.
   - Filtros de UF, região, partido e grupo.
   - Mapa de posições e ranking de desgarrados.
   - Botão "salvar esta visão", que gera um identificador ou URL para usar na narrativa.
   - Marcos na linha do tempo: ministérios, janela partidária e eventos curados.
3. **Metodologia**
   - O método explicado em linguagem clara: regras de contagem, índices, margem de erro, como os grupos e o mapa são calculados, e as limitações dos dados.
   - O código não aparece.

### 7.3 Regras de cálculo (proposta aceita pelo autor)
- **Universo:** só votações nominais do Plenário (`siglaOrgao == "PLEN"`).
- **Alinhamento com o governo:** percentual dos votos do deputado que coincidem com a orientação da bancada "Governo".
  - Não entram: ausências, orientações "Liberado" ou vazias, e votações sem orientação do governo.
  - "Obstrução" conta como orientação: se o governo orientou obstrução, obstruir é seguir a orientação.
  - **Abstenção ou obstrução do deputado quando a orientação foi Sim ou Não conta como divergência**, porque ele não seguiu a orientação. Decisão do autor, igual ao que ele faz hoje no Power BI.
  - **"Artigo 17"** (voto do presidente da sessão) e **votos em branco** ficam numa **categoria à parte**. Não entram no índice, mas aparecem contados no detalhe do deputado.
- **Alinhamento com o partido:** o mesmo cálculo, comparando com a orientação que vale para o partido do deputado *na data do voto*.
  - Se o partido orientou diretamente, vale essa orientação.
  - Se não, vale a orientação do bloco ou da federação a que o partido pertencia.
  - Isso exige uma **tabela que liga cada partido ao seu bloco ou federação em cada período**, junto com a normalização dos nomes de bancada.
- **Índice alternativo:** "votou com a maioria da própria bancada". Serve de comparação e de reserva quando não houver orientação válida.
- **Margem de erro:** intervalo de Wilson a 95%, mais um número mínimo de votos para o deputado aparecer nos rankings.
- **Recorte de tempo:** trimestres (até 16 na legislatura).

### 7.4 Narrativa e dados curados
- O **autor escreve** a narrativa.
- Primeiro arco: a relação do governo com a Câmara.
- Arcos seguintes: os partidos do centrão PP, União, PSD, MDB e Republicanos.
- **Linha do tempo de ministérios** desses cinco partidos: o Claude monta a partir de fontes públicas (Diário Oficial e imprensa) e o autor revisa. Fica num arquivo editável no repositório.
- **Marcos/eventos:** arquivo curado, como janela partidária, trocas de liderança e votações decisivas.

### 7.5 Prazo e conferência dos números
- **Prazo:** o painel deve estar no ar para ser mostrado **até 31/12/2026**.
- **Conferência:** os índices são conferidos com **fontes externas**, como o Radar do Congresso e outros painéis públicos de governismo que estejam disponíveis. Quem constrói verifica quais fontes existem e que método cada uma usa. Uma amostra de deputados e períodos vira um teste automático: se os números divergirem além de uma tolerância, sem uma diferença de método que explique, a publicação diária é bloqueada. Também há testes de consistência interna, como totais de votos que batem com o placar oficial de cada votação.

## 8. Decisões do Claude (o autor pode corrigir)

- **Fases, para cumprir o prazo de 31/12:**
  - **Fase 1 (meados de dezembro):** dados, métricas, atualização diária, tela Explorar e Metodologia. Já serve para o trabalho do autor e para ele levantar os insights.
  - **Fase 2 (até 31/12):** tela Narrativa, com visões salvas, linha do tempo de ministérios e marcos. O texto dos capítulos é do autor.
  - **Depois do prazo:** mapa de posições refinado (W-NOMINATE), filtro por tema e a validação da janela publicada como capítulo.

- **Grupos.** Usar mistura gaussiana ou k-médias sobre os dois eixos, escolhendo o número de grupos por critério estatístico (BIC ou silhueta). O padrão é 3. Os grupos recebem nomes como base, independentes e oposição conforme a posição do centro no eixo do governo. O esboço com dados de 2025 encontrou 361, 69 e 94 deputados.
- **Mapa de posições.** Começar com PCA sobre a matriz de votos centrada, descartando votações quase unânimes. É barato e fácil de explicar. A orientação do eixo é fixa (PT à esquerda), para não inverter de um trimestre para outro. W-NOMINATE (em R) pode entrar depois como melhoria.
- **Desgarrados.** Classificados pela direção do desvio (em direção ao governo ou à oposição), já que as duas situações têm leituras políticas diferentes.
- **Filtro por tema da votação.** Desejável, mas fora do núcleo da v1. Depende de buscar os temas das proposições na API.
- **Janelas de tempo.** Cada trimestre mostra os índices **acumulados nos últimos 12 meses** até aquele trimestre (janela móvel de 4 trimestres). Um trimestre isolado tem cerca de 80 votações com orientação do governo, pouco para dar números estáveis. Uma opção mostra também o trimestre isolado.
- **Grupos estáveis no tempo.** Os grupos são calculados **uma vez, com a legislatura inteira**. Em cada janela, cada deputado entra no grupo de centro mais próximo. Assim os nomes dos grupos não mudam, e os rastros e o filtro "grupo" continuam coerentes.
- **Período.** A 57ª legislatura vai de 01/02/2023 a 31/01/2027, e votações de janeiro de 2027 entram se houver. A legislatura e os anos ficam como parâmetro. Ao fim da legislatura, o site é congelado. Continuar na 58ª é decisão futura.
- **Validação da janela de 2026 (G6).** Primeiro é uma análise interna. Conta como troca qualquer mudança de partido de 2023 a 2026, com destaque para a janela de março e abril de 2026. Troca para outro partido da mesma federação aparece marcada à parte. O autor decide se o resultado vira capítulo público. Se virar, os erros do método aparecem também, com honestidade.
- **Detalhe do deputado.** Na v1 é um painel lateral dentro do Explorar, e não páginas próprias.
- **Visões salvas.** Ficam guardadas no endereço da página (URL). Os capítulos da narrativa as referenciam em Markdown.

## 9. Deixado para quem vai construir

- A estrutura exata dos dados agregados e o formato dos arquivos (JSON ou Parquet).
- A biblioteca de gráficos dentro do Observable Framework.
- O identidade visual, dentro do critério de acabamento de portfólio.
- O número mínimo exato de votos para o ranking.
- Como montar e manter a tabela de partidos, blocos e federações, desde que seja auditável e fique explicada na Metodologia.
- Confirmar que `siglaPartido` nos votos é o partido na data do voto. Se não for, usar o histórico de partidos da API.
