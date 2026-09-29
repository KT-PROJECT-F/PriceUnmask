# Week 1 guide

Week 1 runs from **Wed 30 Sept to Wed 7 Oct**. Working days are Monday to Friday.
**Fri 2 Oct is a holiday** (Gandhi Jayanti): no issue, no PR that day.

This guide covers how you work every day. What to build is in your daily issue. For the full
rules, see [CONTRIBUTING.md](../CONTRIBUTING.md); for how the system fits together, see
[ARCHITECTURE.md](ARCHITECTURE.md).

Commands are the same in PowerShell and bash unless both are shown.

---

## 1. Your daily rhythm

| Time (IST) | What you do |
|---|---|
| **9:30 AM** | First, read the review comments on your PR from yesterday and fix them (push to the same branch). Then open today's issue. |
| 9:30 to 10:00 | Read the whole issue. Read the files and docs it links. Plan your steps on paper. |
| 10:00 to 1:00 | Work. Commit small and often. |
| **1:00 PM** | Self-check: how many acceptance criteria are done? Are you stuck on anything? If yes, ask now (section 8), not at 4:30. |
| 1:00 to 5:00 | Work. Run the checks before every push. |
| **5:00 PM** | Open a PR into `dev`, or a **Draft PR** with a progress comment if you are not finished. Both are fine. |
| Next morning | Read review comments first, then the new issue. |

A Draft PR at 5:00 is **not a failure**. Pushing nothing at all is the only thing we want to avoid.

---

## 2. Picking up today's issue

1. On GitHub, open the repo and click **Issues**.
2. Click **Assignee** and choose yourself, or type `is:open assignee:@me` in the search box.
3. Today's issue starts with `[W1D<n>]`. Note its **number** (for example `#31`): you need it for
   your branch, your commits and your PR.
4. Read the **Acceptance criteria**. They are the definition of "finished" for today. If one is
   unclear, ask before you start.
5. If the issue is on the team project board, move it from **Todo** to **In progress**. When your PR
   is open, move it to **In review**. It moves to **Done** when the mentor merges and the issue closes.

---

## 3. Branch naming

**Rules**

- Start from the latest `dev`, every time.
- `feature/<issue-number>-<short-name>` for new work, `fix/<issue-number>-<short-name>` for bug fixes.
- Lowercase, words separated by hyphens, 2 to 4 words after the number.
- One branch per issue. Your issue gives you the exact name.

```bash
git switch dev
git pull
git switch -c feature/31-retries-robots
```

**Examples**

| Track | Example 1 | Example 2 |
|---|---|---|
| scraper | `feature/14-price-parser` | `feature/30-parse-listing` |
| db | `feature/16-crud-reads` | `feature/32-crud-writes` |
| scheduler | `feature/17-scrape-cycle` | `feature/43-scheduler-timer` |
| analysis | `feature/18-basic-signals` | `feature/35-detect-anomalies` |
| api | `feature/36-products-endpoints` | `feature/46-history-runs` |
| frontend | `feature/21-product-grid` | `feature/47-price-chart` |
| fix | `fix/58-price-comma-parsing` | `fix/61-empty-history-crash` |

Not allowed: `Feature/31_Retries`, `my-branch`, `naveen-work`, `feature/fix-stuff`.

---

## 4. Commits

**Format:** `<module>: <what changed> (#<issue>)`

- `module` is one of `scraper`, `db`, `scheduler`, `analysis`, `api`, `frontend`, `docs`, `tests`.
- "What changed" is short, lowercase, and says what the code does now.
- Commit small pieces that work, not one giant commit at 5 PM.

**Good**

```text
scraper: parse prices with commas and pound sign (#14)
scraper: retry temporary errors twice with backoff (#31)
db: find or create product before adding a snapshot (#32)
scheduler: record failed runs instead of raising (#33)
api: return 404 for unknown product id (#36)
frontend: format paise as rupees in product cards (#21)
```

**Bad**

```text
fixed stuff                      <- which module? what was fixed? which issue?
WIP                              <- says nothing; commit when a small piece works
Update product_scraper.py        <- the file name is already in the commit; say what changed
```

---

## 5. Opening a PR, step by step

