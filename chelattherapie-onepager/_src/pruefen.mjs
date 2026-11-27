#!/usr/bin/env node
/*
 * Prüfwerkzeug für die Onepager-Entwürfe: Headless-Chrome über das DevTools-Protokoll, ohne Zusatzpakete (Node >= 22).
 *
 *   node _src/pruefen.mjs shots entwurf-a-salbei.html --w 375,1440     Screenshots: ganze Seite + Bildschirm für Bildschirm
 *   node _src/pruefen.mjs audit entwurf-a-salbei.html --w 375,768,1280 Layout-/Barriere-Check als JSON (Überlauf, Kontrast, Tippflächen …)
 *   node _src/pruefen.mjs jank  entwurf-a-salbei.html --w 375,1440     Ruckel-Messung: Trace beim Laden und beim Scrollen
 *   node _src/pruefen.mjs menue entwurf-a-salbei.html --w 375,844 --h 812,390
 *                                                                      Menü-Prüfung als JSON + Screenshots: Tippen, Fokus,
 *                                                                      Tab-Reihenfolge, Escape, Klick daneben, Scrollen im
 *                                                                      Menü (letzter Punkt erreichbar), Leiste weg, Abdunklung
 *   node _src/pruefen.mjs cls   entwurf-a-salbei.html --w 1024,1440 --netz slow4g --runs 5
 *                                                                      Nur Ladeverhalten, mehrfach: CLS mit Verschiebungen, FCP, LCP
 *   node _src/pruefen.mjs mechanik entwurf-a-salbei.html --w 375,1440
 *                                                                      Gemeinsame Mechanik als JSON: Handy-Leiste an jeder Scroll-
 *                                                                      Position (sichtbar genau dann, wenn kein [data-mcta-hide]-
 *                                                                      Bereich im Bild ist; der Streifen hinter einer festen Kopf-
 *                                                                      zeile zählt nicht), Header .scrolled, data-tel, Kopieren,
 *                                                                      aktiver Menüpunkt je Abschnitt (aria-current)
 *
 * Optionen:  --out <ordner>   Ausgabe (Standard: %TEMP%/chelat-pruefung), darin ein Unterordner je Seite
 *            --root <ordner>  anderer Wurzelordner für den Server, relativ zum Projekt (z. B. _release). Standard: Projekt
 *            --reduced        prefers-reduced-motion: reduce emulieren
 *            --no-tiles       bei shots nur die ganze Seite
 *            --max-tiles <n>  bei shots höchstens n Bildschirme (von oben)
 *            --klick <css>    shots: nach dem Laden auf das Element tippen/klicken, dann NUR den ersten Bildschirm
 *                             aufnehmen (<breite>-klick.jpg), kein Durchscrollen. Beispiel: --klick .menu-btn
 *            --vorher <js>    shots mit --klick / menue: JavaScript nach dem Laden, vor dem Klick (z. B. "scrollTo(0,2000)")
 *            --nachher <js>   shots mit --klick: JavaScript nach dem Klick, vor dem Screenshot
 *            --netz <profil>  Netz drosseln: slow4g (150 ms, 1,6 Mbit/s) oder fast4g (40 ms, 9 Mbit/s); Standard: ungedrosselt
 *            --cpu <n>        CPU n-fach verlangsamen (z. B. 4 = Mittelklasse-Handy)
 *            --runs <n>       cls: Anzahl Ladevorgänge je Breite (CLS schwankt, Standard 3)
 *            --dpr <n>        Pixeldichte (Standard 1)
 *            --ohne-gpu       Software-Compositing (--disable-gpu). Für gesperrte Windows-Sitzungen: Dort drosselt Windows
 *                             den GPU-Prozess, Frame-Werte von jank sind dann wertlos (Frames im 250/500-ms-Takt)
 *            --h <px>         Fensterhöhe (Standard: 812 Handy, 1024 Tablet, 900 Desktop). Mehrere Werte (812,390)
 *                             gelten paarweise zu --w
 * Breiten unter 1024 px werden als Touch-Gerät emuliert (kein Hover, grober Zeiger, Tippen per Touch-Ereignis),
 * ab 1024 als Desktop mit Maus.
 */
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const PROJEKT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CHROME = process.env.CHROME || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].find(p => fs.existsSync(p));
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------------------------------------------------------------- Argumente
const [cmd, page, ...rest] = process.argv.slice(2);
const opt = { w: '375,1440', out: path.join(os.tmpdir(), 'chelat-pruefung'), dpr: '1' };
for (let i = 0; i < rest.length; i++) {
  const a = rest[i];
  if (!a.startsWith('--')) continue;
  const k = a.slice(2);
  if (['reduced', 'no-tiles', 'ohne-gpu'].includes(k)) opt[k] = true; else opt[k] = rest[++i];
}
if (!['shots', 'audit', 'jank', 'menue', 'mechanik', 'cls'].includes(cmd) || !page) {
  console.error('Aufruf: node _src/pruefen.mjs <shots|audit|jank|menue|mechanik|cls> <seite.html> [--w 375,1440] [--h 812] [--out ordner] [--root ordner]'
    + ' [--reduced] [--no-tiles] [--max-tiles n] [--klick css] [--vorher js] [--nachher js] [--netz slow4g] [--cpu 4] [--runs 3] [--dpr 2]');
  process.exit(2);
}
if (!CHROME) { console.error('Chrome/Edge nicht gefunden (Umgebungsvariable CHROME setzen).'); process.exit(2); }
const ROOT = opt.root ? path.resolve(PROJEKT, opt.root) : PROJEKT;
if (!fs.existsSync(ROOT)) { console.error('Wurzelordner fehlt: ' + ROOT); process.exit(2); }
const widths = String(opt.w).split(',').map(Number).filter(Boolean);
const heights = String(opt.h || '').split(',').map(Number);
const sizes = widths.map((w, i) => [w, heights[i] || heights[0] || 0]);   // [breite, höhe oder 0 = Standard]
const multiH = heights.filter(Boolean).length > 1;   // nur dann steht die Höhe im Dateinamen/Schlüssel (rückwärtskompatibel)
const keyOf = (w, h) => (multiH && h ? `${w}x${h}` : `${w}`);
const OUT = path.resolve(opt.out, path.basename(page, '.html'));
fs.mkdirSync(OUT, { recursive: true });

// ---------------------------------------------------------------- Statischer Server
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.svg': 'image/svg+xml', '.webp': 'image/webp', '.avif': 'image/avif', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
  '.ico': 'image/x-icon', '.txt': 'text/plain; charset=utf-8', '.md': 'text/markdown; charset=utf-8', '.xml': 'application/xml',
  '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.woff2': 'font/woff2', '.woff': 'font/woff' };
