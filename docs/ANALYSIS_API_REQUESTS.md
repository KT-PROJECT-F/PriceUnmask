# Analysis API Request Measurements — Issue #255

## Price-Drop API Request Count

Measured using Chrome DevTools Network tab on the PriceUnmask dashboard.

**Test setup:**
- Watched products: 20 (IDs 1–20)
- Available products: 63
- Browser: Chrome
- Network filter: Fetch/XHR, `price-drop`
- Browser cache: Disabled

**Results:**
- Price-drop API requests: **20**
- Price-drop API responses: HTTP 200
- Total network requests during page load: 95
- Page load network finish: 2.19 seconds

**Conclusion:** The frontend makes one `GET /api/products/{id}/price-drop` request per watched product. With 20 watched products, 20 price-drop API requests were observed.

## Price-Drop Request Performance and Batch API Proposal

With 20 watched products, the frontend currently makes 20 individual `GET /api/products/{id}/price-drop` requests.

This is functional for a small watchlist, but it creates unnecessary HTTP overhead and scales linearly with the number of watched products.

### Proposed Backend Improvement

To reduce 20 requests to 1, the backend would need a batch price-drop endpoint.

Suggested API contract:

- **Endpoint:** `POST /api/products/price-drops/batch`
- **Request:** An array of watched product IDs.
- **Response:** A result for each product, including its product ID, price-drop status, and the existing price-drop details required by the frontend.
- **Error handling:** Define how invalid product IDs and partial failures are reported.

This endpoint would allow the frontend to retrieve price-drop analysis for the entire watchlist in a single HTTP request.

**Dependency:** The batch endpoint must be agreed upon and implemented by Rajesh before the frontend can switch to it.

**Current decision:** Keep the existing individual price-drop API integration until the batch endpoint is available. Do not introduce an unsupported API call.

## Trends Overview and Product Price Chart

The frontend uses two data sources:

- **30-Day Trend Overview:** Calls `GET /api/trends/overview?period_days=30` to display backend-calculated trend statistics.
- **Selected Product Price Trend:** Calls `GET /api/products/{id}/history` only when a product is selected. The chart displays that product's percentage price change from its starting price.

### History API Request Measurements

Measured using Chrome DevTools Network tab with 63 seeded products.

| Scenario | History API Requests |
|---|---:|
| Original chart loading all 63 products | 63 |
| Optimized initial dashboard load | 0 |
| Selecting one product | 1 |
| Selecting two products consecutively | 2 |

**Result:** History API requests per product selection decreased from 63 to 1, a reduction of approximately 98.4%.

### What the Trends Overview API Can Provide

The backend overview endpoint provides:

- Total products analyzed.
- Counts of products with increasing, decreasing, and stable prices.
- Count of products with insufficient history.
- Average percentage price change over the analysis period.
- First-to-latest price-change summaries for individual products.

### What the Trends Overview API Cannot Provide

The current overview response does not provide:

- Daily price-history data points.
- A complete time series for an individual product.
- Daily percentage changes needed to plot a historical line chart.
- A daily fixed-cohort median across products.

### Implementation Decision

The frontend uses the backend Trends Overview API for aggregate trend statistics.

The previous frontend-calculated fixed-cohort median chart has been removed. The remaining chart displays only the selected product's historical percentage price change.

Product history is fetched on demand instead of requesting histories for all 63 products during dashboard loading.