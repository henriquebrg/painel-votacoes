# Painel de Votações — Fase 1 (dados, métricas, Explorar, Metodologia) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a site that updates itself every day. It shows each federal deputy's alignment with the government and with their party in Plenário roll-call votes from 2023 to 2026. It has computed groups, a position map, a ranking of deputies who stray from their party, and a Metodologia page.

**Architecture:**
- **Python pipeline** (`painel/`). It downloads the Câmara's annual bulk files, normalizes them, computes indices per time window, the groups (GMM), the position map (PCA) and the ranking of deputies who stray from their party.
- **Validation.** The pipeline validates the data against the official tallies and an external source, and blocks publishing if they diverge.
- **Output.** The pipeline writes compact JSON into `site/src/data/`.
- **Site.** An Observable Framework site (`site/`) reads that JSON and renders it.
- **Daily job.** A GitHub Actions run once a day runs the pipeline, builds the site and publishes it to Cloudflare Pages.

**Tech Stack:**
- Python 3.12 with uv, pandas, numpy, scikit-learn, requests and pytest.
- Node 20 with Observable Framework (`@observablehq/framework`), Observable Plot and `node --test`.
- GitHub Actions and Cloudflare Pages, deployed with wrangler.

**Spec:** `docs/superpowers/specs/2026-11-13-painel-votacoes-design.md`. Phase 2 (Narrativa, the ministries timeline and milestones) will get a separate plan.

## Global Constraints

- **Site language:** Portuguese (pt-BR). Every page shows "Fonte: Câmara dos Deputados — Dados Abertos" and the date of the last update.
- **Votes included:** only Plenário roll-call votes (`siglaOrgao == "PLEN"`).
- **Legislature:** the 57th, from 2023-02-01 to 2027-01-31.
- **Years downloaded:** 2023, 2024, 2025, 2026, plus 2027 if the file exists. A 404 is accepted only for 2027.
- **Data source:** bulk files at `https://dadosabertos.camara.leg.br/arquivos/{tipo}/json/{tipo}-{ano}.json`, where `tipo` is `votacoes`, `votacoesVotos` or `votacoesOrientacoes`. The live API is used only by the bloc seeding script (Task 3).
- **Alignment rule** (`seguiu`):
  - The orientation is `"Liberado"`, empty, or missing → the vote is excluded.
  - The deputy's vote is `Artigo 17` or blank → the vote is excluded and counted as a separate category.
  - The deputy abstained → divergence.
  - Otherwise → aligned only when the vote matches the orientation (Sim = Sim, Não = Não, Obstrução = Obstrução).
- **Party alignment:** compared against the deputy's party **on the date of the vote**.
- **Margin of error:** Wilson interval at 95% (z = 1.96).
- **Ranking minimum:** a deputy needs 30 counted votes in the window to enter the ranking.
- **Time windows:**
  - `movel` (default): the 4 calendar quarters ending at the selected quarter.
  - `trimestre`: the selected quarter alone.
  - `legislatura`: everything.
- **Groups:** fitted once on the `legislatura` window, with `k = 3` by default. Labels are assigned by the centers sorted by government alignment, highest first: "Base", "Independentes", "Oposição".
- **Files never committed:**
  - `data/raw/` (raw downloads)
  - `.superpowers/`
  - `site/dist/`
  - `site/src/.observablehq/cache/`
- **Repository:** private.

## Review Focus

1. **Deputy with few votes in a window** (a substitute, a deputy on leave, the first quarter of the term) → they appear with a wide interval, stay out of the ranking, and nothing crashes. *Test in Task 4 (`test_indices_poucos_votos`) and Task 7 (`test_ranking_exclui_n_baixo`).*
2. **Deputy who changes party in the middle of a window** → each vote is compared with the party of that day. The party shown is the most recent one in the window, and the trail stays continuous because it is keyed by `deputado_id`. *Test in Task 4 (`test_troca_de_partido_na_janela`).*
3. **Vote where the party has no direct orientation and its bloc cannot be found** → `orientacao_partido` is left empty and the vote **does not count as divergence**. The pipeline reports coverage. *Test in Task 3 (`test_sem_bloco_nao_e_divergencia`).*
4. **Download fails, comes back partial, or `dados` is empty** → the pipeline exits with code ≠ 0 and nothing is published, so the previous site stays online. *Test in Task 1 (`test_baixar_json_invalido_falha`) and Task 8 (`test_cli_falha_sem_publicar`).*
5. **Different spellings of bancada and party names** ("União"/"UNIÃO", "Republican", "Solidaried", "PCdoB") → they are normalized to the same code. *Test in Task 2 (`test_normalizar_sigla_variantes`).*

---

## File Structure