const notFound = [];
function serve() {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      let u = decodeURIComponent(new URL(req.url, 'http://x').pathname);
      if (u.endsWith('/')) u += 'index.html';
      const f = path.join(ROOT, u);
      if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { notFound.push(u); rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'content-type': TYPES[path.extname(f).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-store' });
      fs.createReadStream(f).pipe(rsp);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

// ---------------------------------------------------------------- CDP
class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map(); this.handlers = new Set();
    ws.onmessage = e => {
      const m = JSON.parse(typeof e.data === 'string' ? e.data : Buffer.from(e.data).toString());
      if (m.id && this.pending.has(m.id)) {
        const { res, rej, method } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(method + ': ' + m.error.message)) : res(m.result);
      } else if (m.method) for (const h of this.handlers) h(m);
    };
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    return new Promise((res, rej) => this.pending.set(id, { res, rej, method }));
  }
  on(fn) { this.handlers.add(fn); return () => this.handlers.delete(fn); }
  once(pred, timeout = 30000) {
    return new Promise((res, rej) => {
      const t = setTimeout(() => { off(); rej(new Error('Zeitüberschreitung beim Warten auf Ereignis')); }, timeout);
      const off = this.on(m => { if (pred(m)) { clearTimeout(t); off(); res(m); } });
    });
  }
}

async function launch() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pruefen-chrome-'));
  const proc = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${dir}`, '--no-first-run',
    '--no-default-browser-check', '--hide-scrollbars', '--force-color-profile=srgb', '--mute-audio', '--disable-extensions',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
    '--disable-features=CalculateNativeWinOcclusion', ...(opt['ohne-gpu'] ? ['--disable-gpu'] : []), 'about:blank'], { stdio: 'ignore' });
  const portFile = path.join(dir, 'DevToolsActivePort');
  let port = '';
  for (let i = 0; i < 200 && !port; i++) {
    await sleep(100);
    try { port = fs.readFileSync(portFile, 'utf8').split('\n')[0].trim(); } catch {}
  }
  if (!port) throw new Error('Chrome hat keinen DevTools-Port geöffnet');
  const { webSocketDebuggerUrl } = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  const ws = new WebSocket(webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  const cdp = new CDP(ws);
  cdp.close = async () => {
    try { await cdp.send('Browser.close'); } catch {}
    try { ws.close(); } catch {}
    await sleep(300); try { proc.kill(); } catch {}
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
  };
  return cdp;
}

// In jeder Seite vor dem ersten Skript: CLS, LCP und lange Frames (LoAF) mitschreiben
const OBSERVERS = `(() => {
  const d = n => { if (!n || n.nodeType !== 1) return '?'; let s = n.tagName.toLowerCase(); if (n.id) s += '#' + n.id;
    if (n.classList && n.classList.length) s += '.' + [...n.classList].slice(0, 3).join('.'); return s; };
  // __cls wie Chrome/Lighthouse (ohne Verschiebungen kurz nach Eingaben), __clsAll ALLE Verschiebungen: In der
  // Handy-Emulation markiert Chrome Verschiebungen kurz nach dem Laden als hadRecentInput, __cls wäre dort fälschlich 0
  window.__cls = 0; window.__clsAll = 0; window.__shifts = []; window.__loaf = []; window.__lcp = null;
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) { __clsAll += e.value; if (!e.hadRecentInput) __cls += e.value;
    __shifts.push({ value: +e.value.toFixed(4), t: Math.round(e.startTime), ...(e.hadRecentInput ? { recent: true } : {}), sources: (e.sources || []).map(s => d(s.node)) }); } })
    .observe({ type: 'layout-shift', buffered: true }); } catch (e) {}
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) __loaf.push({ t: Math.round(e.startTime), dur: Math.round(e.duration),
    blocking: Math.round(e.blockingDuration || 0), scripts: (e.scripts || []).map(s => (s.invoker || '') + ' ' + (s.sourceURL || '').split('/').pop()) }); })
    .observe({ type: 'long-animation-frame', buffered: true }); } catch (e) {}
  try { new PerformanceObserver(l => { const e = l.getEntries().pop(); if (e) __lcp = { t: Math.round(e.startTime), el: d(e.element), size: e.size }; })
    .observe({ type: 'largest-contentful-paint', buffered: true }); } catch (e) {}
})();`;

const NETZ = { slow4g: { latency: 150, downloadThroughput: 1.6e6 / 8, uploadThroughput: 750e3 / 8 },
  fast4g: { latency: 40, downloadThroughput: 9e6 / 8, uploadThroughput: 1.5e6 / 8 } };

async function openPage(cdp, width, { reduced, h } = {}) {
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  const s = (m, p) => cdp.send(m, p, sessionId);
  const touch = width < 1024;
  const height = Number(h) || (width < 768 ? 812 : touch ? 1024 : 900);
  const log = { console: [], exceptions: [], failed: [] };
  cdp.on(m => {
    if (m.sessionId !== sessionId) return;
    if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning', 'assert'].includes(m.params.type))
      log.console.push(m.params.type + ': ' + m.params.args.map(a => a.value ?? a.description ?? '').join(' ').slice(0, 300));
    if (m.method === 'Runtime.exceptionThrown') log.exceptions.push((m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 400));
    if (m.method === 'Log.entryAdded' && ['error', 'warning'].includes(m.params.entry.level)) log.console.push('log-' + m.params.entry.level + ': ' + m.params.entry.text.slice(0, 300) + (m.params.entry.url ? ' @ ' + m.params.entry.url : ''));
    if (m.method === 'Network.loadingFailed' && !m.params.canceled) log.failed.push(m.params.errorText + ' ' + (m.params.type || ''));
    if (m.method === 'Network.responseReceived' && m.params.response.status >= 400) log.failed.push(m.params.response.status + ' ' + m.params.response.url);
  });
  await s('Page.enable'); await s('Runtime.enable'); await s('Network.enable'); await s('Log.enable');
  await s('Network.setCacheDisabled', { cacheDisabled: true });
  if (opt.netz) { if (!NETZ[opt.netz]) throw new Error('Unbekanntes Netzprofil: ' + opt.netz); await s('Network.emulateNetworkConditions', { offline: false, ...NETZ[opt.netz] }); }
  if (opt.cpu) await s('Emulation.setCPUThrottlingRate', { rate: Number(opt.cpu) });
  await s('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: Number(opt.dpr) || 1, mobile: touch });
  if (touch) await s('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await s('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: reduced ? 'reduce' : 'no-preference' }, { name: 'prefers-color-scheme', value: 'light' }] });
  await s('Page.addScriptToEvaluateOnNewDocument', { source: OBSERVERS });
  // userGesture false: sonst zählt Chrome Verschiebungen danach als Folge einer Eingabe (hadRecentInput)
  const evaluate = async (expr, awaitPromise = true, userGesture = false) => {
    const r = await s('Runtime.evaluate', { expression: expr, awaitPromise, returnByValue: true, userGesture });
    if (r.exceptionDetails) throw new Error('evaluate: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  };
  const goto = async url => {
    const loaded = cdp.once(m => m.sessionId === sessionId && m.method === 'Page.loadEventFired', 45000);
    await s('Page.navigate', { url });
    await loaded;
    await evaluate('document.fonts.ready.then(() => true)');
  };
  const close = () => cdp.send('Target.closeTarget', { targetId }).catch(() => {});
  // Tippen (Touch-Breiten) bzw. Klicken (Desktop) auf einen Punkt im Fenster
  const tap = async (x, y) => {
    x = Math.round(x); y = Math.round(y);
    if (touch) {
      await s('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
      await sleep(40);
      await s('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    } else {
      await s('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
      await s('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
      await s('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
    }
    await sleep(60);
  };
  // Auf die Mitte des (ersten sichtbaren) Elements tippen. Gibt false zurück, wenn es nicht zu sehen ist.
  const tapOn = async sel => {
    const r = await evaluate(`(() => { const el = [...document.querySelectorAll(${JSON.stringify(sel)})].find(e => e.getClientRects().length);
      if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
    if (!r) return false;
    await tap(r.x, r.y); return true;
  };
  const KEYS = { Tab: 9, Enter: 13, Escape: 27, ' ': 32 };
  const key = async (k, shift = false) => {
    const p = { key: k, code: k === ' ' ? 'Space' : k, windowsVirtualKeyCode: KEYS[k], nativeVirtualKeyCode: KEYS[k], modifiers: shift ? 8 : 0 };
    await s('Input.dispatchKeyEvent', { type: 'rawKeyDown', ...p });
    if (k === 'Enter' || k === ' ') await s('Input.dispatchKeyEvent', { type: 'char', ...p, text: k === 'Enter' ? '\r' : ' ' });
    await s('Input.dispatchKeyEvent', { type: 'keyUp', ...p });
    await sleep(80);
  };
  const shot = async (file, quality = 82) => {
    const { data } = await s('Page.captureScreenshot', { format: 'jpeg', quality });
    fs.writeFileSync(file, Buffer.from(data, 'base64')); return file;
  };
  const resize = (w, hh, mobile) => s('Emulation.setDeviceMetricsOverride', { width: w, height: hh, deviceScaleFactor: Number(opt.dpr) || 1, mobile });
  return { s, evaluate, goto, close, log, width, height, touch, sessionId, tap, tapOn, key, shot, resize };
}

