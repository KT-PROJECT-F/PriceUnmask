"""Print a read-only health report for the PriceUnmask database."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db import crud
from backend.db.database import SessionLocal
from backend.db.models import ScrapeRun

STALE_AFTER = timedelta(hours=24)


def find_problems(
    latest_run: ScrapeRun,
    snapshots_in_run: int,
    missing_count: int,
    duplicates: list[tuple[str, str, int]],
    now: datetime | None = None,
) -> list[str]:
    """Return one sentence per problem. An empty list means healthy."""
    problems: list[str] = []

    finished_at = latest_run.finished_at

    if finished_at is None:
        problems.append(f"latest finished run {latest_run.id} has no finished_at timestamp")
    elif finished_at.tzinfo is None or finished_at.utcoffset() is None:
        problems.append(f"latest finished run {latest_run.id} has a naive finished_at timestamp")
    else:
        current_time = now or datetime.now(UTC)
        if current_time - finished_at > STALE_AFTER:
            problems.append(f"latest finished run {latest_run.id} is older than 24 hours")

    if latest_run.status != "success":
        problems.append(f"latest finished run {latest_run.id} has status {latest_run.status}")

    if snapshots_in_run != latest_run.products_seen:
        problems.append(
            f"run {latest_run.id} saved {snapshots_in_run} snapshots "
            f"but products_seen is {latest_run.products_seen}"
        )

    if missing_count:
        problems.append(f"{missing_count} products have no snapshot in run {latest_run.id}")

    if duplicates:
        count = len(duplicates)
        noun = "product name" if count == 1 else "product names"
        problems.append(f"{count} {noun} stored more than once")

    return problems


def report(session: Session) -> None:
    """Print a read-only database health report."""
    now = datetime.now(UTC)
    runs = crud.list_scrape_runs(session)
    runs_by_status = crud.count_runs_by_status(session)
    snapshots_by_run = crud.count_snapshots_by_run(session)
    duplicates = crud.list_duplicate_product_names(session)

    print("=== PriceUnmask Database Health ===")

    print("\nRuns by status (all runs):")
    for status, count in sorted(runs_by_status.items()):
        print(f"  {status}: {count}")

    print(f"\nTotal products: {crud.count_products(session)}")

    print("\nSnapshots per run (newest 20 runs):")
    for run in runs:
        saved = snapshots_by_run.get(run.id, 0)
        print(
            f"  Run {run.id} ({run.status}): {saved} snapshots, products_seen {run.products_seen}"
        )

    print("\nDuplicate product names:")
    if duplicates:
        for source, name, count in duplicates:
            print(f"  {source} / {name}: {count} times")
    else:
        print("  None")

    problems: list[str] = []

    # Report old running runs without changing their database status.
    stale_after = timedelta(minutes=settings.stale_run_minutes)

    for run in runs:
        if run.status != "running":
            continue

        started_at = run.started_at

        if started_at.tzinfo is None or started_at.utcoffset() is None:
            problems.append(f"running run {run.id} has a naive started_at timestamp")
        elif now - started_at > stale_after:
            age_minutes = int((now - started_at).total_seconds() // 60)
            problems.append(
                f"running run {run.id} started at {started_at.isoformat()} "
                f"and has been running for {age_minutes} minutes "
                f"(threshold: {settings.stale_run_minutes} minutes)"
            )

    finished = [run for run in runs if run.status != "running"]

    if not finished:
        problems.append("no finished scrape run found")
        print("\nHealth status: CHECK REQUIRED")
        for problem in problems:
            print(f"  - {problem}")
        return

    latest_run = finished[0]
    missing = crud.list_products_not_seen_in_run(session, latest_run.id)

    print("\nLatest finished run:")
    print(f"  ID: {latest_run.id}")
    print(f"  Status: {latest_run.status}")
    print(f"  Finished at: {latest_run.finished_at}")
    print(f"  Error: {latest_run.error_message or '-'}")
    print(f"  Products without a snapshot in this run: {len(missing)}")

    problems.extend(
        find_problems(
            latest_run,
            snapshots_by_run.get(latest_run.id, 0),
            len(missing),
            duplicates,
            now=now,
        )
    )

    if problems:
        print("\nHealth status: CHECK REQUIRED")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("\nHealth status: HEALTHY")


def main() -> None:
    """Read database health metrics through crud functions only."""
    try:
        with SessionLocal() as session:
            report(session)
    except OperationalError as exc:
        print("Cannot read the database. Does it exist and have the scrape_runs table?")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
