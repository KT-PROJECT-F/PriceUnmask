
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const script = fs.readFileSync(
  path.join(__dirname, "../frontend/script.js"),
  "utf8"
);

function createElement(tagName = "div") {
  return {
    tagName,
    textContent: "",
    className: "",
    children: [],
    style: {},
    append(...elements) {
      this.children.push(...elements);
    },
    replaceChildren(...elements) {
      this.children = [...elements];
    },
    addEventListener() {},
    querySelector() {
      return null;
    },
    focus() {}
  };
}

function createFrontend(watchlist = []) {
  const elements = new Map();

  elements.set("app", createElement());
  elements.set("product-status", createElement());
  elements.set("product-search", {
    value: "",
    addEventListener() {}
  });
  elements.set("search-box", createElement());
  elements.set("collector-status-message", createElement());
  elements.set("run-collector-button", createElement());
  elements.set("collector-action-message", createElement());
  elements.set("category-trends-status", createElement());
  elements.set("category-trend-chart", createElement());
  elements.set("trend-product-select", {
    value: "",
    disabled: false,
    addEventListener() {},
    replaceChildren() {},
    append() {}
  });

  for (const id of [
    "notification-status",
    "notification-list",
    "trend-overview-status",
    "trend-overview-summary"
  ]) {
    elements.set(id, createElement());
  }

  const requests = [];
  let mockFetch = async () => {
    throw new Error("Unexpected API request");
  };

  const context = vm.createContext({
    window: {
      addEventListener() {}
    },
    console,
    Intl,
    Date,
    Number,
    Set,
    Map,
    Promise,
    encodeURIComponent,
    localStorage: {
      getItem(key) {
        return key === "priceunmask-watchlist"
          ? JSON.stringify(watchlist)
          : null;
      }
    },
    document: {
      getElementById(id) {
        return elements.get(id) || null;
      },
      querySelector() {
        return null;
      },
      createElement
    },
    fetch(url) {
      requests.push(url);
      return mockFetch(url);
    }
  });

  context.PRICEUNMASK_DISABLE_AUTO_START = true;
  vm.runInContext(script, context);

  return {
    elements,
    requests,
    context,
    setFetch(fn) {
      mockFetch = fn;
    }
  };
}

function mockResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return data;
    }
  };
}


test("price-drop notifications use the backend API", async () => {
  const frontend = createFrontend(["1"]);

  frontend.setFetch(async (url) => {
    assert.equal(url, "/api/products/1/price-drop");

    return mockResponse({
      product_id: 1,
      status: "price_dropped",
      previous_price_minor: 299900,
      current_price_minor: 104900,
      drop_amount_minor: 195000,
      drop_percent: 0.96
    });
  });

  const products = [
    {
      id: 1,
      name: "Demo Air Fryer",
      currency: "INR"
    }
  ];

  await vm.runInContext(
    "updatePriceDropNotifications",
    frontend.context
  )(products);

  assert.deepEqual(frontend.requests, [
    "/api/products/1/price-drop"
  ]);

  const status = frontend.elements.get("notification-status");
  const list = frontend.elements.get("notification-list");

  assert.match(status.textContent, /1 watched product/);
  assert.equal(list.children.length, 1);

  const alert = list.children[0];

  assert.equal(alert.children[0].textContent, "Demo Air Fryer");
  assert.match(alert.children[1].textContent, /₹2,999/);
  assert.equal(
  alert.children[2].textContent,
  "Price dropped 0.96%"
);
});


test("no_drop response does not create an alert", async () => {
  const frontend = createFrontend(["1"]);

  frontend.setFetch(async () =>
    mockResponse({
      product_id: 1,
      status: "no_drop",
      previous_price_minor: 100000,
      current_price_minor: 100000,
      drop_amount_minor: 0,
      drop_percent: 0
    })
  );

  await vm.runInContext(
    "updatePriceDropNotifications",
    frontend.context
  )([
    { id: 1, name: "Demo Product", currency: "INR" }
  ]);

  assert.equal(
    frontend.elements.get("notification-list").children.length,
    0
  );

  assert.match(
    frontend.elements.get("notification-status").textContent,
    /No recent price drops/
  );
});

test("insufficient_history response is handled", async () => {
  const frontend = createFrontend(["1"]);

  frontend.setFetch(async () =>
    mockResponse({
      product_id: 1,
      status: "insufficient_history",
      previous_price_minor: null,
      current_price_minor: null,
      drop_amount_minor: null,
      drop_percent: null
    })
  );

  await vm.runInContext(
    "updatePriceDropNotifications",
    frontend.context
  )([
    { id: 1, name: "Demo Product", currency: "INR" }
  ]);

  assert.equal(
    frontend.elements.get("notification-list").children.length,
    0
  );

  assert.match(
    frontend.elements.get("notification-status").textContent,
    /insufficient price history/
  );
});


test("empty watchlist does not call the price-drop API", async () => {
  const frontend = createFrontend([]);

  const products = [
    { id: 1, name: "Demo Product", currency: "INR" }
  ];

  await vm.runInContext(
    "updatePriceDropNotifications",
    frontend.context
  )(products);

  assert.equal(frontend.requests.length, 0);

  assert.equal(
    frontend.elements.get("notification-list").children.length,
    0
  );

  assert.equal(
    frontend.elements.get("notification-status").textContent,
    "No watched products to check."
  );
});


