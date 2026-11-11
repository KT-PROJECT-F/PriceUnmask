"use strict";
const API_BASE_URL = "/api";

const API_ENDPOINTS = {
  products: `${API_BASE_URL}/products`,
  product: (id) => `${API_BASE_URL}/products/${id}`,
  history: (id) => `${API_BASE_URL}/products/${id}/history`,
  trustScore: (id) => `${API_BASE_URL}/products/${id}/trust-score`,
  scrapeRuns: `${API_BASE_URL}/scrape-runs`,
  runScrape: `${API_BASE_URL}/scrape/run`,
};

// Load products from the live API and render the product grid.
const app = document.getElementById("app");
const productStatus = document.getElementById("product-status");
const searchInput = document.getElementById("product-search");
const searchBox = document.getElementById("search-box");
const collectorStatusMessage = document.getElementById("collector-status-message");
const runCollectorButton = document.getElementById("run-collector-button");
const collectorActionMessage = document.getElementById("collector-action-message");
let priceHistoryChart = null;

const categoryTrendsStatus = document.getElementById(
  "category-trends-status"
);
const categoryTrendCanvas = document.getElementById(
  "category-trend-chart"
);

let categoryTrendChart = null;
let categoryTrendRequestId = 0;
let trendProducts = [];
const trendProductSelect = document.getElementById("trend-product-select");

const trustLabels = {
  genuine: "Genuine",
  uncertain: "Uncertain",
  likely_inflated: "Likely inflated",
  insufficient_data: "Insufficient data",
  no_discount: "No discount to judge"
};

const noScoreLabels = ["insufficient_data", "no_discount"];

function formatPrice(price, currency) {
  if (price === null || price === undefined || !currency) {
    return "—";
  }

  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency
    }).format(price / 100);
  } catch (error) {
    console.error("Invalid currency:", currency, error);
    return "—";
  }
}

 // Load scrape runs once and reuse the response when updating the status.
async function fetchScrapeRuns() {
  const response = await fetch(API_ENDPOINTS.scrapeRuns);

  if (!response.ok) {
    throw new Error("Unable to load collector status.");
  }

  const runs = await response.json();

  if (!Array.isArray(runs)) {
    throw new Error("Invalid collector status data.");
  }

  return runs;
}

