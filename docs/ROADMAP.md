# PriceUnmask roadmap: v1.1 and v2.0

Status: active plan, written 2026-11-03 after v1.0 shipped (tag `v1.0`, commit `ca674da6`). This file is the durable record of the plan; it does not depend on any external tool or conversation to stay available. Update the tracking table below as issues close — do not let this page go stale.

## Where v1.0 leaves us

v1.0 shipped 2026-11-03: tag `v1.0` on commit `ca674da6`, merged via PR #218 (`dev` → `main`, non-squashed). Fresh-clone verification was clean: `ruff check` and `ruff format --check` pass, 346 tests pass.

Confirmed working end to end: a scraper against one site (books.toscrape.com), a scheduler running every 4 hours, append-only SQLite history, a FastAPI `/api`, a rule-based Trust Score (5 signals, 4 labels plus `no_discount`), rolling z-score anomaly detection, and a dashboard with grid, chart, and badges.

**The one gap that matters most:** across more than three weeks of live collection, the collector never once observed a price change or a recorded original price. Both design-note analyses (`docs/design/anomaly_findings.md`, `docs/design/trust_score_findings.md`), each covering 20 products and 700+ snapshots, found zero flagged snapshots and zero products with any discount claim. Every product scored `genuine`/100 or "not flagged" by default — not because the model is good, but because the one thing it exists to catch, a fake discount, has never once appeared in front of it. The product's actual job has not yet been exercised.

Collector reliability is also still an open problem structurally, not just a one-off: two multi-day outages happened in a single pilot month (24–26 Oct, and 30 Oct–2 Nov, the second one spanning the live demo itself), both from a personal laptop sleeping, and both were only caught by cross-checking the database by hand against a written log. The second outage was initially misreported as "no gap, ran throughout demo day" before the real database record corrected it (see issue #155's full thread for that history — worth reading as a case study in verifying claims against evidence, not taking a status report at face value).

## v1.1 — Stabilization

Make what already exists trustworthy and self-monitoring before building anything new on top of it.

### Real discount data

Add a source with changing prices and real discount claims. Books to Scrape provides a fixed catalogue and has not supplied the price changes or discount claims needed to validate the core scoring logic. The existing schema supports multiple sources through `products.source` and `external_id`, with `external_id` unique per source.

The implementation PR for #223 has landed, but real-price validation remains limited. Do not treat the source integration alone as proof that the Trust Score has been validated against real discounts.

### Collector reliability

Move scheduled collection away from a personal laptop so collection is not interrupted when a laptop sleeps or shuts down. Evaluate a reliable scheduled GitHub Actions or Linux VM environment and ensure collector failures can be detected.

### Automated health alerting

Replace manual health check-ins with scheduled database and collector health checks. Use `check_db` to identify collection or database problems and make failures visible rather than relying on someone to inspect the database manually.

### API hardening

Standardize API error responses, add scrape-progress reporting, and strengthen API contract tests. Follow the decisions documented in `docs/design/api.md`.

### Database hardening

Add concurrent-write integration tests and make a deliberate SQLite-versus-server-database decision. Follow the decisions documented in `docs/design/database.md`.

## v2.0 — Growth

Once v1.1's real-data and reliability work have landed, grow the product itself.

### Multi-site scraping

Split `scraper/` into per-site adapters that share the existing `ScrapedProduct` dataclass contract. Add a lightweight site registry so the scheduler can run multiple sources instead of one. The existing `products.source` field supports multiple sources without requiring a schema change.

### ML anomaly detection

Compare IsolationForest with the existing rolling z-score detector. Use synthetic fixtures for controlled comparison while real price-change history remains limited. Evaluate real historical data before relying on ML results in production.

### Shopper-facing features

Explore product watchlists, price-drop notifications, and category or price-trend views. Introduce accounts and authentication only when a feature such as watchlists actually requires them.

### Production deployment

Prepare the application for deployment on an Ubuntu 24.04 Linux VM using WSL2 or VirtualBox. Configure and verify systemd services for the API and collector, health checks, process restart, SQLite backup, and rollback procedures.

Keep the SSH deployment workflow configured but disabled until a real production host is available. Public hosting, a public URL, and live SSH deployment are deferred under the revised scope of issue #244. VM deployment readiness must not be described as a completed public production deployment.

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

Issues filed 2026-11-03. Update this table as issues close. It is the source of truth for plan status; keep it consistent with the current GitHub issue and PR state.

| Issue | Tracking |
|---|---|
| #220 | Dashboard redesign specification — merged |
| #221 | Dashboard redesign implementation — open — @Kanamarlapudipk |
| #222 | PR #232 — @Saidivya-20 |
| #223 | PR #236 — @Naveen5901; implementation landed, but real-price validation remains limited |
| #224 | PR #234 — @rajeshkandlapalli-glitch |
| #225 | PR #235 — @Hemalatha1729 |
| #226 | Interim validation recorded in closure commit `739d92f`; real-data limitation remains |
| #227 | PR #239 — @mathango |
| #228 | PR #231 — @lakshmiprasanna45 |
| #229 | Backlog tracker — @yaswanthtechie; not started, blocked on v1.1 completion |
| #241 | Open — @mathango, @Naveen5901; PR #249 merged, second-site Terms evidence pending |
| #242 | Merged — PR #247 — @sujithareddy-1324 |
| #243 | Open — @Kanamarlapudipk, @lakshmiprasanna45, @rajeshkandlapalli-glitch; PR #248 merged and PR #246 in review |
| #244 | Open — @Hemalatha1729, @Saidivya-20; PRs #251 and #252 in review |
| #254 | Open — @Naveen5901 |
| #255 | Open / blocked — @Kanamarlapudipk |
| #256 | Open — @lakshmiprasanna45 |
| #257 | In review — PR #258 — @sujithareddy-1324 |

## Visual reference

A live design canvas (two mocked-up dashboard screens) exists outside this repo, shared directly with whoever implements #221 — not linked here since it isn't guaranteed to stay reachable long-term. `docs/design/DESIGN.md` is the authoritative, version-controlled spec; treat the canvas as a preview, not the source of truth.