// Einmal langsam durchscrollen, damit alle Einblend-Animationen ausgelöst werden
const REVEAL_ALL = `(async () => {
  const H = innerHeight;
  for (let y = 0; y < document.documentElement.scrollHeight; y += Math.round(H * .45)) {
    scrollTo({ top: y, behavior: 'instant' }); await new Promise(r => setTimeout(r, 90));
  }
  scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' });
  await new Promise(r => setTimeout(r, 1900));
  scrollTo({ top: 0, behavior: 'instant' }); await new Promise(r => setTimeout(r, 700));
  return document.documentElement.scrollHeight;
})()`;

// ---------------------------------------------------------------- Audit (läuft in der Seite)
const AUDIT = `(async () => {
  const W = innerWidth, touch = matchMedia('(pointer: coarse)').matches;
  const desc = el => { if (!el || el.nodeType !== 1) return String(el); let s = el.tagName.toLowerCase(); if (el.id) s += '#' + el.id;
    if (el.classList.length) s += '.' + [...el.classList].slice(0, 3).join('.');
    const p = el.parentElement && el.parentElement.closest('section[id], [id], header, footer, .mcta');
    if (p) s = (p.id ? '#' + p.id : p.tagName.toLowerCase() + (p.classList[0] ? '.' + p.classList[0] : '')) + ' > ' + s; return s; };
  const shown = el => { for (let a = el; a && a.nodeType === 1; a = a.parentElement) { const c = getComputedStyle(a);
      if (c.display === 'none' || c.visibility === 'hidden' || +c.opacity === 0) return false; }
    const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const txt = el => [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').replace(/\\s+/g, ' ').trim();
  const out = { width: W, touch, scrollWidth: document.documentElement.scrollWidth, pageHeight: document.documentElement.scrollHeight };
  const all = [...document.body.querySelectorAll('*')];

  // 1) Horizontaler Überlauf (nicht durch einen Vorfahren mit overflow hidden/clip abgeschnitten)
  out.overflow = [];
  for (const el of all) {
    if (el.closest('.skip') || !shown(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right <= W + 1 && r.left >= -1) continue;
    let clipped = false;
    for (let a = el.parentElement; a && a !== document.documentElement; a = a.parentElement) {
      const c = getComputedStyle(a); if (/hidden|clip/.test(c.overflowX)) { const ar = a.getBoundingClientRect(); if (ar.right <= W + 1 && ar.left >= -1) { clipped = true; break; } }
    }
    if (!clipped) out.overflow.push({ el: desc(el), left: Math.round(r.left), right: Math.round(r.right) });
  }
  out.overflow = out.overflow.slice(0, 25);

  // 2) Ragt aus dem Elternelement heraus (Text/Buttons zu breit), ohne absichtlich randlose Bilder
  out.sticksOut = [];
  for (const el of document.body.querySelectorAll('a, button, h1, h2, h3, p, dt, dd, li, span, b, small, strong, summary, .btn, figcaption')) {
    if (!shown(el) || el.closest('.skip, .mcta')) continue;
    const p = el.parentElement; if (!p) continue; const pc = getComputedStyle(p); if (pc.display === 'inline') continue;
    const r = el.getBoundingClientRect(), pr = p.getBoundingClientRect();
    if (r.right > pr.right + 2 && getComputedStyle(el).position !== 'absolute') out.sticksOut.push({ el: desc(el), by: Math.round(r.right - pr.right), text: (el.textContent || '').trim().slice(0, 50) });
  }
  out.sticksOut = out.sticksOut.slice(0, 25);

  // 3) Text-Kontrast (WCAG AA): Vordergrund gegen den effektiven Hintergrund
  const parse = c => { const m = /rgba?\\(([^)]+)\\)/.exec(c); if (!m) return null; const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lin = v => { v /= 255; return v <= .04045 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); };
  const lum = c => .2126 * lin(c.r) + .7152 * lin(c.g) + .0722 * lin(c.b);
  const blend = (f, b) => ({ r: f.r * f.a + b.r * (1 - f.a), g: f.g * f.a + b.g * (1 - f.a), b: f.b * f.a + b.b * (1 - f.a), a: 1 });
  const hex = c => '#' + [c.r, c.g, c.b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  const bgOf = el => { const layers = []; let note = '';
    for (let a = el; a && a.nodeType === 1; a = a.parentElement) { const c = getComputedStyle(a);
      if (c.backgroundImage !== 'none') note = /gradient/.test(c.backgroundImage) ? 'gradient' : 'image';
      const col = parse(c.backgroundColor); if (col && col.a > 0) { layers.push(col); if (col.a >= 1) break; } }
    let bg = { r: 255, g: 255, b: 255, a: 1 }; for (let i = layers.length - 1; i >= 0; i--) bg = blend(layers[i], bg); return { bg, note }; };
  const seen = new Map();
  for (const el of all) {
    const t = txt(el); if (!t || !shown(el)) continue;
    const c = getComputedStyle(el); let fg = parse(c.color); if (!fg) continue;
    let op = 1; for (let a = el; a && a.nodeType === 1; a = a.parentElement) op *= +getComputedStyle(a).opacity;
    const { bg, note } = bgOf(el); fg = blend({ ...fg, a: fg.a * op }, bg);
    const L1 = lum(fg), L2 = lum(bg), ratio = (Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05);
    const size = parseFloat(c.fontSize), bold = +c.fontWeight >= 700, large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5;
    if (ratio + 0.005 < need) { const k = hex(fg) + '/' + hex(bg) + '/' + size;
      if (!seen.has(k)) seen.set(k, { el: desc(el), text: t.slice(0, 40), fg: hex(fg), bg: hex(bg), ratio: +ratio.toFixed(2), need, size, note, count: 0 });
      seen.get(k).count++; }
  }
  out.contrast = [...seen.values()].sort((a, b) => a.ratio - b.ratio).slice(0, 40);

  // 4) Tippflächen (nur Touch) und Mini-Schrift
  out.smallTargets = [];
  if (touch) for (const el of document.querySelectorAll('a, button, summary, [role=button], input, select')) {
    if (!shown(el) || el.closest('.skip')) continue; const r = el.getBoundingClientRect();
    const inline = getComputedStyle(el).display === 'inline' && !!el.closest('p, li, dd');
    if ((r.width < 44 || r.height < 44) && !inline) out.smallTargets.push({ el: desc(el), w: Math.round(r.width), h: Math.round(r.height), text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 40) });
  }
  const tiny = new Map();
  for (const el of all) { const t = txt(el); if (!t || !shown(el)) continue; const f = parseFloat(getComputedStyle(el).fontSize); if (f < 12.5) tiny.set(desc(el) + ' ' + f + 'px', t.slice(0, 30)); }
  out.tinyText = [...tiny].slice(0, 25).map(([k, v]) => k + ' «' + v + '»');

  // 5) Bilder: tatsächliche vs. benötigte Auflösung, Ladeattribute. Mit srcset ist naturalWidth dichte-korrigiert
  //    (Datei 800 px bei sizes 400px = 400); deshalb die echte Dateibreite getrennt laden. dichte = Dateipixel je CSS-Pixel
  const imgs = [...document.images].filter(shown);
  const datei = await Promise.all(imgs.map(i => new Promise(res => { const t = new Image(); t.onload = () => res([t.naturalWidth, t.naturalHeight]); t.onerror = () => res([0, 0]); t.src = i.currentSrc || i.src; })));
  out.images = imgs.map((i, k) => { const r = i.getBoundingClientRect(), [fw, fh] = datei[k];
    return { src: (i.currentSrc || i.src).split('/').slice(-2).join('/'), shown: Math.round(r.width) + 'x' + Math.round(r.height), natural: i.naturalWidth + 'x' + i.naturalHeight,
      datei: fw + 'x' + fh, dichte: r.width ? +(fw / r.width).toFixed(2) : 0, srcsetVarianten: (i.closest('picture') && i.closest('picture').querySelector('source[srcset]') || i).getAttribute('srcset') ? ((i.closest('picture') && i.closest('picture').querySelector('source[srcset]') || i).getAttribute('srcset').split(',').length) : 0,
      sharpAt1x: fw >= r.width, sharpAt2x: fw >= r.width * 2, loading: i.loading, decoding: i.decoding, fetchpriority: i.getAttribute('fetchpriority') || '', complete: i.complete, alt: i.alt ? 'ja' : 'FEHLT' }; });

  // 6) Überschriften, Barrierefreiheit, Semantik
  out.headings = [...document.querySelectorAll('h1, h2, h3')].filter(shown).map(h => h.tagName + ' ' + h.textContent.replace(/\\s+/g, ' ').trim().slice(0, 90));
  out.h1count = document.querySelectorAll('h1').length;
  out.ids = (() => { const m = {}; for (const e of document.querySelectorAll('[id]')) m[e.id] = (m[e.id] || 0) + 1; return Object.keys(m).filter(k => m[k] > 1); })();
  out.brokenAnchors = [...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href')).filter(h => h.length > 1 && !document.getElementById(decodeURIComponent(h.slice(1))));
  out.linksNoName = [...document.querySelectorAll('a, button')].filter(a => shown(a) && !(a.textContent.trim() || a.getAttribute('aria-label'))).map(desc);
  out.blankNoopener = [...document.querySelectorAll('a[target=_blank]')].filter(a => !/noopener|noreferrer/.test(a.rel)).map(desc);
  out.fonts = [...document.fonts].filter(f => f.status !== 'unloaded').map(f => f.family.replace(/"/g, '') + ' ' + f.weight + (f.style !== 'normal' ? ' ' + f.style : '') + ' ' + f.status);
  out.cls = +(window.__cls || 0).toFixed(4); out.clsAll = +(window.__clsAll || 0).toFixed(4); out.shifts = (window.__shifts || []).slice(0, 15); out.lcp = window.__lcp;
  return out;
})()`;

