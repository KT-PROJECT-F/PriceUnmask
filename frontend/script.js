// Load mock products and render product cards with prices and trust labels.
const productStatus = document.getElementById("product-status");

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

function createProductCard(product) {
  const card = document.createElement("article");
  card.className = "product-card";

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

  return card;
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

    products.forEach((product) => {
      grid.append(createProductCard(product));
    });

    document.getElementById("app").append(grid);
    productStatus.textContent = "";
  } catch (error) {
    productStatus.textContent =
      "Unable to load products. Please try again later.";
    console.error(error);
  }
}

loadProducts();