// Display collector status using an existing response when available.
async function loadCollectorStatus(existingRuns = null) {
  if (!collectorStatusMessage) {
    return;
  }

  try {
    const runs = existingRuns ?? await fetchScrapeRuns();

    if (runs.length === 0) {
      collectorStatusMessage.textContent =
        "No price collection has been recorded yet.";
      return;
    }

    const latestRun = runs[0];
    const latestSuccessfulRun = runs.find(
      (run) =>
        run.status === "success" &&
        typeof run.finished_at === "string" &&
        Number.isFinite(Date.parse(run.finished_at))
    );

    if (
      latestRun.status === "running" ||
      latestRun.status === "failed"
    ) {
      const statusText =
        latestRun.status === "running"
          ? "Price collection is currently in progress."
          : "The latest price collection failed.";

      if (!latestSuccessfulRun) {
        collectorStatusMessage.textContent =
          `${statusText} No successful collection is recorded yet.`;
        return;
      }

      const lastSuccessfulAt = new Date(
        latestSuccessfulRun.finished_at
      ).toLocaleString();

      const productsSeen =
        Number.isInteger(latestSuccessfulRun.products_seen) &&
        latestSuccessfulRun.products_seen >= 0
          ? latestSuccessfulRun.products_seen
          : "Unavailable";

      collectorStatusMessage.textContent =
        `${statusText} Last successful collection: ${lastSuccessfulAt} | ` +
        `Products seen: ${productsSeen}`;
      return;
    }

    if (
      latestRun.status !== "success" &&
      latestRun.status !== "partial"
    ) {
      collectorStatusMessage.textContent =
        "The latest price collection status is unknown.";
      return;
    }

    if (
      typeof latestRun.finished_at !== "string" ||
      !Number.isFinite(Date.parse(latestRun.finished_at))
    ) {
      collectorStatusMessage.textContent =
        "The latest collection's finish time is unavailable.";
      return;
    }

    const finishedAt = new Date(
      latestRun.finished_at
    ).toLocaleString();

    const productsSeen =
      Number.isInteger(latestRun.products_seen) &&
      latestRun.products_seen >= 0
        ? latestRun.products_seen
        : "Unavailable";

    const statusText =
      latestRun.status === "success"
        ? "Completed successfully"
        : "Completed with partial results";

    collectorStatusMessage.textContent =
      `Last collected: ${finishedAt} | ` +
      `Status: ${statusText} | Products seen: ${productsSeen}`;
  } catch (error) {
    console.error("Unable to load collector status:", error);
    collectorStatusMessage.textContent =
      "Collector status is temporarily unavailable.";
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForScrapeCompletion(runId) {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    await sleep(5000);

    // One scrape-runs request per polling cycle.
    const runs = await fetchScrapeRuns();
    const currentRun = runs.find((run) => run.id === runId);

    await loadCollectorStatus(runs);

    if (!currentRun) {
      throw new Error("Could not find the collection run.");
    }

    if (currentRun.status !== "running") {
      if (currentRun.status === "success") {
        collectorActionMessage.textContent =
          "Price collection completed successfully.";

        window.dispatchEvent(
          new Event("priceunmask:collection-complete")
        );
      } else if (currentRun.status === "partial") {
        collectorActionMessage.textContent =
          "Price collection finished with partial results.";

        window.dispatchEvent(
          new Event("priceunmask:collection-complete")
        );
      } else {
        collectorActionMessage.textContent =
          "Price collection did not complete successfully. Check the collector status.";
      }

      return;
    }
  }

  collectorActionMessage.textContent =
    "Collection is taking longer than expected. Please check back shortly.";
}

async function handleRunCollector() {
  if (!runCollectorButton || !collectorActionMessage) {
    return;
  }

  let requestAccepted = false;

  runCollectorButton.disabled = true;
  runCollectorButton.textContent = "Starting...";
  collectorActionMessage.textContent =
    "Requesting a price collection run...";

  try {
    const response = await fetch(API_ENDPOINTS.runScrape, {
      method: "POST",
      headers: {
        Accept: "application/json"
      }
    });

    if (response.status === 409) {
      collectorActionMessage.textContent =
        "A price collection is already running. We'll update the status automatically.";

      const runs = await fetchScrapeRuns();
      await loadCollectorStatus(runs);

      const activeRun = runs.find((run) => run.status === "running");

      if (activeRun) {
        runCollectorButton.textContent = "Running...";
        requestAccepted = true;
        await waitForScrapeCompletion(activeRun.id);
      }

      return;
    }

    if (response.status !== 202) {
      // Do not expose HTTP status details or server error text to shoppers.
      throw new Error("start-failed");
    }

    const startedRun = await response.json();

    if (startedRun.id === undefined || startedRun.id === null) {
      throw new Error("start-failed");
    }

    requestAccepted = true;
    runCollectorButton.textContent = "Running...";
    collectorActionMessage.textContent =
      "Price collection started. Progress will update automatically.";

    await loadCollectorStatus();
    await waitForScrapeCompletion(startedRun.id);
  } catch (error) {
    console.error("Collector action failed:", error);

    if (requestAccepted) {
      collectorActionMessage.textContent =
        "Collection was started, but we couldn't refresh its status. Please check the collector status again.";
    } else if (
      error instanceof TypeError
    ) {
      collectorActionMessage.textContent =
        "Could not connect to the server. Please try again later.";
    } else {
      collectorActionMessage.textContent =
        "We couldn't start the price collection. Please try again later.";
    }
  } finally {
    runCollectorButton.disabled = false;
    runCollectorButton.textContent = "Run now";
  }
}

if (runCollectorButton) {
  runCollectorButton.addEventListener("click", handleRunCollector);
}


const WATCHLIST_STORAGE_KEY = "priceunmask-watchlist";

function getWatchlist() {
  try {
    const saved = JSON.parse(
      localStorage.getItem(WATCHLIST_STORAGE_KEY) || "[]"
    );
    return Array.isArray(saved) ? saved.map(String) : [];
  } catch (error) {
    console.error("Unable to read watchlist:", error);
    return [];
  }
}

function isWatchlisted(productId) {
  return getWatchlist().includes(String(productId));
}

function toggleWatchlist(productId) {
  const id = String(productId);
  const watchlist = getWatchlist();

  const updated = watchlist.includes(id)
    ? watchlist.filter((item) => item !== id)
    : [...watchlist, id];

  try {
    localStorage.setItem(
      WATCHLIST_STORAGE_KEY,
      JSON.stringify(updated)
    );
  } catch (error) {
    console.error("Unable to save watchlist:", error);
    return watchlist.includes(id);
  }

  return updated.includes(id);
}

function createProductCard(product, onSelect) {
  const card = document.createElement("article");
  card.className = "product-card";
  if (product.trust_label === "insufficient_data") {
    card.classList.add("product-card-insufficient-data");
  }
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-label", `View details for ${product.name}`);

  const name = document.createElement("h2");
  name.textContent = product.name;

  const latestPrice = document.createElement("p");
  latestPrice.textContent =
    "Latest Price: " +
    formatPrice(product.latest_price_minor, product.currency);

  const lowestPrice = document.createElement("p");
  lowestPrice.textContent =
    "Lowest Price: " +
    formatPrice(product.lowest_price_minor, product.currency);

  const trustLabel = document.createElement("span");
  const label = product.trust_label;

  trustLabel.className = "trust-badge";

  if (label && Object.prototype.hasOwnProperty.call(trustLabels, label)) {
    trustLabel.classList.add(`trust-badge-${label}`);
    trustLabel.textContent = trustLabels[label];
  } else {
    trustLabel.classList.add("trust-badge-insufficient_data");
    trustLabel.textContent = trustLabels.insufficient_data;
  }

  const watchlistButton = document.createElement("button");
  watchlistButton.type = "button";
  watchlistButton.className = "watchlist-button";

  function updateWatchlistButton() {
    const saved = isWatchlisted(product.id);
    watchlistButton.textContent = saved
      ? "\u2665 Remove from Watchlist"
      : "\u2661 Add to Watchlist";
    watchlistButton.setAttribute("aria-pressed", String(saved));
  }

  updateWatchlistButton();

  watchlistButton.addEventListener("click", (event) => {
    event.stopPropagation();

    const wasWatchlisted = isWatchlisted(product.id);
    const isNowWatchlisted = toggleWatchlist(product.id);

    updateWatchlistButton();

    // Notify only when the watchlist was successfully changed.
    if (wasWatchlisted !== isNowWatchlisted) {
      window.dispatchEvent(new Event("watchlist-changed"));
    }
  });

  card.append(
    name,
    latestPrice,
    lowestPrice,
    trustLabel,
    watchlistButton
  );

  card.addEventListener("click", () => onSelect(product));

  card.addEventListener("keydown", (event) => {
    if (event.target !== card) return;

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(product);
    }
  });

  return card;
}

