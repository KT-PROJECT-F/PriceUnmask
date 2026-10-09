# Shop Evaluation

**Evaluation date:** 9 October 2026

**Purpose:** Evaluate Croma and Reliance Digital as potential shops for future price tracking in PriceUnmask.

## 1. Croma

* **Shop:** https://www.croma.com/
* **Category URL evaluated:** https://www.croma.com/campaign/best-deals/c/7625
* **Product evaluated:** Croma 6.5 kg 5 Star Semi Automatic Washing Machine with Built-in Soak Function (Burgundy)
* **Product URL:** https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023

### Evaluation

| Check                   | Result                                              | Evidence                                                                                                                                                                                                                           |
| ----------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| robots.txt              | Requires final verification                         | https://www.croma.com/robots.txt — initial notes recorded `User-agent: *` and `Allow: /*`. Recheck the rules applicable to the selected category path before implementation. robots.txt alone does not grant permission to scrape. |
| Terms of Use            | Unclear                                             | https://www.croma.com/terms-of-use — initial notes identified sections 7(d) and 7(e) as potentially relevant to website use and unauthorized access. Verify the exact wording and applicable restrictions before implementation.   |
| Price in raw HTML       | Reported in initial inspection; requires rechecking | Initial notes recorded pricing fields such as `formattedValue` and `mrp` in the category page source. Confirm these fields in the current page source before implementation.                                                       |
| Discount display        | Reported in initial inspection; requires rechecking | Initial notes recorded a displayed price of ₹7,790, an MRP of ₹12,000, and savings of ₹4,210. Recheck the live product page before treating these figures as current.                                                              |
| Price changes over time | Not verified                                        | Two independently recorded observations of the same product are required to establish price movement.                                                                                                                              |

### Assessment

The initial inspection reported that Croma displayed a product price, MRP, and discount, and that pricing fields were present in the category page source.

However, the applicable Terms of Use do not yet establish permission for automated price collection. The relevant terms and robots.txt rules must be reviewed before implementation. Price movement has not been established through two observations.

## 2. Reliance Digital

* **Shop:** https://www.reliancedigital.in/
* **Category evaluated:** Washing Machines
* **Example product URL from the initial inspection:** https://www.reliancedigital.in/product/oppo-k14x-5g-64-gb-4-gb-ram-prism-violet-mobile-phone-mnd10i-9996248

**Category consistency:** The OPPO product URL above is for a mobile phone, not a washing machine. The washing-machine products listed in Section 3 are used for the price comparison.

### Evaluation

| Check                   | Result                                              | Evidence                                                                                                                                                                                                                                              |
| ----------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| robots.txt              | Requires rechecking                                 | https://www.reliancedigital.in/robots.txt — initial notes recorded `User-agent: *`, an empty `Disallow:` directive, and restrictions for some paths and query URLs. Recheck the rules applicable to the intended washing-machine category URL.        |
| Terms of Use            | Unclear; manual verification required               | Open the official website's footer and select Policies → Terms of Use. Check the exact terms relating to automated access, crawling, scraping, bots, data mining, and extraction. Record the relevant section numbers and wording after verification. |
| Price in raw HTML       | Reported in initial inspection; requires rechecking | Initial notes recorded structured pricing data on the OPPO product page, including `"priceCurrency": "INR"` and `"price": "17499"`. Confirm the price fields on a current washing-machine product page before relying on them.                        |
| Discount display        | Reported in initial inspection; requires rechecking | Initial notes recorded a deal price of ₹17,499, an offer price of ₹18,999, an MRP of ₹31,999, and a displayed discount of 45% for the OPPO product. These historical notes do not establish current washing-machine prices.                           |
| Price changes over time | Not verified                                        | Two independently recorded observations of the same product are required to establish price movement.                                                                                                                                                 |

### Assessment

The initial inspection reported structured pricing information on a Reliance Digital product page. Multiple price values were recorded, so the correct selling-price field must be identified before implementing a tracker.

The applicable Terms of Use and robots.txt rules still need to be checked. The current evidence does not establish price movement over time or permission for automated price collection.

## 3. Price Observations

