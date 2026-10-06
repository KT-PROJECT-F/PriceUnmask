from backend.scheduler import jobs


class FakeRun:
    id = 1


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeProduct:
    pass


def test_happy_path_saves_all_and_returns_count(monkeypatch):
    calls = {"upset": [], "finish": None}

    def fake_start(s):
        return FakeRun()

    def fake_scrape(url, source):
        return [FakeProduct(), FakeProduct()]

    def fake_upsert(s, p):
        calls["upset"].append(p)

    def fake_finish(s, run, status, products_seen, error=None):
        calls["finish"] = (status, products_seen)

    monkeypatch.setattr(jobs, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(jobs.crud, "start_scrape_run", fake_start)
    monkeypatch.setattr(jobs, "scrape", fake_scrape)
    monkeypatch.setattr(jobs.crud, "upsert_product_and_snapshot", fake_upsert)
    monkeypatch.setattr(jobs.crud, "finish_scrape_run", fake_finish)

    count = jobs.run_scrape_cycle()
    assert count == 2
    assert len(calls["upset"]) == 2
    assert calls["finish"] == ("success", 2)


def test_empty_scrape_finishes_with_zero(monkeypatch):
    calls = {}

    def fake_finish(s, run, status, products_seen, error=None):
        calls["finish"] = (status, products_seen)

    monkeypatch.setattr(jobs, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(jobs.crud, "start_scrape_run", lambda s: FakeRun())
    monkeypatch.setattr(jobs, "scrape", lambda url, source: [])
    monkeypatch.setattr(jobs.crud, "upsert_product_and_snapshot", lambda s, p: None)
    monkeypatch.setattr(jobs.crud, "finish_scrape_run", fake_finish)

    count = jobs.run_scrape_cycle()
    assert count == 0
    assert calls["finish"] == ("success", 0)


def test_source_key_and_url_passed(monkeypatch):
    captured = {}

    def fake_scrape(url, source):
        captured["url"] = url
        captured["source"] = source
        return []

    monkeypatch.setattr(jobs, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(jobs.crud, "start_scrape_run", lambda s: FakeRun())
    monkeypatch.setattr(jobs, "scrape", fake_scrape)
    monkeypatch.setattr(jobs.crud, "upsert_product_and_snapshot", lambda s, p: None)
    monkeypatch.setattr(jobs.crud, "finish_scrape_run", lambda *a, **k: None)

    jobs.run_scrape_cycle()
    assert captured["source"] == jobs.SOURCE_KEY
    assert captured["source"] == "demo-shop"
