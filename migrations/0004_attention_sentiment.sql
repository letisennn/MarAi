-- 0004: nyckelordsbaserad sentiment på nyhetskanalen.
--
-- 2026-09-16 (Jonas): riktiga Trends/nyhets-adaptrar kopplas in. Nyhetskanalen
-- får en extra kolumn för en enkel, regelbaserad sentimentpoäng (positiva minus
-- negativa nyckelord i rubriker, normaliserat -1..1) — INGEN LLM (CLAUDE.md
-- regel 4, gäller till v0.5). NULL för search/forum och för äldre rader.

ALTER TABLE attention_daily ADD COLUMN IF NOT EXISTS sentiment DOUBLE;
