MARC AI — CHANGES & ADDITIONS ONLY

Purpose of this document
This file contains ONLY proposed changes and additions to the existing Marc AI specification. It is not a rewritten or merged version of the original project document.

==================================================
1. REDEFINE THE LONG-TERM GOAL: FROM SHORT-TERM EXPLOSIVE MOVES TO POTENTIAL 5X–10X+ OUTCOMES
==================================================

The current project already studies large price movements such as +50% within 30–90 days. That should remain an important research target, but it should no longer be treated as the ultimate objective.

Add a second, more ambitious long-term objective:

> Identify small-cap companies that may be at the beginning of a structural rerating capable of producing 5x–10x+ returns over a multi-year horizon.

The purpose is not to assume that any company will become a 10x investment. The purpose is to detect when a company may be transitioning from being misunderstood, ignored or narrowly valued into being recognized as something substantially larger.

The core long-term research question should become:

> Can measurable changes in market psychology, expectations, attention, fundamentals and narrative help identify companies at the beginning of a multi-year rerating that may ultimately produce 5x–10x+ returns?

Shorter-horizon targets such as +50% within 30–90 days should be treated as early validation targets and potential signs that the system can detect the beginning of larger repricing processes.

==================================================
2. ADD A MULTIBAGGER / STRUCTURAL RERATING ENGINE
==================================================

Create a separate research layer focused specifically on distinguishing short-term speculative moves from genuine long-term rerating candidates.

The system should distinguish between:

A. Explosive move
Example:
100 → 150 within a few months

B. Structural rerating
Example:
100 → 150 → 220 → 400 → 700 → 1000 over a longer period

The system should investigate which early signals historically separate these two patterns.

Potential Multibagger Engine inputs:

* narrative expansion
* addressable market expansion
* revenue scalability
* margin scalability
* business-model operating leverage
* recurring revenue potential
* evidence of product-market fit
* repeat customers
* order size progression
* customer quality
* contract progression
* international expansion potential
* management execution
* balance-sheet capacity
* dilution risk
* capital intensity
* competitive advantage
* technology differentiation
* strategic importance of the product/service
* industry tailwinds
* institutional awareness
* analyst awareness
* valuation relative to plausible future scale
* market-cap asymmetry
* expectation gap

The objective is to ask:

> Is this merely a stock experiencing temporary excitement, or is the market beginning to revalue what the company could fundamentally become?

==================================================
3. ADD EXPECTATIONS RUNWAY
==================================================

Create a concept called EXPECTATIONS RUNWAY.

Definition:

> How much room is left for the market's expectations about a company to rise?

A company may have excellent fundamentals but limited expectations runway if the market already assumes exceptional future growth.

Another company may have weaker current fundamentals but large expectations runway if investors still price it as a small, niche or low-growth business while evidence increasingly supports a much larger future opportunity.

Potential inputs:

* current valuation
* consensus revenue estimates
* consensus earnings estimates
* target prices
* implied growth assumptions
* current dominant narrative
* institutional ownership
* analyst coverage
* social/media awareness
* current market capitalization
* plausible future revenue scenarios
* plausible future margin scenarios

Potential output:

EXPECTATIONS RUNWAY:
Low / Medium / High / Very High

The system should attempt to estimate:

> How much of the potential future story is already reflected in today's expectations?

==================================================
4. ADD MARKET-CAP ASYMMETRY
==================================================

Create a dedicated feature measuring the relationship between current market capitalization and plausible future business scale.

Example:

Current market cap: 600 MSEK
Potential long-term revenue opportunity: several billion SEK
Addressable market: tens of billions SEK

This may represent substantially more asymmetry than a company already valued at tens of billions.

The system should not treat total addressable market as guaranteed revenue.

Instead, investigate:

* current market cap
* current revenue
* plausible revenue scenarios
* gross-margin potential
* operating-margin potential
* capital requirements
* dilution requirements
* market size
* market growth
* realistic market-share scenarios

Potential metric:

MARKET-CAP ASYMMETRY SCORE

Weights must not be assigned arbitrarily. Any composite score should be research-derived.

==================================================
5. ADD EVIDENCE ACCUMULATION / THESIS MATURATION
==================================================

Create a system that tracks whether a company's investment thesis is becoming progressively stronger or weaker over time.

