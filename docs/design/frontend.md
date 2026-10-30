# Frontend Design Note

## What it does

PriceUnmask provides a web interface for searching products, viewing product details, and checking historical prices. It displays Trust Score labels and reasons to help shoppers understand whether a discount appears genuine, likely inflated, or cannot be judged. It also displays price-history charts, anomaly information, and collector status. The frontend uses HTML, CSS, and JavaScript and communicates with the backend through the `/api` endpoints.

## Decisions

- **Plain JavaScript instead of a frontend framework:** The existing application uses HTML, CSS, and JavaScript. Keeping this approach avoids adding a frontend framework and allows the current application structure to remain simple. See [`frontend/script.js`](../../frontend/script.js).

- **Chart.js for price history:** Chart.js displays historical prices in the product detail view. A chart library provides a convenient way to visualize price changes over time instead of building a chart manually. See [chart initialization and fallback handling](../../frontend/script.js#L539).

- **Relative API URL:** The frontend uses `/api` as its API base URL. This allows requests to use the same origin as the application rather than depending on a hard-coded backend address. See [`API_BASE_URL`](../../frontend/script.js#L2).

- **Price formatting:** The frontend uses a shared price-formatting function to display prices consistently, including currency formatting and handling missing values. This keeps formatting logic in one place. See [`formatPrice`](../../frontend/script.js#L33).

- **Trust Score validation:** The frontend validates the returned Trust Score information before displaying it. Unsupported or missing labels should not be presented as valid assessments because shoppers could misunderstand the result. See [`loadTrustScore`](../../frontend/script.js#L358).

- **Separate product, Trust Score, and history requests:** These requests are handled independently so that a Trust Score or price-history failure does not necessarily prevent the product details from appearing. See [`showProductDetail`](../../frontend/script.js#L796).

- **Collector response handling:** The Run now action handles accepted requests and an already-running collector separately. HTTP `202 Accepted` indicates that a request has been accepted for processing; HTTP `409 Conflict` can indicate that a collection is already running. The interface also polls for completion and displays status messages. See [HTTP 409 handling](../../frontend/script.js#L219) and [HTTP 202 handling](../../frontend/script.js#L237).

## How it fails, and what happens then

- **API unavailable:** The frontend is designed to display an error message if product loading fails. This failure scenario has not yet been manually verified.
- **No search results:** Verified manually. Searching for `YZNonExistentProduct123` displayed `No products match your search.`
- **No price history:** The product detail view is designed to display an explanatory message when historical price data is unavailable. This scenario has not yet been manually verified.
- **Trust Score unavailable:** The product details are designed to remain available if the Trust Score request fails, with a fallback message for the unavailable assessment. This scenario has not yet been manually verified.
- **Invalid response data:** The frontend validates important response fields and uses fallback behavior when data is missing or invalid. Manual verification is still pending.
- **Chart.js unavailable:** The frontend is designed to display a message when the chart library cannot be used. This scenario has not yet been manually verified.
- **Collector request fails:** The interface is designed to display an error message and restore the Run now button when appropriate. Manual verification is still pending.
- **No discount to evaluate:** Verified on the A Light in the Attic detail page. The Trust Score displayed `No discount to judge`, with an explanatory reason.

These observations distinguish behavior verified in the browser from failure scenarios that still require testing. They also help identify which cases need additional manual verification.

## How it is tested

The frontend should be checked manually in a browser. The following scenarios cover the main user flows and failure cases:

1. Load the dashboard and confirm that product cards appear.
2. Search for an existing product and verify the results.
3. Search for a product that does not exist and verify the no-results message.
4. Open the Demo Air Fryer and check its Trust Score, reasons, and anomaly information.
5. Open the Demo Running Shoes and inspect the price-history chart.
6. Open a real book and verify the displayed No Discount state when applicable.
7. Check a product without price history and verify the explanatory message.
8. Stop or make the API unavailable temporarily and verify the product-loading error. Restart the application afterward.
9. Test the collector status panel and Run now behavior, including the already-running and error cases where they can be reproduced safely.
10. Check the product grid and detail views at desktop and phone widths.
11. Check keyboard activation and visible focus styling.

The repository also provides these quality checks:

```powershell
ruff check .
ruff format --check .
pytest -q
```

**Testing status:** The repository quality checks completed successfully: `ruff check .` passed, `ruff format --check .` passed, and `pytest -q` reported 339 passed with 1 warning. Eight demo screenshots were captured for the product grid and three product detail views at desktop and phone widths.

Three manual browser scenarios were verified:
1. **Product detail:** Opened *A Light in the Attic*. The detail view displayed the latest and lowest prices (£51.77), the **No discount to judge** Trust Score state, and its explanatory reason.
2. **No search results:** Searched for `YZNonExistentProduct123`. The frontend displayed **No products match your search.**
3. **Trust Score:** Opened *Demo Air Fryer (fake discount)*. The detail view displayed the latest price (₹1,049.00), lowest price (₹969.57), **20 — Likely inflated**, and the reasons for the assessment.

The remaining manual scenarios have not yet been verified and should not be reported as passed.

## Known limits and what we would do next

- Historical charts depend on the availability and quality of saved price snapshots.
- Trust Score and anomaly information depend on backend responses and available historical data.
- Chart rendering depends on Chart.js loading successfully from its configured CDN.
- Collector status depends on the scrape-run information returned by the backend.
- Manual browser testing is needed to confirm responsive behavior and failure messages.
- More frontend-specific automated tests would help protect search, product details, Trust Score rendering, and error handling against regressions.
- Further improvements could include broader testing of API failures, clearer recovery guidance, and additional responsive-layout checks.