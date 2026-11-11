# PriceUnmask roadmap: v1.1 and v2.0

Status: active plan, written 2026-11-03 after v1.0 shipped (tag `v1.0`, commit `ca674da6`). This file is the durable record of the plan; it does not depend on any external tool or conversation to stay available. Update the tracking table below as issues close — do not let this page go stale.

## Where v1.0 leaves us

v1.0 shipped 2026-11-03: tag `v1.0` on commit `ca674da6`, merged via PR #218 (`dev` → `main`, non-squashed). Fresh-clone verification was clean: `ruff check` and `ruff format --check` pass, 346 tests pass.

Confirmed working end to end: a scraper against one site (books.toscrape.com), a scheduler running every 4 hours, append-only SQLite history, a FastAPI `/api`, a rule-based Trust Score (5 signals, 4 labels plus `no_discount`), rolling z-score anomaly detection, and a dashboard with grid, chart, and badges.

**The one gap that matters most:** across more than three weeks of live collection, the collector never once observed a price change or a recorded original price. Both design-note analyses (`docs/design/anomaly_findings.md`, `docs/design/trust_score_findings.md`), each covering 20 products and 700+ snapshots, found zero flagged snapshots and zero products with any discount claim. Every product scored `genuine`/100 or "not flagged" by default — not because the model is good, but because the one thing it exists to catch, a fake discount, has never once appeared in front of it. The product's actual job has not yet been exercised.

Collector reliability is also still an open problem structurally, not just a one-off: two multi-day outages happened in a single pilot month (24–26 Oct, and 30 Oct–2 Nov, the second one spanning the live demo itself), both from a personal laptop sleeping, and both were only caught by cross-checking the database by hand against a written log. The second outage was initially misreported as "no gap, ran throughout demo day" before the real database record corrected it (see issue #155's full thread for that history — worth reading as a case study in verifying claims against evidence, not taking a status report at face value).


### v1.1 — Stabilization

Make what already exists trustworthy and self-monitoring before building anything new on top of it.

- [x] #222 — scheduler: move collector off a personal laptop and automate health alerting — @Saidivya-20 — [PR #232](https://github.com/KT-PROJECT-F/PriceUnmask/pull/232)
- [x] #223 — scraper: add a source with real price changes and discount claims — @Naveen5901 — [PR #236](https://github.com/KT-PROJECT-F/PriceUnmask/pull/236)
- [x] #224 — api: standardize error responses and scrape-progress reporting — @rajeshkandlapudi-glitch — [PR #234](https://github.com/KT-PROJECT-F/PriceUnmask/pull/234)
- [x] #225 — db: concurrent-write integration tests and SQLite-vs-server-DB decision — @Hemalatha1729 — [PR #235](https://github.com/KT-PROJECT-F/PriceUnmask/pull/235)
- [x] #226 — analysis: re-validate Trust Score and anomaly detection — @sujithareddy-1324 — closure commit `739d92f` (interim validation; real-data limitation remains)
- [x] #227 — docs: v1.1 release verification pass — @mathango — [PR #239](https://github.com/KT-PROJECT-F/PriceUnmask/pull/239)
- [x] #228 — docs: document the real limitations found this cycle — @lakshmiprasanna45 — [PR #231](https://github.com/KT-PROJECT-F/PriceUnmask/pull/231)

### v2.0 — Growth

Once v1.1's real data and reliability work have landed, grow the product itself.

- [ ] #241 — scraper: multi-site source-adapter pattern — @mathango, @Naveen5901 — **Open** (PR #249 merged; second-site Terms evidence pending review)
- [x] #242 — analysis: validate anomaly detection against synthetic price fixtures — @sujithareddy-1324 — **Merged** (PR #247)
- [ ] #243 — frontend: shopper-facing features (watchlists, price-drop notifications, trend views) — @Kanamarlapudipk, @lakshmiprasanna45, @rajeshkandlapalli-glitch — **Open** (PR #248 merged; PR #246 in review)
- [ ] #244 — setup: production deployment (host, process supervisor, CI/CD deploy step) — @Hemalatha1729, @Saidivya-20 — **Open** (PRs #251 and #252 in review)
- [ ] #254 — scraper: collect every configured source in one run — @Naveen5901 — **Open**
- [ ] #255 — frontend: use analysis API instead of duplicated JavaScript rules — @Kanamarlapudip — **Open / Blocked**
- [ ] #256 — analysis: price-position summary — @lakshmiprasanna45 — **Open**
- [ ] #257 — analysis: compare IsolationForest with z-score — @sujithareddy-1324 — **Open**


## Architecture changes needed

- **Source adapter pattern.** Split `scraper/` into per-site submodules that share the existing `ScrapedProduct` dataclass contract, plus a lightweight site registry so the scheduler can run N sources instead of one. No schema change required — `products.source` already exists for exactly this.
- **Notification channel.** v1.1's automated alerting and v2.0's price-drop notifications both need one delivery mechanism. Start minimal — a GitHub issue/comment bot or plain email — rather than building full infra, consistent with this project's existing "no framework unless needed" approach (see `docs/design/frontend.md`).
- **DB scaling decision.** Already flagged in `docs/design/database.md`: SQLite write concurrency and database growth as multi-site collection increases volume. Decide server database (e.g. Postgres) vs. staying on SQLite once v1.1's real volume is known — not speculatively now.
- **Accounts and auth.** Needed only if watchlists ship in v2.0. Leave it out of scope until that feature is actually being built; building it ahead of a concrete need adds complexity with nothing yet to justify it.

## Risks

- The core scoring logic has never seen a real discount or a real price move. v1.1 must fix this before v2.0 adds anything on top of it.
- Collector failures have twice gone unnoticed until someone checked by hand, including on the actual demo day. v1.1's monitoring work targets this directly.
- Don't let v2.0 start early. An unvalidated foundation stays unvalidated no matter how much is built on it.

## Tracking

Issues filed 2026-11-03. Update the checkboxes as they close — this table is the source of truth for plan status, not any external tool.

### Dashboard redesign (parallel track, independent of v1.1 stabilization)

- [x] #220 — `docs/design/DESIGN.md` spec (merged)
- [ ] #221 — frontend: implement the dashboard redesign — @Kanamarlapudipk

### v1.1 — Stabilization

- [ ] #222 — scheduler: move the collector off a personal laptop and automate health alerting — @Saidivya-20
- [ ] #223 — scraper: add a source with real price changes and discount claims — @Naveen5901
- [ ] #224 — api: standardize error responses and scrape-progress reporting — @rajeshkandlapalli-glitch
- [ ] #225 — db: concurrent-write integration tests and a SQLite-vs-server-DB decision — @Hemalatha1729
- [ ] #226 — analysis: re-validate Trust Score and anomaly detection against real data — @sujithareddy-1324 (blocked on #223)
- [ ] #227 — docs: v1.1 release verification pass — @mathango (blocked on #222, #223, #224, #225)
- [ ] #228 — docs: document the real limitations found this cycle — @lakshmiprasanna45

### v2.0 — Growth (not started)

- [ ] #229 — backlog tracker — @yaswanthtechie (blocked on all v1.1 issues above; not to be broken into separate issues until v1.1 ships)

## Visual reference

A live design canvas (two mocked-up dashboard screens) exists outside this repo, shared directly with whoever implements #221 — not linked here since it isn't guaranteed to stay reachable long-term. `docs/design/DESIGN.md` is the authoritative, version-controlled spec; treat the canvas as a preview, not the source of truth.
