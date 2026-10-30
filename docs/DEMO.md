# PriceUnmask Demo Script

## Problem We Solve

PriceUnmask helps shoppers evaluate advertised discounts using available product price history and implemented analysis rules.

It classifies discount results as:

- `genuine` – the discount meets the application's genuine classification rules.
- `likely_inflated` – the discount shows suspicious price patterns according to the implemented rules.
- `uncertain` – the available evidence does not support a confident classification.
- `insufficient_data` – fewer than six price snapshots are available.
- `no_discount` – sufficient history is available, but no valid discount claim exists in the available history.

The Trust Score is an assessment based on available evidence. It does not prove seller manipulation or guarantee that a discount is genuine.

## Five-Minute Live Demo

**Total duration: 5 minutes**

### 1. Product Grid — 0:00–0:40

**Presenter:** Pavan Kalyan — Frontend

**Action:** Show the product grid and explain how shoppers can browse products and select one to view its price history and discount analysis.

**Key point:** PriceUnmask helps shoppers evaluate discounts using historical price information instead of relying only on advertised discount percentages.

**Backup screenshots:**
- Desktop: `product-grid-desktop`
- Mobile: `product-grid-phone`

### 2. Air Fryer Demo — 0:40–1:10

**Presenter:** Sujitha — Analysis

**Action:** Open the Air Fryer details and show the Trust Score of 20 and the label `Likely inflated`.

**Key point:** The score is based on implemented analysis rules and available price history. It is a warning for further investigation, not proof of seller manipulation.

**Backup screenshots:**
- Desktop: `air-fryer-detail-desktop-history`
- Mobile: `air-fryer-detail-phone`

### 3. Analysis Reasons — 1:10–1:40

**Presenter:** Lakshmiprasanna — Analysis

**Action:** Show the Air Fryer's analysis section and explain the reasons displayed by the application.

**Key point:** Explain only the factors actually implemented and displayed.

**Backup screenshots:**
- Desktop: `air-fryer-detail-desktop-history`
- Mobile: `air-fryer-detail-phone`

### 4. Running Shoes Demo — 1:40–2:20

**Presenter:** Naveen Reddy — Price History

**Action:** Open the Running Shoes details and show the historical price information or chart.

**Key point:** Historical price observations help shoppers understand how prices changed over time.

**Backup screenshots:**
- Desktop: `running-shoes-detail-desktop`
- Mobile: `running-shoes-detail-phone`

### 5. Book — No Discount to Judge — 2:20–3:00

**Presenter:** Hemalatha — Backend / Data Collection

**Action:** Open the selected book from Books to Scrape and show the `No discount to judge` result.

**Key point:** `no_discount` means at least six snapshots are available but no valid discount claim exists in the available history. The Trust Score is null, not 100. This differs from `insufficient_data`, which means fewer than six snapshots are available.

**Backup screenshots:**
- Desktop: `book-detail-desktop`
- Mobile: `book-detail-phone`

### 6. Collector Status and Run Now — 3:00–3:50

**Presenter:** Sai Divya — Backend / Data Collection

**Action:** Show the collector status and Run Now button. Demonstrate the button if the live application is available.

**Possible responses:**
- **Started:** The backend accepts the collection request.
- **Already running:** Another collection job is in progress.
- **Error:** The request fails or collection cannot complete successfully.

**Backup screenshot — Database Health Check:**
`../design/screenshots/collector-db-health.jpg`

Captured details:
- Latest finished run: ID 54.
- Status: success.
- Snapshots collected: 60.
- Products seen: 60.
- Products without a snapshot: 0.
- Health status: HEALTHY.

**Backup screenshot — Scheduler Execution:**
`../design/screenshots/scheduler-execution.jpg`

Captured details:
- Scheduler job executed successfully.
- Scraper fetched 3 pages.
- 20 products collected from each page.
- Total products collected: 60.
- Next run was scheduled.

**Key point:** These screenshots demonstrate recorded database health and scheduler execution at the time they were captured. They do not independently prove that the frontend Run Now button works.

### 7. Scrape-Run History — 3:50–4:30

**Presenter:** Mathan — Backend

**Action:** Show the available `GET /api/scrape-runs` response.

**Backup screenshot:** `Media (1).jpg`

Captured response:
- Run ID 2: running, 0 products seen.
- Run ID 1: success, 60 products seen.
- HTTP status: 200 OK.

**Key point:** Scrape-run history helps monitor collection activity through statuses, timestamps, product counts, and error details. A running status means the job is in progress, not necessarily that it failed.

### 8. API and Conclusion — 4:30–5:00

**Presenter:** Rajesh — API

