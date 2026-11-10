# Shop Evaluation

**Evaluation date:** 3 November 2026

**Purpose:** Evaluate Croma, Reliance Digital, and Web Scraper's demo site as potential sources for
PriceUnmask, and document the price observations used to assess feasibility.

## Evaluation Standard

A practice site is considered suitable only after reviewing the current `robots.txt` rules for the
exact listing and product paths under the applicable user-agent group, with no matching
`Disallow`. A robots.txt error or unclear rule leaves the site unverified; an allowed path is not
permission by itself.

The applicable terms must explicitly permit the intended automated access and use, or the site
owner must provide written permission. Permission to fetch a page does not automatically permit
retaining or redistributing it as a test fixture; that use must also be covered. Record the source
URLs, relevant rule or terms clause, and review date. If either robots or terms are unclear, do not
call the site clear or enable collection.

## 1. Croma

**Shop:** https://www.croma.com/
**Category URL:** https://www.croma.com/home-appliances/washing-machines-dryers/c/48

| Check             | Result                          | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ----------------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Terms of Use      | Unclear                         | https://www.croma.com/terms-of-use — Section 7(d) prohibits use that could damage or overburden the site; Section 7(e) says not to obtain information through means not intentionally made available. On 3 November 2026, browser Find for `scrape`, `automated`, `bot`, and `robot` found no matches. Neither this nor the public product page establishes permission for automated collection. |
| robots.txt        | Selected category path not disallowed by visible rules | https://www.croma.com/robots.txt — On 3 November 2026, the visible `User-agent: *` block included `Allow: /*`; browser Find did not find the selected category path. No matching disallow was identified. This is not permission to scrape. |
| Price in raw HTML | Found; one mismatch and one price not found | 10 kg product https://www.croma.com/croma-10-kg-5-star-fully-automatic-top-load-washing-machine-aqua-reserve-neel-black-/p/322406 — `offers.price` and `pdpPriceReducer.pdpPriceData.sellingPrice.value` = `19990.00`; `pdpPriceReducer.pdpPriceData.mrp.value` = `36000.00`, matching the displayed ₹19,990.00 and ₹36,000.00. 6.5 kg product https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023 — source `sellingPrice.value` = `7990.00`, while the page displayed ₹8,390.00; `mrp.value` = `12000.00`, matching ₹12,000.00. 7.5 kg product https://www.croma.com/croma-7-5-kg-5-star-fully-automatic-top-load-washing-machine-fuzzy-control-grey-/p/243594 — browser Find returned 0/0 for both `14390.00` and `14390`; the displayed selling-price value was not found in page source. |
| Price changes     | Observed on 3 November 2026 | The 10 kg product was ₹19,990.00 on 12 October 2026 and ₹19,390.00 on 3 November 2026, with MRP ₹36,000.00 on both observations. On 3 November, the displayed discount was ₹16,610 (46.14% off). This is a manual browser observation; it has not been collected by the application. |

## 2. Reliance Digital

**Shop:** https://www.reliancedigital.in/
**Category URL:** https://www.reliancedigital.in/sections/washing-machines

| Check             | Result                                        | Evidence                                                                                                                                                                                                                                                                                                                                                                                         |
| ----------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Terms of Use      | Forbidden                                     | https://www.reliancedigital.in/c/terms-of-use — Section 12: “Introduce any Trojans, viruses, any other malicious software, any bots or scrape Reliance Digital Platform for any information;” This prohibits using bots or scraping the platform for information. Reviewed 12 October 2026.                                                                                                                                                      |
| robots.txt        | Allowed by listed rules | https://www.reliancedigital.in/robots.txt — `User-agent: *`; `/sections/washing-machines` has no matching `Disallow`, and its general `Disallow:` is empty. Rules in the block: `Disallow:` (empty); `Disallow: /cart`; `Disallow: /checkout`; `Disallow: /c/rone-loyalty`; `Disallow: /auth/register`; `Disallow: /c/my-credit`; `Disallow: /c/pan-gst`; `Disallow: /profile`; `Disallow: /products?q=*`; `Disallow: /wishlist`; `Disallow: /solutionbox`; `Disallow: /c/resource-center/products?q=`; `Disallow: /*?is_available=`; `Disallow:/*?internal_source=*`; `Disallow: /*?is_available=*`; `Disallow: /*?*`; `Disallow: /?page_no=*`; `Disallow: /?storeId=*`; `Disallow: /?gad_source=*`; `Allow: /c/resource-center/tag/`. Reviewed 12 October 2026. This is not permission to scrape. |
| Price in raw HTML | Yes                                           | Lloyd washing machine https://www.reliancedigital.in/product/lloyd-8-kg-top-loading-semi-automatic-washing-machine-elante-glwms80avgel-lg55vo — source `offers.price` = `13590`, matching displayed Deal Price ₹13,590; `selling.min` and `selling.max` = `15490`, matching displayed Offer Price ₹15,490. |
| Price changes     | Not assessed                                  | Reliance Digital is ruled out for automated tracking by section 12 of its Terms of Use; no second product-price visit was made.                                                                                                                                                                                                                          |