// ---------------------------------------------------------------- Befehle
const tagOf = (w, h) => keyOf(w, h) + (opt.reduced ? '-reduced' : '');

async function shots(cdp, base) {
  for (const [w, h] of sizes) {
    const p = await openPage(cdp, w, { reduced: opt.reduced, h });
    await p.goto(base + page);
    const tag = tagOf(w, h);
    if (opt.klick) {   // Zustand nach einem Klick: nur der erste Bildschirm, kein Durchscrollen
      if (opt.vorher) { await p.evaluate(`(async () => { ${opt.vorher} ; })()`); await sleep(500); }
      const ok = await p.tapOn(opt.klick);
      if (!ok) console.log(`  ${w}px: ${opt.klick} nicht sichtbar, kein Klick`);
      await sleep(600);
      if (opt.nachher) { await p.evaluate(`(async () => { ${opt.nachher} ; })()`); await sleep(400); }
      const f = await p.shot(path.join(OUT, `${tag}-klick.jpg`));
      console.log(`${w}px: nach Klick auf ${opt.klick} -> ${f}`);
      if (p.log.exceptions.length || p.log.failed.length) console.log('  Fehler:', JSON.stringify({ exceptions: p.log.exceptions, failed: p.log.failed }));
      await p.close();
      continue;
    }
    const hPage = await p.evaluate(REVEAL_ALL);
    const maxTiles = Number(opt['max-tiles']) || Infinity;
    if (!opt['no-tiles']) {
      let n = 0;
      for (let y = 0; y < hPage && n < maxTiles; y += p.height) {
        // Nach dem Sprung zwei echte Frames abwarten, sonst nimmt Headless-Chrome gelegentlich veraltete Kacheln auf
        await p.evaluate(`scrollTo({ top: ${y}, behavior: 'instant' }); new Promise(r => setTimeout(r, 450)).then(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))))`);
        const { data } = await p.s('Page.captureScreenshot', { format: 'jpeg', quality: 82 });
        const f = path.join(OUT, `${tag}-t${String(++n).padStart(2, '0')}.jpg`); fs.writeFileSync(f, Buffer.from(data, 'base64'));
      }
      console.log(`${w}px: ${n} Bildschirme -> ${path.join(OUT, tag + '-tNN.jpg')}`);
    }
    await p.evaluate(`scrollTo({ top: 0, behavior: 'instant' }); new Promise(r => setTimeout(r, 400))`);
    const m = await p.s('Page.getLayoutMetrics');
    const H = Math.min(Math.ceil(m.cssContentSize.height), 16000);
    const { data } = await p.s('Page.captureScreenshot', { format: 'jpeg', quality: 78, captureBeyondViewport: true, clip: { x: 0, y: 0, width: w, height: H, scale: 1 } });
    const f = path.join(OUT, `${tag}-ganz.jpg`); fs.writeFileSync(f, Buffer.from(data, 'base64'));
    console.log(`${w}px: ganze Seite (${w}x${H}) -> ${f}`);
    if (p.log.exceptions.length || p.log.failed.length) console.log('  Fehler:', JSON.stringify({ exceptions: p.log.exceptions, failed: p.log.failed }));
    await p.close();
  }
}