1. Run the checks. CI runs the same ones and blocks the PR if they fail.

   bash:
   ```bash
   ruff check . && ruff format --check . && pytest -q
   ```
   PowerShell (Windows PowerShell 5.1 has no `&&`, so run them one by one):
   ```powershell
   ruff check .
   ruff format --check .
   pytest -q
   ```
   `ruff format .` fixes formatting for you.

2. Push your branch:
   ```bash
   git push -u origin feature/31-retries-robots
   ```
3. On GitHub a yellow bar appears: click **Compare & pull request**.
4. Check the top line: **base: `dev`** ← compare: your branch. If it says `main`, change it to `dev`.
5. Title: use the PR title from your issue, for example `scraper: retry with backoff and check robots.txt`.
6. Fill in the template: what you did, how you tested it, and tick the checklist honestly.
7. Make sure the body contains `Closes #31` (your issue number). GitHub then closes the issue
   automatically when the PR is merged.
8. Click **Create pull request**.
9. On the right, under **Reviewers**, request your **review buddy**.

### Draft PRs

Use a Draft PR when it is 5:00 PM and you are not finished, or when you want early feedback.

1. Push your branch as usual.
2. On the PR page, click the arrow next to **Create pull request** and choose
   **Create draft pull request**.
3. Add a comment with three parts:
   ```text
   Works: price parsing for £ and ₹, 8 tests passing.
   Left: "Rs." with no space, the None cases.
   Stuck: not sure whether "1,299.5" should be 129950 or None.
   ```
4. The next day, keep pushing to the same branch. When everything is done, click
   **Ready for review** at the bottom of the PR and request your buddy's review.

---

## 6. Handling review

1. **Reply to every comment.** Either "Fixed in <commit>" or a short explanation of why you
   disagree. A question from a reviewer deserves an answer, not just a code change.
2. **Push fixes to the same branch.** The PR updates by itself. Do not open a new PR.
   ```bash
   git add backend/scraper/product_scraper.py tests/test_fetcher.py
   git commit -m "scraper: do not retry 404 responses (#31)"
   git push
   ```
3. **Resolve conversations** with the **Resolve conversation** button once a comment is dealt with.
   Unresolved conversations block the merge.
4. **Re-request review:** under **Reviewers**, click the circular arrows next to the reviewer's name.
5. **After approval, do not merge. The mentor merges.** Once your PR is merged, clean up:
   ```bash
   git switch dev
   git pull
   git branch -D feature/31-retries-robots
   ```
   (`-D` is needed because PRs are squash-merged; only run it after GitHub shows **Merged**.)

---

## 7. Keeping your branch up to date with dev

Do this when your PR says "This branch is out-of-date", when it shows a conflict, or before you
start work each morning.

```bash
git switch dev
git pull
git switch feature/31-retries-robots
git merge dev
```

If there is no conflict, run the checks and `git push`. Done.

### Resolving a merge conflict

1. `git status` lists the files under **both modified**.
2. Open each file. You will see blocks like this:
   ```text
   <<<<<<< HEAD
   - Naveen: scraper-fetching
   =======
   - Mathan: scraper-parsing
   >>>>>>> dev
   ```
   Top part (`HEAD`) is your branch, bottom part is what came from `dev`.
3. Edit the block to what the file should really contain (often: keep both), and delete the three
   marker lines. VS Code offers **Accept Both Changes** above the block.
4. Search the file for `<<<<<<<` to make sure none are left.
5. Finish the merge:
   ```bash
   git add docs/notes.md
   git commit
   ```
   (Git prepares a message like `Merge branch 'dev' into ...`. Save and close the editor.)
6. Run the checks, then `git push`.

If you get lost in the middle of a merge, `git merge --abort` puts everything back as it was, and you
can ask your buddy.

---

## 8. Getting unstuck

| Stuck for | Do this |
|---|---|
| 30 minutes | Ask your **review buddy**. |
| 1 hour | Ask the **mentor**, using the template below. |

```text
Issue: #31
What I am trying to do: skip retries for 404 responses
What I tried: 1) checked response.status_code in the loop, 2) caught requests.HTTPError
Exact error (copy-paste, not a screenshot of text):
    AttributeError: 'FakeResponse' object has no attribute 'raise_for_status'
What I expected: the test to pass with only 1 call to requests.get
```