**Action:** Show Swagger UI and `GET /api/scrape-runs`. Explain how the frontend communicates with the backend API.

**Backup screenshots:**
- `Media.jpg` — Swagger GET `/api/scrape-runs` endpoint.
- `Media (1).jpg` — API response.

**Key point:** The frontend sends HTTP requests to the backend. The backend processes requests and returns responses, typically JSON, which the frontend uses to display information.

**Next steps:**
- Expand product coverage.
- Collect more historical price observations.
- Test edge cases and improve error handling.
- Consider machine learning when sufficient reliable, labelled data is available.

## Key Takeaway

PriceUnmask helps shoppers evaluate advertised discounts using historical price information and explainable analysis rules.

Its results depend on available evidence. It does not guarantee that a discount is genuine or prove that a seller manipulated prices.

## Live Demo Backup Plan

If a live operation fails or the application becomes unavailable:

1. Show the relevant backup screenshot.
2. Explain exactly what the screenshot demonstrates.
3. Show the latest available scrape-run history or previously collected data.
4. Distinguish historical evidence from the current live application state.

Never invent a result or claim that a collection run succeeded if it did not.

## Likely Questions

### 1. Is web scraping allowed?

**Owner:** Hemalatha — Backend / Data Collection

**Answer:** Web scraping depends on website terms, applicable laws, access restrictions, and data protection requirements. We should follow permitted access rules and respect rate limits.

**Design note:** [Data Collection](design/data-collection.md)

### 2. Why does the selected book show "No discount to judge"?

**Owner:** Lakshmiprasanna — Analysis

**Answer:** The application requires at least six price snapshots. If sufficient history exists but no valid discount claim appears, the result is `no_discount` with a null Trust Score. Fewer than six snapshots results in `insufficient_data`.

**Design note:** [Discount Rules and Scoring](design/discount-rules-scoring.md)

### 3. How do you know the scheduler ran automatically?

**Owner:** Sai Divya — Backend / Data Collection

**Answer:** We check scheduler configuration, execution logs, and recorded run history, including timestamps and statuses. A manual collection run alone does not prove automatic scheduling.

**Design note:** [Scheduler](design/scheduler.md)

### 4. Why not use machine learning for the Trust Score?

**Owner:** Sujitha — Analysis

**Answer:** We currently use rule-based analysis because it is easier to explain and validate with available historical data. Machine learning could be considered when sufficient reliable, labelled data becomes available.

**Design note:** [Scoring and Anomaly Detection](design/scoring-anomaly-detection.md)

### 5. What happens if a shopping website changes its structure?

**Owner:** Hemalatha — Backend / Data Collection

**Answer:** The scraper may fail to locate expected product information. Error handling and monitoring help identify failures. The extraction logic may need to be updated and tested.

**Design note:** [Data Collection](design/data-collection.md)

### 6. How is the Trust Score calculated?

**Owner:** Sujitha — Analysis

**Answer:** The Trust Score uses implemented scoring rules and available price history.

Classification ranges:
- 70–100: `genuine`
- 40–69: `uncertain`
- 0–39: `likely_inflated`

Fewer than six snapshots results in `insufficient_data` with a null score. Sufficient history without a valid discount claim results in `no_discount` with a null score.

**Design note:** [Discount Rules and Scoring](design/discount-rules-scoring.md)

### 7. How are historical prices stored?

**Owner:** Naveen Reddy — Price History

**Answer:** Historical price observations are stored with product information and timestamps. These records help compare current prices with previously collected prices.

Explain the actual database fields and relationships when showing the database design.

**Design note:** [Database and Price History](design/database-price-history.md)

### 8. How can we check whether a scraping run succeeded?

**Owner:** Mathan — Backend

**Answer:** We inspect scrape-run history, including statuses, timestamps, product counts, and error details where available.

**Design note:** [Data Collection](design/data-collection.md)

### 9. How does the frontend communicate with the backend?

**Owner:** Rajesh — API

**Answer:** The frontend sends HTTP requests to the backend API. The backend processes each request and returns a response, typically JSON.

**Design note:** [Architecture and API](design/architecture-api.md)

### 10. How do you detect unusual price changes?

**Owner:** Lakshmiprasanna — Analysis

**Answer:** The anomaly detector compares observed prices with recent historical prices using the statistical rules implemented in the project. It identifies unusual price movements for further investigation. An anomaly warning is not proof that a discount is fake.

**Design note:** [Scoring and Anomaly Detection](design/scoring-anomaly-detection.md)

## Final Confirmation

All presenters should confirm their assigned sections in the team chat before the final demo.

Each presenter should demonstrate only features and results available in the current application.
