# CLAUDE.md — Marc AI

> Läs hela den här filen innan du gör något i repot. Den kodifierar projektets
> filosofi och de hårda reglerna som varje session måste följa.

## Vad det här är

Marc AI är ett **privat internt research-verktyg** för två personer (Jonas och
Hugo). Det är en AI-driven marknadspsykologi- och discovery-motor för **nordiska
small-cap-bolag** (Sverige primärt; Norge, Danmark, Finland sekundärt).

Det är **inte** en produkt. Ingen multi-tenant, ingen auth utöver det basala,
ingen betalning, ingen marknadsföringssida. Bygg det enklaste som fungerar för
två användare — men håll research-motorn i ett rent, importerbart Python-paket
(`src/marc/`) så att den kan skalas eller öppnas upp senare utan omskrivning.

## Kärnfilosofi

> Vi försöker inte förutsäga framtiden med magisk AI. Vi försöker mäta
> förändringar i mänskligt beteende och marknadens förväntningar, upptäcka
> återkommande mönster, och testa om de mönstren innehåller användbar information
> om framtida prisrörelser.

Utvecklingsordning, hoppas aldrig över:

> Tillförlitlig data → beteendemätningar → statistisk evidens → maskininlärning →
> LLM-tolkning → live discovery scanner.

Det primära studieobjektet är **vad marknaden tror om ett bolag och hur de
uppfattningarna förändras** — inte "är aktien billig". Den centrala
forskningsfrågan (spec §38): vilka mätbara beteendeförändringar 1–4 veckor före
en stor prisrörelse bär statistiskt signifikant information om sannolikheten och
storleken på den rörelsen.

Projektet följer `docs/marc_ai_spec.md`. Ett tidigare "changes & additions"-
dokument (structural rerating / multibagger) är struket i sin helhet — se
`docs/archive/`.

## Hårda regler

1. **Inga godtyckliga scoring-vikter.** Vikterna i en composite score måste
   härledas ur statistik eller ML och valideras out-of-sample. Innan dess finns
   ingen score. Exemplet "Discovery Score" i specen är endast illustrativt.
2. **Ingen signal kallas prediktiv förrän den är testad** mot en riktig
   kontrollgrupp, med konfidensintervall, på data som inte användes för att
   upptäcka den.
3. **Inga dyra API:er** (Bloomberg, Refinitiv, RavenPack, betald X/Twitter osv.)
   utan uttryckligt godkännande från Jonas/Hugo. Även billiga källor (~$20–30/mån)
   kräver grönt ljus innan de kopplas in — se `docs/data_sources.md`.
4. **Ingen avancerad AI/LLM-analys ännu.** LLM-arbete börjar i v0.5. När det gör
   det hanterar LLM:er endast ostrukturerad text och får aldrig hitta på
   kvantitativa påståenden ("AI-narrativ ger +35%"). Kvantitativa påståenden
   kommer från databasen och statistiklagret.
5. **Point-in-time-disciplin.** Varje feature vid tidpunkt `t` får bara använda
   information som var känd vid `t`. Kurser lagras ojusterade; justeringar
   härleds as-of. Allt som revideras (aktier utestående, fundamenta, estimat)
   lagras bitemporalt. Se `docs/methodology.md`.
6. **Survivorship-bias-hantering är obligatorisk.** Universumet är tidsvarierande
   (`universe_membership` as-of-queries, aldrig `SELECT * FROM security`).
   Avnoterade / förvärvade / konkursade namn stannar i panelen med en explicit
   delisting-return. Seed-universumet innehåller med flit döda namn. Ett bolag
   som växer ut ur small-cap (> SEK 1.7bn) behålls i universumet men taggas
   `cap_segment_at_entry = 'mid'`; huvudanalysen filtrerar till `'small'`.
7. **Hypotesgenerering och hypotestestning är separata steg.** Utforskande fynd
   promotas till `src/marc/` och testas om på en avskild period innan de tros på.
8. **Endast kronologisk out-of-sample.** Train/test-splittar är tidsordnade med
   ett purge- + embargo-band lika med den längsta target-horisonten. Ingen
   slumpmässig blandning av observationer med överlappande fönster.
9. **Allt är reproducerbart och loggat.** Ingestion-körningar stämplar ett
   `vintage_id`; experiment registrerar code git SHA och de data-vintages som
   användes. En signal måste kunna rekonstrueras ur det databasen lagrade vid
   tillfället.
10. **Misslyckade hypoteser är resultat.** Registrera nollresultat och trasiga
    regler i `experiment_result` och skriv upp dem. Släng dem inte tyst.
11. **Bryt aldrig mot en datakällas användarvillkor.** Scrapa inte där det är
    förbjudet. Notera licensvillkor i `docs/data_sources.md` innan en källa
    läggs till.

## Teknisk stack

- **Python 3.11+**, `src/`-layout, `uv` för env/deps.
- **DuckDB**, en fil på `data/marc.duckdb`, är databasen. Råa käll-dumpar sparas
  som immutabel Parquet/JSON under `data/raw/` för proveniens och registreras som
  views. Migrations är numrerade `.sql`-filer i `migrations/` som körs av en
  liten runner, spårade i `schema_migrations`.