Good questions get fast answers. "It doesn't work" does not.

---

## 9. Definition of done

A task is done when **all** of these are true:

- [ ] Every acceptance criterion in the issue is ticked, and you checked each one yourself
- [ ] Tests exist for the new behaviour, including what happens when things go wrong
- [ ] Tests never use the network
- [ ] `ruff check .`, `ruff format --check .` and `pytest -q` pass locally, and CI is green
- [ ] You only changed files your track owns (ARCHITECTURE.md section 9), unless the issue says otherwise
- [ ] No `print` (use `logging`), no `float` for money, datetimes are timezone-aware UTC
- [ ] The PR targets `dev`, uses the template, and contains `Closes #<issue>`
- [ ] Your buddy has reviewed it, every comment is answered and resolved
- [ ] You can explain every line of it, because you wrote every line of it (see CONTRIBUTING.md)

---

## 10. Week 1 goals per track

| # | Track | By the end of Week 1 |
|---|---|---|
| 1 | Scraper: parsing | Prices and product cards from https://books.toscrape.com are parsed correctly from saved HTML, broken cards are skipped and logged, and the result matches the live site. |
| 2 | Scraper: fetching | Pages are fetched politely (our User-Agent, timeout, retries with backoff, robots.txt, delay) and the raw HTML is saved. A written recommendation for the real shop we will track. |
| 3 | Database | All crud functions work and are tested, the database can be exported safely, and there is a health report for the live database. |
| 4 | Scheduler | The collector runs by itself on a timer, records every run including failures, never crashes, and is documented. |
| 5 | Analysis: rules | The Trust Score tells the three seeded products apart and explains itself in plain sentences. |
| 6 | Analysis: ML | A rolling z-score anomaly pass, tuned on seeded data, with the evidence written down. |
| 7 | API | Products, history, scrape runs and trust score endpoints working on the seeded database. |
| 8 | Frontend | Product grid, search, detail view with Trust Score and a price chart, running on the live API. |

Team milestone: **M1 Collecting by Wed 7 Oct**. Scraper, crud and scheduler are on `dev` and
the collector runs unattended. Tracks 5 to 8 work on fake data from
`python -m backend.devtools.seed_fake_data`, so nobody waits for real data.

---

## 11. Common errors and fixes

### Push rejected: "Repository rule violations"

```text
! [remote rejected] dev -> dev (push declined due to repository rule violations)
```

You tried to push to `dev` or `main` directly. That is the rules working. Push a branch instead.
If your commits are on `dev`, see the next error.

### I committed on `dev` by mistake

Move the commit to a new branch, then put `dev` back. Commit or stash any unsaved work first,
because `reset --hard` throws away uncommitted changes.

```bash
git status                          # must say "nothing to commit"
git branch feature/31-retries-robots  # new branch pointing at your commit
git reset --hard origin/dev         # put your local dev back to match GitHub
git switch feature/31-retries-robots
git push -u origin feature/31-retries-robots
```

### My PR goes into `main`

The Gatekeeper check fails and comments on your PR. Click **Edit** next to the PR title, change the
base branch from `main` to `dev`, and save. No need to close the PR.

### CI is red: ruff

Open the failed check, read the first error, then run locally:

```bash
ruff check . --fix     # fixes what it safely can
ruff format .          # fixes formatting
ruff check .           # whatever is left, fix by hand
```

Commit and push. CI runs again by itself.

### CI is red: pytest

Run `pytest -q` locally and read the **first** failure from the top. To run just one test file:
`pytest tests/test_fetcher.py -q`. If it passes on your machine but fails in CI, check for a test that
depends on the network, on your `.env`, on your local database, or on the current time.

### venv not activated

Symptoms: `ModuleNotFoundError: No module named 'fastapi'`, or `ruff` / `pytest` "is not recognized"
/ "command not found". Your prompt should start with `(.venv)`.

bash:
```bash
source .venv/bin/activate
```
PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```
If PowerShell says "running scripts is disabled on this system", run this once, then try again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