Example progression:

Technology developed
→ pilot project
→ first commercial customer
→ repeat order
→ larger contract
→ second major customer
→ international customer
→ growing backlog
→ analyst coverage begins
→ institutional ownership increases

The system should treat this as an evidence chain rather than isolated announcements.

For each company, track:

* thesis-supporting events
* thesis-weakening events
* evidence quality
* evidence magnitude
* evidence novelty
* whether evidence is independent or repetitive
* time between milestones
* whether commercial validation is accelerating

Potential output:

THESIS MATURITY
Stage 1 — Concept
Stage 2 — Early validation
Stage 3 — Commercial proof
Stage 4 — Scaling evidence
Stage 5 — Broad market recognition

The stage definitions should ultimately be validated against historical examples rather than hard-coded as predictive truths.

==================================================
6. ADD A COMPANY EVENT TIMELINE
==================================================

Every company should have a unified chronological event timeline.

The timeline should combine all major data categories in one place.

Example:

4 March
Insider purchase

7 March
Google attention +41%

9 March
Forum participation +74%

11 March
New narrative detected

14 March
Relative volume = 2.8x

18 March
Major contract announcement

20 March
Stock +18%

The purpose is to make it possible to study the actual sequence of events.

The timeline should contain:

* timestamp
* event type
* source
* raw observation
* processed feature
* market price at event time
* market reaction after event
* narrative state at event time
* attention state at event time

This should help answer:

> What changed first?

==================================================
7. ADD INFORMATION DIFFUSION ANALYSIS
==================================================

The current system measures narrative spread across platforms. Expand this into a dedicated INFORMATION DIFFUSION layer.

The goal is to understand how a story moves through the market.

Example progression:

Stage 1 — niche stock forum
Stage 2 — specialist investors
Stage 3 — finance social media
Stage 4 — wider retail audience
Stage 5 — financial media
Stage 6 — mainstream awareness

Investigate:

* where a narrative first appeared
* which platform picked it up next
* time between platform transitions
* number of new participants at each stage
* changes in language as the narrative spreads
* whether the narrative becomes simplified or exaggerated
* whether institutional/news coverage follows retail attention or leads it

Potential feature:

NARRATIVE DIFFUSION VELOCITY

Example:

Forum → X/Twitter: 3 days
X/Twitter → finance media: 6 days
Finance media → mainstream retail: 4 days

Research question:

> Do rapidly spreading narratives have different forward-return characteristics from slowly spreading narratives?

==================================================
8. MAKE NEW INVESTOR INFLUX A FIRST-CLASS FEATURE
==================================================

The current specification already distinguishes unique authors and new authors. Elevate this into a major research category.

Create features such as:

* new participant count
* new participant growth
* new participant share
* returning participant count
* returning participant share
* first-time poster acceleration
* cross-platform new participant growth

Example:

Total comments: +40%
Existing posters: +14%
New posters: +230%

This may contain more information than total activity alone.

The system should investigate whether a company is being discussed mainly by existing shareholders or being discovered by entirely new groups of investors.

Potential metric:

NEW INVESTOR INFLUX
Low / Moderate / Accelerating / Extreme

==================================================
9. ADD NARRATIVE → PRICE LEAD/LAG ANALYSIS
==================================================

Create a dedicated module for determining whether narrative and attention changes tend to lead or follow price moves.

Example A:

Narrative change
→ search acceleration
→ new participants
→ volume acceleration
→ price breakout

This may represent early discovery.

Example B:

Price +40%
→ social mentions explode
→ narrative appears

This may represent late-stage explanation or hype rather than early information.

For each narrative shift, calculate where possible:

* time from narrative shift to price move
* time from attention acceleration to price move
* time from news event to narrative shift
* time from price move to social acceleration
* time from price move to search acceleration

Potential output:

NARRATIVE LEAD/LAG
Narrative leads price by 6 days
Price leads narrative by 2 days
Simultaneous
Unclear

This should be treated as a historical research feature, not assumed predictive.

==================================================
10. ADD MARC MEMORY — LONGITUDINAL COMPANY NARRATIVE HISTORY
==================================================

Create a persistent company-level memory system.

For every company, Marc should preserve historical descriptions of:

