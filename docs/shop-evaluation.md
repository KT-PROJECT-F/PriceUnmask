# Shop Evaluation

**Evaluation date:** 9 October 2026

**Purpose:** Evaluate two Indian e-commerce shops as potential candidates for future price tracking in PriceUnmask.

## 1. Croma

* **Shop:** https://www.croma.com/
* **Category URL:** https://www.croma.com/campaign/best-deals/c/7625
* **Product evaluated:** Croma 6.5 kg 5 Star Semi Automatic Washing Machine with Built-in Soak Function (Burgundy)
* **Product URL:** https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023

### Evaluation

| Check                   | Result                                                                                 | Evidence                                                                                                                                                                                                       |
| ----------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| robots.txt              | The selected category path does not appear explicitly disallowed by the rules checked. | https://www.croma.com/robots.txt — the checked rules include `User-agent: *` and `Allow: /*`. This is not, by itself, proof that automated scraping is permitted.                                              |
| Terms of Use            | Automated-access permission remains unconfirmed.                                       | https://www.croma.com/terms-of-use — sections 7(d) and 7(e) contain restrictions relating to harmful interference and unauthorized access. The applicable terms need careful review before automated tracking. |
| Price in raw HTML       | Yes, according to the initial inspection.                                              | The category page source was observed to contain product pricing fields, including `formattedValue` and `mrp`.                                                                                                 |
| Discount display        | Yes.                                                                                   | The product page displayed a price of ₹7,790, an MRP of ₹12,000, and savings of ₹4,210 (35.08% off).                                                                                                           |
| Price changes over time | Not verified.                                                                          | The current observation on 9 October 2026 showed ₹7,790. A separately timestamped earlier observation is not available to establish whether the price changed.                                                 |

### Assessment

Croma displays a product price, MRP, and discount. Pricing fields were also found in the category page source during the initial inspection. The checked robots.txt rules did not explicitly disallow the selected category path.

However, robots.txt alone does not establish permission for automated access. The Terms of Use require further review, and a price change over time has not been established.

## 2. Reliance Digital

* **Shop:** https://www.reliancedigital.in/
* **Product evaluated:** OPPO K14x 5G, 64 GB, 4 GB RAM, Prism Violet
* **Product URL:** https://www.reliancedigital.in/product/oppo-k14x-5g-64-gb-4-gb-ram-prism-violet-mobile-phone-mnd10i-9996248

### Evaluation

| Check                   | Result                                                                               | Evidence                                                                                                                                                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| robots.txt              | The selected product URL does not appear explicitly disallowed by the rules checked. | https://www.reliancedigital.in/robots.txt — the checked rules include `User-agent: *`, an empty `Disallow:` directive, and restrictions for specific paths and query URLs. This does not establish permission for automated access. |
| Terms of Use            | Automated-access permission remains unconfirmed.                                     | The Terms of Use are linked from the website. Initial searches for `scraping`, `automated`, and `robot` did not identify an explicit prohibition using those exact terms. This is not proof of permission.                          |
| Price in raw HTML       | Yes, according to the initial inspection.                                            | The product page source contained structured pricing data including `"priceCurrency": "INR"` and `"price": "17499"`. It also contained selling-price data with `min: 18999` and `max: 18999`.                                       |
| Discount display        | Yes.                                                                                 | The product page displayed a deal price of ₹17,499, an offer price of ₹18,999, an MRP of ₹31,999, and a displayed discount of 45%.                                                                                                  |
| Price changes over time | Not verified.                                                                        | The current observation on 9 October 2026 showed the prices listed above. A separately timestamped earlier observation is not available to establish whether the price changed.                                                     |

### Assessment

Reliance Digital exposes structured pricing information in the product page source. The product page displays a deal price, offer price, MRP, and discount.

The difference between the deal price and offer price needs to be understood before choosing which value a future tracker should record. Automated-access permission remains unconfirmed, and a price change over time has not been established.

## 3. Comparison

| Criterion                                                      | Croma                                   | Reliance Digital                                                                       |
| -------------------------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------- |
| Product price displayed                                        | Yes                                     | Yes                                                                                    |
| MRP and discount displayed                                     | Yes                                     | Yes                                                                                    |
| Pricing data found in page source                              | Yes, according to initial inspection    | Yes, according to initial inspection                                                   |
| Selected URL explicitly disallowed by checked robots.txt rules | Not observed                            | Not observed                                                                           |
| Automated-access permission confirmed                          | No                                      | No                                                                                     |
| Price changes over time verified                               | No                                      | No                                                                                     |
| Main outstanding concern                                       | Terms review and price-history evidence | Terms review, price-history evidence, and deal-price versus offer-price interpretation |

## 4. Preliminary Recommendation

Both Croma and Reliance Digital are candidates for further evaluation because their product pages display pricing and discount information, and pricing data was found in their page source during the initial inspection.

**Neither shop is conclusively recommended for automated price tracking at this stage.**

Before selecting a shop:

1. Complete a careful review of the applicable Terms of Use and access restrictions.
2. Record timestamped price observations at different times and compare them to establish whether prices change.
3. Confirm that any future scraper respects robots.txt, uses the configured User-Agent, and observes the required request delay.
4. If a shop is selected, verify the relevant category/listing URL and determine which displayed price should be tracked.
5. Run the project checks and record their actual results.

### Verification status

* Initial browser-based shop evaluation: recorded.
* Current product prices on 9 October 2026: recorded.
* Price changes over time: not established.
* Automated-access permission: not confirmed.
* Scraper logging and politeness check on Books to Scrape: completed separately.
* Project checks: 178 tests passed; Ruff checks passed during the recorded run.

**Final status:** Preliminary evaluation documented. Final shop selection remains pending further verification.
