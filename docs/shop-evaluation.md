# Shop Evaluation

**Evaluation date:** 12 October 2026

**Purpose:** Evaluate Croma and Reliance Digital as potential shops for price tracking in PriceUnmask.

## 1. Croma

**Shop:** https://www.croma.com/
**Category URL:** https://www.croma.com/home-appliances/washing-machines-dryers/c/48

| Check             | Result                          | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ----------------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Terms of Use      | Unclear                         | https://www.croma.com/terms-of-use — Section 7(d): “User shall not use the Website, services and/or materials therein in any manner which could damage, disable, overburden and/or impair the Website and/or any services therein and/or the network(s) connected to the Website and interfere with other Users use and enjoyment of the Website and/or services therein.” Section 7(e): “User shall not or shall not attempt to obtain any materials or information through any means not intentionally made available to User through the Website.” These sections do not explicitly mention automated price tracking. Sections 7(d)–7(e) reviewed in full on 12 October 2026. |
| robots.txt        | Allowed by listed rules         | https://www.croma.com/robots.txt — In the `User-agent: *` block, `Allow: /*` matches `/home-appliances/washing-machines-dryers/c/48`; no listed `Disallow` matches this path. This is not, by itself, permission to scrape.                                                                                                                                                                                                                 |
| Price in raw HTML | Found; one mismatch and one price not found | 10 kg product https://www.croma.com/croma-10-kg-5-star-fully-automatic-top-load-washing-machine-aqua-reserve-neel-black-/p/322406 — `offers.price` and `pdpPriceReducer.pdpPriceData.sellingPrice.value` = `19990.00`; `pdpPriceReducer.pdpPriceData.mrp.value` = `36000.00`, matching the displayed ₹19,990.00 and ₹36,000.00. 6.5 kg product https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023 — source `sellingPrice.value` = `7990.00`, while the page displayed ₹8,390.00; `mrp.value` = `12000.00`, matching ₹12,000.00. 7.5 kg product https://www.croma.com/croma-7-5-kg-5-star-fully-automatic-top-load-washing-machine-fuzzy-control-grey-/p/243594 — browser Find returned 0/0 for both `14390.00` and `14390`; the displayed selling-price value was not found in page source. |
| Price changes     | No change in short repeat checks | The three Croma products showed the same displayed prices on repeat checks 13, 63, and 61 minutes after the initial observations. This does not establish whether prices move over several hours or days.                                                                                                                                                                                                                   |

## 2. Reliance Digital

**Shop:** https://www.reliancedigital.in/
**Category URL:** https://www.reliancedigital.in/sections/washing-machines

| Check             | Result                                        | Evidence                                                                                                                                                                                                                                                                                                                                                                                         |
| ----------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Terms of Use      | Forbidden                                     | https://www.reliancedigital.in/c/terms-of-use — Section 12: “Introduce any Trojans, viruses, any other malicious software, any bots or scrape Reliance Digital Platform for any information;” This prohibits using bots or scraping the platform for information. Reviewed 12 October 2026.                                                                                                                                                      |
| robots.txt        | Allowed by listed rules                      | https://www.reliancedigital.in/robots.txt — In the `User-agent: *` block, the general `Disallow:` is empty and no listed path-specific rule matches `/sections/washing-machines`; `Disallow: /*?*` blocks query-string URLs. This is not, by itself, permission to scrape. Reviewed 12 October 2026. |
| Price in raw HTML | Yes                                           | Lloyd washing machine https://www.reliancedigital.in/product/lloyd-8-kg-top-loading-semi-automatic-washing-machine-elante-glwms80avgel-lg55vo — source `offers.price` = `13590`, matching displayed Deal Price ₹13,590; `selling.min` and `selling.max` = `15490`, matching displayed Offer Price ₹15,490. |
| Price changes     | Not assessed                                  | Reliance Digital is ruled out for automated tracking by section 12 of its Terms of Use; no second product-price visit was made.                                                                                                                                                                                                                          |

## 3. Price Observations

Manual browser observations; bank, exchange and EMI offers are recorded separately from the displayed selling price.