async function audit(cdp, base) {
  const result = {};
  for (const [w, h] of sizes) {
    const p = await openPage(cdp, w, { reduced: opt.reduced, h });
    await p.goto(base + page);
    await p.evaluate(REVEAL_ALL);
    const a = await p.evaluate(AUDIT);
    a.console = p.log.console; a.exceptions = p.log.exceptions; a.failedRequests = p.log.failed;
    result[keyOf(w, h)] = a;
    await p.close();
  }
  result.notFoundOnServer = [...new Set(notFound)];
  const f = path.join(OUT, `audit${opt.reduced ? '-reduced' : ''}.json`);
  fs.writeFileSync(f, JSON.stringify(result, null, 1));
  console.log(JSON.stringify(result, null, 1));
  console.log('-> ' + f);
}

const CATS = ['devtools.timeline', 'disabled-by-default-devtools.timeline', 'disabled-by-default-devtools.timeline.frame',
  'blink.animations', 'disabled-by-default-devtools.timeline.paint', 'benchmark', 'rail', 'loading'];

// Chromium CompositorAnimations::FailureReason (Bitmaske)
const FAIL = ['acceleratedAnimationsDisabled', 'effectSuppressedByDevtools', 'invalidAnimationOrEffect', 'unsupportedTimingParameters',
  'nonReplaceCompositeMode', 'targetHasInvalidCompositingState', 'targetHasIncompatibleAnimations', 'targetHasCSSOffset', 'obsolete8',
  'affectsNonCSSProperties', 'transformCannotBeAcceleratedOnTarget', 'transformDependsOnBoxSize', 'filterMayMovePixels', 'unsupportedCSSProperty',
  'obsolete14', 'mixedKeyframeValueTypes', 'timelineSourceInvalid', 'compositorPropertiesHaveNoEffect', 'affectsImportantProperty', 'svgIndependentTransform'];
const NO_EFFECT = 1 << 17;
const reasons = m => FAIL.filter((_, i) => m & (1 << i));

function summarize(events) {
  const mains = new Set(), threadName = {};
  for (const e of events) if (e.ph === 'M' && e.name === 'thread_name') { threadName[e.pid + ':' + e.tid] = e.args.name; if (e.args.name === 'CrRendererMain') mains.add(e.pid + ':' + e.tid); }
  const byName = {}, anim = {}, frames = {}, all = {};
  let longTasks = 0;
  for (const e of events) {
    const key = e.pid + ':' + e.tid;
    if (e.ph === 'X' && e.dur) {
      all[e.name] = (all[e.name] || 0) + e.dur;
      if (mains.has(key)) {
        const b = byName[e.name] || (byName[e.name] = { ms: 0, n: 0 }); b.ms += e.dur / 1000; b.n++;
        if (e.name === 'RunTask' && e.dur > 50000) longTasks++;
      }
    }
    if (e.name === 'Animation' && e.args?.data) {
      const d = e.args.data, id = e.id2?.local || e.id || d.id;
      const a = anim[id] || (anim[id] = { name: '', node: '', compositeFailed: 0, unsupported: [] });
      if (d.displayName || d.name) a.name = d.displayName || d.name; if (d.nodeName) a.node = d.nodeName;
      if (d.compositeFailed) a.compositeFailed |= d.compositeFailed;
      if (d.unsupportedProperties) a.unsupported = [...new Set([...a.unsupported, ...d.unsupportedProperties])];
    }
    if (e.name === 'PipelineReporter' && e.args?.chrome_frame_reporter?.state) { const st = e.args.chrome_frame_reporter.state; frames[st] = (frames[st] || 0) + 1; }
    if (e.name === 'DroppedFrame') frames.DroppedFrame = (frames.DroppedFrame || 0) + 1;
  }
  const top = Object.entries(byName).sort((a, b) => b[1].ms - a[1].ms).slice(0, 14).map(([k, v]) => `${k}: ${v.ms.toFixed(1)} ms (${v.n}x)`);
  const ms = n => +((all[n] || 0) / 1000).toFixed(1);
  const anims = Object.values(anim);
  return {
    mainThreadTop: top, longTasksOver50ms: longTasks,
    paintMs: +(byName.Paint?.ms || 0).toFixed(1), paintCount: byName.Paint?.n || 0,
    layoutMs: +(byName.Layout?.ms || 0).toFixed(1), layoutCount: byName.Layout?.n || 0,
    styleMs: +((byName.UpdateLayoutTree?.ms || 0) + (byName.RecalculateStyles?.ms || 0)).toFixed(1),
    rasterMs: ms('RasterTask'), imageDecodeMs: +(ms('ImageDecodeTask') + ms('Decode Image') + ms('Decode LazyPixelRef')).toFixed(1),
    gpuMs: ms('GPUTask'),
    animations: anims.length, nonComposited: Object.values(anims.filter(a => a.compositeFailed && !(a.compositeFailed === NO_EFFECT)).reduce((m, a) => { const k = a.name + '|' + a.node.replace(/ rv( in)?/, '') + '|' + a.compositeFailed; (m[k] ||= { name: a.name, node: a.node, reasons: reasons(a.compositeFailed), unsupported: a.unsupported, count: 0 }).count++; return m; }, {})).slice(0, 30),
    compositedOk: anims.filter(a => !a.compositeFailed).length, noVisibleEffect: anims.filter(a => a.compositeFailed === NO_EFFECT).length,
    frames,
  };
}

