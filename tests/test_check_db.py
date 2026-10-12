from types import SimpleNamespace

from backend.devtools.check_db import find_problems


def make_run(status: str = "success", products_seen: int = 24):
    return SimpleNamespace(
        id=7,
        status=status,
        products_seen=products_seen,
    )


def test_healthy_run_has_no_problems() -> None:
    assert find_problems(make_run(), 24, 0, []) == []


def test_missing_snapshots_are_a_problem() -> None:
    problems = find_problems(make_run(products_seen=24), 12, 0, [])
    assert any("saved 12 snapshots but products_seen is 24" in problem for problem in problems)


def test_failed_run_and_unseen_products_are_problems() -> None:
    problems = find_problems(
        make_run(status="failed", products_seen=0),
        0,
        3,
        [],
    )
    assert any("status failed" in problem for problem in problems)
    assert any("3 products have no snapshot" in problem for problem in problems)


def test_duplicates_are_a_problem() -> None:
    problems = find_problems(make_run(), 24, 0, [("shop", "Phone", 2)])
    assert any("stored more than once" in problem for problem in problems)


def test_find_problems_uses_singular_for_one_duplicate_name():
    latest_run = SimpleNamespace(id=1, status="success", products_seen=0)

    problems = find_problems(latest_run, 0, 0, [("shop", "Book A", 2)])

    assert "1 product name stored more than once" in problems


def test_find_problems_uses_plural_for_two_duplicate_names():
    latest_run = SimpleNamespace(id=1, status="success", products_seen=0)

    problems = find_problems(
        latest_run,
        0,
        0,
        [("shop", "Book A", 2), ("shop", "Book B", 2)],
    )

    assert "2 product names stored more than once" in problems
