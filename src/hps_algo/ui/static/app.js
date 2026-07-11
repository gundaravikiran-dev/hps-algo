const setupView = document.querySelector("#setupView");
const loginView = document.querySelector("#loginView");
const appView = document.querySelector("#appView");
const apiKeyInput = document.querySelector("#apiKeyInput");
const apiSecretInput = document.querySelector("#apiSecretInput");
const saveSetupButton = document.querySelector("#saveSetupButton");
const setupMessage = document.querySelector("#setupMessage");
const primaryLoginButton = document.querySelector("#primaryLoginButton");
const quitLoginButton = document.querySelector("#quitLoginButton");
const loginMessage = document.querySelector("#loginMessage");
const quitStrategyButton = document.querySelector("#quitStrategyButton");
const strategyMenu = document.querySelector("#strategyMenu");
const strategyMessage = document.querySelector("#strategyMessage");
const strategyRows = document.querySelector("#strategyRows");
const resultCount = document.querySelector("#resultCount");
const resultTitle = document.querySelector("#resultTitle");
const exportMenu = document.querySelector("#exportMenu");
const exportMenuButton = document.querySelector("#exportMenuButton");
const txtExportLink = document.querySelector("#txtExportLink");
const excelExportLink = document.querySelector("#excelExportLink");
const sortButtons = document.querySelectorAll("[data-sort]");

let currentResults = [];
let currentSort = {
  key: "",
  direction: "",
};

const strategies = {
  "run-hps": {
    title: "HPS-Algo",
    endpoint: "/api/strategy/hps-algo/run",
    txtExport: "/api/strategy/hps-algo/export.txt",
    excelExport: "/api/strategy/hps-algo/export.xls",
    runningMessage: "Running HPS-Algo scanner...",
    errorMessage: "Unable to run HPS-Algo.",
  },
  "run-ath": {
    title: "ATH-Algo",
    endpoint: "/api/strategy/ath-algo/run",
    txtExport: "/api/strategy/ath-algo/export.txt",
    excelExport: "/api/strategy/ath-algo/export.xls",
    runningMessage: "Running ATH-Algo scanner...",
    errorMessage: "Unable to run ATH-Algo.",
  },
  "run-ema": {
    title: "EMA",
    endpoint: "/api/strategy/ema/run",
    txtExport: "/api/strategy/ema/export.txt",
    excelExport: "/api/strategy/ema/export.xls",
    runningMessage: "Running EMA scanner...",
    errorMessage: "Unable to run EMA.",
  },
  "run-ema-pre-cross": {
    title: "EMA_PRE_CROSS",
    endpoint: "/api/strategy/ema-pre-cross/run",
    txtExport: "/api/strategy/ema-pre-cross/export.txt",
    excelExport: "/api/strategy/ema-pre-cross/export.xls",
    runningMessage: "Running EMA_PRE_CROSS scanner...",
    errorMessage: "Unable to run EMA_PRE_CROSS.",
  },
  "run-ema-pre-cross-10": {
    title: "EMA_PRE_CROSS_10",
    endpoint: "/api/strategy/ema-pre-cross-10/run",
    txtExport: "/api/strategy/ema-pre-cross-10/export.txt",
    excelExport: "/api/strategy/ema-pre-cross-10/export.xls",
    runningMessage: "Running EMA_PRE_CROSS_10 scanner...",
    errorMessage: "Unable to run EMA_PRE_CROSS_10.",
  },
};

async function loadApp() {
  const showApp = new URLSearchParams(window.location.search).get("app") === "1";
  const [statusResponse, configResponse] = await Promise.all([
    fetch("/api/kite/status"),
    fetch("/api/config"),
  ]);
  const kite = await statusResponse.json();
  await configResponse.json();

  if (showApp && kite.connected) {
    setupView.hidden = true;
    loginView.hidden = true;
    appView.hidden = false;
    return;
  }

  setupView.hidden = true;
  loginView.hidden = false;
  appView.hidden = true;
}