* dominant narrative
* secondary narratives
* investor concerns
* investor expectations
* management messaging
* analyst framing
* perceived catalysts
* perceived risks
* hype stage
* institutional awareness

Example:

2022
"Space edge computing"

2024
"Turnaround"

2025
"Defense / ISR"

2026
"European sovereign space infrastructure"

Marc should be able to compare today's market language against previous months and years.

Core questions:

* What does the market believe today?
* What did it believe 3 months ago?
* What did it believe 12 months ago?
* What changed?
* Which words or themes are new?
* Which old narratives disappeared?
* Is the current narrative broader or narrower than before?

The purpose is to make narrative detection longitudinal rather than isolated.

==================================================
11. ADD STRUCTURAL RERATING STAGES
==================================================

In addition to the existing hype-cycle stages, introduce a separate STRUCTURAL RERATING framework.

Potential research stages:

Stage 0 — Ignored / misunderstood
Stage 1 — Early evidence
Stage 2 — Emerging thesis
Stage 3 — Commercial validation
Stage 4 — Expectations expansion
Stage 5 — Institutional recognition
Stage 6 — Broad market recognition
Stage 7 — Mature expectations

Important:

These stages should initially be descriptive research labels only.

Do not assume that progressing through these stages predicts positive returns.

The purpose is to investigate whether historical 5x–10x stocks showed recurring sequences before major reratings.

==================================================
12. ADD HISTORICAL MULTIBAGGER RESEARCH
==================================================

Create a dedicated historical study of Nordic small-cap companies that achieved very large long-term returns.

Potential historical targets:

* +100% within 1 year
* +200% within 2 years
* +300% within 3 years
* +500% within 5 years
* +1000% within 5–10 years

For each historical multibagger, analyze what was visible BEFORE the majority of the return occurred.

Potential questions:

* What was the company's market cap at the beginning?
* What did investors believe about the company then?
* What was the dominant narrative?
* How much analyst coverage existed?
* How much institutional ownership existed?
* Was attention low?
* Were fundamentals already improving?
* Was the addressable market being redefined?
* Did management communication change?
* Did revenue growth accelerate?
* Did margins improve?
* Did order size or customer quality improve?
* Was there a sequence of commercial validation?
* When did mainstream awareness appear?

Then compare multibaggers against companies that appeared similar but failed.

This control group is essential.

The system should research:

> What separated genuine long-term reratings from temporary small-cap hype?

==================================================
13. ADD FALSE-POSITIVE / FAILED-THESIS DATABASE
==================================================

Do not only study winners.

Create a dedicated database of companies that displayed apparently attractive early signals but failed to become major winners.

Examples:

* strong narrative but no revenue
* high attention but repeated dilution
* major TAM but no competitive advantage
* contract hype without repeat orders
* management promises without execution
* large price move followed by collapse
* strong retail interest but no institutional adoption

The purpose is to identify what KILLS a potential multibagger thesis.

Potential output:

MULTIBAGGER FAILURE FACTORS

* dilution pressure
* weak balance sheet
* customer concentration
* lack of repeat business
* poor gross margins
* capital intensity
* management credibility deterioration
* regulatory dependency
* technological obsolescence
* hype running ahead of evidence

This is equally important as identifying positive signals.

==================================================
14. ADD A SEPARATE "10X CANDIDATES" VIEW IN THE WEB APP
==================================================

In addition to short-term discovery alerts, the future web app should contain a separate long-horizon research view.

Example:

MARC — 10X CANDIDATES

Company A
Multibagger Research Score: 87/100
Narrative stage: Early
Attention: Accelerating
Expectations runway: Very High
Fundamental optionality: High
Evidence trend: Strengthening
Institutional awareness: Low
Market-cap asymmetry: High
Rerating stage: 1 / 7

MARC THESIS

"The market currently values the company primarily as X, while emerging evidence increasingly supports a potential transition toward Y. Investor awareness remains limited and current expectations appear below the scenario implied by recent commercial developments."

Important:

Any eventual score should be based on historical evidence or models. Do not manually invent weights.

==================================================
15. ADD A "WHY COULD THIS BECOME MUCH BIGGER?" ANALYSIS
==================================================

For every long-horizon candidate, Marc should explicitly answer:

