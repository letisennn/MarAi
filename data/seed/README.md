# data/seed/ — ILLUSTRATIVE seed universe

`securities.csv` and `corporate_actions.csv` are a **hand-built illustrative
seed** so v0.1 has something to run on with the synthetic price source.

- Company **names and yahoo tickers** are real, best-effort.
- **ISINs are synthetic** (`XX0SYN######`), not real identifiers.
- **Shares outstanding, market segment, sector, list dates and corporate-action
  dates are approximate or fabricated.**
- The `status` column deliberately includes delisted / acquired / bankrupt names
  so survivorship handling and delisting-return stitching run from day one.

Replace this with a verified list (ISIN-keyed, point-in-time) before connecting a
real data source. Nothing here should be treated as market data.

## securities.csv columns

| column | meaning |
|---|---|
| isin | synthetic primary key |
| name, country, currency | — |
| mic, market_segment | primary listing venue + segment |
| yahoo | Yahoo Finance ticker (for the optional yfinance source) |
| sector | coarse sector label |
| shares_out_millions | constant shares outstanding (v0.1 simplification; bitemporal later) |
| list_date | first day in the panel |
| status | listed / delisted / acquired / bankrupt |
| status_date | delisting date (blank if listed) |
| status_detail | acquisition offer price in local currency, or a note |

## corporate_actions.csv columns

`isin, action_type, ex_date, ratio, cash_amount, currency, detail` —
`action_type` is `split` (use `ratio`, e.g. 3 = 3:1) or `dividend` (use
`cash_amount`). Delisting / acquisition / bankruptcy actions are derived from
`securities.csv` by the loader, not listed here.
