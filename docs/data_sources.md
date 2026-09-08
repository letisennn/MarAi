# Data sources

Status: **research notes**, pending Jonas/Hugo review. Rule: no source is wired
in — free or paid — without a green light. Verify licensing before adding.

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

Tidigarelagt från v0.2–0.4. **Syntetisk källa först** (`marc.ingestion.attention.
SyntheticAttentionSource`, offline, deterministisk — INTE riktig data), som skriver
`attention_daily` (kanaler: `search` / `news` / `forum`). Kausala features:
`search_level_z`, `search_accel`, `search_abnormal`, `forum_buzz_z`, `forum_accel`,
`news_rate_z` (feature-set `v0.2`). Riktiga adaptrar kopplas in som `--source`:

| Kanal | Riktig källa (planerad) | Kostnad | ToS / begränsning | Status |
|---|---|---|---|---|
| search | `pytrends` (Google Trends) | Gratis | Ostabil normalisering, sampling, rate-limit; inofficiellt API | Stub (`ingestion/trends_source.py`) |
| news | Google News RSS per bolagsnamn / GDELT 2.0 | Gratis | RSS: personligt bruk; GDELT: öppet, brusigt | Stub (`ingestion/news_source.py`) |
| forum | Reddit officiella API (r/aktier m.fl.) | Gratis (begränsad) | Kräver app-credentials; Pushshift nedlagt → tunn historik; GDPR: hasha user-id | Stub (`ingestion/forum_source.py`) |

Nordiska forum (Placera, Shareville, Di.se) — ToS varierar, scrapa inte där det är
förbjudet (regel 11). Kollas per källa innan inkoppling.

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
