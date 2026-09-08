# PROJECT: Marc AI — Small-Cap Market Psychology & Discovery Engine

## 1. PROJECT OVERVIEW

We are building an AI-powered research and discovery system for the stock market.

The initial focus is Nordic small-cap and growth companies, with Sweden as the primary market and Norway, Denmark and Finland as secondary markets.

The long-term goal is to investigate whether we can systematically identify changes in market psychology, investor expectations, attention, narratives and behavior that tend to occur before significant stock-price movements.

The central idea is NOT:

> "Find undervalued stocks."

The central idea is:

> "Understand what the market believes about a company, why investors value it the way they do, how those beliefs are changing, and whether changes in market psychology tend to precede large price movements."

An especially important research question is:

> "What signals tend to appear 1–4 weeks before a small-cap company experiences an explosive price increase?"

One initial target we want to investigate is:

> +50% within approximately 30–90 days.

This is a research hypothesis, not an assumption that the system can reliably predict such movements.

---

# 2. THE CORE PHILOSOPHY

The market is made up of people and institutions making decisions based on:

* expectations
* beliefs
* information
* narratives
* fear
* greed
* uncertainty
* speculation
* incentives
* social influence
* momentum
* perceived future potential

Therefore, the system should analyze not only companies, but also the PEOPLE and PARTICIPANTS around those companies.

We want to understand:

* What are investors talking about?
* What are they searching for?
* What are they becoming excited about?
* What are they becoming worried about?
* What narratives are emerging?
* How quickly are those narratives spreading?
* Who is participating?
* Is participation coming from existing investors or new people?
* Is attention accelerating?
* Is the market becoming more optimistic?
* Is the market becoming more pessimistic?
* Is a new theme being attached to the company?
* Is the stock price moving before or after the narrative?
* Is the narrative already widely known and therefore potentially priced in?
* Are expectations changing faster than fundamentals?

The system should treat market psychology as measurable behavior wherever possible.

---

# 3. TWO DIFFERENT QUESTIONS

The system should distinguish between two major questions.

## Question A — What is the company worth?

This includes:

* revenue
* growth
* margins
* earnings
* cash flow
* debt
* valuation
* competitive position
* future earnings potential

## Question B — What does the market THINK the company is worth?

This includes:

* investor expectations
* analyst expectations
* growth expectations
* narratives
* sentiment
* hype
* attention
* positioning
* momentum
* social activity
* search activity
* news flow
* ownership changes

Question B is the primary focus of this project.

The system should attempt to understand the gap between:

> Fundamental reality

and

> Market expectations.

---

# 4. MARKET EXPECTATIONS

One of the most important concepts in this project is EXPECTATIONS.

A company can be fundamentally strong but have poor stock performance if the market already expected even better results.

A company can also be fundamentally weak but have strong stock performance if expectations were extremely low and the company exceeded them.

Therefore, whenever possible, the system should investigate:

> "What must happen for today's valuation to be reasonable?"

For example:

If a company trades at a very high valuation, determine approximately what future growth, margins and earnings the market appears to be pricing in.

Then investigate:

* Are these expectations realistic?
* Are they conservative?
* Are they extremely optimistic?
* Are analyst estimates consistent with the valuation?
* Are estimates increasing or decreasing?
* Has the market already priced in a major catalyst?
* Is the current narrative already reflected in the share price?

This does NOT mean the system should become a traditional valuation model.

Instead, fundamental analysis should help us understand the expectations underlying market behavior.

---

# 5. PRIMARY RESEARCH UNIVERSE

Initial universe:

* Nordic small-cap companies
* Sweden as primary market
* Norway
* Denmark
* Finland

Initial historical research period:

> Approximately 2020–2026

The exact period may be adjusted depending on data availability and quality.

We must avoid survivorship bias.

Where possible, historical analysis should include companies that:

* were later delisted
* were acquired
* went bankrupt
* changed ticker
* changed exchange
* otherwise disappeared from the current universe

Do not analyze only companies that exist today.

---

# 6. PRIMARY RESEARCH TARGETS

The main initial research target is:

> Identify signals that occur approximately 1–4 weeks before large future price movements.

One major target:

> +50% within 30–90 days.

Additional targets should be tested to understand different types of price movements:

* +10% within 5 trading days
* +25% within 20 trading days
* +50% within 30 days
* +50% within 60 days
* +50% within 90 days
* +100% within 180 days

Also measure:

* maximum forward return
* maximum drawdown
* time to peak
* duration of the move
* whether the move was sustained
* whether the move reversed quickly