```
.gitignore
pyproject.toml                  # uv project; package painel
painel/
  __init__.py
  baixar.py                     # download bulk files (Task 1)
  carregar.py                   # parsing + normalization (Task 2)
  orientacao_partido.py         # party → own/bloc/federation orientation (Task 3)
  metricas.py                   # windows, alignment, Wilson, indices (Task 4)
  grupos.py                     # GMM, labels, distance to center (Task 5)
  mapa.py                       # PCA per window (Task 6)
  desgarrados.py                # direction + ranking (Task 7)
  validacao.py                  # tallies, sanity, external reference (Task 8)
  exportar.py                   # JSON for the site (Task 8)
  cli.py                        # orchestration: python -m painel.cli (Task 8)
scripts/semear_blocos.py        # draft of the bloc table from the API (Task 3)
data/curado/blocos.csv          # bloc/federation → parties table, curated (Task 3)
data/referencia/externa.csv     # external sample for checking (Task 8)
tests/fixtures/*.json           # mini-files in the bulk format (Task 2)
tests/test_*.py
site/
  package.json  observablehq.config.js
  src/index.md                  # Explorar (Tasks 10–11)
  src/metodologia.md            # (Task 9)
  src/components/estado.js      # URL state + filters + trail (Task 10)
  src/components/graficos.js    # scatter, map, ranking, detail (Tasks 10–11)
  src/components/rodape.js      # source + date (Task 9)
  test/estado.test.js
.github/workflows/atualizar.yml # daily job (Task 12)
```

---

### Task 1: Project base and download

**Files:**
- Create: `.gitignore`, `pyproject.toml`, `painel/__init__.py`, `painel/baixar.py`, `tests/test_baixar.py`
- Move: the spec and this plan are already in `docs/superpowers/` and go into the first commit.

**Interfaces:**
- Produces:
  - `URL_BASE = "https://dadosabertos.camara.leg.br/arquivos"`
  - `TIPOS = ("votacoes", "votacoesVotos", "votacoesOrientacoes")`
  - `baixar(tipo: str, ano: int, destino: Path, obter: Callable[[str], tuple[int, bytes]] | None = None) -> Path | None`. It saves `destino/{tipo}-{ano}.json` atomically and returns `None` only on a 404 when `ano == 2027`.
  - `class DownloadFalhou(Exception)`
  - `baixar_todos(anos: list[int], destino: Path) -> dict[tuple[str, int], Path]`

- [ ] **Step 1: Set up the repository.**
  - Run `git init`.
  - Create a `.gitignore` with the entries from Global Constraints, plus `.venv/` and `node_modules/`.
  - Run `uv init --package --name painel --python 3.12`, then `uv add pandas numpy scikit-learn requests` and `uv add --dev pytest`.
  - Expected: `uv run pytest` runs and reports "no tests ran".
- [ ] **Step 2: Write the failing tests in `tests/test_baixar.py`.**

```python
def test_baixar_salva_arquivo(tmp_path):
    corpo = b'{"dados":[{"id":"1"}]}'
    p = baixar("votacoes", 2025, tmp_path, obter=lambda url: (200, corpo))
    assert p == tmp_path / "votacoes-2025.json" and p.read_bytes() == corpo

def test_baixar_url_correta(tmp_path):
    urls = []
    baixar("votacoesVotos", 2023, tmp_path, obter=lambda u: (urls.append(u), (200, b'{"dados":[1]}'))[1])
    assert urls == ["https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/json/votacoesVotos-2023.json"]

def test_baixar_404_2027_retorna_none(tmp_path):
    assert baixar("votacoes", 2027, tmp_path, obter=lambda u: (404, b"")) is None

def test_baixar_404_outro_ano_falha(tmp_path):
    with pytest.raises(DownloadFalhou):
        baixar("votacoes", 2026, tmp_path, obter=lambda u: (404, b""))

def test_baixar_json_invalido_falha(tmp_path):
    for corpo in (b'{"dados":[]}', b'{"dad', b'{}'):
        with pytest.raises(DownloadFalhou):
            baixar("votacoes", 2025, tmp_path, obter=lambda u, c=corpo: (200, c))
    assert not (tmp_path / "votacoes-2025.json").exists()
```

- [ ] **Step 3: Run the tests.** Command: `uv run pytest tests/test_baixar.py -v`. Expected: FAIL (ImportError).
- [ ] **Step 4: Implement `baixar` and `baixar_todos` in `painel/baixar.py`.**
  - The default `obter` uses `requests.get` with a 120 s timeout and 3 attempts with backoff.
  - Validate that the body parses as JSON and that `dados` is a non-empty list *before* writing.
  - Write to `.tmp`, then `os.replace` it into place.
- [ ] **Step 5: Run the tests.** Command: `uv run pytest tests/test_baixar.py -v`. Expected: 5 passed.
- [ ] **Step 6: Commit.** `git add -A && git commit -m "feat: base do projeto e download dos arquivos anuais da Câmara"`

---

### Task 2: Loading and normalization

**Files:**
- Create: `painel/carregar.py`, `tests/fixtures/votacoes-2025.json`, `tests/fixtures/votacoesVotos-2025.json`, `tests/fixtures/votacoesOrientacoes-2025.json`, `tests/test_carregar.py`

**Interfaces:**
- Consumes: the files produced by `baixar`. The formats were checked against the real 2025 files:
  - votações have `id`, `data` (YYYY-MM-DD), `siglaOrgao`, `votosSim`, `votosNao`, `votosOutros`, `descricao`.
  - votos have `idVotacao`, `dataHoraVoto`, `voto`, `deputado_{id,nome,siglaPartido,siglaUf}`.
  - orientações have `idVotacao`, `siglaBancada`, `orientacao`.