The following prices and promotional details were recorded in the initial inspection notes on 9 October 2026. The exact observation time has not been confirmed here. No scraping scripts were used to collect these observations.

Three washing-machine products were selected from each shop. The second observation has not yet been recorded, so price movement cannot currently be established.

### First Observation

| Shop             | Product URL                                                                                                                                    | Observation Date | Displayed Price |     MRP | Displayed Discount or Offer                                          |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | --------------: | ------: | -------------------------------------------------------------------- |
| Croma            | https://www.croma.com/croma-6-5-kg-5-star-semi-automatic-washing-machine-with-built-in-soak-function-burgundy-/p/307023                        | 9 Oct 2026       |          ₹7,790 | ₹12,000 | Save ₹4,210; 35.08% off; extra ₹800 discount                         |
| Croma            | https://www.croma.com/croma-10-kg-5-star-fully-automatic-top-load-washing-machine-aqua-reserve-neel-black-/p/322406                            | 9 Oct 2026       |         ₹19,990 | ₹36,000 | Save ₹16,010; 44.47% off; extra ₹1,000 bank offer; exchange benefits |
| Croma            | https://www.croma.com/croma-7-5-kg-5-star-fully-automatic-top-load-washing-machine-fuzzy-control-grey-/p/243594                                | 9 Oct 2026       |         ₹13,990 | ₹24,000 | Save ₹10,010; 41.71% off; extra discount and exchange benefits       |
| Reliance Digital | https://www.reliancedigital.in/product/lloyd-8-kg-top-loading-semi-automatic-washing-machine-elante-glwms80avgel-lg55vo                        | 9 Oct 2026       |         ₹13,590 | ₹19,990 | 32% off; offer price ₹15,490; ₹12,571 with applicable offers         |
| Reliance Digital | https://www.reliancedigital.in/product/bosch-9-kg-fully-automatic-front-loading-washing-machine-black-grey-wga244ztin-ly4e6h-7724948           | 9 Oct 2026       |         ₹43,990 | ₹58,990 | Deal price ₹43,990; offer price ₹47,490; 25% off                     |
| Reliance Digital | https://www.reliancedigital.in/product/ifb-8-kg-fully-automatic-front-loading-washing-machine-metallic-silver-senator-msn-8012k-lzj0an-8112379 | 9 Oct 2026       |         ₹38,890 | ₹47,080 | Deal price ₹38,890; offer price ₹39,890; 17% off                     |

These figures are recorded observations, not independently reverified current prices. Recheck the live product pages before relying on them.

### Second Observation

A second observation is required for each of the six selected products.

| Shop             | Product                                                        | Second Observation Date | Price        | MRP          | Result  |
| ---------------- | -------------------------------------------------------------- | ----------------------- | ------------ | ------------ | ------- |
| Croma            | 6.5 kg Semi-Automatic Washing Machine, Burgundy                | Pending                 | Not recorded | Not recorded | Pending |
| Croma            | 10 kg Fully Automatic Top-Load Washing Machine, Aqua Reserve   | Pending                 | Not recorded | Not recorded | Pending |
| Croma            | 7.5 kg Fully Automatic Top-Load Washing Machine, Fuzzy Control | Pending                 | Not recorded | Not recorded | Pending |
| Reliance Digital | Lloyd 8 kg Semi-Automatic Washing Machine                      | Pending                 | Not recorded | Not recorded | Pending |
| Reliance Digital | Bosch 9 kg Fully Automatic Front-Load Washing Machine          | Pending                 | Not recorded | Not recorded | Pending |
| Reliance Digital | IFB 8 kg Fully Automatic Front-Load Washing Machine            | Pending                 | Not recorded | Not recorded | Pending |

### What Changed?

Price movement cannot yet be established because only one observation is recorded for each selected product.

The difference between an MRP and a displayed selling price does not, by itself, prove that the product's price changed over time. Promotional badges, bank discounts, and exchange offers do not independently establish a historical price reduction.

### What This Tells Us

The first observation provides an initial record of displayed prices and promotional offers for three products from each shop.

