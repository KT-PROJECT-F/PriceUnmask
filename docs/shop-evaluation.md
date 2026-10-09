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

### 3. Price Comparison

The issue requires three products from each shop to be checked at 10:30 AM and 3:30 PM.

The following are individual product pages to use for the comparison. Record prices and MRPs from your actual observations; do not treat the links or current listings as evidence of historical price changes.

Shop

Product URL

10:30 AM price

10:30 AM MRP

3:30 PM price

3:30 PM MRP

Changed?

Croma

6.5 kg Semi-Automatic Washing Machine, Burgundy

Not recorded

Not recorded

Not recorded

Not recorded

Unverified

Croma

6.5 kg Fully Automatic Washing Machine, Inox Grey

Not recorded

Not recorded

Not recorded

Not recorded

Unverified

Croma

8 kg Semi-Automatic Washing Machine, Black

Not recorded

Not recorded

Not recorded

Not recorded

Unverified

Reliance Digital

Samsung 6.5 kg Fully Automatic Washing Machine

Not recorded

Not recorded

Not recorded

Not recorded

Unverified

Reliance Digital

Voltas Beko 6.5 kg Fully Automatic Washing Machine

Not recorded

Not recorded

Not recorded

Not recorded

Unverified

Reliance Digital

LG 7.5 kg Fully Automatic Washing Machine

Not recorded

Not recorded

Not recorded

Not recorded

Unverified

The existing observations establish that both shops display prices and discounts, but they do not establish that either shop's prices changed during the day.

If no price moved during the observation period, record that result and say whether a displayed “was” price or “deal ends” badge suggests a discount without proving that the actual price changed.

## 4. Recommendation (9 October 2026)

Provisional pick: Croma.

Category URL to evaluate: https://www.croma.com/campaign/best-deals/c/7625

Why this one

Terms and robots.txt: The recorded robots.txt inspection did not identify an explicit disallow rule for the selected category path. However, the applicable Terms of Use still need to be reviewed to determine whether the proposed automated collection is permitted.

Prices in raw HTML: The initial inspection found pricing fields, including formattedValue and mrp, in the category page source.

Price changes: Price changes have not yet been established using timestamped observations. The six-product comparison must be completed before the recommendation can be treated as final.

Main risk: Croma's applicable terms may not permit the proposed automated collection. If permission cannot be established, do not proceed with automated scraping; choose another source.

Why not Reliance Digital?

Reliance Digital also exposes pricing information, but the recorded product page shows a ₹17,499 deal price and a ₹18,999 offer price. The correct value to track needs clarification. Its automated-access permission and price changes also remain unverified.

Conditions before implementation

Read the applicable Terms of Use and record the exact relevant sentence and section number for both shops.

Confirm that the category/listing URL is suitable for collecting product listings.

Complete the three-product price comparison for each shop using genuine observations.

Determine which price field should be recorded when multiple prices appear.

Do not begin automated collection until the access restrictions have been resolved.

If the chosen shop proves unsuitable, stop and select another candidate in accordance with docs/ARCHITECTURE.md, section 8.
