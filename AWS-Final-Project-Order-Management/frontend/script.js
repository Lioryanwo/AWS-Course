// Set this to the deployed API Gateway invoke URL, e.g.
// "https://abc123.execute-api.us-east-1.amazonaws.com/prod"
const API_BASE_URL = "https://b849mbwba8.execute-api.us-east-1.amazonaws.com/prod";

async function callApi(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  let body;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  return { status: response.status, body };
}

function showResult(elementId, result) {
  document.getElementById(elementId).textContent = JSON.stringify(result, null, 2);
}

// ---------- Toasts & status pills ----------

function showToast(message, type) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function setStatusPill(elementId, status) {
  const pill = document.getElementById(elementId);
  if (!pill) return;
  const ok = typeof status === "number" && status >= 200 && status < 300;
  pill.hidden = false;
  pill.textContent = `Last call: HTTP ${status ?? "—"}`;
  pill.className = `status-pill ${ok ? "ok" : "err"}`;
}

// Reports the outcome of one user-triggered action via both a toast and the
// section's status pill, without altering the underlying fetch/response
// handling - purely additive feedback on top of the existing result object.
function notifyResult(actionLabel, statusPillId, result) {
  const ok = typeof result.status === "number" && result.status >= 200 && result.status < 300;
  setStatusPill(statusPillId, result.status);
  const detail = ok ? "" : ` — ${result.body?.error || "request failed"}`;
  showToast(`${actionLabel}: HTTP ${result.status}${detail}`, ok ? "success" : "error");
}

// ---------- Orders ----------

async function refreshOrders() {
  const sort = document.getElementById("orders-sort").value;
  const result = await callApi(`/orders?order=${sort}`, { method: "GET" });
  showResult("orders-result", result);
  const orders = result.body?.orders || [];
  renderOrdersTable(orders);

  const totalOrdersEl = document.getElementById("summary-total-orders");
  if (totalOrdersEl && result.status === 200) {
    totalOrdersEl.textContent = orders.length;
  }

  return result;
}

function renderOrdersTable(orders) {
  const body = document.getElementById("orders-table-body");
  body.innerHTML = "";
  for (const order of orders) {
    const row = document.createElement("tr");

    const cellValues = [
      order.orderId ?? "",
      order.description ?? "",
      order.price ?? "",
      order.creationDate ?? "",
      order.lastModifiedDate ?? "",
    ];
    for (const value of cellValues) {
      const cell = document.createElement("td");
      // Order fields are persisted user input (e.g. description) and must
      // never be inserted as HTML - textContent keeps this XSS-safe.
      cell.textContent = String(value);
      row.appendChild(cell);
    }

    const actionsCell = document.createElement("td");
    const useIdButton = document.createElement("button");
    useIdButton.className = "btn btn-secondary use-order-id";
    useIdButton.textContent = "Use ID";
    useIdButton.dataset.orderId = order.orderId ?? "";
    useIdButton.addEventListener("click", () => {
      const id = useIdButton.dataset.orderId;
      document.getElementById("get-order-id").value = id;
      document.getElementById("update-order-id").value = id;
      document.getElementById("delete-order-id").value = id;
    });
    actionsCell.appendChild(useIdButton);
    row.appendChild(actionsCell);

    body.appendChild(row);
  }
}

document.getElementById("create-order-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const description = document.getElementById("create-description").value;
  const price = parseFloat(document.getElementById("create-price").value);

  const result = await callApi("/orders", {
    method: "POST",
    body: JSON.stringify({ description, price }),
  });
  showResult("orders-result", result);
  notifyResult("Create order", "orders-status", result);
  event.target.reset();
  refreshOrders();
});

document.getElementById("get-order-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const orderId = document.getElementById("get-order-id").value;
  const result = await callApi(`/orders/${encodeURIComponent(orderId)}`, { method: "GET" });
  showResult("orders-result", result);
  notifyResult("Get order", "orders-status", result);
});

