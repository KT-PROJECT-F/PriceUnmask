// Load mock products and render product cards with prices and trust labels.
const app = document.getElementById("app");
const productStatus = document.getElementById("product-status");
const searchInput = document.getElementById("product-search");

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
      currency: currency
    }).format(price / 100);
  } catch (error) {
    console.error("Bad currency", currency, error);
    return "—";
  }
}

function createProductCard(product, onSelect) {
  const card = document.createElement("article");
  card.className = "product-card";
  card.tabIndex = 0;

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
  trustLabel.textContent =
    "Trust Label: " +
    (trustLabels[product.trust_label] ?? "Not available");
  trustLabel.className = "trust-label";

  card.append(name, latestPrice, lowestPrice, trustLabel);

  card.addEventListener("click", () => {
    onSelect(product);
  });

  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
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
    product.name.toLowerCase().includes(normalizedSearch)
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

async function loadTrustScore(productId) {
  const response = await fetch(`mock/trust-score-${productId}.json`);

  if (!response.ok) {
    throw new Error("Could not load trust score");
  }

  const trustScore = await response.json();

  if (!trustScore || typeof trustScore !== "object") {
    throw new Error("Invalid trust score data");
  }

  return trustScore;
}

async function showProductDetail(product, showGrid) {
  const grid = document.querySelector(".product-grid");

  if (grid) {
    grid.hidden = true;
  }

  searchInput.hidden = true;
  productStatus.textContent = "Loading product details...";

  let trustScore;

  try {
    trustScore = await loadTrustScore(product.id);
  } catch (error) {
    productStatus.textContent =
      "Unable to load product details. Please try again later.";
    console.error(error);
    return;
  }

  const detail = document.createElement("section");
  detail.className = "product-detail";
  detail.setAttribute("aria-labelledby", "product-detail-title");

  const backButton = document.createElement("button");
  backButton.type = "button";
  backButton.textContent = "Back to products";
  backButton.addEventListener("click", showGrid);

  const title = document.createElement("h2");
  title.id = "product-detail-title";
  title.textContent = product.name;

  const shopLink = document.createElement("a");
  shopLink.href = product.url;
  shopLink.target = "_blank";
  shopLink.rel = "noopener noreferrer";
  shopLink.textContent = "Visit shop";

  const latestPrice = document.createElement("p");
  latestPrice.textContent =
    "Latest Price: " +
    formatPrice(product.latest_price_minor, product.currency);

  const lowestPrice = document.createElement("p");
  lowestPrice.textContent =
    "Lowest Price: " +
    formatPrice(product.lowest_price_minor, product.currency);

  const scoreHeading = document.createElement("h3");
  scoreHeading.textContent = "Trust Score";

  const scoreBadge = document.createElement("span");
  scoreBadge.className = `trust-badge trust-badge-${trustScore.label}`;
  scoreBadge.textContent =
    trustScore.score === null
      ? trustLabels[trustScore.label]
      : `${trustScore.score} — ${trustLabels[trustScore.label]}`;

  const reasonsHeading = document.createElement("h3");
  reasonsHeading.textContent = "Why?";

  const reasonsList = document.createElement("ul");

  trustScore.reasons.forEach((reason) => {
    const reasonItem = document.createElement("li");
    reasonItem.textContent = reason;
    reasonsList.append(reasonItem);
  });

  const chartPlaceholder = document.createElement("div");
  chartPlaceholder.className = "price-chart-placeholder";
  chartPlaceholder.textContent = "Price chart — coming next working day";
  chartPlaceholder.setAttribute("aria-label", "Price chart placeholder");

  detail.append(
    backButton,
    title,
    shopLink,
    latestPrice,
    lowestPrice,
    scoreHeading,
    scoreBadge,
    reasonsHeading,
    reasonsList,
    chartPlaceholder
  );

  app.append(detail);
  productStatus.textContent = "";
  backButton.focus();
}

function showProductGrid(grid, products, onSelect) {
  const detail = document.querySelector(".product-detail");

  if (detail) {
    detail.remove();
  }

  searchInput.hidden = false;
  grid.hidden = false;

  renderProducts(
    filterProducts(products, searchInput.value),
    grid,
    onSelect
  );

  searchInput.focus();
}

async function loadProducts() {
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

    app.append(grid);

    const showGrid = () => {
      showProductGrid(grid, products, showProductDetailForProduct);
    };

    const showProductDetailForProduct = (product) => {
      showProductDetail(product, showGrid);
    };

    renderProducts(products, grid, showProductDetailForProduct);

    searchInput.addEventListener("input", (event) => {
      const filteredProducts = filterProducts(
        products,
        event.target.value
      );

      renderProducts(
        filteredProducts,
        grid,
        showProductDetailForProduct
      );
    });
  } catch (error) {
    productStatus.textContent =
      "Unable to load products. Please try again later.";
    console.error(error);
  }
}

loadProducts();