- Produces:
  - `normalizar_sigla(s: str) -> str`
  - `carregar_votacoes(paths: list[Path]) -> pd.DataFrame`, with columns `id_votacao, data (datetime64), sigla_orgao, votos_sim, votos_nao, votos_outros, descricao`.
  - `filtrar_plenario(votacoes) -> pd.DataFrame`
  - `carregar_votos(paths) -> pd.DataFrame`, with columns `id_votacao, deputado_id (str), nome, partido (normalized), uf, categoria`. `categoria` is one of `"sim","nao","abstencao","obstrucao","artigo17","branco"`.
  - `carregar_orientacoes(paths) -> pd.DataFrame`, with columns `id_votacao, bancada (normalized), orientacao`. `orientacao` is one of `"sim","nao","obstrucao","liberado"` or `None` when empty.
  - `REGIOES: dict[str, str]`, mapping each UF to a region (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).

- [ ] **Step 1: Build the fixtures.**
  - Take 3 real votações from 2025: 2 `PLEN` and 1 `CCJC`.
  - Include about 12 deputies from PT, PL, UNIÃO, PCdoB and PSD. At least one deputy should have `Abstenção`, one `Obstrução`, one `Artigo 17` and one blank vote.
  - Include orientations with `"Governo"`, `"Fdr PT-PCdoB-PV"`, `"Bl UniPpPsd..."`, `"Republican"` and `"Liberado"`, plus one empty orientation.
  - Keep the votos and the placar (`votosSim`, `votosNao`) consistent.
- [ ] **Step 2: Write the failing tests.**

```python
def test_normalizar_sigla_variantes():
    assert normalizar_sigla("União") == normalizar_sigla("UNIÃO") == "UNIÃO"
    assert normalizar_sigla("Republican") == "REPUBLICANOS"
    assert normalizar_sigla("Solidaried") == "SOLIDARIEDADE"
    assert normalizar_sigla("Podemos") == "PODE"
    assert normalizar_sigla("PCdoB") == "PCDOB"
    assert normalizar_sigla("Bl UniPpPsd...") == "BL UNIPPPSD"
    assert normalizar_sigla(" Fdr PSDB-CIDADAN ") == "FDR PSDB-CIDADANIA"

def test_categorias_de_voto(fixtures):
    v = carregar_votos([fixtures / "votacoesVotos-2025.json"])
    assert set(v.categoria) <= {"sim","nao","abstencao","obstrucao","artigo17","branco"}
    assert {"abstencao","obstrucao","artigo17","branco"} <= set(v.categoria)

def test_filtrar_plenario(fixtures):
    vt = filtrar_plenario(carregar_votacoes([fixtures / "votacoes-2025.json"]))
    assert set(vt.sigla_orgao) == {"PLEN"} and len(vt) == 2

def test_orientacao_vazia_vira_none(fixtures):
    o = carregar_orientacoes([fixtures / "votacoesOrientacoes-2025.json"])
    assert o.orientacao.isna().any() and set(o.orientacao.dropna()) <= {"sim","nao","obstrucao","liberado"}

def test_regioes_cobrem_27_ufs():
    assert len(REGIOES) == 27 and REGIOES["BA"] == "Nordeste" and REGIOES["DF"] == "Centro-Oeste"
```

- [ ] **Step 3: Run the tests.** Command: `uv run pytest tests/test_carregar.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement `painel/carregar.py`.**
  - `normalizar_sigla` applies, in order: `strip` → `upper()` → remove a trailing `"..."` → collapse spaces → apply the alias map `{"REPUBLICAN": "REPUBLICANOS", "SOLIDARIED": "SOLIDARIEDADE", "PODEMOS": "PODE", "FDR PSDB-CIDADAN": "FDR PSDB-CIDADANIA"}`.
  - Map the raw vote values: `"Sim"`, `"Não"`, `"Abstenção"`, `"Obstrução"`, `"Artigo 17"`, `""`. An unknown value raises `ValueError` naming the value, so a new category does not pass silently.
- [ ] **Step 5: Run the tests.** Command: `uv run pytest tests/test_carregar.py -v`. Expected: PASS.
- [ ] **Step 6: Commit.** `git commit -am "feat: carga e normalização de votações, votos e orientações"` (add the new files first).

---

### Task 3: Applicable party orientation (party, bloc, federation)

**Files:**
- Create: `painel/orientacao_partido.py`, `scripts/semear_blocos.py`, `data/curado/blocos.csv`, `tests/test_orientacao_partido.py`

**Interfaces:**
- Consumes: `carregar_orientacoes`, `filtrar_plenario(carregar_votacoes(...))`, `carregar_votos` (Task 2).
- Produces:
  - `carregar_tabela_blocos(path: Path) -> pd.DataFrame`. The CSV has columns `bancada_prefixo,partido,inicio,fim,observacao`. Dates are ISO and `fim` may be empty. Prefix and party are normalized with `normalizar_sigla`.
  - `orientacao_aplicavel(orientacoes, votacoes, votos, blocos) -> pd.DataFrame`, with columns `id_votacao, partido, orientacao, fonte`, where `fonte` is `"partido"`, `"bloco"` or `"federacao"`. There is one row for each (votação, party with a deputy present).
  - `cobertura(aplicavel, votos) -> float`: the share of (vote, deputy) pairs whose party received an orientation (any value, including "liberado"; only `None` counts as uncovered), counted over all pairs whose vote is sim/nao/abstencao/obstrucao.

- [ ] **Step 1: Write the failing tests.** Use a synthetic table in the test. In it, `BL UNIPPPSD` contains UNIÃO, PP and PSD from 2025-02-01, and `FDR PT-PCDOB-PV` contains PT, PCDOB and PV.

```python
def test_orientacao_direta_tem_prioridade(): ...   # party oriented itself AND its bloc too → fonte == "partido"
def test_partido_herda_do_bloco_na_data(): ...      # PSD has no own orientation → gets BL UNIPPPSD's, fonte == "bloco"
def test_bloco_fora_da_vigencia_nao_vale(): ...     # votação before inicio → no row for PSD
def test_federacao(): ...                           # PCDOB gets FDR PT-PCDOB-PV's, fonte == "federacao"
def test_sem_bloco_nao_e_divergencia(): ...         # party with nothing → orientacao is None (never "nao")
def test_cobertura(): ...                           # fixture with 4 pairs, 3 covered → 0.75
```

Each test builds DataFrames of 1–3 rows by hand and asserts the exact `orientacao` and `fonte`.

- [ ] **Step 2: Run the tests.** Command: `uv run pytest tests/test_orientacao_partido.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `orientacao_aplicavel`.**
  - For each votação, start from the parties that have a deputy in the votos.
  - Use the party's direct orientation if it exists.
  - Otherwise, find the bancada of that votação whose normalized name `startswith(bancada_prefixo)` for a table row containing the party and in force on the votação's date (`inicio <= data <= fim or fim is null`).
  - `fonte = "federacao"` when the prefix starts with `"FDR "`, otherwise `"bloco"`.