async function openKiteLogin() {
  setupMessage.textContent = "Enter your Kite API key and secret to continue.";
  await populateSavedCredentials();
  setupView.hidden = false;
  loginView.hidden = true;
  appView.hidden = true;
}

async function populateSavedCredentials() {
  try {
    const response = await fetch("/api/kite/credentials");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not load saved Kite credentials.");
    }

    apiKeyInput.value = payload.api_key || "";
    apiSecretInput.value = payload.api_secret || "";
  } catch (error) {
    setupMessage.textContent = error.message;
  }
}

async function continueToKiteLogin() {
  primaryLoginButton.disabled = true;
  primaryLoginButton.textContent = "Opening";
  loginMessage.textContent = "";

  try {
    const response = await fetch("/api/kite/login-url");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not create Kite login URL");
    }
    window.location.href = payload.login_url;
  } catch (error) {
    loginMessage.textContent = error.message;
    primaryLoginButton.disabled = false;
    primaryLoginButton.textContent = "Login with Zerodha Kite";
  }
}

async function saveSetup() {
  const apiKey = apiKeyInput.value.trim();
  const apiSecret = apiSecretInput.value.trim();
  if (!apiKey || !apiSecret) {
    setupMessage.textContent = "API key and secret are required.";
    return;
  }

  saveSetupButton.disabled = true;
  saveSetupButton.textContent = "Saving";
  setupMessage.textContent = "";

  try {
    const response = await fetch("/api/kite/credentials", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api_key: apiKey,
        api_secret: apiSecret,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not save Kite credentials.");
    }

    setupMessage.textContent = "Saved. Opening Kite login...";
    apiSecretInput.value = "";
    await continueToKiteLogin();
  } catch (error) {
    setupMessage.textContent = error.message;
  } finally {
    saveSetupButton.disabled = false;
    saveSetupButton.textContent = "Save";
  }
}

async function quitApp(button) {
  button.disabled = true;
  button.textContent = "Closing";

  try {
    await fetch("/api/app/shutdown", {
      method: "POST",
    });
    window.setTimeout(() => {
      document.body.innerHTML = `
        <main class="login-view">
          <p class="setup-message">Momentum Algo has been closed.</p>
        </main>
      `;
    }, 400);
  } catch (error) {
    button.disabled = false;
    button.textContent = "Quit App";
  }
}

document.addEventListener("click", handlePageClick);
document.addEventListener("click", closeStrategyMenuOnOutsideClick);
strategyMenu.addEventListener("mouseleave", closeStrategyMenu);
for (const button of sortButtons) {
  button.addEventListener("click", () => sortResults(button.dataset.sort));
}

loadApp();

function handlePageClick(event) {
  const actionElement = event.target.closest("[data-action]");
  if (!actionElement) {
    return;
  }

  const action = actionElement.dataset.action;
  if (action === "save-setup") {
    saveSetup();
  } else if (action === "open-kite-login") {
    openKiteLogin();
  } else if (action === "quit-login") {
    quitApp(quitLoginButton);
  } else if (action === "toggle-strategy-menu") {
    strategyMenu.classList.toggle("menu-open");
  } else if (strategies[action]) {
    strategyMenu.classList.remove("menu-open");
    runSelectedStrategy(action, actionElement);
  } else if (action === "reset-sort") {
    resetSort();
  } else if (action === "quit-strategy") {
    quitApp(quitStrategyButton);
  }
}

function formatNumber(value) {
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  });
}

function closeStrategyMenuOnOutsideClick(event) {
  if (event.target.closest(".strategy-menu")) {
    return;
  }

  closeStrategyMenu();
}

function closeStrategyMenu() {
  strategyMenu.classList.remove("menu-open");
}