async function jank(cdp, base) {
  const result = {};
  for (const [w, h] of sizes) {
    const p = await openPage(cdp, w, { reduced: opt.reduced, h });
    const events = []; const off = cdp.on(m => { if (m.method === 'Tracing.dataCollected') events.push(...m.params.value); });
    const complete = cdp.once(m => m.method === 'Tracing.tracingComplete', 120000);
    await cdp.send('Tracing.start', { transferMode: 'ReportEvents', traceConfig: { recordMode: 'recordAsMuchAsPossible', includedCategories: CATS } });
    const t0 = Date.now();
    await p.goto(base + page);
    await sleep(2600);  // Lade-Animationen im Hero
    const loadEnd = Date.now() - t0;
    const scrollH = await p.evaluate(`document.documentElement.scrollHeight - innerHeight`);
    await p.evaluate(`window.__frames = []; window.__stop = false; (() => { let last = performance.now(); const f = t => { __frames.push(t - last); last = t; if (!__stop) requestAnimationFrame(f); }; requestAnimationFrame(f); })(); true`);
    let method = 'synthesizeScrollGesture';
    try {
      // Eigener Timeout: Bei gesperrter Windows-Sitzung kehrt die Geste auf Touch-Breiten teils nie zurück
      const geste = p.s('Input.synthesizeScrollGesture', { x: Math.round(w / 2), y: Math.round(p.height / 2), yDistance: -scrollH, speed: 1400,
        gestureSourceType: p.touch ? 'touch' : 'mouse', preventFling: true });
      geste.catch(() => {});
      await Promise.race([geste, sleep(Math.max(30000, scrollH / 1400 * 1000 * 3)).then(() => { throw new Error('Geste ohne Antwort'); })]);
    } catch (e) { method = 'rAF (' + e.message + ')'; }
    let y = await p.evaluate('scrollY');
    if (y < scrollH * .8) {  // Fallback: in der Seite scrollen
      method += ' + rAF-Fallback';
      await p.evaluate(`new Promise(r => { let y = scrollY; const max = document.documentElement.scrollHeight - innerHeight; const st = () => { y += 22; scrollTo({ top: y, behavior: 'instant' }); y < max ? requestAnimationFrame(st) : r(); }; requestAnimationFrame(st); })`);
      y = await p.evaluate('scrollY');
    }
    await sleep(1600);
    const inPage = await p.evaluate(`(() => { __stop = true; const f = __frames.slice(2).sort((a, b) => a - b); const q = x => f[Math.min(f.length - 1, Math.floor(f.length * x))] || 0;
      return { frames: f.length, p50: +q(.5).toFixed(1), p95: +q(.95).toFixed(1), p99: +q(.99).toFixed(1), max: +(f[f.length - 1] || 0).toFixed(1),
        over25ms: f.filter(x => x > 25).length, over50ms: f.filter(x => x > 50).length, cls: +(__cls || 0).toFixed(4), clsAll: +(__clsAll || 0).toFixed(4), shifts: __shifts.slice(0, 10), lcp: __lcp,
        loafOver50: __loaf.filter(l => l.dur > 50).slice(0, 12) }; })()`);
    await cdp.send('Tracing.end');
    await complete; off();
    result[keyOf(w, h)] = { scroll: { method, distance: scrollH, reached: Math.round(y), loadPhaseMs: loadEnd }, rafDuringScroll: inPage, trace: summarize(events),
      exceptions: p.log.exceptions, failedRequests: p.log.failed };
    await p.close();
  }
  const f = path.join(OUT, `jank${opt.reduced ? '-reduced' : ''}.json`);
  fs.writeFileSync(f, JSON.stringify(result, null, 1));
  console.log(JSON.stringify(result, null, 1));
  console.log('-> ' + f);
}

// Zustand von Menü, Fokus, Leiste und Abdunklung (läuft in der Seite)
const MENU_STATE = `(() => {
  const d = el => { if (!el || el.nodeType !== 1) return String(el && el.nodeName); let s = el.tagName.toLowerCase(); if (el.id) s += '#' + el.id;
    if (el.classList.length) s += '.' + [...el.classList].slice(0, 3).join('.'); const t = (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 30);
    return s + (t ? ' «' + t + '»' : ''); };
  const html = document.documentElement, nav = document.getElementById('nav-main'), mb = document.querySelector('.menu-btn');
  const bar = document.querySelector('.mcta'), hdr = document.querySelector('header.site');
  const links = nav ? [...nav.querySelectorAll('a')].filter(a => a.getClientRects().length) : [];
  const last = links[links.length - 1], nr = nav && nav.getBoundingClientRect();
  const lr = last && last.getBoundingClientRect();
  const hit = lr ? document.elementFromPoint(lr.left + Math.min(lr.width / 2, 40), lr.top + lr.height / 2) : null;
  const scrim = getComputedStyle(document.body, '::after');
  const bs = bar && getComputedStyle(bar);
  return {
    open: html.classList.contains('nav-open'), expanded: mb && mb.getAttribute('aria-expanded'), label: mb && mb.getAttribute('aria-label'),
    active: d(document.activeElement), scrollY: Math.round(scrollY), innerHeight,
    header: hdr ? { bottom: Math.round(hdr.getBoundingClientRect().bottom), z: getComputedStyle(hdr).zIndex, scrolled: hdr.classList.contains('scrolled') } : null,
    nav: nr ? { top: Math.round(nr.top), bottom: Math.round(nr.bottom), clientH: nav.clientHeight, scrollH: nav.scrollHeight, scrollTop: Math.round(nav.scrollTop),
      navMax: nav.style.getPropertyValue('--nav-max'), overflowY: getComputedStyle(nav).overflowY, links: links.length } : null,
    lastLink: lr ? { text: last.textContent.trim().slice(0, 30), top: Math.round(lr.top), bottom: Math.round(lr.bottom),
      insideViewport: lr.top >= 0 && lr.bottom <= innerHeight, insideNav: nr ? lr.top >= nr.top - 1 && lr.bottom <= nr.bottom + 1 : false,
      notCovered: !!hit && (hit === last || last.contains(hit)) } : null,
    bar: bs ? { display: bs.display, visibility: bs.visibility, opacity: +bs.opacity, mctaOn: html.classList.contains('mcta-on') } : null,
    scrim: { content: scrim.content, position: scrim.position, z: scrim.zIndex, bg: scrim.backgroundColor },
    htmlOverflow: getComputedStyle(html).overflowY
  };
})()`;