- **Polars** för feature-/panel-transformationer; **pandas** vid stats-gränsen.
- **statsmodels / scipy / numpy** för den statistiska baslinjen. scikit-learn →
  LightGBM/XGBoost senare (v0.7). Anthropic SDK senare (v0.5).
- **Typer**-CLI (`marc <verb>`) + `Makefile` + cron för schemaläggning. Prefect
  bara om pipelines blir komplexa (v0.3+).
- **Streamlit** för webbappen, read-only mot DuckDB. All research-logik ligger i
  `marc`; appen importerar bara och renderar.
- Kvalitet: `ruff`, `mypy`, `pytest` + `hypothesis` (property-tester för
  kausalitet), `pre-commit`.

## Repo-layout

```
src/marc/
  ingestion/   per-källa-adaptrar -> immutabla rårader + vintage
  reference/   securities, ISIN-xref-historik, tidsvarierande universum, corp actions
  cleaning/    validering, FX till basvaluta, as-of justeringsfaktorer, delisting-stitching
  features/    rena kausala feature-funktioner -> feature_panel (versionerat)
  targets/     forward returns / events -> target_panel (framtida data by design; aldrig en feature)
  signals/     regelbaserad signalgenerering -> signal_log (inga skattade vikter än)
  stats/       baslinjefrekvenser, univariata quintil-sorteringar, rank-IC, kontroll-lift, Fama-MacBeth, block-bootstrap → experiment_result
  panel.py     bygger observation + feature_panel + target_panel (veckovis)
  pipeline.py  end-to-end-orkestrering (marc pipeline)
  backtest/    event study + portföljformering — fortf. skelett (quintil/lift finns i stats)
  ml/          v0.7 — endast skelett
  llm/         v0.5 — endast skelett
  reporting/   figurer/tabeller för appen och write-ups (skelett)
app/           Streamlit-sidor: Home, Universe, Security, Experiments, Signals (ingen affärslogik, read-only)
config/        universe.yml (universumdefinition), targets.yml (target-parametrar), sources.yml, logging.yml
docs/          spec, arkitektur, datakällor, metodik, roadmap, ADR:er, experiment, resultat (docs/archive/ = struket, bygg inget därifrån)
migrations/    numrerade .sql-schemamigrations
tests/         property-tester för kausalitet / targets / universe-as-of
data/          gitignorerad: marc.duckdb + raw/ interim/ analytical/
```

`marc.features` får aldrig importera `marc.targets` (enforced i CI via
`tests/test_layering.py`).

## Target-konventioner (v0.1 — `config/targets.yml`)

- **Baspris P0** = glidande 5-handelsdagars medel av justerad close `[t-4, t]`,
  inte en enskild `close(t)`. Nämnare för alla forward-mått.
- **Omsättningsgrind:** en dag räknas mot ett event / max-return / drawdown /
  time-to-peak endast om dess SEK-omsättning ≥ `max(SEK 250k, 0.5 × glidande
  60-dagars median)`. Enstaka tunna affärer som printar extremvärden ignoreras.
- Avnotering i fönstret: konkurs → terminal −100%; förvärv → terminal budkurs
  (inte sista betalkurs); handelsstopp → bär sista kurs.

## Köra (v0.1 är implementerat)

```
uv sync --extra dev                          # installera (uv provisionerar Python 3.11+)
uv run marc pipeline --source synthetic --reset   # hela kedjan: migrate → seed → ingest → clean → universe → panel → E1 → signals
uv run streamlit run app/Home.py             # webbappen (läser data/marc.duckdb read-only)
```

Delkommandon: `marc db migrate`, `marc panel`, `marc stats`, `marc signals`,
`marc info`. `--source yfinance` byter till riktig (men survivorship-biased,
rate-limitad) prisdata. Standard är `synthetic` — deterministisk pseudo-slump,
ingen marknadsdata, finns för att köra och demo:a systemet.

Snabb testdelmängd: `uv run pytest tests/test_features_causality.py
tests/test_targets.py tests/test_layering.py`. Full svit (inkl. integrationstest
som kör hela pipelinen i en temp-DB): `uv run pytest`.

## Scope per version

- **v0.1** marknadsbaslinje: universum, pris/volym/market cap, kausala features,
  forward-return-targets, DuckDB, statistisk baslinje (experiment E1), enkel
  backtest. Mål: bär enkel pris-/volym-beteende information? "Nej" är ett giltigt
  svar.
- **v0.2** attention (Google/sök). **v0.3** nyhetsflöde. **v0.4** social/forum.
- **v0.5** LLM narrative detection. **v0.6** förväntningar (analytikerestimat,
  insiders, blankning, ägande, earnings calls). **v0.7** maskininlärning.
  **v1.0** live scanner.

## Fråga innan

- Inkoppling av någon betald datakälla.
- Att lägga till en ny extern datakälla (licenskontroll först).
- Att införa skattade vikter eller en composite score.
- Att starta LLM- eller ML-arbete före dess version.
- Något påstående i output om att en signal förutsäger en rörelse.
