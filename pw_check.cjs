const { chromium } = require("playwright");
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1400, height: 900 });
  const consoleErrors = [];
  page.on("console", msg => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
  page.on("pageerror", err => consoleErrors.push("PAGEERROR: " + err.message));
  await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 15000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: "D:\\ict-backtest\\screenshot_initial.png", fullPage: false });
  const result = {
    title: await page.title(),
    consoleErrors,
    h1: await page.locator("h1").textContent().catch(() => null),
    loadBtn: await page.locator("button:has-text('Load Chart')").isVisible().catch(() => false),
    backtestBtn: await page.locator("button:has-text('Run Backtest')").isVisible().catch(() => false),
    kzOnly: await page.locator("text=KZ Only").isVisible().catch(() => false),
    reqSweep: await page.locator("text=Req. Sweep").isVisible().catch(() => false),
    ingestBtn: await page.locator("button:has-text('Ingest Data')").isVisible().catch(() => false),
  };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})();
