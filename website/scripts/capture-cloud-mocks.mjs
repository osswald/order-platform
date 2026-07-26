/**
 * One-off: render HTML UI mocks to PNGs for marketing bands that need Cloud visuals.
 * Run: node scripts/capture-cloud-mocks.mjs  (requires playwright)
 */
import { chromium } from 'playwright'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(__dirname, '../public/images')

const shell = (title, body) => `<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: "Segoe UI", system-ui, sans-serif;
    background: #e8eef7;
    color: #0f172a;
  }
  .app {
    width: 1280px;
    height: 720px;
    display: grid;
    grid-template-columns: 220px 1fr;
    background: #f8fafc;
  }
  .nav {
    background: #0f172a;
    color: #e2e8f0;
    padding: 1.25rem 1rem;
  }
  .nav .brand { font-weight: 700; font-size: 1.1rem; margin-bottom: 1.5rem; color: #fff; }
  .nav a {
    display: block;
    padding: 0.55rem 0.75rem;
    border-radius: 0.5rem;
    color: #cbd5e1;
    text-decoration: none;
    margin-bottom: 0.25rem;
    font-size: 0.92rem;
  }
  .nav a.active { background: #2563eb; color: #fff; }
  .main { padding: 1.5rem 1.75rem; overflow: hidden; }
  h1 { margin: 0 0 0.35rem; font-size: 1.55rem; }
  .sub { color: #64748b; margin: 0 0 1.25rem; font-size: 0.95rem; }
  .card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 0.85rem;
    padding: 1.1rem 1.25rem;
    margin-bottom: 1rem;
  }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  label { display: block; font-size: 0.78rem; color: #64748b; margin-bottom: 0.25rem; }
  .field {
    border: 1px solid #e2e8f0;
    border-radius: 0.45rem;
    padding: 0.55rem 0.7rem;
    background: #f8fafc;
    font-size: 0.95rem;
  }
  table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
  th, td { text-align: left; padding: 0.55rem 0.4rem; border-bottom: 1px solid #e2e8f0; }
  th { color: #64748b; font-weight: 600; font-size: 0.78rem; }
  .pill {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    background: #dbeafe;
    color: #1d4ed8;
    font-size: 0.78rem;
    font-weight: 600;
  }
  .pill.ok { background: #dcfce7; color: #15803d; }
  .row { display: flex; gap: 0.75rem; align-items: center; }
  .btn {
    background: #2563eb;
    color: #fff;
    border: none;
    border-radius: 0.5rem;
    padding: 0.55rem 0.9rem;
    font-weight: 600;
    font-size: 0.9rem;
  }
  .muted { color: #64748b; font-size: 0.9rem; }
</style>
</head>
<body>
  <div class="app" id="shot">
    <aside class="nav">
      <div class="brand">Vendiqo</div>
      <a class="${title === 'org' ? 'active' : ''}">Organisationen</a>
      <a class="${title === 'event' ? 'active' : ''}">Veranstaltungen</a>
      <a class="${title === 'reuse' ? 'active' : ''}">Artikel</a>
      <a>Kellner</a>
      <a>Geräteausleihen</a>
    </aside>
    <main class="main">${body}</main>
  </div>
</body>
</html>`