async function menue(cdp, base) {
  const result = {};
  for (const [w, h] of sizes) {
    const p = await openPage(cdp, w, { reduced: opt.reduced, h });
    await p.goto(base + page);
    const tag = tagOf(w, h), r = { size: `${w}x${p.height}`, touch: p.touch, schritte: {} };
    const st = () => p.evaluate(MENU_STATE);
    const hasMenu = await p.evaluate(`(() => { const b = document.querySelector('.menu-btn'); return !!b && getComputedStyle(b).display !== 'none'; })()`);
    if (!hasMenu) { result[tag] = { ...r, hinweis: 'kein Menü-Button sichtbar bei dieser Breite' }; await p.close(); continue; }
    // 1) Seite ein Stück scrollen, damit die Handy-Leiste sichtbar ist (falls es eine gibt)
    await p.evaluate(opt.vorher ? `(async () => { ${opt.vorher} ; })()` : `scrollTo({ top: Math.round(document.documentElement.scrollHeight * .35), behavior: 'instant' })`);
    await sleep(900);
    r.schritte.vorher = await st();
    // 2) Antippen: offen, Fokus auf dem ersten Link, Leiste weg, Abdunklung, Seite gesperrt
    await p.tapOn('.menu-btn'); await sleep(450);
    const offen = r.schritte.offen = await st();
    await p.shot(path.join(OUT, `menue-${tag}-offen.jpg`));
    // Seite scrollen versuchen (Mausrad bzw. Wischen auf der Abdunklung)
    const y0 = offen.scrollY;
    await p.s('Input.dispatchMouseEvent', { type: 'mouseWheel', x: Math.round(w / 2), y: p.height - 20, deltaX: 0, deltaY: 400 }); await sleep(300);
    const yWheel = await p.evaluate('Math.round(scrollY)');
    // 3) Im Menü ganz nach unten scrollen: letzter Punkt erreichbar und nicht verdeckt
    await p.evaluate(`(() => { const n = document.getElementById('nav-main'); if (n) n.scrollTop = n.scrollHeight; })()`); await sleep(250);
    const unten = r.schritte.untenImMenue = await st();
    await p.shot(path.join(OUT, `menue-${tag}-unten.jpg`));
    // 4) Tab-Reihenfolge ab dem Fokus nach dem Öffnen (bis der Fokus den Header verlässt)
    await p.evaluate(`(() => { const n = document.getElementById('nav-main'); if (n) n.scrollTop = 0; const f = [...n.querySelectorAll('a')].find(a => a.getClientRects().length); f && f.focus(); })()`);
    const tabs = [];
    for (let i = 0; i < 14; i++) {
      await p.key('Tab');
      const s2 = await st(); tabs.push(s2.active + (s2.open ? '' : ' [zu]'));
      if (!s2.open) break;
    }
    r.schritte.tab = tabs;
    // 5) Tastatur: Button fokussieren, Enter öffnet (Fokus erster Link), Escape schließt (Fokus zurück auf den Button)
    await p.evaluate(`document.querySelector('.menu-btn').focus()`); await p.key('Enter'); await sleep(300);
    const nachEnter = await st();
    await p.key('Escape'); await sleep(250);
    const nachEsc = await st();
    // Shift+Tab vom ersten Link (muss im Header bleiben)
    await p.key('Enter'); await sleep(300); await p.key('Tab', true); await sleep(150);
    const shiftTab = await st();
    await p.key('Escape'); await sleep(200);
    // 6) Klick daneben schließt
    await p.tapOn('.menu-btn'); await sleep(400);
    await p.tap(Math.round(w / 2), p.height - 30); await sleep(350);
    const nachAussen = await st();
    // 7) Größenänderung auf Desktop schließt
    await p.tapOn('.menu-btn'); await sleep(400);
    await p.resize(1440, 900, false); await sleep(500);
    const nachResize = await st();
    await p.resize(w, p.height, p.touch); await sleep(300);
    const first = offen.active;
    r.ergebnis = {
      oeffnetPerTipp: offen.open && offen.expanded === 'true',
      fokusErsterLink: /^a/.test(first) && !/menu-btn/.test(first),
      ariaLabelFest: offen.label === 'Menü',
      leisteWeg: !offen.bar || offen.bar.visibility === 'hidden' || offen.bar.display === 'none',
      leisteVorherSichtbar: r.schritte.vorher.bar ? r.schritte.vorher.bar.visibility === 'visible' && r.schritte.vorher.bar.display !== 'none' : null,
      abdunklung: offen.scrim.position === 'fixed' && offen.scrim.content !== 'none',
      seiteGesperrt: yWheel === y0,
      menueScrollt: offen.nav.scrollH > offen.nav.clientH ? unten.nav.scrollTop > 0 : 'passt ohne Scrollen',
      navUnterkanteImFenster: offen.nav.bottom <= offen.innerHeight + 1,
      letzterPunktErreichbar: !!(unten.lastLink && unten.lastLink.insideViewport && unten.lastLink.insideNav && unten.lastLink.notCovered),
      tabBleibtImMenue: tabs.length > 1 && tabs.slice(0, -1).every(t => !/\[zu\]/.test(t)),
      schliesstWennFokusRaus: /\[zu\]/.test(tabs[tabs.length - 1] || ''),
      enterFokusErsterLink: nachEnter.open && /^a/.test(nachEnter.active),
      escapeSchliesst: !nachEsc.open && nachEsc.expanded === 'false',
      escapeFokusZurueck: /menu-btn/.test(nachEsc.active),
      shiftTabImHeader: shiftTab.open ? 'offen, Fokus: ' + shiftTab.active : 'zu, Fokus: ' + shiftTab.active,
      klickDanebenSchliesst: !nachAussen.open,
      resizeSchliesst: !nachResize.open && nachResize.expanded === 'false',
    };
    r.schritte = { ...r.schritte, nachEnter, nachEsc, shiftTab, nachAussen, nachResize, wheel: { vorher: y0, nachher: yWheel } };
    r.exceptions = p.log.exceptions; r.failedRequests = p.log.failed; r.console = p.log.console;
    result[tag] = r;
    await p.close();
  }
  const f = path.join(OUT, 'menue.json');
  fs.writeFileSync(f, JSON.stringify(result, null, 1));
  for (const [k, v] of Object.entries(result)) console.log(k, JSON.stringify(v.ergebnis || v.hinweis));
  console.log('-> ' + f + '  (Screenshots menue-<größe>-offen.jpg / -unten.jpg daneben)');
}

// Ladeverhalten mehrfach messen (CLS schwankt je nach Zeitpunkt, zu dem die Webfonts ankommen)
async function cls(cdp, base) {
  const result = {}, runs = Number(opt.runs) || 3;
  for (const [w, h] of sizes) {
    const reihe = [];
    for (let i = 0; i < runs; i++) {
      const p = await openPage(cdp, w, { reduced: opt.reduced, h });
      await p.goto(base + page); await sleep(opt.netz ? 3500 : 1800);
      const r = await p.evaluate(`(() => { const fcp = performance.getEntriesByName('first-contentful-paint')[0];
        return { cls: +(__cls || 0).toFixed(4), clsAll: +(__clsAll || 0).toFixed(4), fcp: fcp ? Math.round(fcp.startTime) : null, lcp: __lcp, shifts: __shifts.filter(s => s.value >= 0.0005).slice(0, 6) }; })()`);
      r.exceptions = p.log.exceptions.length; r.failed = p.log.failed.length;
      reihe.push(r); await p.close();
    }
    result[keyOf(w, h)] = reihe;
    const c = reihe.map(r => r.clsAll), c2 = reihe.map(r => r.cls);
    console.log(`${keyOf(w, h)}: CLS (alle Verschiebungen) ${c.join(' / ')} (max ${Math.max(...c)}; ohne hadRecentInput max ${Math.max(...c2)}) | FCP ${reihe.map(r => r.fcp).join('/')} | LCP ${reihe.map(r => r.lcp && r.lcp.t).join('/')}`
      + (reihe.some(r => r.shifts.length) ? '\n   ' + reihe.filter(r => r.shifts.length).slice(0, 2).map(r => JSON.stringify(r.shifts.slice(0, 3))).join('\n   ') : ''));
  }
  const f = path.join(OUT, `cls${opt.netz ? '-' + opt.netz : ''}${opt.cpu ? '-cpu' + opt.cpu : ''}.json`);
  fs.writeFileSync(f, JSON.stringify(result, null, 1));
  console.log('-> ' + f);
}

// Gemeinsame Mechanik aus SCRIPTS: Handy-Leiste, Header .scrolled, Anruf-Links, Nummer kopieren
const BAR_STATE = `(() => {
  const bar = document.querySelector('.mcta'), html = document.documentElement;
  const cs = bar && getComputedStyle(bar);
  if (!bar || cs.display === 'none') return { bar: false };
  const zoneTop = innerHeight - (bar.offsetHeight + (parseFloat(cs.bottom) || 0));
  const hdr = document.querySelector('header.site'), hp = hdr ? getComputedStyle(hdr).position : '';
  const oben = hp === 'sticky' || hp === 'fixed' ? hdr.offsetHeight : 0;   // hinter fester Kopfzeile = nicht zu sehen
  const watched = [...document.querySelectorAll('.hero .cta-row, [data-mcta-hide], footer.site')];
  const vis = watched.filter(e => { const r = e.getBoundingClientRect(); return r.height > 0 && r.bottom > oben && r.top < zoneTop; })
    .map(e => (e.closest('section[id], footer') || e).id || e.tagName.toLowerCase());
  const ctas = [...document.querySelectorAll('main a[href^="tel:"], main a[href*="doctolib"], main [data-tel], main .js-call')]
    .filter(a => { const r = a.getBoundingClientRect(); return a.getClientRects().length && r.bottom > oben && r.top < zoneTop; });
  return { bar: true, y: Math.round(scrollY), shown: html.classList.contains('mcta-on') && cs.visibility === 'visible', watchedVisible: vis, ctaVisible: ctas.length };
})()`;