function filterProducts(products, searchTerm) {
  const normalizedSearch = searchTerm.trim().toLowerCase();

  if (!normalizedSearch) {
    return products;
  }

  return products.filter((product) =>
    String(product.name ?? "").toLowerCase().includes(normalizedSearch)
  );
}

function renderProducts(products, grid, onSelect) {
  grid.replaceChildren();

  if (products.length === 0) {
    productStatus.textContent = "No products match";
    return;
  }

  productStatus.textContent = "";

  products.forEach((product) => {
    grid.append(createProductCard(product, onSelect));
  });
}



// Load trust-score data for the selected product.
async function loadTrustScore(productId) {
  const response = await fetch(API_ENDPOINTS.trustScore(productId));

  if (!response.ok) {
    throw new Error(`Could not load trust score: HTTP ${response.status}`);
  }

  const trustScore = await response.json();

  if (
    !trustScore ||
    typeof trustScore !== "object" ||
    !Array.isArray(trustScore.reasons) ||
    !trustScore.reasons.every((reason) => typeof reason === "string") ||
    typeof trustScore.label !== "string" ||
    !Object.prototype.hasOwnProperty.call(trustLabels, trustScore.label) ||
    (
      noScoreLabels.includes(trustScore.label) &&
      trustScore.score !== null
    ) ||
    (
      !noScoreLabels.includes(trustScore.label) &&
      (
        typeof trustScore.score !== "number" ||
        !Number.isFinite(trustScore.score) ||
        trustScore.score < 0 ||
        trustScore.score > 100
      )
    )
  ) {
    throw new Error("Invalid trust score data");
  }

  return trustScore;
}


// Load price history from the live API.
async function loadPriceHistory(productId) {
  const response = await fetch(API_ENDPOINTS.history(productId));

  if (!response.ok) {
    throw new Error("Could not load price history");
  }

  const history = await response.json();

  if (
    history.product_id !== productId ||
    !Array.isArray(history.points) ||
    !history.points.every(
      (point) =>
        typeof point.scraped_at === "string" &&
        Number.isFinite(Date.parse(point.scraped_at)) &&
        typeof point.current_price_minor === "number" &&
        Number.isFinite(point.current_price_minor) &&
        (
          point.original_price_minor === null ||
          (
            typeof point.original_price_minor === "number" &&
            Number.isFinite(point.original_price_minor)
          )
        )
    )
  ) {
    throw new Error("Invalid price history data");
  }

  return history.points;
}

const MIN_PRICE_DROP_PERCENTAGE = 1;

function detectLatestPriceDrop(history) {
  if (!Array.isArray(history) || history.length < 2) {
    return null;
  }

  const sortedHistory = [...history]
    .filter(
      (entry) =>
        Number.isFinite(entry.current_price_minor) &&
        entry.current_price_minor > 0
    )
    .sort(
      (a, b) =>
        Date.parse(a.scraped_at) - Date.parse(b.scraped_at)
    );

  if (sortedHistory.length < 2) {
    return null;
  }

  // Find the start of the latest continuous downward trend.
  let latestIndex = sortedHistory.length - 1;
  let startIndex = latestIndex;

  // Skip repeated readings at the latest price.
  while (
    startIndex > 0 &&
    sortedHistory[startIndex - 1].current_price_minor ===
      sortedHistory[startIndex].current_price_minor
  ) {
    startIndex--;
  }

  // Walk backwards while prices are decreasing.
  while (
    startIndex > 0 &&
    sortedHistory[startIndex - 1].current_price_minor >=
      sortedHistory[startIndex].current_price_minor
  ) {
    startIndex--;
  }

  // No downward trend found.
  if (
    sortedHistory[startIndex].current_price_minor ===
    sortedHistory[latestIndex].current_price_minor
  ) {
    return null;
  }

  const previousPrice = sortedHistory[startIndex].current_price_minor;
  const currentPrice = sortedHistory[latestIndex].current_price_minor;

  const dropPercentage =
    ((previousPrice - currentPrice) / previousPrice) * 100;

  if (dropPercentage < MIN_PRICE_DROP_PERCENTAGE) {
    return null;
  }

  return {
    previousPrice,
    currentPrice,
    dropAmount: previousPrice - currentPrice,
    dropPercentage,
    detectedAt: sortedHistory[latestIndex].scraped_at
  };
}

let priceDropNotificationRequestId = 0;
let hasLoadedPriceDropNotifications = false;

