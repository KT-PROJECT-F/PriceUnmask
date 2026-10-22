# Proposal: No-Discount Trust Score Label

## Status

Proposed design for review. No implementation changes are included in this proposal.

## Context

The current Trust Score uses four labels:

- `genuine`
- `uncertain`
- `likely_inflated`
- `insufficient_data`

In `backend/analysis/trust_score.py`, `claimed_discount_pct` is calculated from the latest snapshot's `original_price_minor`. If that value is absent, the claimed discount is `None`. The current scoring rules can still return a score of 100 and the `genuine` label when no strong warning signals are detected.

However, absence of a recorded discount is not proof that a discount is genuine. The label should communicate whether the available data supports judging an advertised discount.

## Evidence from the Trust Score findings

The findings report for `priceunmask-20261019.db` analyzed 20 of 20 products and 800 snapshots. None of the analyzed products had a recorded original price, and all 20 received score 100 and label `genuine`.

This dataset shows a gap in interpretation: a high score may reflect a lack of warning signals rather than evidence that a discount claim is genuine. The report recommends considering a neutral label for insufficient discount evidence.

## Proposed rule

Introduce a separate label, `no_discount`, displayed to shoppers as **No discount to judge**.

Proposed classification:

1. Keep `insufficient_data` for histories with fewer than the existing minimum of six snapshots.
2. For histories with enough snapshots, use `no_discount` when no valid discount claim is recorded anywhere in the available history.
3. Treat a valid discount claim as a snapshot where `original_price_minor` is present, positive, and greater than `current_price_minor`.
4. If a valid discount claim exists in the history but the latest snapshot has no valid discount claim, do not automatically classify the product as `no_discount`. Existing history-based Trust Score logic should remain available to evaluate the historical evidence.
5. If a valid discount claim exists in the latest snapshot, continue to evaluate it using the existing Trust Score rules.

This is a proposed rule for reviewer agreement, not an implemented behavior. In particular, the team should confirm whether a past discount claim should continue to count as evidence when today's snapshot no longer advertises a discount.

## Proposed score and shopper-facing copy

- API label: `no_discount`
- Display label: `No discount to judge`
- Proposed score: `null`, rather than `100`, because the score should not imply that a discount claim has been validated when no such claim is recorded.
- Provisional message: "No discount is currently recorded for this product, so we can't assess an advertised discount."

The label, score contract, and wording require review before implementation. Request final shopper-facing copy from Lakshmi and align it with issue #160. Do not treat the provisional wording as approved.

## Demo product impact

The frontend demo histories contain 21 snapshots per product, from 2026-09-17 through 2026-10-07.

| Product | Observed history | Expected outcome under the proposed rule |
|---|---|---|
| Demo Bluetooth Speaker (ID 1) | Original price of 219900 minor units is recorded; latest price is 179900. | Keep existing scoring path; not `no_discount`. |
| Demo Running Shoes (ID 2) | Original price of 349900 is recorded; latest price is 279900. | Keep existing scoring path; not `no_discount`. |
| Demo Air Fryer (ID 3) | Latest price is 104900 and latest original price is 349900; earlier snapshots include prices without an original price. | Keep existing scoring path; not `no_discount`. |

These are mock-data observations, not a claim that the demo scores have been recalculated. The currency in these mock files is INR and the prices are stored in minor units.

The collected database findings and the demo mock histories are different datasets; they should not be treated as interchangeable evidence.

## Test-case proposal

| History scenario | Expected label | Expected score |
|---|---|---|
| Fewer than six snapshots | `insufficient_data` | `null` |
| Six or more snapshots; no valid discount claim in any snapshot | `no_discount` | `null` |
| Historical valid discount claim, but no valid claim in the latest snapshot | Existing scoring path; not automatically `no_discount` | Calculated by existing rules |
| Valid discount claim in the latest snapshot | Existing scoring path | Calculated by existing rules |
| Latest original price is missing, zero, or less than/equal to current price, and no valid historical claim exists | `no_discount` | `null` |
| Existing history contains evidence of suspicious price movement and a valid discount claim | Existing scoring path, including current warning rules | Calculated by existing rules |

Reviewers should confirm the expected behavior for the historical-claim case and whether the no-discount classification should take precedence over any other history-based warnings.

## Affected files and responsibilities

Implementation is out of scope for this documentation-only proposal. Likely affected areas are:

- `backend/analysis/trust_score.py` — classification rule and score behavior.
- `backend/schemas.py` — label literals for product and `TrustScoreOut` responses.
- `frontend/script.js` — shopper-facing label mapping, score display, and handling of a `null` score for `no_discount`.
- Frontend styles — badge appearance for the new label.
- `docs/ARCHITECTURE.md` — update the Trust Score contract and label definitions in sections 5 and 6.
- `tests/test_trust_score.py` — unit tests for classification and score behavior, including histories with no original prices and histories with an older discount claim.
- `tests/test_api.py` — API response and schema behavior for the new label.
- Any report tests or label summaries that enumerate Trust Score labels.

The existing test `test_compute_trust_score_without_original_prices_uses_history_signals` currently expects score 100 and label `genuine`. Implementation must deliberately update or replace that expectation if the team approves the proposed rule.

## Open questions for review

1. Should a discount recorded in an older snapshot prevent `no_discount` when today's snapshot has no discount claim?
2. Should `no_discount` always use a `null` score, or should the API separate discount-claim assessability from the numerical Trust Score?
3. What final shopper-facing label and explanation should be used? Please obtain wording approval from Lakshmi and coordinate with issue #160.
4. Should the new label be introduced before or after the v0.2 release? Because this changes the API label contract and frontend behavior, coordinate the rollout across backend, API, and frontend owners.

## Review requested

Please review the proposed classification rule, score semantics, historical-discount behavior, and shopper-facing copy before implementation.

- Rajesh: `@rajeshkandlapalli-glitch`
- Pavan: `@Kanamarlapudipk`
- Lakshmi: `@lakshmiprasanna45`

Request a review from Lakshmi for the shopper-facing wording. This document records a proposal only; it does not mean these reviewers have already approved it.
