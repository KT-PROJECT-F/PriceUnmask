// Frontend track starts here. First task: fetch /api/health and show the result.

const app = document.getElementById("app");

function formatPrice(price, currency) {
  if (price === null || price === undefined) {
    return "—";
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: currency
  }).format(price / 100);
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
    "Trust Label: " + (product.trust_label ?? "Unknown");
  trustLabel.className = "trust-label";

  card.append(name, latestPrice, lowestPrice, trustLabel);

  return card;
}

async function loadProducts() {
  app.replaceChildren();

  const status = document.createElement("p");
  status.textContent = "Loading...";
  status.id = "status";
  app.append(status);

  try {
    const response = await fetch("mock/products.json");

    if (!response.ok) {
      throw new Error("Could not load products");
    }

    const products = await response.json();

    const grid = document.createElement("section");
    grid.className = "product-grid";

    products.forEach((product) => {
      grid.append(createProductCard(product));
    });

    app.replaceChildren(grid);
  } catch (error) {
    status.textContent =
      "Unable to load products. Please try again later.";
    console.error(error);
  }
}

loadProducts();