The system should not assume that one target horizon is optimal.

---

# 7. DATA CATEGORIES

We want to investigate multiple categories of signals.

## A. PRICE & MARKET DATA

Collect where available:

* current price
* historical price
* daily returns
* 1-day momentum
* 5-day momentum
* 20-day momentum
* 60-day momentum
* trading volume
* average volume
* relative volume
* volume acceleration
* volatility
* volatility expansion
* price gaps
* breakouts
* 20-day highs
* 52-week highs
* distance from highs
* liquidity
* market capitalization

The important concept is not just the absolute value.

Measure:

* level
* change
* acceleration
* persistence
* abnormality

---

# 8. INVESTOR ATTENTION

We want to measure how much attention investors are giving a company.

Potential inputs:

* Google Trends / search activity
* searches for company name
* searches for ticker
* searches for products
* searches for technologies
* searches for themes associated with the company
* search acceleration
* abnormal search volume

Important:

A high search volume is not necessarily interesting.

A sudden CHANGE in search activity may be more informative.

Example:

20 searches → 23 → 27 → 65 → 140

This acceleration may be more important than simply having 140 searches.

---

# 9. SOCIAL MEDIA & FORUM ACTIVITY

Potential sources:

* Reddit
* Stocktwits
* X/Twitter where legally and technically available
* Swedish stock forums
* other publicly accessible discussion platforms

Measure:

* number of mentions
* number of posts
* number of comments
* number of unique authors
* number of new authors
* returning authors
* engagement
* discussion growth
* discussion acceleration
* sentiment
* sentiment change
* narrative changes

A key research question:

> Is new participation more informative than total participation?

For example:

100 comments from 10 existing users may represent something different from 100 comments from 80 new users.

---

# 10. SENTIMENT

Do not rely only on absolute sentiment.

Measure:

* absolute sentiment
* sentiment change
* sentiment acceleration
* positive/negative ratio
* uncertainty
* confidence
* fear
* excitement
* speculation

The system should investigate whether:

> "Sentiment becoming more positive"

is more useful than:

> "Sentiment is positive."

Also investigate whether extreme positive sentiment can indicate late-stage hype rather than an early opportunity.

---

# 11. NEWS FLOW

Collect where possible:

* number of news articles
* news frequency
* news acceleration
* sentiment
* novelty
* type of news
* magnitude of news
* market reaction to news

Classify catalysts such as:

* earnings
* contracts
* partnerships
* acquisitions
* product launches
* technology developments
* regulatory changes
* management changes
* financing
* insider activity
* analyst changes
* industry developments

Most importantly, analyze:

> How did the market react to the news?

A positive announcement followed by a negative stock reaction may contain more information than the announcement itself.

---

# 12. PRICED-IN EXPECTATIONS

The system should investigate whether positive information is already priced into the stock.

For example:

A company announces a major contract.

But if the stock already increased 30% beforehand because investors expected the contract, the incremental information may be much smaller than it appears.

Therefore investigate:

* price before news
* price reaction immediately after news
* volume reaction
* previous attention
* previous social discussion
* previous analyst expectations
* previous estimates
* subsequent price behavior

The goal is to understand:

> Information × Expectations × Market Reaction

rather than simply:

> Positive information = bullish.

---

# 13. ANALYST ACTIVITY

Where reliable data is available, collect:

* analyst coverage
* analyst estimates
* earnings estimates
* estimate revisions
* revenue estimates
* EPS estimates
* target prices
* target-price revisions
* analyst upgrades
* analyst downgrades
* initiation of coverage

Important research question:

> Does a change in analyst expectations precede or follow retail/social attention?

Another:

> Does increasing analyst activity amplify an already emerging narrative?

---

# 14. INSIDER ACTIVITY

Where reliable data is available:

* insider purchases
* insider sales
* size of transactions
* number of insiders
* transaction timing
* transaction direction

Investigate whether insider activity becomes more informative when combined with other signals.

Do not assume insider buying is automatically bullish.

---

# 15. SHORT INTEREST

Where reliable data is available:

* short interest
* changes in short interest
* short interest relative to free float
* short interest acceleration
* changes around major price movements

Investigate whether short positioning interacts with:

* social attention
* volume
* price momentum
* news
* sentiment

For example, determine whether certain combinations resemble potential short squeezes.

---

# 16. OWNERSHIP & INSTITUTIONAL ACTIVITY

Where reliable data is available, investigate:

* ownership changes
* institutional ownership
* institutional buying/selling
* major shareholder changes
* free float changes
* insider ownership changes

The objective is to understand:

