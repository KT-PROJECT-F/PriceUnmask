# PriceUnmask — dashboard design system

Status: proposal. Visual reference (live canvas, two screens): see the link shared with this doc. This file is the implementation spec — the exact values, not a picture. Owner of `frontend/*` implements from this file; no code in `frontend/` was changed to produce it.

## Visual thesis

One sentence: **a quiet instrument, not a storefront.** PriceUnmask's job is to tell a shopper whether a "deal" is real, so the UI should read like a compliance report or a brokerage statement — calm, evidence-first, numbers that line up — not like a sale banner. The current design (system-ui font, light-gray background, pastel badge pills, drop-shadow cards) reads as a generic SaaS template. This proposal removes every one of those defaults deliberately:

| Current | Problem | Replacement |
|---|---|---|
| `system-ui, sans-serif` | No point of view; what every unstyled page looks like | IBM Plex Sans (body/UI) + IBM Plex Mono (numbers) + Newsreader (titles only) |
| `background: #f5f7fa` (cold blue-gray) | Generic "SaaS dashboard" blue-gray | `#F7F6F2`, a warm paper tone — closer to a printed report than a web app |
| White cards + `box-shadow` | Shadows read as decorative/AI-generated; "floaty" | Flat white surface, 1px hairline border, no shadow |
| Pastel filled badge pills (mint/amber/red/gray/blue) | Looks like a children's app; low information density | Outlined chip + 6px status dot, muted/desaturated semantic colors |

## Why this avoids "AI slop"

No purple, no gradients, no centered-everything hero treatment, no decorative blobs, no Inter-by-default. The single accent color is a desaturated ink-teal, not the purple that's become a tell for AI-generated interfaces (checked directly against this: Vanta, a trust/compliance product in the same conceptual space, leans on exactly that purple-gradient look — deliberately not copied here). Every color is slightly muted/desaturated rather than saturated-bright, which is what makes a UI read as "considered" rather than "default theme."

## Typography

Three families, used strictly by role — never mixed within one piece of text.

| Role | Family | Weight | Where |
|---|---|---|---|
| Titles (page `<h1>`, product name in detail view) | **Newsreader** (serif) | 500–600 | Sparingly — titles only. Gives gravitas without being a generic display font. |
| UI text, labels, body, card copy | **IBM Plex Sans** | 400 (body), 500 (labels/buttons), 600 (card titles, eyebrow labels) | Everything else. Chosen because it's built for data-dense software (IBM's own enterprise design system), not another Inter clone. |
| Prices, dates, scores, anything numeric | **IBM Plex Mono** | 400–600 | Tabular figures so prices visually line up down a column — reinforces "ledger," not "listing." |