* What is the company today?
* What could the company become?
* What would have to be true for that transformation to happen?
* What evidence supports that scenario?
* What evidence contradicts it?
* What milestones would validate the thesis?
* What milestones would break the thesis?
* How large could the business plausibly become?
* How much does the market already expect?
* What is the biggest bottleneck?

This is different from predicting a target price.

The goal is to map the possible transformation path.

==================================================
16. ADD THESIS BREAKERS / INVALIDATION CONDITIONS
==================================================

Every candidate should have explicit thesis invalidation conditions.

Examples:

* no commercial follow-through after pilot projects
* shrinking backlog
* repeated capital raises without progress
* customer losses
* falling gross margins
* technology fails to scale
* narrative grows while evidence deteriorates
* management repeatedly misses guidance
* new competition destroys differentiation

Potential output:

THESIS STATUS
Strengthening / Stable / Weakening / Broken

This makes Marc useful not only for discovery but also for continuously re-evaluating whether the reason for owning or studying a company still exists.

==================================================
17. ADD MULTI-HORIZON MODEL OUTPUTS
==================================================

The system should not force one model to answer every question.

Separate outputs may eventually include:

SHORT-TERM DISCOVERY
Probability / ranking for unusual move within 5–90 days

MEDIUM-TERM RERATING
Probability / ranking for substantial repricing over 6–24 months

LONG-TERM MULTIBAGGER RESEARCH
Ranking of companies exhibiting characteristics historically associated with exceptional multi-year winners

The features and models for these horizons may be very different.

A social-media acceleration signal may matter more for short-term discovery, while revenue scalability and evidence accumulation may matter much more for long-term multibaggers.

==================================================
18. ADD A CLEARER PRODUCT DEFINITION
==================================================

Proposed long-term product definition:

> Marc AI is a market-intelligence and research platform designed to detect when investor expectations, attention, narratives and company evidence begin to change around Nordic small-cap companies.

> Its short-term research objective is to detect early signs of unusual repricing.

> Its long-term objective is to identify companies that may be at the beginning of a structural rerating capable of producing exceptional multi-year returns, including potential 5x–10x+ outcomes.

Alternative shorter positioning:

> Marc discovers exceptional small-cap companies before the market fully understands what they could become.

==================================================
19. UPDATED ULTIMATE RESEARCH QUESTION
==================================================

Add the following long-term question alongside the existing research questions:

> Can we systematically distinguish temporary hype from the early stages of a genuine structural rerating?

And:

> Do historical multibaggers exhibit measurable combinations of narrative expansion, expectations runway, commercial evidence, attention diffusion, market-cap asymmetry and participant growth before the majority of their long-term returns occur?

And ultimately:

> Can Marc identify companies where the gap between what the company is currently perceived to be and what it may realistically become is unusually large — before that possibility becomes broadly recognized by the market?

==================================================
20. PROPOSED NEW DEVELOPMENT ORDER
==================================================

Do not build all of the above immediately.

Suggested addition to the existing roadmap:

After the core market/attention/news/social/narrative infrastructure is working:

Version 0.8 — Company Memory & Event Timeline

Add:
* unified event timeline
* historical narrative memory
* narrative comparison over time
* evidence tracking

Version 0.9 — Structural Rerating Research

Add:
* expectations runway
* market-cap asymmetry
* evidence accumulation
* rerating stages
* thesis breakers

Version 1.1 — Historical Multibagger Lab

Add:
* historical 2x/3x/5x/10x cohorts
* failed-lookalike control groups
* long-term feature analysis
* multibagger-specific models

Version 1.2 — 10X Candidate Research View

Add:
* ranked long-horizon candidates
* transformation thesis
* thesis validation milestones
* thesis invalidation milestones
* rerating stage
* evidence trend
* expectations runway

==================================================
21. CORE ADDITIONAL PHILOSOPHY
==================================================

Add this principle to the project:

> Marc should not only ask whether a stock may move. It should ask whether the market is beginning to fundamentally change its understanding of what the company could become.

And:

> A temporary price explosion and a genuine 10x rerating are different phenomena. Marc should research the signals that separate them.

And:

> The ultimate opportunity is not simply finding high attention. It is finding expanding evidence, expanding expectations and expanding market perception while the opportunity is still incompletely understood.
