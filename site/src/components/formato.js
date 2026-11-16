// Formatação compartilhada pelas páginas (sem dependências: testável no Node).

// Mínimo de votações contadas para grupo, direção e ranking (igual ao pipeline).
export const N_MIN = 30;
export const ROTULO_SEM_GRUPO = "Sem grupo (poucos votos)";

export const pct = (x) => (x == null || !Number.isFinite(x) ? "—" : `${Math.round(x * 100)}%`);

export const faixaPct = (valores) =>
  valores.length ? `${pct(Math.min(...valores))} e ${pct(Math.max(...valores))}` : "—";

export const rotuloGrupo = (r) => r.grupo ?? ROTULO_SEM_GRUPO;

// Coluna "Governo" do ranking: valor e IC 95%, ou aviso quando n_gov < N_MIN.
export const governoRanking = (r) =>
  (r.n_gov ?? 0) >= N_MIN
    ? `${pct(r.alinh_gov)} (${pct(r.ic_gov_inf)} a ${pct(r.ic_gov_sup)})`
    : `poucos votos (${(r.n_gov ?? 0).toLocaleString("pt-BR")})`;

// "2025T3" -> "3º tri 2025"; outros valores (ex.: "legislatura") voltam como vieram.
export const formatarJanela = (j) => (/^\d{4}T\d$/.test(j) ? `${j.slice(5)}º tri ${j.slice(0, 4)}` : j);
