# PriceUnmask: fake discount detector

Tracks product prices over time and gives each "deal" a Trust Score:
genuine, uncertain, likely inflated, or not enough data yet.

- How it is built: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- How we work (branches, PRs): [CONTRIBUTING.md](CONTRIBUTING.md)

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python -m backend.devtools.seed_fake_data
uvicorn backend.main:app --reload
```

Dashboard: http://127.0.0.1:8000/  API docs: http://127.0.0.1:8000/docs
