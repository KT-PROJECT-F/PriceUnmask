# PriceUnmask roadmap: v1.1 and v2.0

Status: active plan, written 2026-11-03 after v1.0 shipped (tag `v1.0`, commit `ca674da6`). This file is the durable record of the plan; it does not depend on any external tool or conversation to stay available. Update the tracking table below as issues close — do not let this page go stale.

## Where v1.0 leaves us

v1.0 shipped 2026-11-03: tag `v1.0` on commit `ca674da6`, merged via PR #218 (`dev` → `main`, non-squashed). Fresh-clone verification was clean: `ruff check` and `ruff format --check` pass, 346 tests pass.

Confirmed working end to end: a scraper against one site (books.toscrape.com), a scheduler running every 4 hours, append-only SQLite history, a FastAPI `/api`, a rule-based Trust Score (5 signals, 4 labels plus `no_discount`), rolling z-score anomaly detection, and a dashboard with grid, chart, and badges.

**The one gap that matters most:** across more than three weeks of live collection, the collector never once observed a price change or a recorded original price. Both design-note analyses (`docs/design/anomaly_findings.md`, `docs/design/trust_score_findings.md`), each covering 20 products and 700+ snapshots, found zero flagged snapshots and zero products with any discount claim. Every product scored `genuine`/100 or "not flagged" by default — not because the model is good, but because the one thing it exists to catch, a fake discount, has never once appeared in front of it. The product's actual job has not yet been exercised.

