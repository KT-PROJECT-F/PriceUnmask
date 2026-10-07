# Price spike signal thresholds

Date: 2026-10-06

## Signal meanings

- **Spike before discount:** The product's highest price in the seven days before the latest continuous claimed-discount period began was at least 50% above the median price before that window.
- **Spike percentage:** The percent by which the highest price in that seven-day window exceeds the earlier median price.
- **Claimed discount:** The latest strikethrough price's percentage reduction from the latest current price.
- **Real discount vs median:** The latest current price's percentage reduction from the median of all earlier recorded prices, excluding the latest snapshot; prices at or above the median report 0% rather than a negative discount.

## Decision

`SPIKE_WINDOW_DAYS` is **7** and `SPIKE_THRESHOLD_PCT` is **50%**. A seven-day window treats a price hike in the week before a sale as recent, while a 50% rise focuses the signal on conspicuous hikes rather than normal price movement. The reference fake-discount history has an elevated-price period immediately before the claimed sale, so these values detect that pattern without treating small, ordinary changes as spikes.

The spike percentage compares the maximum price in the seven-day window before the latest continuous claimed-discount period began with the median of prices older than that window. This anchors the comparison to when the sale started, so a long-running sale does not push its pre-sale hike outside the window. The sale start is the first consecutive snapshot with an original price higher than the current price. The boolean signal is true only when this rise meets the threshold and the latest row has a positive claimed discount. If either comparison period lacks prices, `spike_pct` is `None`.

## Limits

A permanent price increase shortly before a sale can look like a temporary hike followed by a fake discount. The signal only sees recorded prices and the current strikethrough price; it cannot tell whether a price increase was a legitimate cost change or an artificial reference-price increase. Sparse snapshots can also miss when a sale or price change actually began.

## Alternatives considered

- A **3-day window** would miss hikes that occur several days before the sale is displayed.
- A **14-day window** would catch older increases, but risks attributing unrelated historical movement to the current sale.
- A **25% threshold** would flag more modest fluctuations; a higher threshold such as **100%** could miss meaningful but less dramatic hikes.

The latest price is excluded from the earlier-price median so that the sale price cannot pull its own baseline downward and make the discount appear larger.
