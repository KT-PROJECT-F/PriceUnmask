"use strict";
// Load mock products and render product cards with prices and trust labels.
const app = document.getElementById("app");
const productStatus = document.getElementById("product-status");
const searchInput = document.getElementById("product-search");
const searchBox = document.getElementById("search-box");
let priceHistoryChart = null;
const trustLabels = {
  genuine: "Genuine",
  uncertain: "Uncertain",
  likely_inflated: "Likely inflated",
  insufficient_data: "Insufficient data"
};

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

function createProductCard(product, onSelect) {
  const card = document.createElement("article");
  card.className = "product-card";
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

  const trustLabel = document.createElement("p");
  trustLabel.className = "trust-label";
  trustLabel.textContent =
    "Trust Label: " +
    (trustLabels[product.trust_label] ?? "Not available");

  card.append(name, latestPrice, lowestPrice, trustLabel);

  card.addEventListener("click", () => onSelect(product));

  card.addEventListener("keydown", (event) => {
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
  const response = await fetch(`mock/trust-score-${productId}.json`);

  if (!response.ok) {
    throw new Error("Could not load trust score");
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
      trustScore.score !== null &&
      trustScore.score !== undefined &&
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

// Load price-history data for the selected product.
async function loadPriceHistory(productId) {
  const response = await fetch(
    `mock/price-history-${productId}.json`
  );

  if (!response.ok) {
    throw new Error("Could not load price history");
  }

  const history = await response.json();

  if (
    !Array.isArray(history) ||
    !history.every(
      (item) =>
        typeof item.date === "string" &&
        typeof item.current_price_minor === "number" &&
        Number.isFinite(item.current_price_minor) &&
        (
          item.original_price_minor === null ||
          (
            typeof item.original_price_minor === "number" &&
            Number.isFinite(item.original_price_minor)
          )
        )
    )
  ) {
    throw new Error("Invalid price history data");
  }

  return history;
}

// Render the selected product's price history.
function renderPriceHistoryChart(canvas, history, currency) {
  if (priceHistoryChart) {
    priceHistoryChart.destroy();
    priceHistoryChart = null;
  }

  const formatRupees = (minorUnits) =>
    formatPrice(minorUnits, currency);

  priceHistoryChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: history.map((item) => item.date),
      datasets: [
        {
          label: "Current Price",
          data: history.map(
            (item) => item.current_price_minor / 100
          ),
          borderColor: "#2563eb",
          backgroundColor: "#2563eb",
          tension: 0.2,
        },
        {
          label: "Original Price",
          data: history.map((item) =>
            item.original_price_minor === null
              ? null
              : item.original_price_minor / 100
          ),
          borderColor: "#dc2626",
          backgroundColor: "#dc2626",
          tension: 0.2,
          spanGaps: false,
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
        y: {
          ticks: {
            callback(value) {
              return formatRupees(value * 100);
            },
          },
        },
      },
      plugins: {
        tooltip: {
        backgroundColor: "#1f2937",
        titleColor: "#ffffff",
        bodyColor: "#ffffff",
        borderColor: "#9ca3af",
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
    const [trustScore, history] = await Promise.all([
      loadTrustScore(product.id),
      loadPriceHistory(product.id),
    ]);

    // Avoid rendering if this detail view has already been removed.
    if (!detail.isConnected) {
      return;
    }

    loadingMessage.remove();
    detail.append(...buildDetailContent(product, trustScore));
    const chartCanvas = detail.querySelector("#price-history-chart");
    if (chartCanvas) {
      renderPriceHistoryChart(
        chartCanvas,
        history,
        product.currency
      );
    }
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

  renderProducts(
    filterProducts(products, searchInput.value),
    grid,
    onSelect
  );

  searchInput.focus();
}

async function loadProducts() {
  if (!app || !productStatus || !searchInput) {
    console.error("Required page elements are missing.");
    return;
  }

  const grid = document.createElement("section");
  grid.className = "product-grid";

  productStatus.textContent = "Loading products...";

  try {
    const response = await fetch("mock/products.json");

    if (!response.ok) {
      throw new Error("Could not load products");
    }

    const products = await response.json();

    if (!Array.isArray(products)) {
      throw new Error("Invalid product data");
    }

    if (products.length === 0) {
      productStatus.textContent = "No products yet.";
      return;
    }

    const showGrid = () => {
      showProductGrid(grid, products, showProductDetailForProduct);
    };

    const showProductDetailForProduct = (product) => {
      showProductDetail(product, showGrid);
    };

    app.append(grid);

    renderProducts(products, grid, showProductDetailForProduct);

    searchInput.addEventListener("input", () => {
      // Do not update the hidden grid while details are open.
      if (!grid.hidden) {
        renderProducts(
          filterProducts(products, searchInput.value),
          grid,
          showProductDetailForProduct
        );
      }
    });
  } catch (error) {
    productStatus.textContent =
      "Unable to load products. Please try again later.";

    console.error("Error loading products:", error);
  }
}

loadProducts();