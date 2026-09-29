# How we work (read this first)

## The branches

```
feature/12-price-parser ─┐
feature/15-crud          ├──>  dev  ──(mentor only, at milestones)──>  main
fix/21-empty-history    ─┘
```

- `main`: released, working code. Only the mentor merges into it, only from `dev`.
- `dev`: where everything comes together. You never push to it directly; you open a PR.
- your branch: where you work. Create one per issue.

GitHub enforces all of this. If a push is rejected, that is the rules working, not a bug.

## First-time setup (once)

```bash
git clone https://github.com/<ORG>/priceunmask.git
cd priceunmask
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python -m backend.devtools.seed_fake_data
pytest -q                            # should say "passed"
uvicorn backend.main:app --reload    # open http://127.0.0.1:8000/docs
```

## Every task, every time

1. **Pick an issue** assigned to you on GitHub. No issue? Ask the mentor; do not start untracked work.
2. **Start from the latest dev:**
   ```bash
   git switch dev
   git pull
   git switch -c feature/<issue-number>-<short-name>     # e.g. feature/12-price-parser
   ```
   Use `fix/` instead of `feature/` for bug fixes.
3. **Work in small commits:**
   ```bash
   git add <files>
   git commit -m "scraper: parse prices with commas and rupee sign (#12)"
   ```
4. **Check before pushing** (CI runs the same thing and will block you):
   ```bash
   ruff check . && ruff format --check . && pytest -q
   ```
   `ruff format .` fixes formatting for you.
5. **Push your branch:**
   ```bash
   git push -u origin feature/12-price-parser
   ```
6. **Open a PR** on GitHub. Base: **`dev`**. Fill in the template. Write `Closes #12`.
7. **Ask your review buddy** to review, then the mentor approves. Answer every comment and
   click "Resolve conversation"; unresolved threads block the merge.
8. **After approval, do not merge. The mentor merges.** Once GitHub shows the PR as merged,
   switch back to `dev`, pull, and delete your local branch.
9. Back to step 2 for the next task.

## When dev moved on while you were working

```bash
git switch dev && git pull
git switch feature/12-price-parser
git merge dev          # fix any conflicts, run tests, commit
git push
```

## Things that will be rejected

- Pushing to `dev` or `main` directly
- A PR into `main` (the Gatekeeper bot will tell you to change the base to `dev`)
- A PR with failing lint or tests
- A PR without the mentor's approval, or with unresolved review comments

## Write your own code

This project is for learning, so every line you submit must be written by you.
Do not use AI tools (ChatGPT, Claude, Copilot, Gemini, etc.) to write or complete code.

What is fine:
- Official docs (Python, FastAPI, SQLAlchemy, pandas, Chart.js), tutorials, Stack Overflow
  to understand a concept, then writing the code yourself
- Asking your review buddy or the mentor

In review, the mentor may ask you to explain any line or change it live.
If you cannot explain it, it does not get merged.
