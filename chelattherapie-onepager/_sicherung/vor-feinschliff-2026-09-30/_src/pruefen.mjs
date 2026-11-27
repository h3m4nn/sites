#!/usr/bin/env node
/*
 * Prüfwerkzeug für die Onepager-Entwürfe: Headless-Chrome über das DevTools-Protokoll, ohne Zusatzpakete (Node >= 22).
 *
 *   node _src/pruefen.mjs shots entwurf-a-salbei.html --w 375,1440     Screenshots: ganze Seite + Bildschirm für Bildschirm
 *   node _src/pruefen.mjs audit entwurf-a-salbei.html --w 375,768,1280 Layout-/Barriere-Check als JSON (Überlauf, Kontrast, Tippflächen …)
 *   node _src/pruefen.mjs jank  entwurf-a-salbei.html --w 375,1440     Ruckel-Messung: Trace beim Laden und beim Scrollen
 *
 * Optionen:  --out <ordner>   Ausgabe (Standard: %TEMP%/chelat-pruefung)
 *            --reduced        prefers-reduced-motion: reduce emulieren
 *            --no-tiles       bei shots nur die ganze Seite
 *            --dpr <n>        Pixeldichte (Standard 1)
 *            --h <px>         Fensterhöhe (Standard: 812 Handy, 1024 Tablet, 900 Desktop)
 * Breiten unter 1024 px werden als Touch-Gerät emuliert (kein Hover, grober Zeiger), ab 1024 als Desktop mit Maus.
 */
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
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
  if (['reduced', 'no-tiles'].includes(k)) opt[k] = true; else opt[k] = rest[++i];
}
if (!['shots', 'audit', 'jank'].includes(cmd) || !page) {
  console.error('Aufruf: node _src/pruefen.mjs <shots|audit|jank> <seite.html> [--w 375,1440] [--out ordner] [--reduced] [--no-tiles] [--dpr 2]');
  process.exit(2);
}
if (!CHROME) { console.error('Chrome/Edge nicht gefunden (Umgebungsvariable CHROME setzen).'); process.exit(2); }
const widths = String(opt.w).split(',').map(Number).filter(Boolean);
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
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding', 'about:blank'], { stdio: 'ignore' });
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
  window.__cls = 0; window.__shifts = []; window.__loaf = []; window.__lcp = null;
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) { __cls += e.value;
    __shifts.push({ value: +e.value.toFixed(4), t: Math.round(e.startTime), sources: (e.sources || []).map(s => d(s.node)) }); } })
    .observe({ type: 'layout-shift', buffered: true }); } catch (e) {}
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) __loaf.push({ t: Math.round(e.startTime), dur: Math.round(e.duration),
    blocking: Math.round(e.blockingDuration || 0), scripts: (e.scripts || []).map(s => (s.invoker || '') + ' ' + (s.sourceURL || '').split('/').pop()) }); })
    .observe({ type: 'long-animation-frame', buffered: true }); } catch (e) {}
  try { new PerformanceObserver(l => { const e = l.getEntries().pop(); if (e) __lcp = { t: Math.round(e.startTime), el: d(e.element), size: e.size }; })
    .observe({ type: 'largest-contentful-paint', buffered: true }); } catch (e) {}
})();`;

async function openPage(cdp, width, { reduced } = {}) {
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  const s = (m, p) => cdp.send(m, p, sessionId);
  const touch = width < 1024;
  const height = Number(opt.h) || (width < 768 ? 812 : touch ? 1024 : 900);
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
  await s('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: Number(opt.dpr) || 1, mobile: touch });
  if (touch) await s('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await s('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: reduced ? 'reduce' : 'no-preference' }, { name: 'prefers-color-scheme', value: 'light' }] });
  await s('Page.addScriptToEvaluateOnNewDocument', { source: OBSERVERS });
  const evaluate = async (expr, awaitPromise = true) => {
    const r = await s('Runtime.evaluate', { expression: expr, awaitPromise, returnByValue: true, userGesture: true });
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
  return { s, evaluate, goto, close, log, width, height, touch, sessionId };
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
const AUDIT = `(() => {
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

  // 5) Bilder: tatsächliche vs. benötigte Auflösung, Ladeattribute
  out.images = [...document.images].filter(shown).map(i => { const r = i.getBoundingClientRect(); const need = Math.round(r.width * devicePixelRatio);
    return { src: (i.currentSrc || i.src).split('/').slice(-2).join('/'), shown: Math.round(r.width) + 'x' + Math.round(r.height), natural: i.naturalWidth + 'x' + i.naturalHeight,
      sharpAt1x: i.naturalWidth >= r.width, sharpAt2x: i.naturalWidth >= r.width * 2, loading: i.loading, decoding: i.decoding, fetchpriority: i.getAttribute('fetchpriority') || '', complete: i.complete, alt: i.alt ? 'ja' : 'FEHLT' }; });

  // 6) Überschriften, Barrierefreiheit, Semantik
  out.headings = [...document.querySelectorAll('h1, h2, h3')].filter(shown).map(h => h.tagName + ' ' + h.textContent.replace(/\\s+/g, ' ').trim().slice(0, 90));
  out.h1count = document.querySelectorAll('h1').length;
  out.ids = (() => { const m = {}; for (const e of document.querySelectorAll('[id]')) m[e.id] = (m[e.id] || 0) + 1; return Object.keys(m).filter(k => m[k] > 1); })();
  out.brokenAnchors = [...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href')).filter(h => h.length > 1 && !document.getElementById(decodeURIComponent(h.slice(1))));
  out.linksNoName = [...document.querySelectorAll('a, button')].filter(a => shown(a) && !(a.textContent.trim() || a.getAttribute('aria-label'))).map(desc);
  out.blankNoopener = [...document.querySelectorAll('a[target=_blank]')].filter(a => !/noopener|noreferrer/.test(a.rel)).map(desc);
  out.fonts = [...document.fonts].filter(f => f.status !== 'unloaded').map(f => f.family.replace(/"/g, '') + ' ' + f.weight + (f.style !== 'normal' ? ' ' + f.style : '') + ' ' + f.status);
  out.cls = +(window.__cls || 0).toFixed(4); out.shifts = (window.__shifts || []).slice(0, 15); out.lcp = window.__lcp;
  return out;
})()`;

// ---------------------------------------------------------------- Befehle
async function shots(cdp, base) {
  for (const w of widths) {
    const p = await openPage(cdp, w, { reduced: opt.reduced });
    await p.goto(base + page);
    const hPage = await p.evaluate(REVEAL_ALL);
    const tag = `${w}${opt.reduced ? '-reduced' : ''}`;
    if (!opt['no-tiles']) {
      let n = 0;
      for (let y = 0; y < hPage; y += p.height) {
        await p.evaluate(`scrollTo({ top: ${y}, behavior: 'instant' }); new Promise(r => setTimeout(r, 450))`);
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
  for (const w of widths) {
    const p = await openPage(cdp, w, { reduced: opt.reduced });
    await p.goto(base + page);
    await p.evaluate(REVEAL_ALL);
    const a = await p.evaluate(AUDIT);
    a.console = p.log.console; a.exceptions = p.log.exceptions; a.failedRequests = p.log.failed;
    result[w] = a;
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
  for (const w of widths) {
    const p = await openPage(cdp, w, { reduced: opt.reduced });
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
      await p.s('Input.synthesizeScrollGesture', { x: Math.round(w / 2), y: Math.round(p.height / 2), yDistance: -scrollH, speed: 1400,
        gestureSourceType: p.touch ? 'touch' : 'mouse', preventFling: true });
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
        over25ms: f.filter(x => x > 25).length, over50ms: f.filter(x => x > 50).length, cls: +(__cls || 0).toFixed(4), shifts: __shifts.slice(0, 10), lcp: __lcp,
        loafOver50: __loaf.filter(l => l.dur > 50).slice(0, 12) }; })()`);
    await cdp.send('Tracing.end');
    await complete; off();
    result[w] = { scroll: { method, distance: scrollH, reached: Math.round(y), loadPhaseMs: loadEnd }, rafDuringScroll: inPage, trace: summarize(events),
      exceptions: p.log.exceptions, failedRequests: p.log.failed };
    await p.close();
  }
  const f = path.join(OUT, `jank${opt.reduced ? '-reduced' : ''}.json`);
  fs.writeFileSync(f, JSON.stringify(result, null, 1));
  console.log(JSON.stringify(result, null, 1));
  console.log('-> ' + f);
}

// ---------------------------------------------------------------- Start
const srv = await serve();
const base = `http://127.0.0.1:${srv.address().port}/`;
const cdp = await launch();
try {
  await ({ shots, audit, jank })[cmd](cdp, base);
} catch (e) {
  console.error('FEHLER:', e.stack || e.message); process.exitCode = 1;
} finally {
  await cdp.close(); srv.close();
}