test("price-drop API failure shows an error message", async () => {
  const frontend = createFrontend(["1"]);

  frontend.setFetch(async (url) => {
    assert.equal(url, "/api/products/1/price-drop");

    return mockResponse(
      { detail: "Internal Server Error" },
      500
    );
  });

  const products = [
    { id: 1, name: "Demo Product", currency: "INR" }
  ];

  await vm.runInContext(
    "updatePriceDropNotifications",
    frontend.context
  )(products);

  assert.equal(frontend.requests.length, 1);

  assert.equal(
    frontend.elements.get("notification-list").children.length,
    0
  );

  assert.match(
    frontend.elements.get("notification-status").textContent,
    /1 product\(s\) could not be checked/
  );

  assert.match(
  frontend.elements.get("notification-status").textContent,
  /Unable to check price drops right now/
  );

  assert.doesNotMatch(
    frontend.elements.get("notification-status").textContent,
    /No recent price drops/
  );
});

test("price-drop network failure shows an error message", async () => {
  const frontend = createFrontend(["1"]);

  frontend.setFetch(async () => {
    throw new TypeError("Failed to fetch");
  });

  const products = [
    { id: 1, name: "Demo Product", currency: "INR" }
  ];

  await vm.runInContext(
    "updatePriceDropNotifications",
    frontend.context
  )(products);

  assert.equal(frontend.requests.length, 1);

  assert.equal(
    frontend.elements.get("notification-list").children.length,
    0
  );

  const status =
    frontend.elements.get("notification-status").textContent;

  assert.ok(status.includes("Unable to check price drops right now."));
  assert.ok(status.includes("1 product(s) could not be checked."));
  assert.ok(!status.includes("No recent price drops"));
});

test("loadProducts handles network failure", async () => {
  const frontend = createFrontend();

  const networkError = vm.runInContext(
    'new TypeError("Failed to fetch")',
    frontend.context
  );

  frontend.setFetch(async (url) => {
    assert.equal(url, "/api/products");
    throw networkError;
  });

  await vm.runInContext(
    "loadProducts()",
    frontend.context
  );

  assert.deepEqual(frontend.requests, ["/api/products"]);

  assert.equal(
    frontend.elements.get("product-status").textContent,
    "Cannot connect to the server. Please check that the API is running."
  );

  const app = frontend.elements.get("app");

  assert.equal(app.children.length, 1);
  assert.equal(app.children[0].children.length, 0);
});

test("trend overview displays backend API statistics", async () => {
  const frontend = createFrontend();

  frontend.setFetch(async (url) => {
    assert.equal(url, "/api/trends/overview?period_days=30");

    return mockResponse({
      period_days: 30,
      products_analyzed: 63,
      products_decreasing: 10,
      products_increasing: 5,
      products_stable: 45,
      products_insufficient_history: 3,
      average_change_percent: -2.5,
      products: []
    });
  });

  await vm.runInContext(
    "loadTrendOverview",
    frontend.context
  )();

  assert.deepEqual(frontend.requests, [
    "/api/trends/overview?period_days=30"
  ]);

  const status = frontend.elements.get("trend-overview-status");
  const summary = frontend.elements.get("trend-overview-summary");

  assert.equal(
    status.textContent,
    "30-day trend overview loaded."
  );

  const displayedText = summary.children
    .map((item) =>
      item.children.length
        ? item.children.map((child) => child.textContent).join("")
        : item.textContent
    )
    .join(" ");

  assert.match(displayedText, /Products Analyzed: 63/);
  assert.match(displayedText, /Prices Decreasing: 10/);
  assert.match(displayedText, /Prices Increasing: 5/);
  assert.match(displayedText, /Stable Prices: 45/);
  assert.match(displayedText, /Insufficient History: 3/);
  assert.match(displayedText, /Average Price Change: -2\.5%/);
});


test("trend overview handles API failure", async () => {
  const frontend = createFrontend();

  frontend.setFetch(async (url) => {
    assert.equal(url, "/api/trends/overview?period_days=30");

    return mockResponse(
      { detail: "Internal Server Error" },
      500
    );
  });

  await vm.runInContext(
    "loadTrendOverview",
    frontend.context
  )();

  assert.equal(frontend.requests.length, 1);

  const status = frontend.elements.get("trend-overview-status");
  const summary = frontend.elements.get("trend-overview-summary");

  assert.equal(
    status.textContent,
    "Trend overview is not available right now."
  );

  assert.equal(summary.children.length, 0);
});


test("trend overview handles empty data", async () => {
  const frontend = createFrontend();

  frontend.setFetch(async (url) => {
    assert.equal(url, "/api/trends/overview?period_days=30");

    return mockResponse({
      period_days: 30,
      products_analyzed: 0,
      products_decreasing: 0,
      products_increasing: 0,
      products_stable: 0,
      products_insufficient_history: 0,
      average_change_percent: null,
      products: []
    });
  });

  await vm.runInContext(
    "loadTrendOverview",
    frontend.context
  )();

  const status = frontend.elements.get("trend-overview-status");
  const summary = frontend.elements.get("trend-overview-summary");

  assert.equal(
    status.textContent,
    "No products available for trend analysis."
  );

  assert.equal(summary.children.length, 5);
});