However, the available evidence is insufficient to determine whether either shop changes prices over time. The actual selling price must also be distinguished from offer prices, bank discounts, exchange benefits, and other conditional offers.

### Next Verification Steps

1. Revisit the same six product pages and record the actual date and time of the second observation.
2. Record the displayed selling price and MRP exactly as shown.
3. Record promotional badges and conditional offers separately from the selling price.
4. Compare each product's first and second observations.
5. If a product's displayed selling price is unchanged, record "No price movement observed."
6. If a price changes, record both observations and calculate the difference.
7. If any price or offer cannot be verified, leave it marked as pending rather than inventing a value or timestamp.

**Observation status:** Initial prices recorded; second observations pending. No verified price movement has been established.

## 4. Recommendation (9 October 2026)

**Provisional recommendation: Croma, pending verification.**

**Category URL to evaluate:** https://www.croma.com/home-appliances/washing-machines-dryers/c/48

### Why Croma Is the Provisional Candidate

1. **Terms of Use and robots.txt**

   The initial review recorded wording from section 7(d) of Croma's Terms of Use concerning website use that could damage, disable, overburden, or impair the website or interfere with other users.

   The exact wording of section 7(e) still needs verification. These clauses do not establish whether the proposed automated price tracking is permitted. The current Terms of Use and robots.txt rules must be checked before implementation. robots.txt alone does not grant permission to scrape.

2. **Price availability in HTML**

   The initial inspection notes report that `formattedValue` and `mrp` appeared in Croma's category-page source. These fields must be verified again against the selected category URL before implementation.

   Confirm the actual product title, product URL, selling price, and MRP in the current page source. Do not assume that the field names or structure remain unchanged.

3. **Price changes**

   Section 3 does not yet contain complete observations from two visits for every product. Therefore, price movement has not been established, and displayed discount claims have not been independently verified.

4. **Comparison with Reliance Digital**

   The initial notes report multiple price values on a Reliance Digital product page. The correct selling-price field has not yet been verified against the current page source.

   Reliance Digital's applicable Terms of Use and robots.txt rules also need to be checked before it can be considered a suitable alternative.

### Main Risk

The main risk is that the applicable Terms of Use or robots.txt rules may not permit the proposed automated collection.

Do not begin automated collection until the applicable restrictions have been reviewed. If Croma is ruled out, evaluate Reliance Digital only after checking its terms, robots.txt rules, category page, and price fields. Follow the fallback strategy in `docs/ARCHITECTURE.md`, section 8.

### Why Not Reliance Digital Yet?

The current evidence does not establish that Reliance Digital is a better choice. Its applicable Terms of Use, robots.txt rules, and actual selling-price field remain to be verified.

Section 3 also lacks complete second observations, so neither shop has demonstrated price movement through the recorded evidence.

### What Would Change in Our Code if Croma Is Approved?

* **`parse_listing`:** Update the listing parser to match the verified product-card structure in Croma's category-page HTML. Extract the product title, product URL, displayed selling price, and MRP using fields or selectors confirmed against the actual response.
* **`SOURCE_KEY` and `SCRAPE_TARGET_URL`:** Use the project's chosen Croma source identifier for `SOURCE_KEY`. Set `SCRAPE_TARGET_URL` to the verified category URL: `https://www.croma.com/home-appliances/washing-machines-dryers/c/48`.
* **Currency:** Use INR if the inspected listing confirms that prices are displayed in Indian rupees.
* **Price field:** Store the actual displayed selling price as the tracked price. Keep MRP and displayed discount as separate fields if supported by the project architecture. Verify the exact field names and meanings before implementing the parser.

### Evidence Required Before Final Approval

* Verify the current Terms of Use for both shops and record exact relevant section numbers and quotations.
* Inspect the current robots.txt rules for both proposed category paths.
* Confirm that Croma's selected category URL is stable and suitable for listing products.
* Verify price fields in the actual HTML response.
* Complete two observations for all six products in Section 3, recording the actual dates and times.
* Confirm that the chosen shop satisfies the project's scraping rules before implementing automated collection.

**Decision status:** Croma remains a provisional candidate. The evidence is not yet sufficient for a final recommendation.
