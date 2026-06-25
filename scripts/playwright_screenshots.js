const { chromium } = require('playwright');

(async () => {
  const BASE = process.env.BASE || 'http://localhost:8501';
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await ctx.newPage();

  const pages = [
    { name: 'home',     label: null,                  chart: false },
    { name: 'oglyad',   label: 'Огляд',               chart: true },
    { name: 'trend',    label: 'Тренд і сезонність',  chart: true },
    { name: 'anomaly',  label: 'Аномалії',            chart: true },
    { name: 'forecast', label: 'Прогноз',             chart: true },
    { name: 'patterns', label: 'Патерни',             chart: true },
  ];

  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(6000); // дані + перший рендер

  const results = [];
  for (const p of pages) {
    if (p.label) {
      try {
        await page.getByRole('link', { name: p.label, exact: false }).first().click({ timeout: 15000 });
      } catch (e) {
        results.push({ page: p.name, navError: String(e).slice(0, 120) });
        continue;
      }
      await page.waitForTimeout(2000);
    }
    try {
      if (p.chart) await page.waitForSelector('.js-plotly-plot', { timeout: 60000 });
      else await page.waitForSelector('h1', { timeout: 20000 });
    } catch (e) { /* зафіксуємо нижче як 0 графіків */ }
    await page.waitForTimeout(2500);

    const body = await page.evaluate(() => document.body.innerText);
    const hasException = (await page.locator('[data-testid="stException"]').count()) > 0;
    const hasTraceback = /Traceback \(most recent call last\)/.test(body);
    const chartCount = await page.locator('.js-plotly-plot').count();
    const shot = `/tmp/airalerts-${p.name}.png`;
    await page.screenshot({ path: shot, fullPage: true });
    const rec = { page: p.name, hasException, hasTraceback, chartCount, shot };
    results.push(rec);
    console.log('PAGE', JSON.stringify(rec));
  }

  await browser.close();
  const clean = results.every(r => !r.hasException && !r.hasTraceback && !r.navError);
  console.log('SUMMARY_CLEAN', clean);
})();
