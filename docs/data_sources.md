# Data sources

Status: **research notes**, pending Jonas/Hugo review. Rule: no source is wired
in — free or paid — without a green light. Verify licensing before adding.

## Ändring 2026-09-08 (Jonas) — riktig prisdata på som standard

Den syntetiska källan var för trubbig för att arbeta mot (allt platt, inga
rörelser, stannar i studieperiodens slut). **yfinance (Yahoo Finance) är nu
standardkälla** för `marc pipeline` (`--source synthetic` finns kvar för offline/
demo). Nyckel = Yahoo-ticker (inte riktig ISIN). Small-cap-taket i
`config/universe.yml` höjt 1.7bn → **5bn SEK** (Nasdaq-gränsen var för snäv för
ett användbart universum). Kvarstående brist: Yahoo tappar avnoterade tickers,
så universumet är fortfarande **survivorship-biased** — samma gating som förr,
ingen slutsats är survivorship-ren förrän Börsdata/EODHD är påkopplad.

## Ändring 2026-09-16 (Jonas: "det ska va hela svenska börsen") — brett seed-universum

Seed-universumet gick från ~80 handplockade namn till **671 riktiga
Stockholmsnoterade bolag** (432 blir kvar i panelen efter historik-/
likviditetskrav). Genererat programmatiskt, inte handskrivet:

- Källa: **Yahoo Finances egen screener-API** via `yfinance.screen` /
  `EquityQuery('eq', ['region','se'])` — samma redan godkända/dokumenterade
  källa som prisdatan (rad 1 ovan), inte en ny extern källa och ingen skrapning
  av tredjepartssajter. Paginerad över alla ~1179 svenska instrument Yahoo
  känner till (`exchange=STO`).
- Filter: `quoteType=EQUITY`, `currency=SEK`, `marketCap` ≤ 10 mdr SEK (utesluter
  ~500 large caps/mega caps som ändå aldrig skulle antas i ett small/mid-cap-
  universum — se regel 6), samt bort med teckningsrätter/BTA/ETF/ETN/hävstånds-
  certifikat (`Xtrackers`, `UCITS`, `Bull`/`Bear`, `-BTA`/`-TR`/`-RT`/`XBT` osv.)
  som Yahoo felaktigt taggar som `EQUITY`.
- `sharesOutstanding` och `marketCap` kommer direkt från screenern (en snapshot,
  inte bitemporalt — samma förenkling som tidigare seed-data).
- `mic`/`market_segment` sätts schablonmässigt (`XSTO`/`main`) — screenern
  skiljer inte på huvudlista/First North/Spotlight. Påverkar bara metadata, inte
  cap-gränserna (de räknas på faktisk market cap, inte listnamn).
- Genererande skript kördes en gång manuellt (inte i pipeline/CI) — se
  `docs/roadmap.md` "Tillägg 2026-09-16" om det ska bli ett repeterbart steg
  (t.ex. `marc universe refresh-seed`).

## v0.1 needs only

Daily OHLCV (unadjusted) · shares outstanding history · corporate actions
(splits/divs + delisting/M&A dates) · FX to base currency · symbology/ISIN ·
exchange calendars · a survivorship-complete universe list.

## Source table (v0.1)

| Need | Source | Cost | Nordic small-cap coverage | Historical depth | Delisted names | Licensing / limits | v0.1 role |
|---|---|---|---|---|---|---|---|
| Daily OHLCV | yfinance (Yahoo) | Free | Broad for *listed* .ST/.OL/.CO/.HE; unofficial | ~10–20y nominal | ✗ dropped | ToS disallows scraping/commercial; rate-limited; no SLA | Pipeline bring-up / spike only |
| Daily OHLCV | Stooq | Free | Decent Nordic EOD | ~10y+ | partial | Personal use; bulk limits | Cross-check |
| OHLCV + splits/divs | EODHD | ~$20–80/mo | Good (all 4 exchanges) | 30y+ many | ✓ delisted endpoint / higher tier | Non-redistribution OK for internal | Candidate real source (decide later) |
| OHLCV + fundamentals + delisted | Börsdata | ~200 SEK/mo + API add-on | **Best** Nordic, incl. First North/Spotlight | 10–20y+ | ✓ "avnoterade bolag" | Personal; API terms restrict redistribution | Candidate real source (decide later) |
| Symbology ISIN↔ticker↔FIGI | OpenFIGI | Free | Global | current + some history | ✓ | Free API, rate-limited, attribution | v0.1 |
| ISIN reference | GLEIF / Nasdaq Nordic ISIN lists | Free | Nordic | current | partial | Open | v0.1 |
| FX (SEK base) | Riksbank / ECB SDW | Free | — | 20y+ | — | Open data | v0.1 |
| Exchange calendars | `exchange_calendars` (OSS) | Free | Nordic calendars w/ history | long | — | Apache-2.0 | v0.1 |
| Corporate actions | Börsdata/EODHD + manual seed | mixed | — | — | ✓ | — | v0.1 (manual seed for ~40 known delisted names) |