## 3. Web Scraper Demo Site

**Shop:** https://webscraper.io/
**Practice listing URL:** https://webscraper.io/test-sites/e-commerce/static/computers/laptops
**Evaluation date:** 10 November 2026

| Check | Result | Evidence |
|---|---|---|
| robots.txt | No matching disallow found | https://webscraper.io/robots.txt — Retrieved on 10 November 2026. The file's complete rules are `User-agent: *`, `Disallow: /test-sites/product/`, `Disallow: /test-sites/pagination/`, `Disallow: /test-sites/pagination*?page=`, `Disallow: /test-sites/scroll/`, `Disallow: /test-sites/load-more/`, and `Sitemap: https://webscraper.io/sitemap.xml`. None of the five `Disallow` rules matches the proposed `/test-sites/e-commerce/static/computers/laptops` listing, its `?page=2` pagination URL, or product paths under `/test-sites/e-commerce/static/`. This robots.txt review does not grant permission under the site's terms. |
| Test-site purpose | Permission for fixture use not established | https://webscraper.io/test-sites — Retrieved on 10 November 2026. The page says: “Here are some test sites that you can use for training while learning how to use the Web Scraper extension.” This identifies the pages as training sites for learning the extension, but does not expressly address automated collection by PriceUnmask or retaining/redistributing a page as a repository fixture. Reviewer/site-owner determination is needed before treating this as permission for those uses. |
| Fixture | Not collected pending terms decision | The robots.txt rules do not disallow the proposed path. No real listing page has been added as a fixture because the test-sites page does not clarify whether retaining its HTML in this repository is permitted. Tests currently use controlled HTML only. |
| Adapter tests | Local parser tests | Controlled HTML tests cover valid product cards, cards without a price or link, and product links to an external host. These tests require no network access and do not establish permission for live collection. |

**Decision:** The reviewed robots.txt does not disallow the proposed e-commerce paths, but that alone does not establish permission for collection or retaining a real-page fixture. Ask the reviewer to determine whether the stated training purpose is sufficient or whether written permission is needed. Until then, do not enable live collection or claim the real-page fixture requirement is complete.

## 4. Price Observations — Croma and Reliance Digital

Manual browser observations for Croma and Reliance Digital; bank, exchange and EMI offers are
recorded separately from the displayed selling price. The Web Scraper demo section is a practice
site review, not a retail price observation, and is therefore not included in this table.

