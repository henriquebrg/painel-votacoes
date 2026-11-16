// Nomes por extenso das siglas que aparecem no painel (sem dependências: testável no Node).

export const PARTIDOS = {
  AVANTE: "Avante",
  CIDADANIA: "Cidadania",
  DC: "Democracia Cristã",
  MDB: "Movimento Democrático Brasileiro",
  "MISSÃO": "Missão",
  NOVO: "Partido Novo",
  PATRIOTA: "Patriota (em 2024 se fundiu ao PTB e formou o PRD)",
  PCDOB: "Partido Comunista do Brasil",
  PDT: "Partido Democrático Trabalhista",
  PL: "Partido Liberal",
  PODE: "Podemos",
  PP: "Progressistas",
  PRD: "Partido Renovação Democrática",
  PROS: "Partido Republicano da Ordem Social (incorporado ao Solidariedade em 2023)",
  PSB: "Partido Socialista Brasileiro",
  PSC: "Partido Social Cristão (incorporado ao Podemos em 2023)",
  PSD: "Partido Social Democrático",
  PSDB: "Partido da Social Democracia Brasileira",
  PSOL: "Partido Socialismo e Liberdade",
  PT: "Partido dos Trabalhadores",
  PV: "Partido Verde",
  REDE: "Rede Sustentabilidade",
  REPUBLICANOS: "Republicanos",
  "S.PART.": "Sem partido",
  SOLIDARIEDADE: "Solidariedade",
  "UNIÃO": "União Brasil"
};

export const UFS = {
  AC: "Acre", AL: "Alagoas", AM: "Amazonas", AP: "Amapá", BA: "Bahia", CE: "Ceará",
  DF: "Distrito Federal", ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MG: "Minas Gerais",
  MS: "Mato Grosso do Sul", MT: "Mato Grosso", PA: "Pará", PB: "Paraíba", PE: "Pernambuco",
  PI: "Piauí", PR: "Paraná", RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RO: "Rondônia",
  RR: "Roraima", RS: "Rio Grande do Sul", SC: "Santa Catarina", SE: "Sergipe", SP: "São Paulo",
  TO: "Tocantins"
};

// Sigla desconhecida volta como veio: melhor mostrar a sigla do que esconder o dado.
export const nomePartido = (sigla) => PARTIDOS[sigla] ?? sigla;
export const nomeUf = (sigla) => UFS[sigla] ?? sigla;

// "PSD-PR" -> "Partido Social Democrático. Estado: Paraná."
export const explicaPartidoUf = (partido, uf) => `${nomePartido(partido)}. Estado: ${nomeUf(uf)}.`;
