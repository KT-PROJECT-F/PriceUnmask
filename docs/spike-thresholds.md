# Price spike signal thresholds

Date: 2026-10-06

## Signal meanings

- **Spike before discount:** The product's highest price in the seven days before the latest snapshot was at least 50% above the median price before that window, and the latest row shows a claimed discount.
- **Spike percentage:** The percent by which the highest price in that seven-day window exceeds the earlier median price.
- **Claimed discount:** The latest strikethrough price's percentage reduction from the latest current price.
- **Real discount vs median:** The latest current price's percentage reduction from the median of all earlier recorded prices, excluding the latest snapshot.

## Decision

`SPIKE_WINDOW_DAYS` is **7** and `SPIKE_THRESHOLD_PCT` is **50%**. A seven-day window treats a price hike in the week before a sale as recent, while a 50% rise focuses the signal on conspicuous hikes rather than normal price movement. The reference fake-discount history has an elevated-price period immediately before the claimed sale, so these values detect that pattern without treating small, ordinary changes as spikes.

The spike percentage compares the maximum price in the window before the latest snapshot with the median of prices older than the window. The latest snapshot is excluded from both groups. The boolean signal is true only when this rise meets the threshold and the latest row has a positive claimed discount. If either comparison period lacks prices, `spike_pct` is `None`.

## Alternatives considered

- A **3-day window** would miss hikes that occur several days before the sale is displayed.
- A **14-day window** would catch older increases, but risks attributing unrelated historical movement to the current sale.
- A **25% threshold** would flag more modest fluctuations; a higher threshold such as **100%** could miss meaningful but less dramatic hikes.

The latest price is excluded from the earlier-price median so that the sale price cannot pull its own baseline downward and make the discount appear larger.