- [ ] **Step 4: Run the tests.** Command: `uv run pytest tests/test_orientacao_partido.py -v`. Expected: PASS.
- [ ] **Step 5: Write `scripts/semear_blocos.py` and produce the first `data/curado/blocos.csv`.**
  - The script queries `https://dadosabertos.camara.leg.br/api/v2/blocos?idLegislatura=57&itens=100` and `/blocos/{id}/partidos`, and writes the draft CSV.
  - Federations are added by hand, since they are fixed for the legislature: `FDR PT-PCDOB-PV` (PT, PCDOB, PV), `FDR PSOL-REDE` (PSOL, REDE), `FDR PSDB-CIDADANIA` (PSDB, CIDADANIA).
  - If the API does not return blocs that have ended, or their dates, complete them by hand. Use the distinct bancadas starting with `"BL "` found in the 2023–2026 orientations, and their first and last appearance dates, as evidence. Write the source in `observacao`.
- [ ] **Step 6: Measure real coverage.**
  - Run `uv run python -c` with the real 2023–2026 files, downloaded with `baixar_todos` into `data/raw/`, and print `cobertura` per year.
  - Expected: ≥ 0.90 in every year.
  - **If any year comes in below 0.90, stop and report** the uncovered bancadas to the user before going on. The party index would not be reliable.
- [ ] **Step 7: Commit.** `git add painel/orientacao_partido.py scripts data/curado tests && git commit -m "feat: orientação aplicável por partido via blocos e federações"`

---

### Task 4: Windows, alignment and indices

**Files:**
- Create: `painel/metricas.py`, `tests/test_metricas.py`

**Interfaces:**
- Consumes: Tasks 2 and 3.
- Produces:
  - `seguiu(categoria: str, orientacao: str | None) -> bool | None`, following the rule in Global Constraints.
  - `wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]`. Returns `(0.0, 1.0)` when `n == 0`.
  - `trimestre(d) -> str`, for example `"2023T1"`.
  - `janelas(trimestres: list[str], modo: str) -> dict[str, list[str]]`. `modo` is `"movel"`, `"trimestre"` or `"legislatura"`. The key is the window's final quarter; in `legislatura` the only key is `"legislatura"`.
  - `marcar_alinhamento(votos, votacoes, orientacoes, aplicavel) -> pd.DataFrame`. It is the votos DataFrame plus `data, trimestre, orient_gov, seguiu_gov, orient_partido, seguiu_partido, seguiu_maioria`.
    - The government orientation is the bancada `"GOVERNO"`.
    - `seguiu_maioria` compares with the most common vote among the **other** deputies of the same party in that votação, counting only sim/nao/abstencao/obstrucao. It needs ≥ 3 colleagues; on a tie it is `None`.
  - `indices(marcado, modo) -> pd.DataFrame`, with columns `janela, modo, deputado_id, nome, partido, uf, regiao, n_gov, alinh_gov, ic_gov_inf, ic_gov_sup, n_par, alinh_par, ic_par_inf, ic_par_sup, n_maioria, alinh_maioria, n_artigo17, n_branco`.
    - `partido` is the party in the deputy's last vote in the window.
    - `alinh_*` is `NaN` when `n_* == 0`.

- [ ] **Step 1: Write the failing tests.**