const pages = {
  'cloud-organisation.png': shell(
    'org',
    `
    <h1>Festverein Rheintal</h1>
    <p class="sub">Organisation · CHF · Schweiz</p>
    <div class="grid">
      <div class="card">
        <label>Name</label><div class="field">Festverein Rheintal</div>
        <div style="height:0.75rem"></div>
        <label>Währung</label><div class="field">CHF</div>
        <div style="height:0.75rem"></div>
        <label>Land</label><div class="field">Schweiz</div>
      </div>
      <div class="card">
        <label>Stripe Connect</label>
        <div class="row" style="margin-top:0.35rem">
          <span class="pill ok">Verbunden</span>
          <span class="muted">Auszahlungen an die Organisation</span>
        </div>
        <div style="height:1rem"></div>
        <label>Farbpalette (App Layout)</label>
        <div class="row" style="margin-top:0.5rem">
          <span style="width:28px;height:28px;border-radius:8px;background:#2563eb"></span>
          <span style="width:28px;height:28px;border-radius:8px;background:#0f766e"></span>
          <span style="width:28px;height:28px;border-radius:8px;background:#b45309"></span>
          <span style="width:28px;height:28px;border-radius:8px;background:#be123c"></span>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="row" style="justify-content:space-between;margin-bottom:0.5rem">
        <strong>Benutzer mit Zugriff</strong>
        <span class="muted">3 Personen</span>
      </div>
      <table>
        <thead><tr><th>Name</th><th>Rolle</th><th>E-Mail</th></tr></thead>
        <tbody>
          <tr><td>Lara Meier</td><td>Organisations-Admin</td><td>lara@rheintal.example</td></tr>
          <tr><td>Tom Keller</td><td>Mitglied</td><td>tom@rheintal.example</td></tr>
          <tr><td>Nina Frei</td><td>Mitglied</td><td>nina@rheintal.example</td></tr>
        </tbody>
      </table>
    </div>
    `,
  ),
  'cloud-event.png': shell(
    'event',
    `
    <h1>Sommerfest 2026</h1>
    <p class="sub">12.08.2026 – 14.08.2026 · Status: Konfiguration</p>
    <div class="grid">
      <div class="card">
        <strong>Stationen</strong>
        <table style="margin-top:0.6rem">
          <thead><tr><th>Station</th><th>Drucker</th></tr></thead>
          <tbody>
            <tr><td>Bar West</td><td>Epson TM-T20</td></tr>
            <tr><td>Küche</td><td>Epson TM-T88</td></tr>
            <tr><td>Kasse Eingang</td><td>Epson TM-T20</td></tr>
          </tbody>
        </table>
      </div>
      <div class="card">
        <strong>Geräteausleihe</strong>
        <table style="margin-top:0.6rem">
          <thead><tr><th>Gerät</th><th>Zeitraum</th></tr></thead>
          <tbody>
            <tr><td>Pi Server Rheintal</td><td>11.–15.08.</td></tr>
            <tr><td>4× Tablet Waiter</td><td>11.–15.08.</td></tr>
            <tr><td>2× Bondrucker</td><td>11.–15.08.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <div class="row" style="justify-content:space-between">
        <div>
          <strong>App-Layout</strong>
          <div class="muted">Getränke · Speisen · Menüs · 48 Artikel zugewiesen</div>
        </div>
        <button class="btn">Event speichern</button>
      </div>
    </div>
    `,
  ),
  'cloud-reuse.png': shell(
    'reuse',
    `
    <h1>Artikel · Festverein Rheintal</h1>
    <p class="sub">Katalog bleibt über Events hinweg — für das nächste Fest wiederverwenden</p>
    <div class="card">
      <table>
        <thead><tr><th>Artikel</th><th>Kategorie</th><th>Preis</th><th>Status</th></tr></thead>
        <tbody>
          <tr><td>Craft Beer 0.5</td><td>Getränke</td><td>CHF 6.50</td><td><span class="pill ok">Aktiv</span></td></tr>
          <tr><td>Weisswein Glas</td><td>Getränke</td><td>CHF 7.00</td><td><span class="pill ok">Aktiv</span></td></tr>
          <tr><td>Bratwurst Menü</td><td>Speisen</td><td>CHF 14.00</td><td><span class="pill ok">Aktiv</span></td></tr>
          <tr><td>Pommes</td><td>Speisen</td><td>CHF 5.50</td><td><span class="pill ok">Aktiv</span></td></tr>
          <tr><td>Mineral 0.5</td><td>Getränke</td><td>CHF 3.50</td><td><span class="pill ok">Aktiv</span></td></tr>
          <tr><td>Kaffee</td><td>Getränke</td><td>CHF 3.00</td><td><span class="pill ok">Aktiv</span></td></tr>
        </tbody>
      </table>
    </div>
    <div class="card row" style="justify-content:space-between">
      <div>
        <strong>Nächstes Event vorbereiten</strong>
        <div class="muted">Organisation, Katalog und Kellner sind bereits vorhanden</div>
      </div>
      <button class="btn">Event anlegen</button>
    </div>
    `,
  ),
}

await mkdir(outDir, { recursive: true })
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
for (const [filename, html] of Object.entries(pages)) {
  await page.setContent(html, { waitUntil: 'networkidle' })
  const buf = await page.locator('#shot').screenshot({ type: 'png' })
  const target = path.join(outDir, filename)
  await writeFile(target, buf)
  console.log('wrote', target)
}
await browser.close()