> Who is buying, who is selling, and how the ownership structure is changing?

This may help distinguish retail-driven attention from institutional accumulation.

---

# 17. EARNINGS CALLS & MANAGEMENT COMMUNICATION

Where transcripts or reliable data are available, analyze:

* management tone
* confidence
* uncertainty
* changes in language
* guidance
* discussion of future opportunities
* discussion of risks
* changes in management narrative
* language compared with previous calls

Do not only classify the call as positive/negative.

Look for:

> What changed in management's communication?

---

# 18. NARRATIVE DETECTION

Narrative analysis is a core part of the project.

The system should attempt to identify the STORY forming around a company.

Example:

Previous narrative:

> "Turnaround company."

New narrative:

> "AI infrastructure company."

The system should identify:

* current narrative
* previous narrative
* new narrative
* narrative novelty
* narrative growth
* narrative acceleration
* number of people discussing it
* spread across platforms
* whether the narrative is supported by new information
* whether the narrative is speculative
* whether the narrative appears early or mature

The goal is not simply to classify sentiment.

The goal is to understand:

> "What story are people beginning to believe?"

---

# 19. HYPE CYCLE

The system should investigate whether market attention moves through stages such as:

1. Low attention
2. Early discovery
3. Accelerating attention
4. Rapid hype
5. Mass attention
6. Hype exhaustion
7. Potential reversal

We are particularly interested in:

> Stage 2 → Stage 3

However, the system must learn whether these stages actually exist and whether they have predictive value.

Do not hard-code assumptions without testing them.

---

# 20. SIGNAL INTERACTION

A major objective is to determine whether combinations of signals are more informative than individual signals.

For example:

Volume alone:
weak relationship.

Google search acceleration alone:
weak relationship.

Social acceleration alone:
weak relationship.

But:

> Volume acceleration + search acceleration + new social participants + narrative change

may potentially be much stronger.

The system should investigate interactions between:

* price
* volume
* attention
* social activity
* news
* sentiment
* narrative
* analyst activity
* insider activity
* ownership
* short interest

---

# 21. FIRST RESEARCH QUESTION

The first major experiment should investigate:

> "What signals tend to appear 1–4 weeks before a Nordic small-cap rises at least 50% within approximately 30–90 days?"

We should identify historical examples and compare them against appropriate control observations.

Do not cherry-pick famous winners.

The analysis must use the full available universe according to predefined rules.

---

# 22. STATISTICAL BASELINE

Before using advanced AI or machine learning, establish a statistical baseline.

For every historical observation calculate:

* features available at that time
* future returns
* future volatility
* maximum forward return
* maximum drawdown

Then investigate relationships such as:

* relative volume vs future return
* search acceleration vs future return
* social acceleration vs future return
* sentiment change vs future return
* narrative change vs future return
* combinations of these variables

Compare signals against appropriate control groups.

Example:

If a signal produces +50% within 90 days in 8% of cases, determine what percentage of comparable non-signal observations did the same.

Do not call a signal predictive without statistical evidence.

---

# 23. MACHINE LEARNING

Machine learning should come AFTER the statistical baseline.

The purpose of ML is to identify complex interactions that may not be obvious from simple analysis.

Potential models:

* logistic regression
* random forest
* gradient boosting
* XGBoost
* LightGBM
* other appropriate models

Start with simple models.

Compare complex models against simple baselines.

Do not assume that more complex = better.

The model should output probabilities or rankings where appropriate rather than pretending to know the future.

---

# 24. LLM / AI ROLE

LLMs should primarily handle unstructured information.

Good uses:

* news analysis
* sentiment analysis
* narrative detection
* narrative comparison
* forum summarization
* catalyst classification
* detecting changes in language
* clustering similar narratives
* identifying emerging themes
* identifying whether discussion appears speculative
* analyzing earnings-call language

LLMs should NOT invent quantitative patterns.

For example:

An LLM may say:

> "Discussion increasingly connects this company with AI infrastructure."

But it must NOT claim:

> "AI narratives cause stocks to rise 35%."

unless the actual research database supports that conclusion.

Quantitative claims must come from the database and statistical analysis.

---

# 25. AI SHOULD ANALYZE PEOPLE, NOT JUST COMPANIES

This is a fundamental principle.

The system should attempt to model the behavior of market participants.

Examples:

* What are people searching for?
* What are people discussing?
* What are people becoming excited about?
* What are people afraid of?
* How many people are joining the discussion?
* How quickly is information spreading?
* Are opinions converging?
* Are opinions becoming more extreme?
* Are people changing their beliefs?
* Is a new narrative forming?
* Is the narrative spreading from one platform to another?
* Is attention moving from niche communities toward mainstream audiences?