Collector reliability is also still an open problem structurally, not just a one-off: two multi-day outages happened in a single pilot month (24–26 Oct, and 30 Oct–2 Nov, the second one spanning the live demo itself), both from a personal laptop sleeping, and both were only caught by cross-checking the database by hand against a written log. The second outage was initially misreported as "no gap, ran throughout demo day" before the real database record corrected it (see issue #155's full thread for that history — worth reading as a case study in verifying claims against evidence, not taking a status report at face value).

## v1.1 — Stabilization

Make what already exists trustworthy and self-monitoring before building anything new on top of it.

- **Real discount data (highest priority).** Add or switch to a source with prices that actually change and carry discount claims — books.toscrape.com's fixed catalog has made this impossible to test. The schema already supports it: `products.source` plus `external_id` unique per source. Without this, Trust Score and the anomaly detector stay unvalidated no matter what else ships.
- **Collector reliability.** Move off a personal laptop onto something that can't sleep: a scheduled GitHub Actions workflow is the lowest-cost option (free, no infra, runs on a cron, can commit or export snapshots), or a small always-on VM. This removes the single point of failure behind both outages this month.
- **Automated health alerting.** Replace the manual "post a morning check-in comment" process with a job that runs `check_db` on a schedule and posts or alerts automatically when the latest run is older than expected. The manual version already failed once — missed days, then a mislabeled catch-up comment presented as healthy when it wasn't. Automating the check removes that human-reliability gap entirely.
- **API hardening**, per `docs/design/api.md`: a standardized error-response schema across endpoints, clearer scrape-progress reporting than polling `/api/scrape-runs`, and expanded contract tests as the API grows.
- **DB hardening**, per `docs/design/database.md`: integration tests for concurrent writes (collector writing while the API reads), and a deliberate SQLite-vs-server-database decision once real collection volume is known, not before.

**Status (12 November 2026):** all v1.1 issues are closed (see Tracking). The real-discount source from #223 has landed, but the Trust Score has still not been validated against real discounts.

## v2.0 — Growth

Once v1.1's real data and reliability work have landed, grow the product itself.

- **Multi-site scraping.** Generalize `scraper/` into a source-adapter pattern: one module per site behind the existing `ScrapedProduct` contract. The schema already allows multiple sources per product, so this is additive, not a rewrite — and it further diversifies the data Trust Score and the anomaly detector see.
- **ML anomaly detection.** Upgrade from rolling z-score to IsolationForest. This is already the documented next step in `docs/design/anomaly.md`; it was deliberately deferred until there is real changing-price history to train and validate against, which is exactly what v1.1 is meant to produce.
- **Shopper-facing features.** Watchlists (save a product), price-drop notifications, category or trend views across products. None of this exists today — the app is currently a read-only dashboard with no accounts.
- **Production deployment.** Move off local `uvicorn --reload` to a real host with a process supervisor and a CI/CD deploy step. Revisit the SQLite-vs-server-database decision from v1.1 once there is an actual place to deploy to.

**Status (12 November 2026):**

- Multi-site scraping: source adapters landed in #241 (PR #249). Collecting every configured source in one run is #254 (PR #260, in review). A second source is not approved yet; see `docs/shop-evaluation.md`.
- ML anomaly detection: #257 turned this into a comparison on synthetic fixtures. The decision (PR #258) is to keep the rolling z-score detector until real price-change data exists.
- Shopper-facing features: watchlist, price-drop alerts and trend views landed under #243 (PRs #248, #246, #262). The price-position summary is #256 (PR #261, in review).
- Production deployment: on 10 November #244 was rescoped, because the team has no host. v2.0 is made deploy-ready and proven on an Ubuntu 24.04 Linux VM. The SSH deploy workflow stays switched off until a real host exists (PRs #251, #252, in review). v2.0 is not publicly deployed.


## Architecture changes needed

- **Source adapter pattern.** Split `scraper/` into per-site submodules that share the existing `ScrapedProduct` dataclass contract, plus a lightweight site registry so the scheduler can run N sources instead of one. No schema change required — `products.source` already exists for exactly this.
- **Notification channel.** v1.1's automated alerting and v2.0's price-drop notifications both need one delivery mechanism. Start minimal — a GitHub issue/comment bot or plain email — rather than building full infra, consistent with this project's existing "no framework unless needed" approach (see `docs/design/frontend.md`).
- **DB scaling decision.** Already flagged in `docs/design/database.md`: SQLite write concurrency and database growth as multi-site collection increases volume. Decide server database (e.g. Postgres) vs. staying on SQLite once v1.1's real volume is known — not speculatively now.
- **Accounts and auth.** Needed only if watchlists ship in v2.0. Leave it out of scope until that feature is actually being built; building it ahead of a concrete need adds complexity with nothing yet to justify it.

## Risks

- The core scoring logic has never seen a real discount or a real price move. v1.1 must fix this before v2.0 adds anything on top of it.
- Collector failures have twice gone unnoticed until someone checked by hand, including on the actual demo day. v1.1's monitoring work targets this directly.
- Don't let v2.0 start early. An unvalidated foundation stays unvalidated no matter how much is built on it.
- A Linux VM deployment demonstrates deployment readiness but does not establish that the application is publicly hosted or available through a production URL.
- A second site's robots.txt and Terms review must not be treated as permission to scrape or retain page fixtures unless the required approval is established.

## Tracking

Issues filed 2026-11-03. Update the checkboxes as they close — this table is the source of truth for plan status, not any external tool.

### Dashboard redesign (parallel track, independent of v1.1 stabilization)

- [x] #220 — `docs/design/DESIGN.md` spec (merged)
- [x] #221 — frontend: implement the dashboard redesign — @Kanamarlapudipk — PR #233

### v1.1 — Stabilization (complete)

- [x] #222 — scheduler: move the collector off a personal laptop and automate health alerting — @Saidivya-20 — PR #232
- [x] #223 — scraper: add a source with real price changes and discount claims — @Naveen5901 — PR #236 (source landed; real-price validation still limited)
- [x] #224 — api: standardize error responses and scrape-progress reporting — @rajeshkandlapalli-glitch — PR #234
- [x] #225 — db: concurrent-write integration tests and a SQLite-vs-server-DB decision — @Hemalatha1729 — PR #235
- [x] #226 — analysis: re-validate Trust Score and anomaly detection against real data — @sujithareddy-1324 — closed with interim findings in commit `739d92f`; real-data validation still outstanding
- [x] #227 — docs: v1.1 release verification pass — @mathango — PR #239
- [x] #228 — docs: document the real limitations found this cycle — @lakshmiprasanna45 — PR #231

### v2.0 — Growth (in progress)

- [ ] #229 — backlog tracker — @yaswanthtechie — open; split into the issues below
- [ ] #241 — scraper: multi-site source-adapter pattern — @mathango, @Naveen5901 — PR #249 merged; second-site Terms decision pending
- [x] #242 — analysis: validate anomaly detection against synthetic price fixtures — @sujithareddy-1324 — PR #247
- [ ] #243 — frontend: shopper-facing features (watchlists, price-drop notifications, trend views) — @Kanamarlapudipk, @lakshmiprasanna45, @rajeshkandlapalli-glitch — PRs #248, #246, #262 merged
- [ ] #244 — setup: production deployment (host, process supervisor, CI/CD deploy step) — @Hemalatha1729, @Saidivya-20 — PRs #251, #252 in review
- [x] #253 — docs: bring the v2.0 tracking up to date and record the second site's evidence — @mathango — PR #259
- [ ] #254 — scraper: collect every configured source in one run — @Naveen5901 — PR #260 in review
- [x] #255 — frontend: use the price-drop and trend endpoints instead of the JS copy — @Kanamarlapudipk — PR #262
- [ ] #256 — analysis: price-position summary (how close to the lowest price) — @lakshmiprasanna45 — PR #261 in review
- [x] #257 — analysis: compare IsolationForest with the z-score detector on synthetic fixtures — @sujithareddy-1324 — PR #258