async function mechanik(cdp, base) {
  const result = {};
  for (const [w, h] of sizes) {
    const p = await openPage(cdp, w, { reduced: opt.reduced, h });
    await p.s('Emulation.setFocusEmulationEnabled', { enabled: true }).catch(() => {});
    await cdp.send('Browser.grantPermissions', { permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'], origin: base.replace(/\/$/, '') }).catch(() => {});
    await p.goto(base + page); await sleep(400);
    // Zwei Frames abwarten (höchstens 2 s): IntersectionObserver meldet erst mit dem nächsten Frame, bei gedrosselten
    // Frames (gesperrte Sitzung) reicht eine feste Pause nicht und das Ergebnis hinge einen Schritt hinterher
    const frames = () => p.evaluate('Promise.race([new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 30)))), new Promise(r => setTimeout(r, 2000))])');
    const tag = tagOf(w, h), r = { size: `${w}x${p.height}`, touch: p.touch };
    // Header: .scrolled erst nach dem Scrollen, oben wieder weg
    const sc = async y => { await p.evaluate(`scrollTo({ top: ${y}, behavior: 'instant' })`); await sleep(250); await frames();
      return p.evaluate(`document.querySelector('header.site') && document.querySelector('header.site').classList.contains('scrolled')`); };
    r.header = { oben: await sc(0), nach200px: await sc(200), wiederOben: await sc(0) };
    // Anruf-Links: Handy tel: mit Screenreader-Zusatz, sonst Sprung zum Abschnitt
    r.dataTel = await p.evaluate(`[...document.querySelectorAll('[data-tel]')].map(a => ({ href: a.getAttribute('href'), sr: (a.querySelector('.vh') || {}).textContent || '', name: a.textContent.replace(/\\s+/g, ' ').trim() }))`);
    r.phoneErkannt = await p.evaluate(`matchMedia('(pointer: coarse) and (max-width: 640px), (pointer: coarse) and (max-height: 500px)').matches`);
    // Handy-Leiste: an jeder Scroll-Position genau dann sichtbar, wenn kein beobachteter CTA-Bereich im Bild ist
    const st = await p.evaluate(BAR_STATE);
    if (st.bar) {
      const H = await p.evaluate('document.documentElement.scrollHeight - innerHeight'), schritte = [];
      for (let y = 0; y <= H + 1; y += Math.round(p.height * .25)) {
        await p.evaluate(`scrollTo({ top: ${Math.min(y, H)}, behavior: 'instant' })`); await sleep(420); await frames();
        schritte.push(await p.evaluate(BAR_STATE));
      }
      const falsch = schritte.filter(s => s.shown === (s.watchedVisible.length > 0));
      const ohne = schritte.filter(s => !s.shown && s.ctaVisible === 0);
      r.leiste = { positionen: schritte.length, falsch: falsch.map(s => ({ y: s.y, shown: s.shown, sichtbar: s.watchedVisible })),
        ohneJedenButton: ohne.map(s => s.y), ohneJedenButtonBereiche: [...new Set(ohne.flatMap(s => s.watchedVisible))], sichtbarAnteil: +(schritte.filter(s => s.shown).length / schritte.length).toFixed(2),
        verlauf: schritte.map(s => (s.shown ? 'L' : '-')).join('') };
    } else r.leiste = 'keine Leiste bei dieser Breite';
    // Aktiver Menüpunkt: jeden verlinkten Abschnitt in die Lesezeile (40 % der Fensterhöhe) scrollen, aria-current lesen.
    // amEnde: Seite lässt sich nicht weit genug scrollen (letzter Abschnitt), dann ist der vorige Punkt richtig.
    const ziele = await p.evaluate(`[...new Set([...document.querySelectorAll('#nav-main a[href^="#"]')].map(a => a.getAttribute('href').slice(1)))].filter(id => id && document.getElementById(id))`);
    r.menuepunkt = [];
    for (const id of ziele) {
      const amEnde = await p.evaluate(`(() => { const s = document.getElementById(${JSON.stringify(id)});
        const soll = s.getBoundingClientRect().top + scrollY - innerHeight * .4 + 24, max = document.documentElement.scrollHeight - innerHeight;
        scrollTo({ top: soll, behavior: 'instant' }); return soll > max + 1; })()`);
      await sleep(300); await frames();
      const aktiv = await p.evaluate(`[...document.querySelectorAll('#nav-main a[aria-current]')].map(a => a.getAttribute('href')).join(' ')`);
      r.menuepunkt.push({ abschnitt: id, aktiv, ok: aktiv === '#' + id || (amEnde && aktiv !== ''), amEnde });
    }
    r.menuepunktFalsch = r.menuepunkt.filter(x => !x.ok).map(x => x.abschnitt);
    // Nummer kopieren (nur Maus): role=button, Leertaste kopiert, Statusmeldung
    const calls = await p.evaluate(`[...document.querySelectorAll('.js-call')].map(a => ({ role: a.getAttribute('role'), text: a.textContent.trim() }))`);
    r.kopieren = { buttons: calls };
    if (calls.length && calls[0].role === 'button') {
      await p.evaluate(`(() => { const a = document.querySelector('.js-call'); a.scrollIntoView({ block: 'center' }); a.focus(); })()`); await sleep(200);
      await p.key(' '); await sleep(300);
      r.kopieren.nachLeertaste = await p.evaluate(`({ text: document.querySelector('.js-call').textContent.trim(), status: ([...document.querySelectorAll('[role=status]')].map(e => e.textContent).join(' | ')), url: location.href.split('/').pop() })`);
      r.kopieren.zwischenablage = await p.evaluate(`navigator.clipboard.readText().catch(e => 'nicht lesbar: ' + e.message)`);
    }
    r.exceptions = p.log.exceptions; r.failedRequests = p.log.failed; r.console = p.log.console;
    result[tag] = r;
    await p.close();
  }
  const f = path.join(OUT, 'mechanik.json');
  fs.writeFileSync(f, JSON.stringify(result, null, 1));
  console.log(JSON.stringify(result, null, 1));
  console.log('-> ' + f);
}

// ---------------------------------------------------------------- Start
const srv = await serve();
const base = `http://127.0.0.1:${srv.address().port}/`;
const cdp = await launch();
try {
  await ({ shots, audit, jank, menue, mechanik, cls })[cmd](cdp, base);
} catch (e) {
  console.error('FEHLER:', e.stack || e.message); process.exitCode = 1;
} finally {
  await cdp.close(); srv.close();
}