The company is the object.

The market participants are the behavioral data.

---

# 26. IMPORTANT DISTINCTION: DISCOVERY VS HYPE

The system must distinguish between:

### Early discovery

Attention is low but accelerating.

### Emerging narrative

A new story begins spreading.

### Accelerating hype

Attention, price and volume begin accelerating together.

### Mature hype

Attention is extremely high and the narrative is already widely known.

### Hype exhaustion

Attention remains high but momentum and engagement begin deteriorating.

We should investigate which stages historically have the best risk/reward and predictive characteristics.

Do not assume the answer beforehand.

---

# 27. DATA TIMING

This is CRITICAL.

Every piece of information must have an accurate timestamp where possible.

The system must simulate what an investor could actually have known at a specific point in time.

For example:

If an earnings release was published at 16:30, it must not be treated as available before 16:30.

If a social-media post was created after the market moved, it cannot be used to predict the earlier move.

Avoid:

* look-ahead bias
* survivorship bias
* data leakage
* hindsight bias
* data snooping
* overfitting

Historical features must only contain information available at the prediction timestamp.

---

# 28. HYPOTHESIS GENERATION VS HYPOTHESIS TESTING

These must be separated.

## Hypothesis generation

We can explore data and use AI to suggest:

> "This combination might be interesting."

## Hypothesis testing

We then test the hypothesis on data that was not used to discover it.

Never declare a pattern real simply because it worked in exploratory analysis.

The system should encourage falsification.

If a hypothesis does not work, record that result.

Failed hypotheses are valuable research information.

---

# 29. OUT-OF-SAMPLE TESTING

Whenever possible:

* split historical data chronologically
* use earlier data for discovery/training
* use later data for validation/testing

Do not randomly mix future observations into training and test sets when that would create unrealistic information flow.

For time-series problems, chronological validation is preferred.

---

# 30. HISTORICAL PREDICTION DATABASE

Every generated signal should be saved.

Example:

DATE:
2025-04-12

TICKER:
ABC

SIGNAL:
Attention acceleration

FEATURES:

Relative volume = 3.4x
Search acceleration = +145%
Social acceleration = +210%
Sentiment change = +31
Narrative change = detected

SIGNAL SCORE:
82

Then record:

+5D:
+8.2%

+20D:
+27.4%

+30D:
+35.1%

+60D:
+41.8%

+90D:
+53.2%

This allows us to evaluate the system honestly.

---

# 31. DISCOVERY SCORE

Eventually we may create a composite score such as:

* price acceleration
* volume acceleration
* search acceleration
* social acceleration
* news acceleration
* sentiment change
* narrative change
* new participants
* analyst activity
* insider activity
* short-interest changes
* ownership changes

However:

DO NOT arbitrarily assign weights.

Weights should be derived through research, statistical analysis or machine learning.

The score should be validated out-of-sample.

---

# 32. DATA ARCHITECTURE

Build the project modularly.

Separate:

1. Data ingestion
2. Raw data storage
3. Data cleaning
4. Feature engineering
5. Signal generation
6. Statistical analysis
7. Backtesting
8. Machine learning
9. LLM analysis
10. Reporting/dashboard

New data sources should be easy to add or replace.

---

# 33. DATABASE

Use a proper database.

Do not rely on a collection of disconnected CSV files as the primary database.

The database should preserve:

* timestamps
* ticker
* company
* source
* raw observations
* processed features
* generated signals
* model outputs
* historical outcomes

The system should make it possible to reproduce how a signal was generated.

---

# 34. DATA SOURCE REQUIREMENTS

Before implementing expensive data sources, research:

* availability
* historical depth
* API access
* API limits
* cost
* licensing
* reliability
* timestamp accuracy
* ability to store historical data
* whether commercial use is allowed

Potential categories:

* market data providers
* financial APIs
* news APIs
* Google/search data
* Reddit APIs
* Stocktwits
* X/Twitter
* Nordic forums
* insider data
* ownership data
* short-interest data
* analyst data

Do not assume a data source is free simply because the website is publicly accessible.

Do not violate terms of service or scrape data where prohibited.

---

# 35. COST PHILOSOPHY

Do not purchase expensive subscriptions immediately.

The initial objective is a low-cost research prototype.

First determine which data is genuinely necessary.

Use free or inexpensive sources where appropriate.

Only pay for higher-quality data when it materially improves the research.

The system should be designed so expensive data sources can be added later.