```python
@pytest.mark.parametrize("cat,ori,esp", [
    ("sim","sim",True), ("nao","sim",False), ("abstencao","sim",False), ("obstrucao","sim",False),
    ("obstrucao","obstrucao",True), ("sim","obstrucao",False), ("sim","liberado",None), ("sim",None,None),
    ("artigo17","sim",None), ("branco","nao",None), ("abstencao","nao",False)])
def test_seguiu(cat, ori, esp): assert seguiu(cat, ori) is esp

def test_wilson():
    lo, hi = wilson(8, 10); assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)
    assert wilson(0, 0) == (0.0, 1.0)

def test_trimestre_e_janelas():
    assert trimestre(date(2023, 2, 1)) == "2023T1" and trimestre(date(2026, 10, 1)) == "2026T4"
    t = ["2023T1","2023T2","2023T3","2023T4","2024T1"]
    assert janelas(t, "movel")["2024T1"] == ["2023T2","2023T3","2023T4","2024T1"]
    assert janelas(t, "movel")["2023T2"] == ["2023T1","2023T2"]
    assert janelas(t, "trimestre")["2023T3"] == ["2023T3"]
    assert janelas(t, "legislatura") == {"legislatura": t}

def test_maioria_exclui_o_proprio(): ...       # 3 colleagues vote "nao", the deputy votes "sim" → seguiu_maioria False
def test_indices_poucos_votos(): ...           # deputy with 2 counted votes → n_gov == 2 and ic_gov_sup - ic_gov_inf > 0.5
def test_troca_de_partido_na_janela(): ...     # PL vote in T1, PSD vote in T2: each compared with its own party; partido == "PSD"
def test_artigo17_contado_a_parte(): ...       # n_artigo17 == 1 and it does not enter n_gov
```

- [ ] **Step 2: Run the tests.** Command: `uv run pytest tests/test_metricas.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `painel/metricas.py`.**
  - Do it vectorized with pandas `groupby`. `seguiu` is the single source of the rule; apply it with `np.select` or `map`, equivalent to the function.
- [ ] **Step 4: Run the tests.** Command: `uv run pytest tests/test_metricas.py -v`. Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat: regra de alinhamento, janelas e índices com Wilson"` (after `git add`).

---

### Task 5: Groups

**Files:**
- Create: `painel/grupos.py`, `tests/test_grupos.py`

**Interfaces:**
- Consumes: `indices(..., "legislatura")` and `indices(..., "movel"|"trimestre")` (Task 4).
- Produces:
  - `@dataclass ModeloGrupos: centros: list[tuple[float, float]]; rotulos: list[str]; k: int; bic: dict[int, float]`
  - `ajustar_grupos(ind_legislatura, k: int | None = 3, k_max: int = 5, n_min: int = 30, seed: int = 0) -> ModeloGrupos`
    - It uses `GaussianMixture(covariance_type="full")` on `(alinh_gov, alinh_par)` of the deputies with `n_gov >= n_min` and `n_par >= n_min`.
    - `bic` is always computed for k = 2..k_max, so it can be shown on Metodologia.
    - `k=None` picks the k with the lowest BIC.
    - Labels: the centers are sorted by `alinh_gov` from highest to lowest. With k=3 the labels are "Base", "Independentes", "Oposição". With other k, the first is "Base", the last is "Oposição" and the middle ones are "Intermediário 1..".
  - `atribuir(modelo, ind) -> pd.DataFrame`. It is `ind` plus `grupo` (the label of the nearest center, Euclidean) and `dist_centro`. Rows with `alinh_gov` or `alinh_par` at `NaN` get `grupo = None`.

- [ ] **Step 1: Write the failing tests.**
  - `test_tres_nuvens_rotuladas`: a synthetic sample of 3 clouds, around (0.95, 0.95), (0.55, 0.7) and (0.2, 0.95), 50 points each, seed 0. The labels come out in that order, the centers are within 0.05 of the means, and `set(bic) == {2, 3, 4, 5}`.
  - `test_atribuir_nan_sem_grupo`
  - `test_dist_centro_zero_no_centro`
- [ ] **Step 2: Run the tests.** Expected: FAIL.
- [ ] **Step 3: Implement `painel/grupos.py`.**
- [ ] **Step 4: Run the tests.** Command: `uv run pytest tests/test_grupos.py -v`. Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat: grupos por mistura gaussiana com rótulos estáveis"`

---

### Task 6: Position map

**Files:**
- Create: `painel/mapa.py`, `tests/test_mapa.py`

**Interfaces:**
- Consumes: `marcar_alinhamento` (Task 4), using the columns `id_votacao, deputado_id, partido, trimestre, categoria`.
- Produces: `posicoes(marcado, janelas_movel: dict[str, list[str]], min_votos_dep: int = 50, min_votantes: int = 50, var_min: float = 0.15) -> tuple[pd.DataFrame, dict[str, list[float]]]`.
  - The first value is a DataFrame with `janela, deputado_id, dim1, dim2`.
  - The second is the explained variance per window, `[dim1, dim2]`.
  - Encoding: `sim=+1`, `nao=-1`, anything else is missing.
  - Keep only votações with ≥ `min_votantes` and `1 - média² > var_min`, and deputies with ≥ `min_votos_dep`.
  - Center each column and fill missing values with 0, then run `numpy.linalg.svd`.
  - Signs: `dim1` is flipped so that the PT mean is < 0, and `dim2` so that the PL mean is ≥ 0.

- [ ] **Step 1: Write the failing tests.**
  - `test_dois_blocos_separados_em_dim1`: 20 "PT" deputies always vote with the government and 20 "PL" always against, over 60 votações with some noise. All PT have `dim1 < 0`, all PL have `dim1 > 0`, and the explained variance of dim1 is > 0.5.
  - `test_sinal_estavel`: flipping the order of the columns gives the same signs.
  - `test_filtra_deputados_com_poucos_votos`
- [ ] **Step 2: Run the tests.** Expected: FAIL.
- [ ] **Step 3: Implement `painel/mapa.py`.**
- [ ] **Step 4: Run the tests.** Command: `uv run pytest tests/test_mapa.py -v`. Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat: mapa de posições por PCA com sinal fixo"`

---

### Task 7: Deputies who stray from their party (direction and ranking)

