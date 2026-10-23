# Anomaly Messages

## Purpose

This document explains the three shopper-facing anomaly statuses, when each status appears, and example cases with expected results.

## Statuses and Messages

| Status | Exact shopper-facing message | When it appears |
|---|---|---|
| `insufficient_history` | Not enough price history to detect unusual price changes. | Fewer than 6 price snapshots are available. There is not enough history to check today's price reliably. |
| `normal` | Today's price looks normal based on the available history. | At least 6 snapshots are available, and the detector does not flag the latest price as unusual. |
| `unusual` | An unusual price change was detected. Please review the price history before making a purchase. | At least 6 snapshots are available, and the detector flags the latest price as unusual. |

The detector checks the latest observed price against the available price history. The status describes the price pattern; it does not prove that a discount is genuine or fake.

## Test Cases

The following examples describe expected behaviour. They should be checked against the existing detector rules.

| Case | Price history (oldest to newest) | Expected status | Reason |
|---|---|---|---|
| Too little history | `1000, 1000, 1000, 1000, 1000` | `insufficient_history` | Only 5 snapshots are available. |
| Stable price | `1000, 1000, 1000, 1000, 1000, 1000` | `normal` | The latest price matches the earlier prices. |
| Flat, then large jump | `1000, 1000, 1000, 1000, 1000, 2000` | `unusual` | The latest price is much higher than the stable earlier prices. |
| Flat, then small change | `1000, 1000, 1000, 1000, 1000, 1001` | `normal` | The latest price has changed only slightly. |
| Old spike, back to normal | `1000, 1000, 2000, 1000, 1000, 1000` | `normal` | The latest price is back at the usual level. The current status describes today's price, not every past change. |

## Important Notes

- The minimum history requirement is 6 snapshots.
- Prices are listed from oldest to newest.
- The status is based on the latest price and the detector's existing rules.
- A past unusual price does not automatically mean today's price is unusual.
- These examples document expected behaviour; they do not change the detector implementation.
- The exact shopper-facing sentences must remain consistent with section 5 of `docs/ARCHITECTURE.md`.

## Conclusion

The three statuses help shoppers understand whether there is enough price history to assess a price, whether the latest price looks normal, or whether an unusual change needs attention.
