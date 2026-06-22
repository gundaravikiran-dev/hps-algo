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
const strategyNameButton = document.querySelector("#strategyNameButton");
const athAlgoButton = document.querySelector("#athAlgoButton");
const emaButton = document.querySelector("#emaButton");
const emaPreCrossButton = document.querySelector("#emaPreCrossButton");
const emaPreCross10Button = document.querySelector("#emaPreCross10Button");
const quitStrategyButton = document.querySelector("#quitStrategyButton");
const backtestStrategyInput = document.querySelector("#backtestStrategyInput");
const backtestDateInput = document.querySelector("#backtestDateInput");
const runBacktestButton = document.querySelector("#runBacktestButton");
const strategyMessage = document.querySelector("#strategyMessage");
const strategyRows = document.querySelector("#strategyRows");
const resultCount = document.querySelector("#resultCount");
let latestStrategyResults = [];

async function loadApp() {
  setupBacktestDate();
  const showApp = new URLSearchParams(window.location.search).get("app") === "1";
  const [statusResponse, configResponse] = await Promise.all([
    fetch("/api/kite/status"),
    fetch("/api/config"),
  ]);
  const kite = await statusResponse.json();
  const config = await configResponse.json();
  strategyNameButton.textContent = formatStrategyName(config.strategy.name);

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

function setupBacktestDate() {
  const now = new Date();
  const timezoneOffsetMs = now.getTimezoneOffset() * 60 * 1000;
  const today = new Date(now.getTime() - timezoneOffsetMs).toISOString().slice(0, 10);
  backtestDateInput.max = today;
  backtestDateInput.value = today;
}

function formatStrategyName(value) {
  if (value.toLowerCase() === "hps-algo") {
    return "HPS-Algo";
  }

  return value
    .replaceAll("-", "_")
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

async function openKiteLogin() {
  setupMessage.textContent = "Enter your Kite API key and secret to continue.";
  setupView.hidden = false;
  loginView.hidden = true;
  appView.hidden = true;
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
    primaryLoginButton.textContent = "Login";
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
          <p class="setup-message">HPS-Algo has been closed.</p>
        </main>
      `;
    }, 400);
  } catch (error) {
    button.disabled = false;
    button.textContent = "Quit App";
  }
}

document.addEventListener("click", handlePageClick);

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
  } else if (action === "run-hps") {
    runHpsAlgoStrategy();
  } else if (action === "run-ath") {
    runAthAlgoStrategy();
  } else if (action === "run-ema") {
    runEmaStrategy();
  } else if (action === "run-ema-pre-cross") {
    runEmaPreCrossStrategy();
  } else if (action === "run-ema-pre-cross-10") {
    runEmaPreCross10Strategy();
  } else if (action === "run-backtest") {
    runBacktest();
  } else if (action === "export-txt") {
    exportStockNamesTxt();
  } else if (action === "quit-strategy") {
    quitApp(quitStrategyButton);
  }
}

function runBacktest() {
  const strategyName = backtestStrategyInput.options[backtestStrategyInput.selectedIndex].text;
  const backtestDate = backtestDateInput.value;
  if (!backtestDate) {
    strategyMessage.textContent = "Select a backtest date.";
    return;
  }

  latestStrategyResults = [];
  resultCount.textContent = "-";
  strategyRows.innerHTML = '<tr><td colspan="15">Backtest backend is not connected yet.</td></tr>';
  strategyMessage.textContent = `${strategyName} backtest selected for ${backtestDate}. Backend wiring is next.`;
  runBacktestButton.textContent = "Run Backtest";
}

function exportStockNamesTxt() {
  const symbols = latestStrategyResults
    .map((item) => String(item.symbol || "").trim())
    .filter(Boolean);

  if (symbols.length === 0) {
    strategyMessage.textContent = "Run a strategy first. There are no stock names to export.";
    return;
  }

  const text = `${symbols.join("\n")}\n`;
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const downloadUrl = URL.createObjectURL(blob);
  const downloadLink = document.createElement("a");
  downloadLink.href = downloadUrl;
  downloadLink.download = `stock-names-${new Date().toISOString().slice(0, 10)}.txt`;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  downloadLink.remove();
  URL.revokeObjectURL(downloadUrl);
  strategyMessage.textContent = `Downloaded ${symbols.length.toLocaleString("en-IN")} stock names.`;
}

async function runHpsAlgoStrategy() {
  strategyNameButton.disabled = true;
  strategyNameButton.textContent = "Running";
  strategyMessage.textContent = "Checking LTP, EMA10, and EMA20 above EMA200...";

  try {
    const response = await fetch("/api/strategy/hps-algo/run", {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Strategy run failed");
    }

    resultCount.textContent = payload.count.toLocaleString("en-IN");
    renderStrategyRows(payload.results);
    strategyMessage.textContent = `Source: ${payload.source}`;
  } catch (error) {
    resultCount.textContent = "ERR";
    strategyRows.innerHTML = '<tr><td colspan="15">Unable to run strategy.</td></tr>';
    strategyMessage.textContent = error.message;
  } finally {
    strategyNameButton.disabled = false;
    strategyNameButton.textContent = "HPS-Algo";
  }
}

function formatNumber(value) {
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  });
}

async function runAthAlgoStrategy() {
  athAlgoButton.disabled = true;
  athAlgoButton.textContent = "Running";
  strategyMessage.textContent = "Running ATH-Algo without ATH/52W distance filter...";

  try {
    const response = await fetch("/api/strategy/ath-algo/run", {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "ATH-Algo run failed");
    }

    resultCount.textContent = payload.count.toLocaleString("en-IN");
    renderStrategyRows(payload.results);
    strategyMessage.textContent = payload.source;
  } catch (error) {
    resultCount.textContent = "ERR";
    strategyRows.innerHTML = '<tr><td colspan="15">Unable to run ATH-Algo.</td></tr>';
    strategyMessage.textContent = error.message;
  } finally {
    athAlgoButton.disabled = false;
    athAlgoButton.textContent = "ATH-Algo";
  }
}

async function runEmaStrategy() {
  emaButton.disabled = true;
  emaButton.textContent = "Running";
  strategyMessage.textContent = "Running EMA scanner: daily price above EMA200...";

  try {
    const response = await fetch("/api/strategy/ema/run", {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "EMA strategy run failed");
    }

    resultCount.textContent = payload.count.toLocaleString("en-IN");
    renderStrategyRows(payload.results);
    strategyMessage.textContent = payload.source;
  } catch (error) {
    resultCount.textContent = "ERR";
    strategyRows.innerHTML = '<tr><td colspan="15">Unable to run EMA strategy.</td></tr>';
    strategyMessage.textContent = error.message;
  } finally {
    emaButton.disabled = false;
    emaButton.textContent = "EMA";
  }
}

async function runEmaPreCrossStrategy() {
  emaPreCrossButton.disabled = true;
  emaPreCrossButton.textContent = "Running";
  strategyMessage.textContent = "Running EMA_PRE_CROSS: daily price above EMA200...";

  try {
    const response = await fetch("/api/strategy/ema-pre-cross/run", {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "EMA_PRE_CROSS strategy run failed");
    }

    resultCount.textContent = payload.count.toLocaleString("en-IN");
    renderStrategyRows(payload.results);
    strategyMessage.textContent = payload.source;
  } catch (error) {
    resultCount.textContent = "ERR";
    strategyRows.innerHTML = '<tr><td colspan="15">Unable to run EMA_PRE_CROSS strategy.</td></tr>';
    strategyMessage.textContent = error.message;
  } finally {
    emaPreCrossButton.disabled = false;
    emaPreCrossButton.textContent = "EMA_PRE_CROSS";
  }
}

async function runEmaPreCross10Strategy() {
  emaPreCross10Button.disabled = true;
  emaPreCross10Button.textContent = "Running";
  strategyMessage.textContent =
    "Running EMA_PRE_CROSS_10: previous 10+ EMA stack, then EMA10 cross...";

  try {
    const response = await fetch("/api/strategy/ema-pre-cross-10/run", {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "EMA_PRE_CROSS_10 strategy run failed");
    }

    resultCount.textContent = payload.count.toLocaleString("en-IN");
    renderStrategyRows(payload.results);
    strategyMessage.textContent = payload.source;
  } catch (error) {
    resultCount.textContent = "ERR";
    strategyRows.innerHTML =
      '<tr><td colspan="15">Unable to run EMA_PRE_CROSS_10 strategy.</td></tr>';
    strategyMessage.textContent = error.message;
  } finally {
    emaPreCross10Button.disabled = false;
    emaPreCross10Button.textContent = "EMA_PRE_CROSS_10";
  }
}

function renderStrategyRows(results) {
  latestStrategyResults = results;
  strategyRows.innerHTML = "";
  if (results.length === 0) {
    strategyRows.innerHTML = '<tr><td colspan="15">No stocks matched strategy.</td></tr>';
    return;
  }

  for (const item of results) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.symbol}</td>
      <td>${formatNumber(item.ltp)}</td>
      <td>${formatNumber(item.ema_10)}</td>
      <td>${formatNumber(item.ema_20)}</td>
      <td>${formatNumber(item.ema_50)}</td>
      <td>${formatNumber(item.ema_200)}</td>
      <td>${formatNumber(item.rsi_14)}</td>
      <td>${item.condition}</td>
      <td>${item.entry_zone}</td>
      <td>${formatNumber(item.above_ema_10_pct)}%</td>
      <td>${formatNumber(item.above_ema_20_pct)}%</td>
      <td>${formatNumber(item.above_ema_50_pct)}%</td>
      <td>${item.high_reference}</td>
      <td>${formatNumber(item.high_price)}</td>
      <td>${formatNumber(item.below_high_pct)}%</td>
    `;
    strategyRows.appendChild(row);
  }
}