**Files:**
- Create: `painel/desgarrados.py`, `tests/test_desgarrados.py`

**Interfaces:**
- Consumes: `indices` (Task 4).
- Produces: `classificar(ind, n_min: int = 30) -> pd.DataFrame`. It is `ind` plus three columns:
  - `direcao`: `"rumo ao governo"` if `alinh_gov` > the median `alinh_gov` of the party in the same window, otherwise `"rumo à oposição"`. `None` if `alinh_gov` is NaN.
  - `elegivel_ranking`: `n_par >= n_min`.
  - `posicao_ranking`: among the eligible deputies in each window, ordered by `ic_par_sup` ascending, so first comes whoever is *most certainly* far from the party. Ties are broken by `alinh_par`. `NaN` for those not eligible.

- [ ] **Step 1: Write the failing tests.**
  - `test_direcao_por_mediana_do_partido`
  - `test_ranking_exclui_n_baixo`: a deputy with `n_par = 29` and `alinh_par = 0.1` has no position.
  - `test_ranking_usa_limite_superior`: A with (alinh 0.40, n 200) comes before B with (alinh 0.35, n 31), because B's interval is wider.
- [ ] **Step 2: Run the tests.** Expected: FAIL.
- [ ] **Step 3: Implement `painel/desgarrados.py`.**
- [ ] **Step 4: Run the tests.** Command: `uv run pytest tests/test_desgarrados.py -v`. Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat: ranking de desgarrados com direção e margem de erro"`

---

### Task 8: Validation, export and command line