async function updatePriceDropNotifications(products) {
  const requestId = ++priceDropNotificationRequestId;

  const status = document.getElementById("notification-status");
  const list = document.getElementById("notification-list");

  if (!status || !list) return;

  list.replaceChildren();

  const watchedIds = new Set(getWatchlist());
  const watchedProducts = products.filter(
    (product) => watchedIds.has(String(product.id))
  );

  if (watchedProducts.length === 0) {
    status.textContent = "No watched products to check.";
    return;
  }

  status.textContent = "Checking watched products...";

  const results = await Promise.allSettled(
    watchedProducts.map(async (product) => {
      const history = await loadPriceHistory(product.id);
      return {
        product,
        drop: detectLatestPriceDrop(history)
      };
    })
  );

  // Ignore results from an older notification request.
  if (requestId !== priceDropNotificationRequestId) {
    return;
  }

  let alertCount = 0;
  let failedCount = 0;

  results.forEach((result) => {
    if (result.status === "rejected") {
      console.error("Price history check failed:", result.reason);
      failedCount++;
      return;
    }

    const { product, drop } = result.value;
    if (!drop) return;

    alertCount++;

    const alert = document.createElement("article");
    alert.className = "price-drop-alert";

    const title = document.createElement("strong");
    title.textContent = product.name;

    const price = document.createElement("p");
    price.textContent =
      `${formatPrice(drop.previousPrice, product.currency)} \u2192 ` +
      formatPrice(drop.currentPrice, product.currency);

    const percentage = document.createElement("p");
    percentage.className = "price-drop-percentage";
    percentage.textContent =
      `Price dropped ${drop.dropPercentage.toFixed(1)}%`;

    const detectedDate = new Date(drop.detectedAt);

    const date = document.createElement("p");
    date.className = "price-drop-date";
    date.textContent = Number.isNaN(detectedDate.getTime())
      ? "Drop date unavailable"
      : `Price dropped on ${detectedDate.toLocaleString("en-IN", {
          dateStyle: "medium",
          timeStyle: "short"
        })}`;

    alert.append(title, price, percentage, date);
    list.append(alert);
  });

  if (failedCount > 0) {
    hasLoadedPriceDropNotifications = false;
  }
  status.textContent = alertCount
    ? `${alertCount} watched product(s) have a detected price drop.` +
      (failedCount ? ` ${failedCount} could not be checked.` : "")
    : failedCount
      ? `No drops found. ${failedCount} product(s) could not be checked.`
      : "No recent price drops for watched products.";
}

function resetTrendCache() {
  trendCacheGeneration++;
  cachedTrendProductHistories = null;
  trendHistoriesPromise = null;
  hasLoadedTrendData = false;
  categoryTrendRequestId++;
}

function updateTrendProductOptions(products) {
  const previousIds = trendProducts.map((product) => String(product.id));
  const nextIds = products.map((product) => String(product.id));

  if (
    previousIds.length !== nextIds.length ||
    previousIds.some((id, index) => id !== nextIds[index])
  ) {
    resetTrendCache();
  }

  trendProducts = products;

  if (!trendProductSelect) {
    return;
  }

  // Remember the previously selected product.
  const previousSelection = trendProductSelect.value;

  trendProductSelect.replaceChildren();

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "All Products";
  trendProductSelect.append(placeholder);

  for (const product of products) {
    const option = document.createElement("option");

    option.value = String(product.id);
    option.textContent = product.name;

    // Restore the selected product if it still exists.
    option.selected = previousSelection === option.value;

    trendProductSelect.append(option);
  }

  trendProductSelect.disabled = products.length === 0;
}

