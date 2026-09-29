"""Seed the DB with synthetic history so API, analysis and frontend work can start
before real scraped history exists.

    python -m backend.devtools.seed_fake_data

Creates 3 products covering the patterns the Trust Score must tell apart:
  1. Stable price, small "sale"      -> should score genuine
  2. Real, gradual price drop        -> should score genuine
  3. Price hiked, then "70% OFF"     -> should score likely_inflated
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.db.database import SessionLocal, init_db
from backend.db.models import PriceSnapshot, Product

SNAPSHOTS_PER_DAY = 6  # every 4 hours
DAYS = 21


def _series(kind: str, n: int) -> list[tuple[int, int | None]]:
    rng = random.Random(kind)
    out: list[tuple[int, int | None]] = []
    for i in range(n):
        t = i / n
        if kind == "stable":
            price = 1_999_00 + rng.randint(-50_00, 50_00)
            if t > 0.85:
                price = 1_799_00
            out.append((price, 2_199_00))
        elif kind == "real_drop":
            price = int(3_499_00 - t * 800_00) + rng.randint(-20_00, 20_00)
            out.append((price, 3_499_00))
        else:  # fake_discount
            if t < 0.6:
                price, orig = 999_00 + rng.randint(-30_00, 30_00), None
            elif t < 0.8:
                price, orig = 2_999_00, None  # quiet hike
            else:
                price, orig = 1_049_00, 3_499_00  # "70% OFF!"
            out.append((price, orig))
    return out


def seed(session: Session) -> None:
    start = datetime.now(UTC) - timedelta(days=DAYS)
    n = DAYS * SNAPSHOTS_PER_DAY
    for ext_id, name, kind in [
        ("demo-001", "Demo Bluetooth Speaker (stable)", "stable"),
        ("demo-002", "Demo Running Shoes (real drop)", "real_drop"),
        ("demo-003", "Demo Air Fryer (fake discount)", "fake_discount"),
    ]:
        product = Product(
            source="fake",
            external_id=ext_id,
            name=name,
            url=f"https://example.com/p/{ext_id}",
            created_at=start,
            last_seen_at=datetime.now(UTC),
        )
        session.add(product)
        session.flush()
        for i, (price, orig) in enumerate(_series(kind, n)):
            session.add(
                PriceSnapshot(
                    product_id=product.id,
                    scraped_at=start + timedelta(hours=4 * i),
                    current_price_minor=price,
                    original_price_minor=orig,
                    in_stock=True,
                )
            )
    session.commit()


if __name__ == "__main__":
    init_db()
    with SessionLocal() as s:
        if s.query(Product).filter_by(source="fake").first():
            raise SystemExit("Fake data already seeded.")
        seed(s)
    print("Seeded 3 fake products.")