Google Fonts import (one link, all three families):
```html
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,500;0,600;1,500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

Type scale:
| Token | Size / line-height | Family / weight | Use |
|---|---|---|---|
| `--text-display` | 28–30px / 1.2 | Newsreader 600 | Page `<h1>`, product detail title |
| `--text-eyebrow` | 11px / 1, uppercase, 0.08em tracking | Plex Sans 600 | Section labels ("SEARCH", "COLLECTOR", "PRODUCTS", "WHY THIS SCORE") |
| `--text-card-title` | 16px / 1.35 | Plex Sans 600 | Product card name |
| `--text-body` | 14–15px / 1.5 | Plex Sans 400 | Reasons list, descriptions |
| `--text-price-lg` | 21–26px | Plex Mono 600 | Current price, large context |
| `--text-price-sm` | 13–15px, strikethrough | Plex Mono 400 | Original/struck price |
| `--text-caption` | 12px | Plex Sans 400 | "Updated 2h ago" footers |

## Color tokens

Light mode only (the app has no dark mode today — out of scope for this pass).

```css
:root {
  --bg: #F7F6F2;           /* page background: warm paper, not cold gray */
  --surface: #FFFFFF;       /* card/panel background */
  --surface-tint: #F1F0EA;  /* collector status bar background */
  --border: #E4E2DC;        /* hairline card/panel borders */
  --border-strong: #D8D4CB; /* input borders */

  --ink: #1C1B19;           /* primary text */
  --ink-muted: #6B6860;     /* secondary text (tagline, body) */
  --ink-faint: #8A8678;     /* tertiary text (eyebrow labels, captions) */

  --accent: #1D4D43;        /* single brand accent: ink-teal. Links, primary actions, "genuine" badge */
  --accent-hover: #163B33;
}
```

Semantic badge colors — each is a (text/dot, border, background) triple, all muted, none saturated:

```css
--genuine-color: #1D4D43;   --genuine-border: #CFE0DB;  --genuine-bg: #F2F7F5;
--inflated-color: #8C2F26;  --inflated-border: #EAD3CF; --inflated-bg: #FBF2F1;
--uncertain-color: #8A6418; --uncertain-border: #E8DCC3; --uncertain-bg: #FAF6EC;
--nodiscount-color: #45586B; --nodiscount-border: #D7DEE5; --nodiscount-bg: #F3F5F7;
--insufficient-color: #716C62; --insufficient-border: #D8D4CB (dashed); --insufficient-bg: #F9F8F5;
```

All text/background pairs above meet 4.5:1 contrast (checked for the 12px badge label size).

## Spacing

8px base grid. Page padding 56px top / 32px sides (desktop); card padding 26–28px; grid gap 24px; section gaps 32–40px. This is roughly 40% more whitespace than the current layout (16px page padding, 20px card padding, 20px grid gap) — the single biggest lever for "sleek" vs. "cramped."

## Components

### Product card
Flat white surface, `1px solid var(--border)`, `border-radius: 12px`, `padding: 26px`, **no box-shadow**. Content stack: card title → price row (current price Plex Mono 21px 600 + struck original price if present, 13px muted) → trust badge → caption.

### Trust badge (replaces `.trust-badge-*` classes)
Outlined pill, not filled: `border: 1px solid <state-border>`, `background: <state-bg>`, `color: <state-color>`, plus a 6px filled dot before the label. `insufficient_data` additionally uses a **dashed** border on both the badge and its parent card — a deliberate visual signal of "not yet enough evidence," distinct from the other four which are all confident classifications.

### Collector status bar
Tinted panel (`--surface-tint` background, `--border` outline, `10px` radius), eyebrow label "COLLECTOR," a status line in Plex Mono with a small live-status dot, and an outlined "Run now" button on the right. Replaces the current plain `<p>` text + unstyled button.

### Search
Eyebrow label above a bordered input (`--border-strong`, `8px` radius, `11px 14px` padding) — not the current bare `<input>` with a default browser label.

### Price history chart (Chart.js, in `script.js`)
Keep Chart.js (already a dependency, no need to replace). Restyle its options to match the system: line color `--accent` for genuine/neutral products, `--inflated-color` when the anomaly/trust state is a warning; gridlines in `--border` at low opacity; axis labels in Plex Mono 11px `--ink-faint`; no fill/gradient under the line (flat line, no area fill — area fills under line charts are a common "AI slop" tell).

## What changes in the existing files

- `frontend/index.html`: add the Google Fonts `<link>`; no structural changes needed beyond what the component specs above imply (labels, eyebrow spans).
- `frontend/style.css`: full rewrite of the token values and the classes listed above (`.product-card`, `.trust-badge-*`, `.collector-status`, `#search-box`, `.price-chart-container`). Class names can stay the same — only their declarations change — to minimize the diff against `script.js`, which references these classes by name.
- `frontend/script.js`: only the Chart.js `options` object needs new color values (see "Price history chart" above); no logic changes.

## Non-goals for this pass

- Dark mode (not currently supported; adding it is a separate decision).
- Any change to API contracts, data shapes, or what the five Trust Score labels mean — this is visual only.