// Format history timestamps for readable chart labels.
function formatChartDate(isoString) {
  return new Date(isoString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

function renderCategoryTrendChart(productHistories, selectedProductId = "") {
  if (!categoryTrendCanvas || typeof Chart === "undefined") {
    return;
  }

  if (categoryTrendChart) {
    categoryTrendChart.destroy();
    categoryTrendChart = null;
  }


  const styles = getComputedStyle(document.documentElement);
  const colors = [
    "--accent",
    "--uncertain-color",
    "--nodiscount-color",
    "--inflated-color",
    "--insufficient-color"
  ].map((token) => styles.getPropertyValue(token).trim());

  // Collect unique calendar dates across all product histories.
  const dates = [
    ...new Set(
      productHistories.flatMap(({ history }) =>
        history
          .filter(
            (point) =>
              Number.isFinite(point.current_price_minor) &&
              point.current_price_minor > 0 &&
              !Number.isNaN(Date.parse(point.scraped_at))
          )
          .map((point) => point.scraped_at.slice(0, 10))
      )
    )
  ].sort();

  // Use a shared baseline so later-tracked products cannot
  // change the median simply by entering at 0%.
  const baselineDate = dates[0];

  // Store percentage price changes across products for each date.
  const changesByDate = new Map(
    dates.map((date) => [date, []])
  );

  let fixedCohortCount = 0;

  const datasets = productHistories.map(
    ({ product, history }, index) => {
      const points = [...history]
        .filter(
          (point) =>
            Number.isFinite(point.current_price_minor) &&
            point.current_price_minor > 0 &&
            typeof point.scraped_at === "string" &&
            !Number.isNaN(Date.parse(point.scraped_at))
        )
        .sort(
          (a, b) =>
            new Date(a.scraped_at) - new Date(b.scraped_at)
        );

      const startingPrice = points[0]?.current_price_minor;

      const includeInOverallTrend =
        points[0]?.scraped_at.slice(0, 10) === baselineDate;
      if (includeInOverallTrend) {
        fixedCohortCount++;
      }
      // Use the latest valid recorded price for each date.
      const priceByDate = new Map(
        points.map((point) => [
          point.scraped_at.slice(0, 10),
          point.current_price_minor
        ])
      );

      const isSelected = String(product.id) === selectedProductId;

      return {
        label: product.name,
        data: dates.map((date) => {
           const latestRecordedDate = [...priceByDate.keys()]
            .filter((recordedDate) => recordedDate <= date)
            .pop();

          const price = latestRecordedDate
            ? priceByDate.get(latestRecordedDate)
            : null;

          if (!price || !startingPrice) {
            return null;
          }

          const percentageChange =
              ((price - startingPrice) / startingPrice) * 100;

          if (includeInOverallTrend) {
            changesByDate.get(date).push(percentageChange);
          }

          return percentageChange;
        }),
        borderColor: isSelected ? colors[1] : colors[index % colors.length],
        backgroundColor: isSelected ? colors[1] : colors[index % colors.length],
        borderWidth: isSelected ? 4 : 1,
        pointRadius: isSelected ? 3 : 0,
        borderDash: !selectedProductId || isSelected ? [] : [4, 4],
        tension: 0.2,
        spanGaps: true,
        fill: false
      };
    }
  );

  // Calculate the median percentage change across products.
  const overallTrend = dates.map((date) => {
    const changes = [...changesByDate.get(date)].sort(
      (a, b) => a - b
    );

    if (changes.length === 0) {
      return null;
    }

    const middle = Math.floor(changes.length / 2);

    return changes.length % 2 === 0
      ? (changes[middle - 1] + changes[middle]) / 2
      : changes[middle];
  });

  categoryTrendChart = new Chart(categoryTrendCanvas, {
    type: "line",
    data: {
      labels: dates.map((date) => formatChartDate(`${date}T12:00:00`)),
      datasets: [
        {
          label: `Price Trend (Fixed-Cohort Median, ${fixedCohortCount} products)`,
          data: overallTrend,
          borderColor: colors[0],
          backgroundColor: colors[0],
          borderWidth: 3,
          pointRadius: 2,
          tension: 0.2,
          spanGaps: false,
          fill: false
        },
        ...datasets.filter(
          (dataset, index) =>
            selectedProductId &&
            String(productHistories[index].product.id) === selectedProductId
        )
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          display: true
        },
        tooltip: {
          callbacks: {
            label: (context) =>
              `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
          }
        }
      },
      scales: {
        y: {
          title: {
            display: true,
            text: "Price Change (%)"
          },
          ticks: {
            callback: (value) => `${value}%`
          }
        },
        x: {
          ticks: {
            maxTicksLimit: 8
          }
        }
      }
    }
  });

  return fixedCohortCount;
}

let hasLoadedTrendData = false;
let cachedTrendProductHistories = null;
let trendHistoriesPromise = null;
let trendCacheGeneration = 0;

async function loadCategoryTrendView() {

  if (!categoryTrendCanvas || !categoryTrendsStatus) {
    return;
  }

  // Invalidate any previous price-history request.
  const requestId = ++categoryTrendRequestId;

  // Keep all products for the overall comparison.
  const selectedProducts = trendProducts;
  const requestGeneration = trendCacheGeneration;
  const selectedProductId = trendProductSelect?.value || "";

  try {
    categoryTrendsStatus.textContent =
      "Loading price trends...";

    if (!cachedTrendProductHistories && !trendHistoriesPromise) {
      trendHistoriesPromise = Promise.allSettled(
        selectedProducts.map(async (product) => ({
          product,
          history: await loadPriceHistory(product.id)
        }))
      );
    }

    const activePromise = trendHistoriesPromise;
    const results =
      cachedTrendProductHistories || (await activePromise);

    if (trendHistoriesPromise === activePromise) {
      trendHistoriesPromise = null;
    }

    if (
      (cachedTrendProductHistories === null) &&
      (trendHistoriesPromise === null) &&
      requestGeneration === trendCacheGeneration &&
      results.every((result) => result.status === "fulfilled")
    ) {
      cachedTrendProductHistories = results;
    }
    const productHistories = results
      .filter((result) => result.status === "fulfilled")
      .map((result) => result.value)
      .filter(({ history }) => {
        const validDates = new Set(
          history
            .filter(
              (point) =>
                Number.isFinite(point.current_price_minor) &&
                point.current_price_minor > 0 &&
                typeof point.scraped_at === "string" &&
                !Number.isNaN(Date.parse(point.scraped_at))
            )
            .map((point) => point.scraped_at.slice(0, 10))
        );

        return validDates.size >= 2;
      });

    if (requestId !== categoryTrendRequestId) {
      return;
    }

    if (productHistories.length < 2) {
      hasLoadedTrendData = false;

      if (categoryTrendChart) {
        categoryTrendChart.destroy();
        categoryTrendChart = null;
      }

      categoryTrendsStatus.textContent =
        "At least two products with price history are needed for comparison.";
      return;
    }

    const fixedCohortCount =
      renderCategoryTrendChart(productHistories, selectedProductId);

    categoryTrendsStatus.textContent =
      `Showing ${productHistories.length} product histories. ` +
      `The overall trend is the median percentage price change ` +
      `of ${fixedCohortCount} products tracked from the earliest ` +
      `available date, measured against their starting prices.` +
      (fixedCohortCount === 1
        ? " Only one product qualifies, so this line represents that product rather than a market-wide median."
        : "");
    } catch (error) {
      if (requestId !== categoryTrendRequestId) {
        return;
      }

    console.error("Error loading price trends:", error);

    hasLoadedTrendData = false;

    if (categoryTrendChart) {
      categoryTrendChart.destroy();
      categoryTrendChart = null;
    }

    categoryTrendsStatus.textContent =
      "Price trends are not available right now.";
  }
}

 // Render the selected product's price history.
function renderPriceHistoryChart(canvas, history, currency, trustScore) {
  if (priceHistoryChart) {
    priceHistoryChart.destroy();
    priceHistoryChart = null;
  }

  const formatRupees = (minorUnits) =>
    formatPrice(minorUnits, currency);

  const styles = getComputedStyle(document.documentElement);

  const accentColor = styles.getPropertyValue("--accent").trim();
  const warningColor = styles.getPropertyValue("--inflated-color").trim();
  const mutedColor = styles.getPropertyValue("--ink-faint").trim();
  const borderColor = styles.getPropertyValue("--border").trim();
  const inkColor = styles.getPropertyValue("--ink").trim();
  const surfaceColor = styles.getPropertyValue("--surface").trim();

  const isWarning =
    trustScore?.label === "likely_inflated" ||
    trustScore?.anomaly_status === "unusual";

  const currentPriceColor = isWarning
    ? warningColor
    : accentColor;

  priceHistoryChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: history.map((item) =>
        formatChartDate(item.scraped_at)
      ),
      datasets: [
        {
          label: "Current Price",
          data: history.map(
            (item) => item.current_price_minor / 100
          ),
          borderColor: currentPriceColor,
          backgroundColor: currentPriceColor,
          tension: 0.2,
          fill: false,
        },
        {
          label: "Original Price",
          data: history.map((item) =>
            item.original_price_minor === null
              ? null
              : item.original_price_minor / 100
          ),
          borderColor: mutedColor,
          borderDash: [6, 4],
          backgroundColor: mutedColor,
          tension: 0.2,
          spanGaps: false,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,

      interaction: {
        mode: "index",
        intersect: false,
      },

      scales: {
        x: {
          grid: {
            color: borderColor,
          },
          ticks: {
            color: mutedColor,
            font: {
              family: '"IBM Plex Mono", monospace',
              size: 11,
            },
          },
        },

        y: {
          grid: {
            color: borderColor,
          },
          ticks: {
            color: mutedColor,
            font: {
              family: '"IBM Plex Mono", monospace',
              size: 11,
            },
            callback(value) {
              return formatRupees(value * 100);
            },
          },
        },
      },

      plugins: {
        legend: {
          labels: {
            color: inkColor,
            font: {
              family: '"IBM Plex Sans", sans-serif',
              size: 12,
            },
          },
        },

        tooltip: {
          backgroundColor: surfaceColor,
          titleColor: inkColor,
          bodyColor: inkColor,
          borderColor: borderColor,
          borderWidth: 1,
          padding: 12,
          displayColors: true,

          callbacks: {
            label(context) {
              const value = context.parsed.y;

              if (value === null) {
                return `${context.dataset.label}: No data`;
              }

              return `${context.dataset.label}: ${formatRupees(
                value * 100
              )}`;
            },
          },
        },
      },
    },
  });
}


// Load and render price history without blocking the Trust Score.
async function showPriceHistory(detail, product, trustScore) {
  const container = detail.querySelector(".price-chart-container");
  const canvas = detail.querySelector("#price-history-chart");

  if (!container) {
    return;
  }

  if (!canvas) {
    return;
  }

  try {
    if (typeof Chart === "undefined") {
      throw new Error("Chart.js is unavailable");
    }

    const history = await loadPriceHistory(product.id);

    // Ignore results if the user has left this product's detail view.
    if (!detail.isConnected) {
      return;
    }
    if (history.length === 0) {
      canvas.remove();
      const message = document.createElement("p");
      message.className = "chart-summary";
      message.setAttribute("role", "status");
      message.textContent = "No price history is available yet.";

      container.append(message);
      return;
    }
    renderPriceHistoryChart(canvas, history, product.currency, trustScore);
    const summary = document.createElement("p");
    summary.className = "chart-summary";
    let lowestPrice = Infinity;
    let highestPrice = -Infinity;

    for (const point of history) {
      lowestPrice = Math.min(lowestPrice, point.current_price_minor);
      highestPrice = Math.max(highestPrice, point.current_price_minor);
    }

    summary.textContent =
      `Price history contains ${history.length} data points. ` +
      `Prices range from ${formatPrice(
        lowestPrice,
        product.currency
      )} to ${formatPrice(
        highestPrice,
        product.currency
      )}.`;

    container.append(summary);
  } catch (error) {
    console.error("Unable to display price history:", error);

    if (!detail.isConnected) {
      return;
    }

    canvas.remove();

    const message = document.createElement("p");
    message.className = "error-message";
    message.setAttribute("role", "status");
    message.textContent = "The price chart is not available right now.";

    container.append(message);
  }
}

function buildAnomalyPanel(trustScore) {
  const anomalyPanel = document.createElement("section");
  anomalyPanel.className = "anomaly-panel";
  anomalyPanel.setAttribute("aria-label", "Price anomaly status");

  const anomalyBadge = document.createElement("span");
  anomalyBadge.className = "anomaly-badge";

  const anomalyMessage = document.createElement("p");
  anomalyMessage.className = "anomaly-message";

  const status = trustScore?.anomaly_status;
  const message = trustScore?.anomaly_message;

  const badges = {
    normal: {
      text: "No anomaly detected",
      className: "anomaly-badge-normal",
    },
    unusual: {
      text: "Unusual price",
      className: "anomaly-badge-unusual",
    },
    insufficient_history: {
      text: "Not enough data",
      className: "anomaly-badge-insufficient",
    },
  };

  const badge = badges[status];

  if (badge && typeof message === "string" && message.trim()) {
    anomalyBadge.classList.add(badge.className);
    anomalyBadge.textContent = badge.text;
    anomalyMessage.textContent = message;
  } else {
    anomalyBadge.classList.add("anomaly-badge-insufficient");
    anomalyBadge.textContent = "Anomaly status unavailable";
    anomalyMessage.textContent =
      "We couldn't check whether today's price is unusual.";
  }

  anomalyPanel.append(anomalyBadge, anomalyMessage);
  return anomalyPanel;
}

function buildDetailContent(product, trustScore) {
  const elements = [];

  const title = document.createElement("h2");
  title.id = "product-detail-title";
  title.tabIndex = -1;
  title.textContent = product.name;
  elements.push(title);

  // Only display links that use HTTP or HTTPS.
  try {
    const parsedURL = new URL(product.url);

    if (
      parsedURL.protocol === "http:" ||
      parsedURL.protocol === "https:"
    ) {
      const shopLink = document.createElement("a");
      shopLink.href = parsedURL.href;
      shopLink.target = "_blank";
      shopLink.rel = "noopener noreferrer";
      shopLink.textContent = "Visit shop";
      elements.push(shopLink);
    }
  } catch (error) {
    console.warn("Invalid product URL; shop link omitted.", error);
  }

  const latestPrice = document.createElement("p");
  latestPrice.textContent =
    "Latest Price: " +
    formatPrice(product.latest_price_minor, product.currency);

  const lowestPrice = document.createElement("p");
  lowestPrice.textContent =
    "Lowest Price: " +
    formatPrice(product.lowest_price_minor, product.currency);

  elements.push(latestPrice, lowestPrice);

  if (!trustScore) {
    const scoreHeading = document.createElement("h3");
    scoreHeading.textContent = "Trust Score";

    const unavailableMessage = document.createElement("p");
    unavailableMessage.className = "trust-score-message";
    unavailableMessage.setAttribute("role", "status");
    unavailableMessage.textContent =
      "Trust Score is temporarily unavailable.";

    elements.push(scoreHeading, unavailableMessage);
    elements.push(buildAnomalyPanel(null));

    const chartContainer = document.createElement("div");
    chartContainer.className = "price-chart-container";

    const chartHeading = document.createElement("h3");
    chartHeading.textContent = "Price History";

    const chartCanvas = document.createElement("canvas");
    chartCanvas.id = "price-history-chart";
    chartCanvas.setAttribute(
      "aria-label",
      `Price history chart for ${product.name}`
    );
    chartCanvas.setAttribute("role", "img");

    chartContainer.append(chartHeading, chartCanvas);
    elements.push(chartContainer);

    return elements;
  }
  // Display the Trust Score and its label.
  const scoreHeading = document.createElement("h3");
  scoreHeading.textContent = "Trust Score";

  const scoreBadge = document.createElement("span");
  scoreBadge.className = `trust-badge trust-badge-${trustScore.label}`;

  const labelText = trustLabels[trustScore.label];

  scoreBadge.textContent =
    trustScore.score === null || trustScore.score === undefined
      ? labelText
      : `${trustScore.score} — ${labelText}`;

  elements.push(scoreHeading, scoreBadge);

  // Explain labels that need additional shopper-facing context.
  if (trustScore.label === "insufficient_data") {
    const insufficientMessage = document.createElement("p");
    insufficientMessage.className = "trust-score-message";
    insufficientMessage.setAttribute("role", "status");
    insufficientMessage.textContent =
      "There isn't enough price history yet to calculate a reliable Trust Score. Check back when more price data is available.";

    elements.push(insufficientMessage);
  } else if (trustScore.label === "no_discount") {
    const noDiscountMessage = document.createElement("p");
    noDiscountMessage.className = "trust-score-message";
    noDiscountMessage.setAttribute("role", "status");
    noDiscountMessage.textContent =
      "The latest price has no discount to evaluate.";

    elements.push(noDiscountMessage);
  }

  // Display the reasons for the Trust Score.
  const reasonsHeading = document.createElement("h3");
  reasonsHeading.textContent = "Why?";

  const reasonsList = document.createElement("ul");

  if (trustScore.reasons.length === 0) {
    const emptyReason = document.createElement("li");
    emptyReason.textContent = "No reasons available.";
    reasonsList.append(emptyReason);
  } else {
    trustScore.reasons.forEach((reason) => {
      const reasonItem = document.createElement("li");
      reasonItem.textContent = reason;
      reasonsList.append(reasonItem);
    });
  }

  elements.push(reasonsHeading, reasonsList);

  // Show the API-provided anomaly status and explanation.
  const anomalyPanel = buildAnomalyPanel(trustScore);
  elements.push(anomalyPanel);

  // Create the price history chart container.
  const chartContainer = document.createElement("div");
  chartContainer.className = "price-chart-container";

  const chartHeading = document.createElement("h3");
  chartHeading.textContent = "Price History";

  const chartCanvas = document.createElement("canvas");
  chartCanvas.id = "price-history-chart";
  chartCanvas.setAttribute(
    "aria-label",
    `Price history chart for ${product.name}`
  );
  chartCanvas.setAttribute("role", "img");

  chartContainer.append(chartHeading, chartCanvas);
  elements.push(chartContainer);

  return elements;
}

async function showProductDetail(product, showGrid) {
  // Find the actual grid and hide it completely.
  const grid = app.querySelector(".product-grid");

  if (grid) {
    grid.hidden = true;
    grid.style.display = "none";
  }

  // Hide the search area as well.
  if (searchBox) {
    searchBox.hidden = true;
    searchBox.style.display = "none";
  } else if (searchInput) {
    searchInput.hidden = true;
    searchInput.style.display = "none";
  }

  // Remove an old detail view, if one exists.
  const existingDetail = app.querySelector(".product-detail");

  if (existingDetail) {
    existingDetail.remove();
  }

  productStatus.textContent = "";

  const detail = document.createElement("section");
  detail.className = "product-detail";
  detail.setAttribute("aria-labelledby", "product-detail-title");
  detail.setAttribute("aria-busy", "true");

  const backButton = document.createElement("button");
  backButton.type = "button";
  backButton.textContent = "Back to products";
  backButton.addEventListener("click", showGrid);

  const loadingMessage = document.createElement("p");
  loadingMessage.textContent = "Loading product details...";

  detail.append(backButton, loadingMessage);
  app.append(detail);

  try {
    let trustScore = null;

    try {
      trustScore = await loadTrustScore(product.id);
    } catch (error) {
      console.error("Error loading trust score:", error);
    }

    // Avoid rendering if this detail view has already been removed.
    if (!detail.isConnected) {
      return;
    }

    loadingMessage.remove();
    detail.append(...buildDetailContent(product, trustScore));
    // Load the chart separately so it doesn't block the Trust Score.
    showPriceHistory(detail, product, trustScore);
    detail.setAttribute("aria-busy", "false");

    const title = detail.querySelector("#product-detail-title");

    if (title) {
      title.focus();
    }
  } catch (error) {
    console.error("Error loading product details:", error);

    if (!detail.isConnected) {
      return;
    }

    loadingMessage.remove();

    const errorMessage = document.createElement("p");
    errorMessage.className = "error-message";
    errorMessage.setAttribute("role", "alert");
    errorMessage.textContent =
      "Unable to load product details. Please try again later.";

    detail.append(errorMessage);
    detail.setAttribute("aria-busy", "false");
  }
}

function showProductGrid(grid, products, onSelect) {
  if (priceHistoryChart) {
    priceHistoryChart.destroy();
    priceHistoryChart = null;
  }
  const detail = app.querySelector(".product-detail");

  if (detail) {
    detail.remove();
  }

  // Restore the search area.
  if (searchBox) {
    searchBox.hidden = false;
    searchBox.style.display = "";
  } else if (searchInput) {
    searchInput.hidden = false;
    searchInput.style.display = "";
  }

  // Restore the product grid.
  grid.hidden = false;
  grid.style.display = "";

  renderProducts(products, grid, onSelect);

  searchInput.focus();
}

async function loadProducts() {
  if (!app || !productStatus || !searchInput) {
    console.error("Required page elements are missing.");
    return;
  }

  const grid = document.createElement("section");
  grid.className = "product-grid";
  app.append(grid);

  let searchTimer;
  let requestId = 0;
  let currentProducts = [];
  let allProducts = [];
  let selectedProductId = null;


  // Refresh notifications for all watched products, even during searches.
  window.addEventListener("watchlist-changed", () => {
    updatePriceDropNotifications(allProducts);
  });

  const showGrid = () => {
    selectedProductId = null;
    showProductGrid(grid, currentProducts, showProductDetailForProduct);
  };

  const showProductDetailForProduct = async (product) => {
    selectedProductId = product.id;

    try {
      const response = await fetch(API_ENDPOINTS.product(product.id));

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("This product could not be found.");
        }
        throw new Error("Unable to load this product.");
      }

      const liveProduct = await response.json();

      if (selectedProductId !== product.id) {
        return;
      }

      await showProductDetail(liveProduct, showGrid);
    } catch (error) {
      console.error("Error loading product details:", error);

      if (selectedProductId !== product.id) {
        return;
      }

      productStatus.textContent =
        error instanceof TypeError
          ? "Cannot connect to the server. Please check that the API is running."
          : error.message || "Unable to load product details. Please try again.";
    }
  };

  async function fetchProducts(searchTerm = "") {
    const thisRequestId = ++requestId;
    productStatus.textContent = "Loading products...";

    try {
      const query = searchTerm.trim();
      const url = query
        ? `${API_ENDPOINTS.products}?search=${encodeURIComponent(query)}`
        : API_ENDPOINTS.products;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Unable to load products (HTTP ${response.status}).`);
      }

      const products = await response.json();

      if (!Array.isArray(products)) {
        throw new Error("Invalid product data received from the server.");
      }

      if (thisRequestId !== requestId) {
        return;
      }

      currentProducts = products;

      if (!query) {
        allProducts = products;
        updateTrendProductOptions(allProducts);

        if (!hasLoadedTrendData) {
          hasLoadedTrendData = true;
          loadCategoryTrendView();
        }
      }

      renderProducts(currentProducts, grid, showProductDetailForProduct);

      // Check all watched products, not just search results.
      if (!query && !hasLoadedPriceDropNotifications) {
        hasLoadedPriceDropNotifications = true;
        updatePriceDropNotifications(allProducts);
      }

      if (products.length === 0) {
        productStatus.textContent = query
          ? "No products match your search."
          : "No products are available yet.";
      }
    } catch (error) {
      if (thisRequestId !== requestId) {
        return;
      }

      console.error("Error loading products:", error);
      grid.replaceChildren();
      productStatus.textContent =
        error instanceof TypeError
          ? "Cannot connect to the server. Please check that the API is running."
          : error.message || "Unable to load products. Please try again.";
    }
  }

  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(() => {
      if (!app.querySelector(".product-detail")) {
        fetchProducts(searchInput.value);
      }
    }, 300);
  });
  window.addEventListener("priceunmask:collection-complete", async () => {
    hasLoadedPriceDropNotifications = false;
    resetTrendCache();

    await fetchProducts();
  });

  await fetchProducts();
}

if (trendProductSelect) {
  trendProductSelect.addEventListener(
    "change",
    loadCategoryTrendView
  );
}

loadProducts();
loadCollectorStatus();
