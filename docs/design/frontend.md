# Frontend Design Note

## What it does

PriceUnmask provides a web interface for searching products, viewing product details, and checking historical prices. It displays Trust Score labels and reasons to help shoppers understand whether a discount appears genuine, likely inflated, or cannot be judged. It also displays price-history charts, anomaly information, and collector status. The frontend uses HTML, CSS, and JavaScript and communicates with the backend through the `/api` endpoints.

## Decisions

- **Plain JavaScript instead of a frontend framework:** The existing application uses HTML, CSS, and JavaScript. Keeping this approach avoids adding a frontend framework and allows the current application structure to remain simple.
- **Chart.js for price history:** Chart.js displays historical prices in the product detail view. A chart library provides a convenient way to visualize price changes over time instead of building a chart manually.
- **Relative API URL:** The frontend uses `/api` as its API base URL. This allows requests to use the same origin as the application rather than depending on a hard-coded backend address.
- **Price formatting:** The frontend uses a shared price-formatting function to display prices consistently, including currency formatting and handling missing values. This keeps formatting logic in one place.
- **Trust Score validation:** The frontend validates the returned Trust Score information before displaying it. Unsupported or missing labels should not be presented as valid assessments because shoppers could misunderstand the result.
- **Separate product, Trust Score, and history requests:** These requests are handled independently so that a Trust Score or price-history failure does not necessarily prevent the product details from appearing.
- **Collector response handling:** The Run now action handles accepted requests and an already-running collector separately. HTTP `202 Accepted` indicates that a request has been accepted for processing; HTTP `409 Conflict` can indicate that a collection is already running. The interface also polls for completion and displays status messages.

## How it fails, and what happens then

- **API unavailable:** If product loading fails, the frontend displays an error message rather than leaving the user with an unexplained empty result.
- **No search results:** The frontend displays a message when no products match the search.
- **No price history:** The product detail view displays an explanatory message when historical price data is unavailable.
- **Trust Score unavailable:** The product details can still be displayed when the Trust Score request fails, with a fallback message for the unavailable assessment.
- **Invalid response data:** The frontend validates important response fields and uses fallback behavior when data is missing or invalid.
- **Chart.js unavailable:** The frontend displays a message when the chart library cannot be used.
- **Collector request fails:** The interface displays an error message and restores the Run now button when appropriate.
- **No discount to evaluate:** The frontend can display the No Discount state rather than presenting a discount assessment that the data does not support.

These behaviors aim to make failures understandable and prevent a problem in one feature from unnecessarily blocking other product information.

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

**Testing status:** Record the actual results of the manual checks and repository commands before submitting the pull request. Do not report a scenario as passed until it has been tested. The frontend behavior described here is based on the current implementation; the manual checks still need to confirm it in the running application.

## Known limits and what we would do next

- Historical charts depend on the availability and quality of saved price snapshots.
- Trust Score and anomaly information depend on backend responses and available historical data.
- Chart rendering depends on Chart.js loading successfully from its configured CDN.
- Collector status depends on the scrape-run information returned by the backend.
- Manual browser testing is needed to confirm responsive behavior and failure messages.
- More frontend-specific automated tests would help protect search, product details, Trust Score rendering, and error handling against regressions.
- Further improvements could include broader testing of API failures, clearer recovery guidance, and additional responsive-layout checks.