## Attention / news / forum — godkänt att börja bygga (Jonas 2026-09-08)

Tidigarelagt från v0.2–0.4. **Syntetisk källa** (`marc.ingestion.attention.
SyntheticAttentionSource`, offline, deterministisk — INTE riktig data) är
fortfarande standard (`--attention-source synthetic`, default). Kausala
features: `search_level_z`, `search_accel`, `search_abnormal`, `forum_buzz_z`,
`forum_accel`, `news_rate_z`, `news_sentiment_z` (feature-set `v0.3`).

**Ändring 2026-09-16 (Jonas): riktiga Trends + nyheter inkopplade** som
`--attention-source real` (opt-in, inte default — tar flera minuter för hela
universumet):

| Kanal | Källa | Kostnad | Djup | Status |
|---|---|---|---|---|
| search | `pytrends` (Google Trends) | Gratis | **Fullt** — en pull per bolag över `today 5-y`, undviker normaliserings-stitching mellan flera pulls | **Riktig** (`ingestion/trends_source.py`) |
| news | Google News RSS per bolagsnamn | Gratis | **Grunt** — RSS-sökningen ger bara ett nuvarande fönster av träffar (typiskt senaste veckorna/månaderna, ibland djupare för lågbevakade bolag). Byggs upp gradvis över kalendertid vid upprepade körningar UTAN `--reset` (upsert, skriver inte över gamla veckor) | **Riktig, grunt** (`ingestion/news_source.py`) |
| forum | Reddit officiella API (r/aktier m.fl.) | Gratis (begränsad) | — | Fortfarande stub — kräver app-credentials (client_id/secret) som bara Jonas kan skapa på reddit.com/prefs/apps |

**ToS-notis för Google News RSS** (regel 11, läs innan användning): flödets
copyright-text säger uttryckligen "personal, non-commercial use ... within a
personal feed reader". Det här är ett privat tvåpersoners forskningsverktyg
som bara aggregerar rubrikräkning + enkel nyckelordsstatistik (republicerar
inte artikeltext) — men notisen är strikt formulerad; avvägningen läggs upp
här synligt i stället för att gömmas.

**Nyhetssentiment** (`attn_news_sentiment` → `news_sentiment_z`) är regelbaserad
räkning av positiva/negativa svenska finansord i rubriktext (se
`ingestion/news_source._POS_WORDS`/`_NEG_WORDS`) — **INGEN LLM** (regel 4,
gäller till v0.5). Grov med flit: en riktningsindikation, inte en tolkning.

Nordiska forum (Placera, Shareville, Di.se) — ToS varierar, scrapa inte där det är
förbjudet (regel 11). Kollas per källa innan inkoppling.

### Insiderhandel + blankning — godkänt och byggt (Jonas 2026-09-16)

Båda gratis, officiella svenska register (FI kräver bara källhänvisning). FI
publicerar dem via sökportaler (marknadssok.fi.se) utan en dokumenterad
bulk-API — mönstret är därför **manuell export, automatiserad inläsning**:
ladda ner en Excel/CSV via portalens egen exportfunktion, kör
`marc ingest insider <fil>` / `marc ingest short-interest <fil>`. Skriver
`insider_transaction` / `short_interest` (migration `0005_insider_short.sql`)
→ kausala features `insider_net_buy_z` (rullande 90-dagars nettobelopp,
beräknat på PUBLICERINGSDATUM inte transaktionsdatum — point-in-time, regel
5), `short_interest_level`, `short_interest_accel` (feature-set v0.4).

**Kolumnmappningen är satt efter FI:s dokumenterade fält, inte verifierad mot
en riktig export än** — `marc.ingestion.insider_short._find_col` ger ett
tydligt fel som listar filens faktiska kolumner om mappningen inte stämmer,
så den är snabb att justera första gången en riktig fil körs igenom.

### Nyanserad nyhetssentiment via LLM — undantag byggt (Jonas 2026-09-16)