async function runSelectedStrategy(action, button) {
  const strategy = strategies[action];
  button.disabled = true;
  button.classList.add("is-loading");
  resultTitle.textContent = `${strategy.title} Results`;
  updateExportLinks(strategy);
  resultCount.textContent = "-";
  currentResults = [];
  currentSort = { key: "", direction: "" };
  updateSortIndicators();
  strategyRows.innerHTML =
    '<tr><td colspan="6"><span class="table-loading"><span class="loading-spinner" aria-hidden="true"></span>Loading strategy results...</span></td></tr>';
  strategyMessage.innerHTML = `<span class="loading-message"><span class="loading-spinner" aria-hidden="true"></span>${strategy.runningMessage}</span>`;

  try {
    const response = await fetch(strategy.endpoint, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `${strategy.title} run failed`);
    }

    resultCount.textContent = payload.count.toLocaleString("en-IN");
    currentResults = payload.results || [];
    currentSort = { key: "", direction: "" };
    updateSortIndicators();
    renderStrategyRows(currentResults);
    strategyMessage.textContent = "";
  } catch (error) {
    currentResults = [];
    updateSortIndicators();
    resultCount.textContent = "ERR";
    strategyRows.innerHTML = `<tr><td colspan="6">${strategy.errorMessage}</td></tr>`;
    strategyMessage.textContent = error.message;
  } finally {
    button.disabled = false;
    button.classList.remove("is-loading");
  }
}

function renderStrategyRows(results) {
  strategyRows.innerHTML = "";
  if (results.length === 0) {
    strategyRows.innerHTML = '<tr><td colspan="6">No stocks matched strategy.</td></tr>';
    return;
  }

  for (const [index, item] of results.entries()) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${index + 1}</td>
      <td>${item.stock_name || item.symbol}</td>
      <td class="stock-cell">${item.symbol}</td>
      <td class="positive-cell">${formatNumber(item.ltp)}</td>
      <td>${formatNumber(item.volume || 0)}</td>
      <td class="${Number(item.latest_candle_pct || 0) >= 0 ? "positive-cell" : "negative-cell"}">${formatNumber(item.latest_candle_pct || 0)}%</td>
    `;
    strategyRows.appendChild(row);
  }
}

function updateExportLinks(strategy) {
  exportMenu.classList.remove("is-disabled");
  exportMenuButton.disabled = false;
  txtExportLink.href = strategy.txtExport;
  txtExportLink.removeAttribute("aria-disabled");
  txtExportLink.removeAttribute("tabindex");
  excelExportLink.href = strategy.excelExport;
  excelExportLink.removeAttribute("aria-disabled");
  excelExportLink.removeAttribute("tabindex");
}

function sortResults(key) {
  if (!currentResults.length) {
    return;
  }

  if (currentSort.key === key && currentSort.direction === "desc") {
    resetSort();
    return;
  }

  const direction =
    currentSort.key === key && currentSort.direction === "asc" ? "desc" : "asc";
  currentSort = { key, direction };
  const sortedResults = [...currentResults].sort((left, right) =>
    compareResultValues(left, right, key, direction),
  );
  renderStrategyRows(sortedResults);
  updateSortIndicators();
}

function resetSort() {
  if (!currentResults.length) {
    return;
  }

  currentSort = { key: "", direction: "" };
  renderStrategyRows(currentResults);
  updateSortIndicators();
}

function compareResultValues(left, right, key, direction) {
  const leftValue = resultSortValue(left, key);
  const rightValue = resultSortValue(right, key);
  const modifier = direction === "asc" ? 1 : -1;

  if (typeof leftValue === "number" && typeof rightValue === "number") {
    return (leftValue - rightValue) * modifier;
  }

  return String(leftValue).localeCompare(String(rightValue), "en", {
    sensitivity: "base",
    numeric: true,
  }) * modifier;
}

function resultSortValue(item, key) {
  if (key === "index") {
    return currentResults.indexOf(item);
  }

  if (key === "stock_name") {
    return item.stock_name || item.symbol || "";
  }

  if (["ltp", "volume", "latest_candle_pct"].includes(key)) {
    return Number(item[key] || 0);
  }

  return item[key] || "";
}

function updateSortIndicators() {
  for (const button of sortButtons) {
    const isActive = button.dataset.sort === currentSort.key;
    button.classList.toggle("is-active", isActive);
    button.dataset.direction = isActive ? currentSort.direction : "";
  }
}