| Shop             | Product URL                                                                                                                                    | Visit | Date and time                | Selling price           | MRP                   | Offer, badge or "was" price |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ---------------------------- | ----------------------- | --------------------- | --------------------------- |
| Croma | https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023 | 1 | 12 October 2026, 12:52 PM | ₹8,390.00 | ₹12,000.00 | Save ₹3,610 (30.08% off); exchange up to ₹1,700 off; ₹395/mo EMI |
| Croma | https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023 | 2 (short repeat check) | 12 October 2026, 1:05 PM | ₹8,390.00 | ₹12,000.00 | Save ₹3,610 (30.08% off); exchange up to ₹1,700 off; ₹395/mo EMI |
| Croma | https://www.croma.com/croma-10-kg-5-star-fully-automatic-top-load-washing-machine-aqua-reserve-neel-black-/p/322406 | 1 | 12 October 2026, 12:03 PM | ₹19,990.00 | ₹36,000.00 | Save ₹16,010 (44.47% off); extra ₹1,000 bank offer; exchange benefit up to ₹1,700; no-cost EMI |
| Croma | https://www.croma.com/croma-10-kg-5-star-fully-automatic-top-load-washing-machine-aqua-reserve-neel-black-/p/322406 | 2 (short repeat check) | 12 October 2026, 1:06 PM | ₹19,990.00 | ₹36,000.00 | Save ₹16,010 (44.47% off); extra ₹1,000 bank offer; exchange benefit up to ₹1,700; no-cost EMI |
| Croma | https://www.croma.com/croma-7-5-kg-5-star-fully-automatic-top-load-washing-machine-fuzzy-control-grey-/p/243594 | 1 | 12 October 2026, 12:06 PM | ₹14,390.00 | ₹24,000.00 | Save ₹9,610 (40.04% off); exchange up to ₹1,700 off; ₹677/mo EMI |
| Croma | https://www.croma.com/croma-7-5-kg-5-star-fully-automatic-top-load-washing-machine-fuzzy-control-grey-/p/243594 | 2 (short repeat check) | 12 October 2026, 1:07 PM | ₹14,390.00 | ₹24,000.00 | Save ₹9,610 (40.04% off); exchange up to ₹1,700 off; ₹677/mo EMI |
| Reliance Digital | https://www.reliancedigital.in/product/lloyd-8-kg-top-loading-semi-automatic-washing-machine-elante-glwms80avgel-lg55vo | 1 | 12 October 2026, 12:24 PM | ₹13,590.00 (Deal Price) | ₹19,990.00 | LIMITED_TIME_OFFER; Offer Price ₹15,490.00 (crossed out); ₹12,571.00 with all applicable offers |

**What changed:** No displayed price change in the Croma 6.5 kg product between 12:52 PM and 1:05 PM (13 minutes), the 10 kg product between 12:03 PM and 1:06 PM (63 minutes), or the 7.5 kg product between 12:06 PM and 1:07 PM (61 minutes). These are short repeat checks, not the several-hours-later comparison requested. The Lloyd observation was made before Reliance Digital’s section 12 restriction was reviewed.

**What this tells us:** The recorded pages show discounts against MRP. Prices did not change during the short repeat-check intervals; these observations do not establish longer-term price movement. No “deal ends” badge was visible in the supplied Croma screenshots.

## 4. Recommendation — 12 October 2026

**Pick:** Croma is the only candidate of the two not expressly ruled out by the reviewed terms. This is not approval to begin automated collection.

**Category URL:** https://www.croma.com/home-appliances/washing-machines-dryers/c/48

**Why Croma:**

1. **Terms and robots.txt:** Croma sections 7(d)–7(e) do not explicitly mention automated price tracking; its `User-agent: *` robots rules include `Allow: /*` and no listed `Disallow` matching the selected category path. This is not legal permission to scrape. Reliance Digital section 12 prohibits bots or scraping.
2. **Price fields:** The Croma 10 kg product’s source prices match the displayed page; the 6.5 kg source selling price does not (₹7,990 in source versus ₹8,390 displayed).
3. **Price movement:** No movement appeared during the short repeat checks; longer-term movement remains unknown.

**Main risk:** Croma’s terms are unclear about automated collection, and one product’s source selling price differs from its displayed price. Resolve the terms concern and validate price consistency before enabling automated collection.

**Why not Reliance Digital:** Section 12 of its Terms of Use says not to use “any bots or scrape Reliance Digital Platform for any information.”

**Implementation changes if Croma is approved:** Set `SOURCE_KEY` to `croma` (currently `demo-shop`) and `SCRAPE_TARGET_URL` to the category URL above. `parse_listing` selectors still need verification against the category-card HTML, which was not inspected. Store the displayed selling price, not bank, exchange, EMI, or conditional-offer amounts; validate source/display consistency because one product’s source selling price differed from its displayed price.