document.getElementById("update-order-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const orderId = document.getElementById("update-order-id").value;
  const description = document.getElementById("update-description").value;
  const price = document.getElementById("update-price").value;

  const payload = {};
  if (description) payload.description = description;
  if (price) payload.price = parseFloat(price);

  const result = await callApi(`/orders/${encodeURIComponent(orderId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  showResult("orders-result", result);
  notifyResult("Update order", "orders-status", result);
  refreshOrders();
});

document.getElementById("delete-order-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const orderId = document.getElementById("delete-order-id").value;
  const result = await callApi(`/orders/${encodeURIComponent(orderId)}`, { method: "DELETE" });
  showResult("orders-result", result);
  notifyResult("Delete order", "orders-status", result);
  refreshOrders();
});

document.getElementById("refresh-orders").addEventListener("click", async () => {
  const result = await refreshOrders();
  notifyResult("Refresh orders", "orders-status", result);
});

// ---------- Notifications ----------

document.getElementById("subscribe-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("subscribe-email").value;
  const result = await callApi("/subscriptions", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  showResult("notifications-result", result);
  notifyResult("Subscribe", "notifications-status", result);
});

document.getElementById("unsubscribe-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("unsubscribe-email").value;
  const result = await callApi("/subscriptions/unsubscribe", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  showResult("notifications-result", result);
  notifyResult("Unsubscribe", "notifications-status", result);
});

// ---------- Reports ----------

document.getElementById("generate-summary").addEventListener("click", async () => {
  const result = await callApi("/reports/summary", { method: "GET" });
  showResult("reports-result", result);
  notifyResult("Generate PDF summary", "reports-status", result);

  const infoEl = document.getElementById("reports-summary-info");
  const countEl = document.getElementById("reports-deleted-count");
  const linkEl = document.getElementById("reports-download-link");

  if (result.body?.url) {
    infoEl.hidden = false;
    countEl.textContent = `Deleted orders included: ${result.body.deletedOrderCount ?? "—"}`;
    linkEl.href = result.body.url;
    linkEl.hidden = false;
  } else {
    linkEl.hidden = true;
  }
});

// ---------- Metrics ----------

const METRIC_LABELS = [
  "Create API Invocations",
  "Delete API Invocations",
  "Lambda Errors",
  "API 4XX Errors",
  "API 5XX Errors",
];

const ERROR_METRIC_LABELS = new Set(["Lambda Errors", "API 4XX Errors", "API 5XX Errors"]);

async function refreshMetrics() {
  const result = await callApi("/metrics", { method: "GET" });
  showResult("metrics-result", result);
  const metrics = result.body?.metrics || {};
  renderMetricsGrid(metrics);

  if (result.status === 200) {
    setSummaryValue("summary-create-invocations", metrics["Create API Invocations"]);
    setSummaryValue("summary-delete-invocations", metrics["Delete API Invocations"]);
    setSummaryValue("summary-lambda-errors", metrics["Lambda Errors"]);
  }

  return result;
}

function setSummaryValue(elementId, value) {
  const el = document.getElementById(elementId);
  if (el && value !== undefined) {
    el.textContent = value;
  }
}

function renderMetricsGrid(metrics) {
  const grid = document.getElementById("metrics-grid");
  grid.innerHTML = "";

  const maxValue = Math.max(1, ...METRIC_LABELS.map((label) => Number(metrics[label]) || 0));

  for (const label of METRIC_LABELS) {
    const value = metrics[label] ?? "-";
    const numericValue = Number(metrics[label]) || 0;

    const tile = document.createElement("div");
    tile.className = "metric-tile" + (ERROR_METRIC_LABELS.has(label) ? " has-errors" : "");

    const valueEl = document.createElement("div");
    valueEl.className = "value";
    valueEl.textContent = value;

    const labelEl = document.createElement("div");
    labelEl.className = "label";
    labelEl.textContent = label;

    const bar = document.createElement("div");
    bar.className = "metric-bar";
    const barFill = document.createElement("div");
    barFill.className = "metric-bar-fill";
    barFill.style.width = `${Math.min(100, (numericValue / maxValue) * 100)}%`;
    bar.appendChild(barFill);

    tile.appendChild(valueEl);
    tile.appendChild(labelEl);
    tile.appendChild(bar);
    grid.appendChild(tile);
  }
}

document.getElementById("refresh-metrics").addEventListener("click", async () => {
  const result = await refreshMetrics();
  notifyResult("Refresh metrics", "metrics-status", result);
});

// ---------- Initial load ----------

function setApiStatusBadge(ordersResult, metricsResult) {
  const badge = document.getElementById("api-status-badge");
  const dot = badge.querySelector(".status-dot") || document.createElement("span");
  dot.className = "status-dot";

  const online = ordersResult.status === 200 && metricsResult.status === 200;
  badge.className = `status-badge ${online ? "status-online" : "status-offline"}`;
  badge.replaceChildren(dot, document.createTextNode(online ? " API Online" : " API Unreachable"));
}

Promise.all([refreshOrders(), refreshMetrics()]).then(([ordersResult, metricsResult]) => {
  setApiStatusBadge(ordersResult, metricsResult);
});
