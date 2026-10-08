"""Print a read-only health report for the PriceUnmask database."""

from backend.db import crud
from backend.db.database import SessionLocal


def main() -> None:
    """Read database health metrics through CRUD functions only."""
    with SessionLocal() as session:
        runs = crud.list_scrape_runs(session)
        runs_by_status = crud.count_runs_by_status(session)
        total_products = crud.count_products(session)
        snapshots_by_run = crud.count_snapshots_by_run(session)

        print("=== PriceUnmask Database Health ===")

        print("\nRuns by status:")
        for status, count in sorted(runs_by_status.items()):
            print(f"  {status}: {count}")

        print(f"\nTotal products: {total_products}")

        print("\nSnapshots per run:")
        for run in runs:
            count = snapshots_by_run.get(run.id, 0)
            print(f"  Run {run.id}: {count}")

        if not runs:
            print("\nLatest run:")
            print("  None")

            print("\nProducts not seen in latest run:")
            print("  Not available — no scrape runs exist.")

            print("\nHealth status: CHECK REQUIRED")
            print("Reason: no scrape runs found.")
            return

        latest_run = runs[0]

        missing_products = crud.list_products_not_seen_in_run(
            session,
            latest_run.id,
        )

        print("\nLatest run:")
        print(f"  ID: {latest_run.id}")
        print(f"  Status: {latest_run.status}")
        print(f"  Products seen: {latest_run.products_seen}")
        print(f"  Products without a snapshot in this run: {len(missing_products)}")

        health = (
            "CHECK REQUIRED" if latest_run.status != "success" or missing_products else "HEALTHY"
        )

        print(f"\nHealth status: {health}")


if __name__ == "__main__":
    main()
