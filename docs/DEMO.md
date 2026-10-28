# PriceUnmask Demo Script

## Problem We Solve

PriceUnmask helps shoppers understand whether a discount is genuine, likely inflated, or impossible to judge because there is no discount to evaluate.

## Five-Minute Walk-through

### 1. Product Grid — 0:00–0:40

**Presenter: Pavan Kalyan — Frontend**

Show the product grid and explain how PriceUnmask helps shoppers judge discounts using price history.

### 2. Demo Air Fryer — 0:40–1:10

**Presenter: Sujitha — Analysis**

Show Trust Score 20 and "Likely inflated". Explain the result displayed by the application.

### 3. Analysis Reasons — 1:10–1:40

**Presenter: Lakshmiprasanna — Analysis**

Explain the reasons behind the Air Fryer's Trust Score using the information displayed by the application. Show how price history helps assess whether a discount may be inflated.

### 4. Demo Running Shoes — 1:40–2:20

**Presenter: Naveen Reddy — Backend / Price History**

Show the genuine price drop and explain how historical prices help identify a real discount.

### 5. Book with No Discount to Judge — 2:20–3:00

**Presenter: Hemalatha — Backend / Data Collection**

Show a real book from Books to Scrape. Explain that when there is no discount to evaluate, the application should not invent a score or claim a fake discount.

### 6. Collector Status and Run Now — 3:00–3:50

**Presenter: Sai Divya — Backend / Data Collection**

Show the collector status and Run now button. Explain the started, already-running, and error messages.

### 7. Scrape Run History — 3:50–4:30

**Presenter: Mathan — Backend**

Show the available scrape-run history and explain how it records collection activity.

### 8. API and What We Would Do Next — 4:30–5:00

**Presenter: Rajesh — API**

Briefly explain how the API supports communication between the frontend and backend.

Conclude with the next steps:
- Improve product coverage and collect more price history.
- Test more edge cases and improve error messages.
- Improve the shopper experience using feedback.

## Key Takeaway

PriceUnmask helps shoppers judge discounts using price history instead of trusting the advertised percentage alone.

## Live Demo Backup Plan

If a live collection run fails or takes too long, show the latest available scrape-run history and previously collected product data. Never invent a result.

**Note:** Presenter assignments must be confirmed by all teammates before the final demo.