`marc.llm.narrative` — Claude (Haiku) klassificerar ett bolags senaste
nyhetsrubriker (hämtade färskt via Google News RSS) till sentiment + kort
tema, på begäran (`marc llm-narrative "<bolag>"`), kräver `ANTHROPIC_API_KEY`.
**Kärnregeln kvarstår:** modellen hanterar bara rubriktext och får aldrig
uppge en sannolikhet/riktkurs/prognos — bara vad texten faktiskt säger.
Kostar riktiga pengar per anrop (litet, per token) — inte del av
standardpipelinen.

### Ännu inte inkopplat — kräver betalkälla eller ny fundamenta-pelare

Jonas svar 2026-09-16: **avvaktar** en betalkälla för nu ("inte just nu").

| Efterfrågat | Bedömning | Väg framåt |
|---|---|---|
| Analytikerestimat, riktkurser, estimatrevideringar | Tunn gratis-historik; rimlig Nordic small-cap-täckning kräver en betalkälla (t.ex. Börsdata ~200 kr/mån) | Kräver betalkälle-OK (avvaktar) |
| Institutionella flöden, ägarförändringar | Mest betalt/partiellt (t.ex. Modular Finance) | Kräver betalkälle-OK (avvaktar) |
| Earnings-call-ton | Transkript existerar i praktiken inte för nordiska små-/mikrobolag | Sannolikt inte byggbart oavsett budget |
| "Vad måste hända för att dagens värdering ska vara rimlig?" (omvänd DCF) | Kräver fundamenta (omsättning/vinst/tillväxt) — helt ny datapelare, finns inte i schemat idag | Godkänt som NÄSTA STEG när en fundamenta-källa finns (Jonas) — ny modul `marc.valuation`, inte startad |

## Later versions (summary)

| Version | Category | Candidate sources | Notes |
|---|---|---|---|
| v0.2 | Google / search | `pytrends` (free, brittle, 2004→now, relative/sampled); SerpApi / Glimpse (paid) | Trends values are re-normalised per pull; needs stitching. |
| v0.3 | News | GDELT 2.0 (free, 2015→now, noisy) backbone; MFN / Cision / Modular Finance press-release feeds (regulatory, often free RSS — great catalyst timing); Marketaux / Tiingo News (cheap) | NewsAPI free tier = 1 month history, useless for backtests. |
| v0.4 | Social / forums | Reddit official API (free tier limited; Pushshift dead → historical Reddit is hard); Stocktwits API (curtailed); X/Twitter API (~$100–5000/mo → excluded); Nordic forums (Placera/Shareville/Di.se, r/aktier) — ToS varies, thin archives | Hardest category historically. GDPR: hash user ids, decide retention. |
| v0.6 | Insider trades | Finansinspektionen PDMR register (SE, free, official, good history); Oslo Børs NewsWeb (NO); FSA (DK); FIN-FSA (FI) — free/official | |
| v0.6 | Short interest | Finansinspektionen short-selling register (SE, free, daily, ≥0.5%, history to 2012); NO/DK/FI equivalents | SE easy; NO/DK/FI harder historically. |
| v0.6 | Ownership | Modular Finance (Holdings), Börsdata ownership, national registers | Mostly paid / partial. |
| v0.6 | Analyst estimates | Börsdata consensus (limited history); Visible Alpha / Refinitiv = expensive, excluded | Hardest to get point-in-time cheaply. Likely thin. |
| v0.6 | Earnings call transcripts | Company IR, Financial Hearings, Börsdata | Rare for Nordic small-cap. |

## MVP-critical vs. can wait

- **Critical:** OHLCV, shares outstanding, corporate actions, FX, symbology,
  exchange calendars, survivorship-complete universe.
- **Can wait:** Trends, news, social, insider, short interest, ownership,
  analyst estimates, transcripts, LLM inputs.

## Hardest to obtain historically

1. Survivorship-complete Nordic small-cap universe incl. delisted + point-in-time
   membership.
2. Historical social media (Reddit / Twitter / Stocktwits).
3. Point-in-time analyst estimates.
4. Fine-grained historical Google Trends with stable normalisation.
5. Historical short interest for NO / DK / FI (SE is easy).

## Known limitation of the free-data v0.1

yfinance/Stooq drop delisted tickers, so the v0.1 universe is **knowingly
incomplete**. This is recorded as a gating limitation: no v0.1 result is trusted
as survivorship-clean until a source with delisted coverage (Börsdata / EODHD) is
signed off and loaded.