| Shop             | Product URL                                                                                                                                    | Visit | Date and time                | Selling price           | MRP                   | Offer, badge or "was" price |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ---------------------------- | ----------------------- | --------------------- | --------------------------- |
| Croma | https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023 | 1 | 12 October 2026, 12:52 PM | ₹8,390.00 | ₹12,000.00 | Save ₹3,610 (30.08% off); exchange up to ₹1,700 off; ₹395/mo EMI |
| Croma | https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023 | 2 (short repeat check) | 12 October 2026, 1:05 PM | ₹8,390.00 | ₹12,000.00 | Save ₹3,610 (30.08% off); exchange up to ₹1,700 off; ₹395/mo EMI |
| Croma | https://www.croma.com/croma-10-kg-5-star-fully-automatic-top-load-washing-machine-aqua-reserve-neel-black-/p/322406 | 1 | 12 October 2026, 12:03 PM | ₹19,990.00 | ₹36,000.00 | Save ₹16,010 (44.47% off); extra ₹1,000 bank offer; exchange benefit up to ₹1,700; no-cost EMI |
| Croma | https://www.croma.com/croma-10-kg-5-star-fully-automatic-top-load-washing-machine-aqua-reserve-neel-black-/p/322406 | 2 (short repeat check) | 12 October 2026, 1:06 PM | ₹19,990.00 | ₹36,000.00 | Save ₹16,010 (44.47% off); extra ₹1,000 bank offer; exchange benefit up to ₹1,700; no-cost EMI |
| Croma | https://www.croma.com/croma-10-kg-5-star-fully-automatic-top-load-washing-machine-aqua-reserve-neel-black-/p/322406 | 3 | 3 November 2026, 1:28 PM IST | ₹19,390.00 | ₹36,000.00 | Save ₹16,610 (46.14% off); extra ₹1,000 bank offer; exchange benefit up to ₹1,700; no-cost EMI |
| Croma | https://www.croma.com/croma-7-5-kg-5-star-fully-automatic-top-load-washing-machine-fuzzy-control-grey-/p/243594 | 1 | 12 October 2026, 12:06 PM | ₹14,390.00 | ₹24,000.00 | Save ₹9,610 (40.04% off); exchange up to ₹1,700 off; ₹677/mo EMI |
| Croma | https://www.croma.com/croma-7-5-kg-5-star-fully-automatic-top-load-washing-machine-fuzzy-control-grey-/p/243594 | 2 (short repeat check) | 12 October 2026, 1:07 PM | ₹14,390.00 | ₹24,000.00 | Save ₹9,610 (40.04% off); exchange up to ₹1,700 off; ₹677/mo EMI |
| Reliance Digital | https://www.reliancedigital.in/product/lloyd-8-kg-top-loading-semi-automatic-washing-machine-elante-glwms80avgel-lg55vo | 1 | 12 October 2026, 12:24 PM | ₹13,590.00 (Deal Price) | ₹19,990.00 | LIMITED_TIME_OFFER; Offer Price ₹15,490.00 (crossed out); ₹12,571.00 with all applicable offers |

**What changed:** The Croma 10 kg washing machine price decreased by ₹600 (about 3.0%) from ₹19,990.00 on 12 October to ₹19,390.00 on 3 November, while its ₹36,000.00 MRP remained unchanged. The earlier same-day Croma repeat checks showed no price change. These observations were made manually in a browser; no automated Croma collection has been run.

**What this tells us:** The manual observations show both a real displayed price change and a discount claim against MRP. This establishes that Croma can supply evidence relevant to the anomaly and trust-score features, but not that automated collection is permitted.

## 5. Recommendation — 3 November 2026

**Pick:** Of the two retail shops evaluated, Croma is the only one not expressly ruled out by the
reviewed terms. It is not approved for automated collection. Web Scraper's demo site was also
evaluated: its proposed listing path is not disallowed by the robots.txt reviewed on 10 November
2026, but the test-sites page does not establish permission to collect or retain the page as a
fixture. The required second ToS-clear practice site remains unresolved pending reviewer or
site-owner determination.

**Category URL:** https://www.croma.com/home-appliances/washing-machines-dryers/c/48

**Current implementation/evidence status:**

1. **Terms and robots.txt:** The visible Croma robots rules did not disallow the chosen category path. Croma’s terms remain unclear about automated collection; robots.txt is not permission.
2. **Page data:** The category page source has no product links (`/p/` search returned 0) or product structured data (`"@type": "Product"` returned 0). Individual product HTML does expose `pdpPriceReducer.pdpPriceData.sellingPrice.value` and `mrp.value`, matching the 3 November displayed price and MRP for product 322406.
3. **Price movement and discount:** Manual browser observations show the 10 kg product changed from ₹19,990.00 to ₹19,390.00 and displayed a 46.14% discount against MRP.
4. **Scraper scope:** The implementation supports a directly configured Croma product-detail URL, not category discovery. Use the existing delay, User-Agent, and robots checks; do not use proxies or fake browsers.

**Main risk:** Croma’s terms are unclear about automated collection, and prior evaluation found a source/display mismatch on another product. Do not start automated collection until these concerns are resolved. If Croma blocks collection or is not suitable, stop and evaluate a different shop permitted by its terms; Reliance Digital is not a fallback because section 12 prohibits bots or scraping.

**Why not Reliance Digital:** Section 12 of its Terms of Use says not to use “any bots or scrape Reliance Digital Platform for any information,” so it is ruled out.

**To enable a supervised Croma collection after permission is established:** Set `SCRAPE_TARGET_URL` to the individual product URL above, not the category URL. The collector stores Croma products under source `croma`; each scrape goes through the configured User-Agent, robots.txt check, and polite delay. The category URL is not supported because its static source contains no product links or prices. Store the displayed selling price, not bank, exchange, EMI, or conditional-offer amounts.