**Files:**
- Create: `painel/validacao.py`, `painel/exportar.py`, `painel/cli.py`, `data/referencia/externa.csv`, `tests/test_validacao.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Tasks 1–7.
- Produces:
  - `class ValidacaoFalhou(Exception)`
  - `checar_placar(votos, votacoes, tolerancia: float = 0.02) -> list[str]`. For each PLEN votação it compares the count of `sim`/`nao` in the votos with `votos_sim`/`votos_nao`. It returns an error if the share of mismatched votações is greater than `tolerancia`, and lists up to 10 of them.
  - `checar_sanidade(ind_movel) -> list[str]`. It returns an error when any of these fails:
    - every window from `2023T2` on has between 400 and 620 deputies with `n_gov > 0`;
    - every `alinh_*` value is in [0, 1];
    - in every window, PT's median `alinh_gov` is ≥ 0.85 and PL's is ≤ 0.50.
  - `checar_referencia(marcado, ref: pd.DataFrame, tolerancia_pp: float = 5.0) -> list[str]`.
    - The CSV columns are `fonte,url,metodo,deputado_id,nome,inicio,fim,alinhamento_governo`.
    - It recomputes `alinh_gov` for the exact period of each row and returns an error for every difference greater than 5 percentage points that does not have `metodo` marked `"diferente"`.
  - `exportar(saida: Path, ind: pd.DataFrame, modelo: ModeloGrupos, mapa: pd.DataFrame, variancia: dict, meta: dict) -> None`.
    - It writes `indices.json` (records; floats rounded to 4 places), `grupos.json` (`centros, rotulos, k, bic`), `mapa.json` (`{posicoes: [...], variancia: {...}}`) and `meta.json`.
    - `meta.json` has the keys `atualizado_em` (ISO, America/Sao_Paulo), `fonte`, `anos`, `n_votacoes_plenario`, `n_votacoes_com_orientacao_governo`, `cobertura_orientacao_partido` (per year) and `janelas` (ordered list).
  - `main(argv: list[str] | None = None) -> int` in `painel/cli.py`, run as `python -m painel.cli [--anos 2023 2024 2025 2026 2027] [--raw data/raw] [--saida site/src/data] [--sem-download]`.
    - Steps: download → load → orientation → marking → indices (`movel`, `trimestre`, `legislatura`) → groups (fitted on `legislatura`, assigned to all) → map (`movel` windows) → stray-deputies ranking → validations → export.
    - Any validation error prints the messages and returns 1 **before** export.

- [ ] **Step 1: Write the failing tests.**
  - `test_placar_confere` and `test_placar_divergente` use the fixtures from Task 2, changing `votos_sim` in one votação.
  - `test_sanidade_pt_baixo_falha`
  - `test_referencia_tolerancia`: 4 pp passes, 6 pp fails, and 6 pp with `metodo="diferente"` passes.
  - `test_cli_falha_sem_publicar`: `main([... "--sem-download"])` with a raw folder whose placar was corrupted returns 1, and `saida/` stays empty.
  - `test_exportar_arquivos`: the 4 files exist and `meta.json` has every listed key.
- [ ] **Step 2: Run the tests.** Expected: FAIL.
- [ ] **Step 3: Implement `validacao.py`, `exportar.py` and `cli.py`.**
- [ ] **Step 4: Build `data/referencia/externa.csv`.**
  - Look for public sources of deputies' government alignment, for example Radar do Congresso, and confirm which ones are available and what their method is: which votações count, how absences and abstentions are treated, and the period.
  - Record 15–20 deputies from different parties, with their periods and URLs. Mark `metodo` as `"igual"` or `"diferente"`, with a short note in the URL column if needed.
  - **If no available public source has data per deputy, stop and report this to the user**, along with what was found. Publishing would then rest only on the internal checks.
- [ ] **Step 5: Run the tests.** Command: `uv run pytest -v`. Expected: everything passes.
- [ ] **Step 6: Run the pipeline end to end on the real data.** Command: `uv run python -m painel.cli`. Expected:
  - exit 0;
  - `site/src/data/*.json` is written;
  - the `meta.json` coverage is ≥ 0.90.

  Also open `indices.json` and check that, in the 2025T4 moving window, João Carlos Bacelar (PL-BA) has `alinh_maioria` < 0.45 and `alinh_gov` > 0.8. This is a sanity check against the 2025 sketch, which used the bancada majority.
- [ ] **Step 7: Commit.** `git add painel tests data/referencia && git commit -m "feat: validações bloqueantes, exportação e CLI do pipeline"`. Do not version `site/src/data/`: add it to `.gitignore`.

---

### Task 9: Site base, footer and Metodologia

**Files:**
- Create: `site/package.json`, `site/observablehq.config.js`, `site/src/components/rodape.js`, `site/src/metodologia.md`, `site/src/index.md` (placeholder), `site/test/rodape.test.js`

**Interfaces:**
- Consumes: `site/src/data/meta.json` and `grupos.json` (Task 8).
- Produces:
  - `rodape(meta: {atualizado_em: string, fonte: string}) -> HTMLElement`. Its text is "Fonte: Câmara dos Deputados — Dados Abertos · Atualizado em DD/MM/AAAA HH:mm".
  - `formatarData(iso: string) -> string`, as "DD/MM/AAAA HH:mm" in America/Sao_Paulo.
  - The config defines `title: "Votações na Câmara — 57ª Legislatura"`, `lang: "pt-BR"`, the pages `[{name:"Explorar", path:"/"}, {name:"Metodologia", path:"/metodologia"}]` and a `footer` that renders the footer on every page.

- [ ] **Step 1: Set up the site.** In `site/`, run `npm init -y && npm i -D @observablehq/framework` and add the scripts `"dev": "observable preview"`, `"build": "observable build"` and `"test": "node --test test/"`.
- [ ] **Step 2: Write the failing test `test/rodape.test.js`.** `formatarData("2026-11-13T06:05:00-03:00") === "13/11/2026 06:05"`, and the footer text contains "Câmara dos Deputados".
- [ ] **Step 3: Run the test.** Command: `npm test`. Expected: FAIL.
- [ ] **Step 4: Implement `rodape.js` and the config.**
- [ ] **Step 5: Write `metodologia.md` in plain language.** It has these sections:
  1. Which votes count (Plenário, roll call).
  2. The alignment rule, with the table from Global Constraints, abstention as divergence, and Artigo 17/blank as a separate category.
  3. Party orientation through blocs and federations, with the coverage read from `meta.json`.
  4. The 12-month moving window and why it is used.
  5. The margin of error (Wilson), with the 30-vote minimum.
  6. Groups: GMM on the whole legislature, with the BIC table read from `grupos.json`.
  7. The position map (PCA) and its explained variance.
  8. How the ranking works (upper bound of the interval) and the two directions.
  9. Checks against external sources and the official tallies.
  10. Known limitations.

  No code.
- [ ] **Step 6: Check the site.** Command: `npm test && npm run build`. Expected: the test passes, the build has no errors, and `dist/metodologia.html` contains "Wilson".
- [ ] **Step 7: Commit.** `git add site && git commit -m "feat: base do site, rodapé com fonte e página de Metodologia"`

---

### Task 10: Explorar — state, filters and the two-axis chart with a trail

**Files:**
- Create: `site/src/components/estado.js`, `site/src/components/graficos.js`, `site/test/estado.test.js`
- Modify: `site/src/index.md`

**Interfaces:**
- Consumes: `indices.json`, `grupos.json` and `meta.json` (Task 8).
- Produces (in `estado.js`):
  - `ESTADO_PADRAO = {modo:"movel", janela:null, ufs:[], regioes:[], partidos:[], grupos:[], deputado:null, eixoPartido:"orientacao"}`. `janela: null` means the last window in `meta.janelas`, and `eixoPartido` is `"orientacao"` or `"maioria"`.
  - `lerEstado(search: string) -> Estado` and `escreverEstado(e: Estado) -> string`. Query parameters: `m, j, uf, rg, p, g, d, ep`; lists are comma-separated and default values are omitted.
  - `filtrar(rows, e) -> rows`, by modo, janela, uf, regiao, partido and grupo. An empty list means no filter.
  - `rastro(rows, deputadoId, modo, ateJanela, janelasOrdem) -> Array<{janela, alinh_gov, alinh_par}>`.
- Produces (in `graficos.js`): `dispersao(rows, {grupos, rastro, eixoPartido, destaque, width}) -> SVGElement`.
  - Observable Plot: x is `alinh_gov` and y is `alinh_par` (or `alinh_maioria`), both 0–100%. Color comes from `grupo`; centers are drawn as black rings with the label.
  - The tooltip shows name (party-UF), government %, party % and n.
  - The trail is a line with dots for the selected deputy.

- [ ] **Step 1: Write the failing tests in `test/estado.test.js`.**
  - Round trip: `lerEstado(escreverEstado(e))` deep-equals `e`, for a state with accented names (`partidos: ["UNIÃO"]`) and `d: "204379"`.
  - `escreverEstado(ESTADO_PADRAO) === ""`.
  - `filtrar` with `regioes:["Nordeste"]` returns only Northeast UFs.
  - `rastro` returns the windows in order and stops at `ateJanela`.
- [ ] **Step 2: Run the tests.** Command: `npm test`. Expected: FAIL.
- [ ] **Step 3: Implement `estado.js` and `dispersao`.**
- [ ] **Step 4: Assemble `index.md`.**
  - Title and a one-line explanation.
  - Inputs: a window mode selector, a quarter slider over `meta.janelas` with a ▶ button that steps through the quarters every 1.5 s, UF/Region/Party/Group multi-selects and a party-axis toggle.
  - The chart.
  - A side panel with details when a deputy is clicked: group, `dist_centro`, the indices with their interval, n, `n_artigo17` and `n_branco`.
  - A "Copiar link desta visão" button.
  - Every change to the inputs updates `location.search` through `history.replaceState(escreverEstado(...))`, and the state is read from the URL when the page loads.
- [ ] **Step 5: Check the site.** Commands: `npm test && npm run build`, then `npm run dev`. Open `/?j=2025T4&p=PL` and confirm that only PL appears. Click a deputy and confirm the trail and the side panel appear, and the URL gains `d=`. Reload the page and confirm the same view comes back.
- [ ] **Step 6: Commit.** `git commit -m "feat: Explorar com filtros, rastro no tempo e estado na URL"` (after `git add`).

---

### Task 11: Explorar — position map and stray-deputies ranking

**Files:**
- Modify: `site/src/components/graficos.js`, `site/src/index.md`, `painel/exportar.py` (only if a field is missing)

**Interfaces:**
- Consumes:
  - `mapa.json`, and `indices.json` with `direcao`, `elegivel_ranking` and `posicao_ranking` (Tasks 6–8).
  - `filtrar` and `Estado` (Task 10).
- Produces:
  - `mapaPosicoes(posicoes, rows, {destaque, width}) -> SVGElement`. Color is by party, using the fixed palette `{PT:"#c0392b", PL:"#1f4e9e", "UNIÃO":"#17a2b8", PSD:"#e67e22", MDB:"#27ae60", PP:"#8e44ad", REPUBLICANOS:"#2c3e50", PSOL:"#f1c40f", NOVO:"#ff7f50"}`; other parties are `#bbb`. The axes are labeled "Dimensão 1 (governo ↔ oposição)" and "Dimensão 2", and the explained variance appears in the caption.
  - `rankingDesgarrados(rows, {limite = 20, direcao = "todas"}) -> HTMLElement`. It is a table with name (party-UF), a party-fidelity bar with the interval range, the interval in text, government % and direction. It uses only `elegivel_ranking` rows, sorted by `posicao_ranking`, and has a "rumo ao governo" / "rumo à oposição" / "todas" filter.
  - Clicking a row or a point sets `estado.deputado`, which is the same highlight as the two-axis chart.

- [ ] **Step 1: Write the failing test in `test/estado.test.js`.** `ordenarRanking(rows, "rumo ao governo")` returns only that direction, in order of `posicao_ranking`. Export `ordenarRanking` from `estado.js`.
- [ ] **Step 2: Run the test.** Command: `npm test`. Expected: FAIL.
- [ ] **Step 3: Implement `ordenarRanking`, `mapaPosicoes` and `rankingDesgarrados`, and place them below the main chart in `index.md`.**
- [ ] **Step 4: Check the site.** Commands: `npm test && npm run build`, then `npm run dev`. In 2025T4, confirm that PT is on the left of the map, and that the ranking shows both directions with the interval range.
- [ ] **Step 5: Commit.** `git commit -m "feat: mapa de posições e ranking de desgarrados no Explorar"` (after `git add`).

---

### Task 12: Daily update and publishing

**Files:**
- Create: `.github/workflows/atualizar.yml`, `README.md`

**Interfaces:**
- Consumes: `python -m painel.cli` (Task 8) and `npm run build` (Task 9).
- Produces: a workflow `atualizar` with `schedule: cron "0 10 * * *"` (07:00 in Brasília, after the Câmara's update at about 04:00) and `workflow_dispatch`.
  - Steps: checkout → `astral-sh/setup-uv` → `uv sync` → `uv run pytest` → `uv run python -m painel.cli` → `actions/setup-node` (20) → `npm ci && npm test && npm run build` (in `site/`) → `cloudflare/wrangler-action@v3`, run as `pages deploy site/dist --project-name=painel-votacoes`.
  - Secrets: `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
  - Any failing step blocks the deploy, so the previous site stays online.

- [ ] **Step 1: Write the workflow and a `README.md`.** The README covers running it locally, how to edit `data/curado/blocos.csv` and `data/referencia/externa.csv`, and what to do when the daily run fails.
- [ ] **Step 2: Hand off to the user (manual steps).** Ask the user to:
  1. Create the **private** repository with `gh repo create painel-votacoes --private --source . --push`, or authorize Claude to run it.
  2. Create the Cloudflare Pages project `painel-votacoes` and an API token with the "Cloudflare Pages: Edit" permission.
  3. Save the two secrets with `gh secret set`.
- [ ] **Step 3: Run the workflow once.** Command: `gh workflow run atualizar && gh run watch`. Expected: every step is green, and the `*.pages.dev` URL opens the Explorar page with today's date in the footer.
- [ ] **Step 4: Commit.** `git add .github README.md && git commit -m "ci: atualização diária e publicação no Cloudflare Pages"`, then `git push`.
