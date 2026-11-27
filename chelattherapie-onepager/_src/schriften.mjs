#!/usr/bin/env node
/*
 * Metrisch angepasste Ersatzschriften gegen Layout-Sprünge beim Nachladen der Webfonts (CLS).
 * Headless-Chrome über das DevTools-Protokoll, ohne Zusatzpakete (Node >= 22). Lädt nichts herunter außer den
 * Webfonts, die die Seite ohnehin von Google lädt.
 *
 *   node _src/schriften.mjs entwurf-a-salbei.html              messen und CSS ausgeben
 *   node _src/schriften.mjs entwurf-a-salbei.html --schreiben  zusätzlich den Block im Template ersetzen
 *                                                              (zwischen "schriften:start" und "schriften:ende")
 *   Optionen: --w 1024,1280,1440,1920   Breiten für den Layout-Vergleich (Standard)
 *             --alle                    ein Face je Schnitt statt je Familie und Ersatzdatei (genauer, aber langsamer)
 *             --out <ordner>            Ergebnis-JSON (Standard: %TEMP%/chelat-pruefung/<seite>/schriften.json)
 *
 * Vorgehen (wie fontaine / Next.js, aber gemessen statt aus den Font-Tabellen gelesen):
 *  1. In der gebauten Seite alle Kombinationen aus Webfont, font-weight und font-style einsammeln, die an Text
 *     vorkommen. Berücksichtigt werden die Familien von h1, h2, h3, .lead und body (Überschriften, Lead, Fließtext).
 *  2. Je Kombination per Canvas messen: Breite eines deutschen Mustertexts sowie fontBoundingBoxAscent/-Descent,
 *     einmal mit der Webfont, einmal mit der lokalen Ersatzschrift (Georgia für Serifen, sonst Arial; ab 600 fett,
 *     kursiv wo nötig). Zeilenabstand (lineGap) aus der Höhe einer Zeile mit line-height:normal.
 *     Mustertext: hat der Schnitt auf der Seite mindestens 1500 Zeichen Text, ist das der Seitentext (trifft die
 *     Laufweite von Fließtext am besten; der feste Mustertext mit Versalien und Ziffern lag bei Source Sans 3 Light
 *     0,8 % daneben), sonst fester Mustertext plus Seitentext.
 *  3. size-adjust = Breite Webfont / Breite Ersatz; ascent/descent/line-gap-override = Webfont-Wert / size-adjust.
 *  4. Gegenprobe: dieselbe Messung mit der angepassten Ersatzschrift (Abweichung in %), danach Layout-Vergleich:
 *     alle Textelemente einmal mit Webfont, einmal nur mit Ersatzschrift (Webfont aus dem Stack entfernt);
 *     gezählt werden Elemente mit anderer Höhe. Das ist genau der Sprung, den Besucher beim Nachladen sehen.
 * Ergebnis: @font-face "<Familie> Fallback" je Kombination. Im Template muss der Stack lauten:
 *   "<Familie>", "<Familie> Fallback", <bisherige Ersatzschriften>
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

const [page, ...rest] = process.argv.slice(2);
const opt = { w: '1024,1280,1440,1920', out: path.join(os.tmpdir(), 'chelat-pruefung') };
for (let i = 0; i < rest.length; i++) {
  const k = rest[i].replace(/^--/, '');
  if (k === 'schreiben' || k === 'alle') opt[k] = true; else if (rest[i].startsWith('--')) opt[k] = rest[++i];
}
if (!page || !CHROME) { console.error('Aufruf: node _src/schriften.mjs <seite.html> [--schreiben] [--w 1024,1440] [--out ordner]'); process.exit(2); }
const widths = String(opt.w).split(',').map(Number).filter(Boolean);
const OUT = path.resolve(opt.out, path.basename(page, '.html'));
fs.mkdirSync(OUT, { recursive: true });

// Deutscher Mustertext (Fließtext-typische Buchstabenverteilung, dazu Versalien, Umlaute, Ziffern, Satzzeichen)
const MUSTER = 'Die Behandlung beginnt mit einem ausführlichen Gespräch über Ihre Vorgeschichte, mögliche Belastungsquellen '
  + 'und bisherige Befunde. Danach planen wir gemeinsam, welche Untersuchungen sinnvoll sind, und besprechen jeden '
  + 'Schritt in Ruhe. Größere Veränderungen erfolgen nie überstürzt, sondern nachvollziehbar und abgestimmt. '
  + 'Termine vergeben wir telefonisch oder online, Rückfragen beantworten wir gern. Qualität, Übersicht, Zeit: '
  + 'KOSTENLOSES ERSTGESPRÄCH, 10 Minuten, 12307 Berlin, 150 Euro, Steinstraße 41D.';

// Lokale Ersatzschriften (Name, PostScript-Name) je Art und Schnitt
const LOCAL = {
  sans:  { r: ['Arial', 'ArialMT'], b: ['Arial Bold', 'Arial-BoldMT'], i: ['Arial Italic', 'Arial-ItalicMT'], bi: ['Arial Bold Italic', 'Arial-BoldItalicMT'] },
  serif: { r: ['Georgia'], b: ['Georgia Bold', 'Georgia-Bold'], i: ['Georgia Italic', 'Georgia-Italic'], bi: ['Georgia Bold Italic', 'Georgia-BoldItalic'] },
};

// ---------------------------------------------------------------- Server + Chrome (wie pruefen.mjs)
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.webp': 'image/webp',
  '.jpg': 'image/jpeg', '.png': 'image/png', '.woff2': 'font/woff2', '.json': 'application/json', '.txt': 'text/plain; charset=utf-8' };
function serve() {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      let u = decodeURIComponent(new URL(req.url, 'http://x').pathname); if (u.endsWith('/')) u += 'index.html';
      const f = path.join(ROOT, u);
      if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'content-type': TYPES[path.extname(f).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-store' });
      fs.createReadStream(f).pipe(rsp);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}
async function launch() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'schriften-chrome-'));
  const proc = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${dir}`, '--no-first-run', '--no-default-browser-check',
    '--hide-scrollbars', '--force-color-profile=srgb', '--mute-audio', '--disable-extensions', 'about:blank'], { stdio: 'ignore' });
  let port = '';
  for (let i = 0; i < 200 && !port; i++) { await sleep(100); try { port = fs.readFileSync(path.join(dir, 'DevToolsActivePort'), 'utf8').split('\n')[0].trim(); } catch {} }
  if (!port) throw new Error('Chrome hat keinen DevTools-Port geöffnet');
  const { webSocketDebuggerUrl } = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  const ws = new WebSocket(webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pending = new Map(), handlers = new Set();
  ws.onmessage = e => { const m = JSON.parse(String(e.data)); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(p.method + ': ' + m.error.message)) : p.res(m.result); } else for (const h of handlers) h(m); };
  const send = (method, params = {}, sessionId) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params, ...(sessionId ? { sessionId } : {}) })); return new Promise((res, rej) => pending.set(i, { res, rej, method })); };
  const close = async () => { try { await send('Browser.close'); } catch {} try { ws.close(); } catch {} await sleep(300); try { proc.kill(); } catch {} try { fs.rmSync(dir, { recursive: true, force: true }); } catch {} };
  return { send, handlers, close };
}

// ---------------------------------------------------------------- In der Seite
const SAMMELN = `(() => {
  const first = ff => ff.split(',')[0].trim().replace(/^["']|["']$/g, '');
  const web = new Set([...document.fonts].map(f => f.family.replace(/^["']|["']$/g, '')));
  const rolle = new Set();
  for (const sel of ['h1', 'h2', 'h3', '.lead', 'body']) { const el = document.querySelector(sel); if (el) rolle.add(first(getComputedStyle(el).fontFamily)); }
  const combos = {}, texte = {}, oben = {};
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (!n.textContent.trim()) continue; const el = n.parentElement; if (!el || el.closest('script, style')) continue;
    const c = getComputedStyle(el), fam = first(c.fontFamily);
    if (!web.has(fam) || !rolle.has(fam)) continue;
    const art = /(^|,)\\s*serif\\s*$/.test(c.fontFamily) ? 'serif' : 'sans';   // generische Familie am Ende des Stacks
    const k = fam + '|' + c.fontWeight + '|' + c.fontStyle + '|' + art;
    combos[k] = (combos[k] || 0) + n.textContent.trim().length;
    const r = el.getBoundingClientRect(); if (r.bottom > 0 && r.top < innerHeight && r.width > 0) oben[k] = (oben[k] || 0) + n.textContent.trim().length;
    if ((texte[k] || '').length < 6000) texte[k] = (texte[k] || '') + ' ' + n.textContent.replace(/\\s+/g, ' ').trim();
  }
  // auch ::before/::after mit Text (z. B. Zähler) zählen nicht zu Text-Knoten: für die Messung genügen die Knoten
  return { rolle: [...rolle].filter(f => web.has(f)), combos, texte, oben, stacks: [...new Set([...document.querySelectorAll('body, h1, h2, h3, .lead, p')].map(e => getComputedStyle(e).fontFamily))] };
})()`;

const MESSEN = (fam, weight, style, src, descr, text = MUSTER) => `(async () => {
  const text = ${JSON.stringify(text)};
  const fontSpec = f => '${style} ${weight} 100px ' + f;
  await document.fonts.load(fontSpec('"${fam}"'), text);
  const face = new FontFace('__fb_messung', ${JSON.stringify(src)}, ${JSON.stringify({ weight: String(weight), style, ...(descr || {}) })});
  document.fonts.add(face);
  try { await face.load(); } catch (e) { document.fonts.delete(face); return { fehler: 'lokale Schrift nicht gefunden: ' + ${JSON.stringify(src)} }; }
  const cv = document.createElement('canvas').getContext('2d');
  const m = f => { cv.font = fontSpec(f); const t = cv.measureText(text);
    const div = document.createElement('div'); div.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;line-height:normal;font:' + fontSpec(f) + ';line-height:normal';
    div.textContent = 'Hxgé'; document.body.appendChild(div); const h = div.getBoundingClientRect().height; div.remove();
    return { width: t.width, ascent: t.fontBoundingBoxAscent, descent: t.fontBoundingBoxDescent, lineNormal: h }; };
  const w = m('"${fam}"'), fb = m('__fb_messung');
  document.fonts.delete(face);
  return { loaded: document.fonts.check(fontSpec('"${fam}"'), text), web: w, fb };
})()`;

// Layout mit Webfont vs. nur Ersatzschrift: Höhe jedes Textelements vergleichen
const LAYOUT = `(async () => {
  await document.fonts.ready;
  const sel = 'h1, h2, h3, p, li, dd, dt, summary, figcaption, blockquote, .btn, a, span, small, b, strong, td, th';
  const els = [...document.querySelectorAll(sel)].filter(e => e.getClientRects().length && e.textContent.trim());
  const d = el => { let s = el.tagName.toLowerCase(); if (el.id) s += '#' + el.id; if (el.classList.length) s += '.' + [...el.classList].slice(0, 2).join('.');
    const p = el.closest('section[id], header, footer, .mcta, [id]'); return (p && p !== el ? (p.id ? '#' + p.id : p.tagName.toLowerCase()) + ' > ' : '') + s; };
  const mess = () => els.map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.height * 10) / 10, Math.round((r.top + scrollY) * 10) / 10]; });
  const a = mess(), H1 = document.documentElement.scrollHeight;
  const all = [...document.querySelectorAll('*')], alt = new Map();
  for (const e of all) { const ff = getComputedStyle(e).fontFamily, parts = ff.split(','); if (parts.length > 1 && /Fallback/.test(parts[1])) { alt.set(e, e.style.fontFamily); e.style.fontFamily = parts.slice(1).join(','); } }
  document.body.offsetHeight; await document.fonts.ready; await new Promise(r => setTimeout(r, 150));   // local()-Schriften laden asynchron
  const fbStatus = [...document.fonts].filter(f => / Fallback$/.test(f.family.replace(/"/g, ''))).map(f => f.status);
  const b = mess(), H2 = document.documentElement.scrollHeight;
  for (const [e, v] of alt) e.style.fontFamily = v;
  const diffs = [];
  els.forEach((e, i) => { if (Math.abs(a[i][0] - b[i][0]) > 0.5) diffs.push({ el: d(e), webfont: a[i][0], ersatz: b[i][0], text: e.textContent.trim().replace(/\\s+/g, ' ').slice(0, 50) }); });
  const verschoben = els.filter((e, i) => Math.abs(a[i][1] - b[i][1]) > 1).length;
  return { elemente: els.length, umgestellt: alt.size, fallbackFaces: fbStatus.length, fallbackGeladen: fbStatus.filter(s => s === 'loaded').length, hoeheAnders: diffs.length, verschoben, seitenhoehe: { webfont: H1, ersatz: H2 }, beispiele: diffs.slice(0, 12) };
})()`;

// ---------------------------------------------------------------- Ablauf
const pct = x => Math.round(x * 10000) / 100;   // 0.8831 -> 88.31
const seitenzeichen = r => r.zeichen;
const localSrc = (art, weight, style) => {
  const k = (+weight >= 600 ? 'b' : '') + (style === 'italic' ? 'i' : '') || 'r';
  return LOCAL[art][k].map(n => `local("${n}")`).join(', ');
};

const srv = await serve();
const base = `http://127.0.0.1:${srv.address().port}/`;
const chrome = await launch();
let exitCode = 0;
try {
  const { targetId } = await chrome.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await chrome.send('Target.attachToTarget', { targetId, flatten: true });
  const s = (m, p) => chrome.send(m, p, sessionId);
  const ev = async expr => { const r = await s('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
  await s('Page.enable'); await s('Runtime.enable');
  await s('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  const loaded = new Promise(r => chrome.handlers.add(m => { if (m.sessionId === sessionId && m.method === 'Page.loadEventFired') r(); }));
  await s('Page.navigate', { url: base + page }); await loaded; await ev('document.fonts.ready.then(() => true)');

  const info = await ev(SAMMELN);
  await s('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true }); await sleep(300);
  const handy = await ev(SAMMELN);
  for (const [k, n] of Object.entries(handy.oben)) info.oben[k] = (info.oben[k] || 0) + n;
  await s('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }); await sleep(300);
  const combos = Object.entries(info.combos).map(([k, n]) => { const [fam, weight, style, art] = k.split('|'); return { fam, weight, style, art, zeichen: n }; })
    .sort((a, b) => a.fam.localeCompare(b.fam) || a.style.localeCompare(b.style) || a.weight - b.weight);
  console.log('Familien (Überschriften/Lead/Fließtext):', info.rolle.join(', '));
  const faces = [], tabelle = [];
  for (const c of combos) {
    const src = localSrc(c.art, c.weight, c.style);
    // Mustertext: reichlich Fließtext dieses Schnitts auf der Seite (>= 1500 Zeichen) trifft die echte Laufweite am
    // besten; sonst fester deutscher Mustertext plus der vorhandene Seitentext
    const seitentext = (info.texte[c.fam + '|' + c.weight + '|' + c.style + '|' + c.art] || '').trim();
    const sample = seitentext.length >= 1500 ? seitentext : (MUSTER + ' ' + seitentext).trim();
    const m = await ev(MESSEN(c.fam, c.weight, c.style, src, null, sample));
    if (m.fehler || !m.loaded) { console.log(`  ${c.fam} ${c.weight} ${c.style}: ${m.fehler || 'Webfont nicht geladen'}`); exitCode = 1; continue; }
    const mMuster = await ev(MESSEN(c.fam, c.weight, c.style, src));   // nur zur Einordnung: fester Mustertext allein
    const size = m.web.width / m.fb.width;
    const asc = m.web.ascent / 100 / size, desc = m.web.descent / 100 / size;
    const gapWeb = Math.max(0, m.web.lineNormal / 100 - (m.web.ascent + m.web.descent) / 100), gap = gapWeb / size;
    const descr = { sizeAdjust: pct(size) + '%', ascentOverride: pct(asc) + '%', descentOverride: pct(desc) + '%', lineGapOverride: pct(gap) + '%' };
    const probe = await ev(MESSEN(c.fam, c.weight, c.style, src, descr, sample));   // Gegenprobe mit den berechneten Werten
    const abw = (a, b) => Math.round((b / a - 1) * 10000) / 100;
    const row = { familie: c.fam, weight: +c.weight, style: c.style, zeichen: c.zeichen, ersatz: src,
      mustertext: seitentext.length >= 1500 ? `Seitentext (${seitentext.length} Zeichen)` : `Muster + Seitentext (${sample.length} Zeichen)`,
      sizeAdjustNurMuster: pct(mMuster.web.width / mMuster.fb.width) + '%',
      sizeAdjust: descr.sizeAdjust, ascent: descr.ascentOverride, descent: descr.descentOverride, lineGap: descr.lineGapOverride,
      gegenprobe: { breite: abw(probe.web.width, probe.fb.width) + '%', ascent: abw(probe.web.ascent, probe.fb.ascent) + '%',
        descent: abw(probe.web.descent, probe.fb.descent) + '%', zeileNormal: abw(probe.web.lineNormal, probe.fb.lineNormal) + '%' } };
    row.obenZeichen = info.oben[c.fam + '|' + c.weight + '|' + c.style + '|' + c.art] || 0;
    row.werte = `src:${src}; size-adjust:${descr.sizeAdjust}; ascent-override:${descr.ascentOverride}; descent-override:${descr.descentOverride}; line-gap-override:${descr.lineGapOverride}`;
    tabelle.push(row);
    console.log(`  ${c.fam} ${c.weight}${c.style !== 'normal' ? ' ' + c.style : ''} gegen ${src.split(',')[0]}: size-adjust ${descr.sizeAdjust}, ascent ${descr.ascentOverride}, `
      + `descent ${descr.descentOverride}, line-gap ${descr.lineGapOverride} | ${row.mustertext}, nur Muster wäre ${row.sizeAdjustNurMuster} | Gegenprobe Breite ${row.gegenprobe.breite}, Zeile ${row.gegenprobe.zeileNormal}`);
  }
  // Jedes Face kostet beim ersten Zeichnen Zeit (gemessen: rund 35 ms FCP je Face bei 4-facher CPU-Drosselung).
  // Deshalb standardmäßig EIN Face je Familie und Ersatzdatei, mit Gewichtsbereich. Die Werte kommen vom Schnitt mit
  // dem meisten Text im ersten Bildschirm (dort entsteht CLS, weil die Webfont beim Laden kommt), sonst vom Schnitt
  // mit dem meisten Text. Gruppen mit weniger als 150 Zeichen und nichts im ersten Bildschirm entfallen (sie nehmen
  // dann das nächstliegende Face der Familie). --alle: ein Face je Schnitt.
  const gruppen = new Map();
  for (const r of tabelle) { const k = opt.alle ? r.familie + '|' + r.style + '|' + r.weight : r.familie + '|' + r.ersatz;
    if (!gruppen.has(k)) gruppen.set(k, []); gruppen.get(k).push(r); }
  const ausgelassen = [];
  for (const [, g] of gruppen) {
    const zeichen = g.reduce((n, r) => n + (seitenzeichen(r) || 0), 0), oben = g.reduce((n, r) => n + r.obenZeichen, 0);
    if (!opt.alle && zeichen < 150 && oben === 0) { ausgelassen.push(g.map(r => `${r.familie} ${r.weight}${r.style !== 'normal' ? ' ' + r.style : ''}`).join(', ') + ` (${zeichen} Zeichen)`); continue; }
    const anker = [...g].sort((a, b) => (b.obenZeichen - a.obenZeichen) || (seitenzeichen(b) - seitenzeichen(a)))[0];
    const ws = g.map(r => r.weight);
    faces.push({ fam: anker.familie, style: anker.style, von: Math.min(...ws), bis: Math.max(...ws), werte: anker.werte,
      anker: `${anker.weight}${anker.style !== 'normal' ? ' ' + anker.style : ''}`, schnitte: g.length });
  }
  faces.sort((a, b) => a.fam.localeCompare(b.fam) || a.style.localeCompare(b.style) || a.von - b.von);
  console.log(`
${faces.length} Faces aus ${tabelle.length} Schnitten` + (ausgelassen.length ? `; ausgelassen (kaum Text): ${ausgelassen.join('; ')}` : ''));
  for (const f of faces) if (f.schnitte > 1) console.log(`  ${f.fam}${f.style !== 'normal' ? ' ' + f.style : ''} ${f.von}-${f.bis}: Werte von ${f.anker}`);
  const block = '/* schriften:start  Ersatzschriften mit gemessenen Metriken gegen Layout-Sprünge beim Nachladen (CLS).\n'
    + `   Automatisch erzeugt von: node _src/schriften.mjs ${page} --schreiben (nicht von Hand ändern) */\n`
    + faces.map(f => `@font-face{font-family:"${f.fam} Fallback"; font-weight:${f.von === f.bis ? f.von : f.von + ' ' + f.bis};`
      + `${f.style !== 'normal' ? ` font-style:${f.style};` : ''} ${f.werte}; unicode-range:{{LATIN}}}`).join('\n') + '\n/* schriften:ende */';
  console.log('\n' + block + '\n');

  // Stacks prüfen: steht "<Familie> Fallback" direkt hinter der Webfont?
  const fehlend = info.rolle.filter(f => !info.stacks.some(st => st.replace(/"/g, '').includes(f + ', ' + f + ' Fallback')));
  if (fehlend.length) console.log('ACHTUNG: Im Template fehlt im font-family-Stack noch "<Familie> Fallback" für: ' + fehlend.join(', '));

  // Layout-Vergleich je Breite
  const layout = {};
  for (const w of widths) {
    await s('Emulation.setDeviceMetricsOverride', { width: w, height: 900, deviceScaleFactor: 1, mobile: false }); await sleep(300);
    layout[w] = await ev(LAYOUT);
    console.log(`Layout ${w}px: ${layout[w].hoeheAnders} von ${layout[w].elemente} Textelementen mit anderer Höhe, ${layout[w].verschoben} verschoben, `
      + `Seitenhöhe ${layout[w].seitenhoehe.webfont} (Webfont) / ${layout[w].seitenhoehe.ersatz} (Ersatz)`
      + `, Fallback-Faces geladen ${layout[w].fallbackGeladen}/${layout[w].fallbackFaces}`
      + (layout[w].umgestellt ? '' : '  [keine Fallback-Familie im Stack gefunden, Vergleich ohne Aussage]'));
    for (const b of layout[w].beispiele.slice(0, 5)) console.log(`   ${b.el}: ${b.webfont} -> ${b.ersatz}  «${b.text}»`);
  }

  if (opt.schreiben) {
    const m = /entwurf-([a-z])-/.exec(path.basename(page));
    const tpl = m && path.join(ROOT, '_src', `entwurf-${m[1]}.src.html`);
    if (!tpl || !fs.existsSync(tpl)) throw new Error('Template zu ' + page + ' nicht gefunden');
    let t = fs.readFileSync(tpl, 'utf8');
    const eol = t.includes('\r\n') ? '\r\n' : '\n', blk = block.replace(/\r?\n/g, eol);
    const re = /\/\* schriften:start[\s\S]*?schriften:ende \*\//;
    if (re.test(t)) t = t.replace(re, () => blk);
    else if (/<style>\r?\n/.test(t)) t = t.replace(/<style>\r?\n/, m => m + blk + eol);
    else throw new Error('Weder Block "schriften:start … schriften:ende" noch <style> im Template gefunden');
    fs.writeFileSync(tpl, t);
    console.log('geschrieben: ' + path.relative(ROOT, tpl) + '  (danach: python _src/build.py ' + m[1] + ')');
  }
  const f = path.join(OUT, 'schriften.json');
  fs.writeFileSync(f, JSON.stringify({ seite: page, familien: info.rolle, tabelle, layout, block }, null, 1));
  console.log('-> ' + f);
} catch (e) {
  console.error('FEHLER:', e.stack || e.message); exitCode = 1;
} finally {
  await chrome.close(); srv.close(); process.exitCode = exitCode;
}