---

# 36. MVP DEVELOPMENT PLAN

Do NOT build the entire system immediately.

## Version 0.1 — Market baseline

Build:

* Nordic small-cap universe
* historical prices
* historical volume
* market capitalization
* basic features
* future-return targets
* database
* statistical analysis
* basic backtesting

Goal:

Determine whether simple price/volume behavior contains useful information.

---

## Version 0.2 — Attention

Add:

* Google/search activity
* search acceleration
* abnormal search activity

Goal:

Determine whether attention adds information beyond price and volume.

---

## Version 0.3 — News

Add:

* news frequency
* news acceleration
* sentiment
* catalyst classification
* market reaction

Goal:

Understand whether changes in news flow add information.

---

## Version 0.4 — Social & forums

Add:

* mentions
* unique participants
* new participants
* engagement
* sentiment
* discussion acceleration

Goal:

Measure changes in market participation and opinion.

---

## Version 0.5 — Narratives

Add LLM analysis for:

* narrative detection
* narrative changes
* emerging themes
* narrative spread
* hype stage

Goal:

Understand what people are beginning to believe.

---

## Version 0.6 — Expectations

Add where data allows:

* analyst estimates
* estimate revisions
* target-price revisions
* valuation expectations
* insider activity
* short interest
* ownership changes
* institutional activity
* earnings-call analysis

Goal:

Understand the relationship between market expectations and market behavior.

---

## Version 0.7 — Machine learning

Use historical features to train models.

Goal:

Determine whether combinations of signals can improve predictive performance out-of-sample.

---

## Version 1.0 — Live Discovery Scanner

The system should eventually scan the Nordic small-cap universe and identify companies experiencing unusual changes in:

* price
* volume
* search activity
* social activity
* news
* sentiment
* narratives
* expectations

The output should be a ranked list of potential discoveries, NOT guaranteed predictions.

---

# 37. EXAMPLE FINAL OUTPUT

A future version of the system could produce something like:

## DISCOVERY ALERT

### Company X

**Price momentum**
+11.4% / 5D

**Relative volume**
4.6x

**Google attention**
+184%

**Social mentions**
+312%

**New participants**
+241%

**News frequency**
+180%

**Sentiment change**
+28 points

**Narrative change**
Detected

**Emerging narrative**
"AI infrastructure"

**Narrative novelty**
91/100

**Hype stage**
Early → Accelerating

**Historical analogues**
63

**Historical outcome after similar signals**

+10% / 5D:
38%

+25% / 30D:
21%

+50% / 90D:
9%

The system should also explain:

> Why this company is being flagged.

> Which signals are unusual.

> Which signals historically matter.

> What the market appears to believe.

> What expectations appear to be priced in.

> Whether the current situation resembles early discovery, accelerating hype or mature hype.

This output must be based on actual database evidence.

---

# 38. THE ULTIMATE RESEARCH QUESTION

The project ultimately seeks to answer:

> "Can we systematically detect when market psychology, attention and expectations around a Nordic small-cap company begin to change before a major price movement occurs?"

And more specifically:

> "Can measurable changes in investor behavior 1–4 weeks before a major move provide statistically significant information about the probability and magnitude of that future move?"

We do not assume the answer is yes.

The purpose of the project is to find out.

---

# 39. FIRST TASK FOR CLAUDE CODE

DO NOT immediately build the complete application.

First:

1. Analyze this specification.
2. Identify ambiguities and potential problems.
3. Propose the technical architecture.
4. Propose the database schema.
5. Identify the minimum viable data sources.
6. Identify free vs paid sources.
7. Identify the historical depth available from each source.
8. Identify licensing and usage limitations.
9. Identify which data sources are hardest to obtain historically.
10. Explain which data sources are essential for MVP and which can wait.
11. Design the initial research pipeline.
12. Design the first statistical experiment.
13. Explain how to avoid look-ahead bias and survivorship bias.
14. Create the project structure.
15. Create CLAUDE.md containing the project's core rules.
16. Do not implement expensive APIs yet.
17. Do not implement advanced AI yet.
18. Do not create arbitrary scoring weights.
19. Do not claim that any signal is predictive before testing it.
20. Present the proposed architecture and MVP plan before writing significant amounts of code.

The development philosophy is:

> Reliable data → behavioral measurements → statistical evidence → machine learning → LLM interpretation → live discovery scanner.

The core philosophy is:

> **We are not trying to predict the future with magic AI. We are trying to measure changes in human behavior and market expectations, discover recurring patterns, and test whether those patterns contain useful information about future price movements.**