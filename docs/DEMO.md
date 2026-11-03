# PriceUnmask Demo Script

## Problem We Solve

PriceUnmask helps shoppers evaluate advertised discounts using available product price history and implemented analysis rules.

It classifies discount results as:

- `genuine` – The discount meets the application's genuine classification rules.
- `likely_inflated` – The discount shows suspicious price patterns according to the implemented rules.
- `uncertain` – The available evidence does not support a confident classification.
- `insufficient_data` – Fewer than six price snapshots are available.
- `no_discount` – Sufficient history is available, but no valid discount claim exists in the available history.

The Trust Score is an assessment based on available evidence. It does not prove seller manipulation or guarantee that a discount is genuine.

---

## Five-Minute Live Demo

**Total duration: 5 minutes**

### 1. Product Grid — 0:00–0:40

**Presenter:** Pavan Kalyan — Frontend

**Action:** Show the product grid and explain how shoppers can browse products and select one to view its price history and discount analysis.

**Key point:** PriceUnmask helps shoppers evaluate discounts using historical price information instead of relying only on advertised discount percentages.

**Backup screenshots:**

- Desktop:

  ![Product Grid Desktop](https://github.com/user-attachments/assets/090e96d8-b3a9-4f70-b372-8b6b185ad5f4)

- Mobile:

  ![Product Grid Mobile](https://github.com/user-attachments/assets/f8ba9e25-3cff-481f-becb-c5a97f8a3f38)

### 2. Air Fryer Demo — 0:40–1:10

**Presenter:** Sujitha — Analysis

**Action:** Open the Air Fryer details and show the Trust Score of 20 and the label `Likely inflated`.

**Key point:** The score is based on implemented analysis rules and available price history. It is a warning for further investigation, not proof of seller manipulation.

**Backup screenshots:**

- Desktop:

  ![Air Fryer Desktop](https://github.com/user-attachments/assets/12dd16f3-c130-4f54-bce9-ed81bed62695)

- Mobile:

  ![Air Fryer Mobile](https://github.com/user-attachments/assets/e68b39f0-4f50-46d4-8e85-557a9c7bc41f)

### 3. Analysis Reasons — 1:10–1:40

**Presenter:** Lakshmiprasanna — Analysis

**Action:** Show the Air Fryer's analysis section and explain the reasons displayed by the application.

**Key point:** Explain only the factors actually implemented and displayed.

**Backup screenshots:** Use the Air Fryer screenshots from Step 2.

### 4. Running Shoes Demo — 1:40–2:20

**Presenter:** Naveen Reddy — Price History

**Action:** Open the Running Shoes details and show the historical price information or chart.

**Key point:** Historical price observations help shoppers understand how prices changed over time.

**Backup screenshots:**

- Desktop:

  ![Running Shoes Desktop](https://github.com/user-attachments/assets/684f4365-c518-4cb1-89cc-5a07d4487b29)

- Mobile:

  ![Running Shoes Mobile](https://github.com/user-attachments/assets/2136f4a8-64df-4f8e-9eff-e9da193e29b8)

### 5. Book — No Discount to Judge — 2:20–3:00

**Presenter:** Hemalatha — Backend / Data Collection

**Action:** Open the selected book from Books to Scrape and show the `No discount to judge` result.

**Key point:** `no_discount` means at least six snapshots are available but no valid discount claim exists in the available history. The Trust Score is null, not 100. This differs from `insufficient_data`, which means fewer than six snapshots are available.

**Backup screenshots:**

- Desktop:

  ![Book Desktop](https://github.com/user-attachments/assets/5f86ca73-a3a5-4bf8-831e-05d8a4587cd9)

- Mobile:

  ![Book Mobile](https://github.com/user-attachments/assets/5801409e-ad7a-4a5d-bdd3-2c31bff84523)

### 6. Collector Status and Run Now — 3:00–3:50

**Presenter:** Sai Divya — Backend / Data Collection

**Action:** Show the collector status and Run Now button. Demonstrate the button if the live application is available.

**Possible responses:**

- **Started:** The backend accepts the collection request (`202 Accepted`).
- **Already running:** Another collection job is in progress (`409 Conflict`).
- **Error:** The request fails or collection cannot complete successfully.

**Backup screenshot — Database Health Check:**

`design/screenshots/collector-db-health.jpg`

**Status:** Pending. Add the actual screenshot before the demo.

Captured details to verify:

- Latest finished run: ID 54.
- Status: `success`.
- Snapshots collected: 60.
- Products seen: 60.
- Products without a snapshot: 0.
- Health status: `HEALTHY`.

**Backup screenshot — Scheduler Execution:**

`design/screenshots/scheduler-execution.jpg`

**Status:** Pending. Add the actual screenshot before the demo.

Captured details to verify:

- Scheduler job executed successfully.
- Scraper fetched 3 pages.
- 20 products collected from each page.
- Total products collected: 60.
- Next run was scheduled.

**Key point:** These screenshots demonstrate recorded database health and scheduler execution at the time they were captured. They do not independently prove that the frontend Run Now button works.

### 7. Scrape-Run History — 3:50–4:30

**Presenter:** Mathan — Backend

**Action:** Show the available `GET /api/scrape-runs` response.

**Backup screenshot:**

`design/screenshots/Media (1).jpg`

**Status:** Pending. Add the actual API response screenshot.

Captured response to verify:

- Run ID 2: `running`, 0 products seen.
- Run ID 1: `success`, 60 products seen.
- HTTP status: `200 OK`.

**Key point:** Scrape-run history helps monitor collection activity through statuses, timestamps, product counts, and error details. A running status means the job is in progress, not necessarily that it failed.

### 8. API and Conclusion — 4:30–5:00

**Presenter:** Rajesh — API

**Action:** Show Swagger UI and `GET /api/scrape-runs`. Explain how the frontend communicates with the backend API.

**Backup screenshots:**

- `design/screenshots/Media.jpg` — Swagger GET `/api/scrape-runs` endpoint. **Pending.**
- `design/screenshots/Media (1).jpg` — API response. **Pending.**

**Key point:** The frontend sends HTTP requests to the backend. The backend processes requests and returns responses, typically JSON, which the frontend uses to display information.

**Next steps:**

- Expand product coverage.
- Collect more historical price observations.
- Test edge cases and improve error handling.
- Consider machine learning when sufficient reliable, labelled data is available.

---

## Key Takeaway

PriceUnmask helps shoppers evaluate advertised discounts using historical price information and explainable analysis rules.

Its results depend on available evidence. It does not guarantee that a discount is genuine or prove that a seller manipulated prices.

---

## Live Demo Backup Plan

If a live operation fails or the application becomes unavailable:

1. Show the relevant backup screenshot, if it has been captured and committed.
2. Explain exactly what the screenshot demonstrates.
3. Show the latest available scrape-run history or previously collected data.
4. Distinguish historical evidence from the current live application state.

Never invent a result or claim that a collection run succeeded if it did not.

---

## Likely Questions

### 1. Is web scraping allowed?

**Owner:** Hemalatha — Backend / Data Collection

**Answer:** Web scraping depends on website terms, applicable laws, access restrictions, and data protection requirements. We should follow permitted access rules and respect rate limits.

**Design note:** [Scraper Design](design/scraper.md)

### 2. Why does the selected book show "No Discount to Judge"?

**Owner:** Lakshmiprasanna — Analysis

**Answer:** The application requires at least six price snapshots. If sufficient history exists but no valid discount claim appears, the result is `no_discount` with a null Trust Score. Fewer than six snapshots results in `insufficient_data`.

**Design notes:**

- [Trust Score Design](design/trust_score.md)
- [No Discount Label](design/no_discount_label.md)

### 3. How do you know the scheduler ran automatically?

**Owner:** Sai Divya — Backend / Data Collection

**Answer:** We check scheduler configuration, execution logs, and recorded run history, including timestamps and statuses. A manual collection run alone does not prove automatic scheduling.

**Design note:** [Scheduler Design](design/scheduler.md)

### 4. Why not use machine learning for the Trust Score?

**Owner:** Sujitha — Analysis

**Answer:** We currently use rule-based analysis because it is easier to explain and validate with available historical data. Machine learning could be considered when sufficient reliable, labelled data becomes available.

**Design note:** [Trust Score Design](design/trust_score.md)

### 5. What happens if a shopping website changes its structure?

**Owner:** Hemalatha — Backend / Data Collection

**Answer:** The scraper may fail to locate expected product information. Error handling and monitoring help identify failures. The extraction logic may need to be updated and tested.

**Design note:** [Scraper Design](design/scraper.md)

### 6. How is the Trust Score calculated?

**Owner:** Sujitha — Analysis

**Answer:** The Trust Score uses implemented scoring rules and available price history.

The demo uses these classification ranges. Verify them against the current application configuration before presenting them as confirmed:

- 70–100: `genuine`
- 40–69: `uncertain`
- 0–39: `likely_inflated`

Fewer than six snapshots results in `insufficient_data` with a null score. Sufficient history without a valid discount claim results in `no_discount` with a null score.

**Design notes:**

- [Trust Score Design](design/trust_score.md)
- [Trust Score Findings](design/trust_score_findings.md)

### 7. How are historical prices stored?

**Owner:** Naveen Reddy — Price History

**Answer:** Historical price observations are stored with product information and timestamps. These records help compare current prices with previously collected prices.

Explain the actual database fields and relationships when showing the database design.

**Design note:** [Database Design](design/database.md)

### 8. How can we check whether a scraping run succeeded?

**Owner:** Mathan — Backend

**Answer:** We inspect scrape-run history, including statuses, timestamps, product counts, and error details where available.

**Design note:** [Scraper Design](design/scraper.md)

### 9. How does the frontend communicate with the backend?

**Owner:** Rajesh — API

**Answer:** The frontend sends HTTP requests to the backend API. The backend processes each request and returns a response, typically JSON.

**Design notes:**

- [API Design](design/api.md)
- [Frontend Design](design/frontend.md)

### 10. How do you detect unusual price changes?

**Owner:** Lakshmiprasanna — Analysis

**Answer:** The current anomaly detector compares an observed price with the five preceding prices using a rolling Z-score approach. It also checks the minimum percentage change before identifying an unusual price movement.

Current implementation details:

- Rolling window: 5 previous prices.
- Z-score threshold: 3.0.
- Minimum percentage change: 10%.
- Six snapshots are required for the first comparison.

The detector uses Pandas and statistical rules. An anomaly warning is not proof that a discount is fake.

**Design notes:**

- [Anomaly Findings](design/anomaly_findings.md)
- [Anomaly Messages](design/anomaly_messages.md)

---

## Design Documentation

The following design documents are available in `docs/design/`:

1. [Anomaly Findings](design/anomaly_findings.md)
2. [Anomaly Messages](design/anomaly_messages.md)
3. [API Design](design/api.md)
4. [Database Design](design/database.md)
5. [Frontend Design](design/frontend.md)
6. [No Discount Label](design/no_discount_label.md)
7. [Scheduler Design](design/scheduler.md)
8. [Scraper Design](design/scraper.md)
9. [Trust Score Design](design/trust_score.md)
10. [Trust Score Findings](design/trust_score_findings.md)

---

## Final Confirmation

All presenters should confirm their assigned sections in the team chat before the final demo.

Each presenter should demonstrate only features and results available in the current application.

Before the demo, verify all screenshot links, design-note links, and implementation details against the current branch.
