# -*- coding: utf-8 -*-
"""
Baut die drei Design-Entwürfe aus den Templates in _src/ und den Upload-Ordner für den Go-live.
Alle Werte (Domain, Praxis, Kontakt, Datum, FAQ, Bilder, Go-live-Schalter) stehen in _src/stammdaten.py,
Meta-Tags, JSON-LD, SEO-Dateien und Release in _src/seo.py. Hier: Templates füllen, SHARED_CSS, SCRIPTS, Bilder.
Alle Entwürfe bekommen denselben <head> und dieselben strukturierten Daten, bleiben also SEO-identisch.

Aufruf:  python _src/build.py          alle Entwürfe + robots.txt, llms.txt, sitemap.xml, index.md, site.webmanifest
         python _src/build.py b        nur Entwurf B (schreibt NUR entwurf-b-klarheit.html, parallel sicher)
         python _src/build.py a c      nur A und C
         python _src/build.py release b                  Go-live: _release/ aus Entwurf B (index,follow, Canonical)
         python _src/build.py release b --probe          Test-Hosting: noindex, robots.txt sperrt alles
         python _src/build.py release b --ziel <ordner>  anderer Zielordner (außerhalb des Projekts oder _release*)
  Entwürfe im Projektordner tragen immer noindex und kein Canonical. Hochgeladen wird nur der Inhalt von _release/.
  Ohne --probe bricht der Release ab, solange DOMAIN der Platzhalter ist oder in stammdaten.FREIGABEN etwas auf
  False steht. Er prüft sich selbst; nur bei „Release OK“ hochladen. IndexNow ruft er nicht auf (README).

Build-Block (je Template im <head> direkt vor {{HEAD}}, wird beim Bauen gelesen und entfernt):
  <!--build {"fonts": "<Google-Fonts-URL>", "theme": "#RRGGBB",
             "preload": {"href": "assets/nina-klimek.webp", "media": "(min-width: 641px)", "sizes": "..."} } -->
  preload darf null sein. media ist optional. sizes wird Pflicht, sobald es vom Bild mehrere Breiten gibt
  (dann Preload per imagesrcset/imagesizes) und muss exakt dem sizes-Attribut am Bild entsprechen, sonst lädt
  der Browser das Bild doppelt. Der Build prüft das.
  "fonts" darf "" sein, sobald die Schriften lokal liegen (Dateien in fonts/, @font-face im Template).
  Optional "schriften": ["fonts/<datei>.woff2", ...] lädt diese Schnitte vor (H1 und Fließtext, README).

Platzhalter (jeder übrig gebliebene {{...}} bricht den Build ab):
  {{HEAD}} {{FAQ}} {{SCRIPTS}}                      Bausteine (HEAD aus seo.head)
  aus stammdaten.werte(), reiner Text:
  {{DOMAIN}} {{HOST}} {{UPDATED}} {{UPDATED_DE}} {{YEAR}} {{TITLE}} {{DESC}} {{SITE_NAME}}
  {{PHONE_INTL}} {{PHONE_DE}} {{PHONE_READ}} {{EMAIL}} {{DOCTOLIB}} {{MAIN_SITE}} {{MAPS}} {{INSTAGRAM}}
  {{IMPRESSUM}} {{DATENSCHUTZ}} {{UEBER_MICH}}      Links der Hauptseite (später eigene Seiten)
  {{PRAXIS}} {{STREET}} {{ZIP}} {{CITY}} {{DISTRICT}} {{BEZIRK}}   Praxisname und Adresse, eine Quelle für alle
  {{STREET_NB}}                                     Straße mit geschütztem Leerzeichen vor der Hausnummer (nur HTML)
  {{FAQ_COUNT}}                                     Zahl der Fragen
  {{HINWEIS}}                                       Pflichthinweis im Footer (hier HTML-maskiert)
  {{GEPRUEFT}}                                      " und geprüft", nur wenn REVIEWED gesetzt ist, sonst leer
  {{LATIN}}                                         unicode-range der Google-Latin-Schnitte (für Fallback-@font-face)
  {{IMG_X}} {{IMG_X_SRCSET}} {{IMG_X_W}} {{IMG_X_H}} je Bild aus IMAGES (größte Variante, srcset, echte Maße)
  {{PORTRAIT}} {{PORTRAIT_JPG}} {{PORTRAIT_SRCSET}} {{PORTRAIT_W}} {{PORTRAIT_H}}   Porträt (WebP, JPG-Fallback)
"""
import json, html, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
sys.path.insert(0, str(SRC))
sys.dont_write_bytecode = True   # kein __pycache__ im Projekt
from bilder import BREITEN   # Breitenstufen der Bildvarianten: eine Quelle für bilder.py und build.py
# Alle Werte (Domain, Praxis, Kontakt, Datum, FAQ, Bilder, Go-live-Schalter) stehen nur in stammdaten.py,
# Meta-Tags, JSON-LD, SEO-Dateien und Release in seo.py. Die Namen hier sind nur durchgereicht (auch für Prüfskripte).
import stammdaten as S, seo
from stammdaten import (BuildFehler, fill, slug, faq_ids, de_datum, DOMAIN, UPDATED, UPDATED_DE, REVIEWED, HINWEIS,
                        TITLE, DESC, PHONE_INTL, PHONE_DE, EMAIL, DOCTOLIB, MAIN_SITE, INSTAGRAM, ANALYTICS_DOMAIN,
                        MAPS, IMAGES, PORTRAIT, PORTRAIT_JPG, FAQ)

# ---------------------------------------------------------------------------
# FAQ im sichtbaren HTML. Fragen und Antworten: stammdaten.FAQ, ids: stammdaten.faq_ids()
# (dieselbe Quelle für FAQPage-Schema, index.md und llms.txt)
# ---------------------------------------------------------------------------
# Umbruchschutz nur im sichtbaren HTML (JSON-LD, llms.txt und index.md bleiben unverändert).
# Antworten (text-wrap:pretty, auf dem Handy mit Silbentrennung): <span class="nw"> um Begriffe, die nicht am
# Bindestrich umbrechen sollen. Fragen (h3, text-wrap:balance): KEIN Span, denn ein Span schaltet in Chrome balance
# für die ganze Überschrift ab (gemessen in Entwurf B). Dort Wortverbinder U+2060 nach dem Bindestrich und weiche
# Trennstellen U+00AD für sehr lange Wörter. In beiden: geschütztes Leerzeichen U+00A0 (Hausnummer, Postleitzahl,
# „in Berlin“).
WJ, NBSP, SHY = chr(0x2060), chr(0xA0), chr(0xAD)
STREET_NB = NBSP.join(S.PRAXIS["street"].rsplit(" ", 1))   # Hausnummer bleibt an der Straße ({{STREET_NB}})
NOWRAP = ("Detox-Kur", "EDTA-Infusion", f'{S.PRAXIS["city"]}-{S.PRAXIS["district"]}')   # nicht am Bindestrich
BINDEN = {S.PRAXIS["street"]: STREET_NB}                                                # nicht am Leerzeichen
BINDEN.update({w: w.replace(" ", NBSP) for w in (f'{S.PRAXIS["zip"]} {S.PRAXIS["city"]}', f'in {S.PRAXIS["city"]}')})
TRENNEN = {"Schwermetallbelastung": f"Schwermetall{SHY}belastung"}                      # nur in Fragen

def nowrap(text_html, frage=False):
    wort = lambda w: re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)")
    for w, ersatz in BINDEN.items():
        text_html = wort(w).sub(ersatz, text_html)
    for w in NOWRAP:
        text_html = wort(w).sub(w.replace("-", "-" + WJ) if frage else f'<span class="nw">{w}</span>', text_html)
    if frage:
        for w, t in TRENNEN.items():
            text_html = text_html.replace(w, t)
    return text_html

def faq_html():
    out = []
    for i, ((q, a), fid) in enumerate(zip(FAQ, faq_ids())):
        out.append(
            f'<details class="faq-item" id="{fid}"{" open" if i == 0 else ""}>\n'
            f'  <summary><h3>{nowrap(html.escape(q), frage=True)}</h3></summary>\n'
            f'  <div class="faq-answer"><p>{nowrap(html.escape(a))}</p></div>\n'
            f'</details>')
    return "\n".join(out)

# ---------------------------------------------------------------------------
# <head>: Meta-Tags, JSON-LD, Icons, Manifest und Schriften baut seo.head (Werte aus stammdaten.py)
# ---------------------------------------------------------------------------
def head(fonts_url, theme_color, preload=None, modus="entwurf", schriften=()):
    """Kompletter <head>-Inhalt. preload: Angabe aus dem Build-Block (oder None), schriften: .woff2 zum Vorladen.
    modus: "entwurf" (Projektordner: noindex, kein Canonical), "probe" (Test-Hosting: noindex),
    "release" (Go-live: index,follow, Canonical). MOTION_HEAD geht als kopf_skript mit: seo.head setzt es vor das
    Schrift-CSS (ein Inline-Skript hinter einem ladenden Stylesheet wartet auf dessen Download), die CSP im Release
    nimmt seinen Hash automatisch auf."""
    return seo.head(fonts_url, theme_color, preload_link(preload), modus, css=SHARED_CSS, kopf_skript=MOTION_HEAD,
                    schrift_preloads=schriften)

# Gemeinsames CSS für alle Entwürfe (steht vor dem Entwurfs-CSS, das Farben und Feinheiten überschreibt).
# NUR Mechanik, keine Designwerte: Umbruch, Hilfsklassen, Menü, Handy-Leiste, Einblenden, Bilder im Text, Kontrastmodus.
SHARED_CSS = """
html{-webkit-text-size-adjust:100%; text-size-adjust:100%}
/* Umbruch: Überschriften ausgeglichen, Absätze ohne einzelnes Wort in der letzten Zeile (Chrome 114+, Safari 17.5+) */
h1,h2,h3{text-wrap:balance}
p,li,dd,figcaption,blockquote{text-wrap:pretty}
/* .nw: nicht umbrechen (Namen, Zahl + Einheit). .vh: nur für Screenreader */
.nw{white-space:nowrap}
.vh{position:absolute!important; width:1px!important; height:1px!important; margin:-1px!important; padding:0!important; border:0!important; overflow:hidden!important; clip:rect(0 0 0 0)!important; clip-path:inset(50%)!important; white-space:nowrap!important}
a,button,summary,[role=button]{-webkit-tap-highlight-color:transparent}
.menu-btn{display:none; width:46px; height:46px; margin-left:10px; border-radius:50%; border:1px solid currentColor; background:transparent; color:inherit; cursor:pointer; flex:none; flex-direction:column; align-items:center; justify-content:center; gap:6px; padding:0}
.menu-btn span{display:block; width:18px; height:1.5px; background:currentColor; transition:transform .25s}
html.nav-open .menu-btn span:first-child{transform:translateY(3.75px) rotate(45deg)}
html.nav-open .menu-btn span:last-child{transform:translateY(-3.75px) rotate(-45deg)}
/* Menü offen: Seite gesperrt und abgedunkelt (Farbe --nav-scrim, je Entwurf überschreibbar), Menü scrollt in sich
   (Höhe --nav-max setzt SCRIPTS: Fensterhöhe minus Unterkante des Headers), Handy-Leiste ausgeblendet.
   Header liegt in allen Entwürfen mit z-index 50 über der Abdunklung (40). */
html.nav-open{overflow:hidden; scrollbar-gutter:stable}
html.nav-open body::after{content:""; position:fixed; inset:0; z-index:40; background:var(--nav-scrim,rgba(16,24,20,.32)); animation:nav-scrim .2s ease-out}
@keyframes nav-scrim{from{opacity:0}}
html.nav-open nav.main{max-height:var(--nav-max,calc(100vh - 80px)); overflow-y:auto; overscroll-behavior:contain}
.mcta{transition:transform .35s ease, opacity .35s ease, visibility 0s}
html:not(.mcta-on) .mcta, html.nav-open .mcta{transform:translateY(calc(100% + 28px)); opacity:0; visibility:hidden; transition:transform .35s ease, opacity .35s ease, visibility 0s .35s}
/* Einblenden beim Scrollen. html.js-rv setzt MOTION_HEAD vor dem ersten Zeichnen: der Startzustand gilt ab dem
   ersten Frame und ohne Übergang, animiert wird nur das Einblenden (.in, setzt SCRIPTS). Verschachtelte Treffer
   kommen mit dem äußeren Block. Endzustand translateY(0) statt none, sonst ein Layout je Block am Ende der Bewegung */
.js-rv :is(__REVEAL__):not(:is(__REVEAL__) *):not(.in){opacity:0; transform:translateY(18px)}
.js-rv :is(__REVEAL__):not(:is(__REVEAL__) *).in{transform:translateY(0); transition:opacity .6s ease, transform .8s cubic-bezier(.2,.7,.2,1)}
/* Wer per Tastatur in einen noch nicht eingeblendeten Block springt, sieht ihn sofort */
.js-rv :is(__REVEAL__):not(:is(__REVEAL__) *):focus-within{opacity:1; transform:translateY(0); transition:none}
/* Bilder im Textfluss: .media (mit Bildunterschrift), .sec-split (Abschnittskopf links, Bild rechts), .call-img */
.media,.call-img{margin:0}
.media .ph,.call-img .ph{position:relative; overflow:hidden; border-radius:var(--r,14px); background:#E6E1D6; aspect-ratio:3/2}
.media img,.call-img img{position:absolute; inset:0; width:100%; height:100%; object-fit:cover}
.media figcaption{font-size:14px; line-height:1.5; margin-top:12px; opacity:.8}
.call-img{margin-bottom:30px}
.sec-split{display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:56px; align-items:end; margin-bottom:60px}
.sec-split .sec-head{margin-bottom:0}
/* Kein Zoom auf Bildern im Text: Chrome zeichnet ein skaliertes Bild als eigene GPU-Ebene weicher und zieht es am Ende
   sichtbar scharf (gemessen: Handy 3x p99 22 Graustufen). Die Bilder kommen mit ihrem Block (.media) herein und
   werden vorher geladen und dekodiert (SCRIPTS). */
/* FAQ: sanftes Auf- und Zuklappen, nur wo der Browser Höhen-Übergänge auf auto kann (Chrome/Edge ab 131), sonst wie bisher */
@supports (interpolate-size:allow-keywords) and selector(::details-content){
  .faq-item{interpolate-size:allow-keywords}
  .faq-item::details-content{block-size:0; overflow-y:clip; transition:block-size .3s cubic-bezier(.2,.7,.2,1), content-visibility .3s allow-discrete}
  .faq-item[open]::details-content{block-size:auto}
}
@media (max-width:1020px){
  .sec-split{grid-template-columns:minmax(0,1fr); gap:34px; align-items:start}
}
@media (max-width:640px){
  /* Fokus-Scrollen hält Abstand zur festen Handy-Leiste */
  html{scroll-padding-bottom:calc(84px + env(safe-area-inset-bottom))}
  p,li,dd{-webkit-hyphens:auto; hyphens:auto}
  h1,h2,h3{overflow-wrap:break-word}
  /* Auf dem Handy randlos: klare Unterbrechung im Text */
  .media{margin-left:-16px; margin-right:-16px}
  .media .ph{border-radius:0; aspect-ratio:4/3}
  .media figcaption{padding:0 16px}
  .sec-split{gap:26px; margin-bottom:34px}
  .call-img{margin-bottom:24px}
}
/* Windows-Kontrastmodus: Buttons behalten eine Kante, Menü-Striche bleiben sichtbar */
@media (forced-colors:active){
  .btn{border:1px solid ButtonText}
  .menu-btn span{background:ButtonText; forced-color-adjust:none}
}
@media print{
  .js-rv :is(__REVEAL__){opacity:1!important; transform:none!important; transition:none!important}
  .mcta,.menu-btn{display:none!important}
}
@media (prefers-reduced-motion:reduce){
  .js-rv :is(__REVEAL__){opacity:1; transform:none; transition:none}
  .faq-item::details-content{transition:none}
  html.nav-open body::after{animation:none}
}
"""

# Elemente, die beim Hinscrollen einmalig dezent einblenden: EINE Liste für CSS (Startzustand) und JS (Auslöser).
# Wer die Liste ändert, ändert sie nur hier. Das Porträt im Hero gehört nicht dazu (nur Zoom, kein Einblenden).
REVEAL = ", ".join([
    ".sec-head", ".glance-card", ".spec", ".metal", ".mtable", ".steps li", ".timeline li", ".flow > div",
    ".care > div", ".care li", ".check", ".media", "div.callnow", "section.callnow .wrap > *", ".about > *",
    ".faq", ".contact-grid > *", ".contact-card", ".statement", ".cols > div", ".mech-text > div"])
SHARED_CSS = SHARED_CSS.replace("__REVEAL__", REVEAL)

# Steht im <head> VOR dem Font-Stylesheet (ein Inline-Skript hinter einem noch ladenden Stylesheet hält den Parser an):
# js = JavaScript an, js-rv = Einblenden aktiv (nicht bei "Bewegung reduzieren"). Läuft SCRIPTS nicht durch
# (Fehler), nimmt DOMContentLoaded js-rv wieder weg: dann ist alles sofort sichtbar.
MOTION_HEAD = ("<script>(function(d,w){d.classList.add('js');if('IntersectionObserver' in w&&!(w.matchMedia&&"
               "w.matchMedia('(prefers-reduced-motion: reduce)').matches)){d.classList.add('js-rv');"
               "document.addEventListener('DOMContentLoaded',function(){if(!w.__rv)d.classList.remove('js-rv')})}}"
               ")(document.documentElement,window)</script>")

# Zeichenbereich der Google-Latin-Schnitte. Die metrisch angepassten Ersatzschriften (@font-face "... Fallback"
# in den Templates, Werte aus _src/schriften.mjs) gelten nur hier; andere Zeichen (z. B. Pfeile) nehmen wie bisher
# die Systemschrift.
LATIN = ("U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, "
         "U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD")

# Gemeinsames Verhalten (am Ende von <body>):
#  - Handy (grober Zeiger und schmal ODER niedrig): [data-tel] wird zum Anruf-Link, mit Screenreader-Zusatz
#  - feiner Zeiger (Maus): .js-call kopiert die Nummer (role=button, Leertaste, Statusmeldung), Fallback tel:
#  - Menü (.menu-btn / #nav-main): Fokus ins Menü, Escape zurück zum Button, Klick außerhalb, Fokus verlässt den
#    Header, Größenänderung; aria-expanded; --nav-max
#  - Handy-Leiste .mcta: sichtbar, solange weder .hero .cta-row noch [data-mcta-hide] noch footer.site im Bild ist
#    (ein von der Leiste oder von einer festen Kopfzeile verdeckter Teil zählt nicht)
#  - Aktiver Menüpunkt: aria-current="location" am Link des Abschnitts in der Lesezeile (40 % der Fensterhöhe);
#    Abschnitte ohne eigenen Menüpunkt lassen keinen aktiv. Aussehen je Entwurf im CSS
#  - header.site bekommt .scrolled, sobald mehr als data-scrolled px (Standard 10) gescrollt ist (IntersectionObserver)
#  - Einblenden: setzt .in an Elementen aus REVEAL (Startzustand macht das CSS über html.js-rv aus MOTION_HEAD),
#    Bilder darin werden eine Bildschirmhöhe vorher geladen und dekodiert
#  - [data-zoom] (Hero-Porträt A/C) bekommt .go, sobald das Foto dekodiert und zu 20 % sichtbar ist
#  - Klick-Tracking (nur mit ANALYTICS_DOMAIN)
SCRIPTS = """<script>
(function () {
  var root = document.documentElement, IO = 'IntersectionObserver' in window;
  var mq = function (q) { return !!(window.matchMedia && matchMedia(q).matches); };
  var fine = mq('(hover: hover) and (pointer: fine)');
  var phone = mq('(pointer: coarse) and (max-width: 640px), (pointer: coarse) and (max-height: 500px)');
  var NUM = '__NUM__';
  function where(el) {
    if (el.closest('.mcta')) return 'Mobil-Leiste';
    if (el.closest('header')) return 'Header';
    if (el.closest('.strip')) return 'Topbar';
    if (el.closest('footer')) return 'Footer';
    var s = el.closest('section');
    return s ? (s.id || (s.classList.contains('hero') ? 'Hero' : 'Seite')) : 'Seite';
  }
  function track(name, el) { if (window.plausible) window.plausible(name, { props: { Bereich: where(el) } }); }

  // Handy: "Kostenloses Erstgespräch" ruft direkt an, Screenreader hören das mit. Tablet/Desktop: Sprung zum Abschnitt.
  if (phone) document.querySelectorAll('[data-tel]').forEach(function (a) {
    a.href = a.getAttribute('data-tel');
    a.insertAdjacentHTML('beforeend', '<span class="vh">, Anruf starten</span>');
  });
  // Maus: Anruf-Buttons kopieren die Nummer (die Nummer steht groß daneben). Schlägt das fehl: normaler tel:-Link.
  if (fine && navigator.clipboard && navigator.clipboard.writeText) {
    var live = document.createElement('p');
    live.className = 'vh'; live.setAttribute('role', 'status');
    document.body.appendChild(live);
    document.querySelectorAll('.js-call').forEach(function (a) {
      var t = a.querySelector('.t'), label = 'Nummer kopieren', tm;
      if (t) t.textContent = label;
      a.setAttribute('role', 'button');
      function copy(e) {
        e.preventDefault();
        navigator.clipboard.writeText(NUM).then(function () {
          if (t) { t.innerHTML = 'Kopiert <span aria-hidden="true">\\u2713</span>'; clearTimeout(tm); tm = setTimeout(function () { t.textContent = label; }, 2200); }
          live.textContent = 'Telefonnummer ' + NUM + ' wurde kopiert.';
          setTimeout(function () { live.textContent = ''; }, 4000);
        }, function () { location.href = a.getAttribute('href'); });
        track('Nummer kopiert', a);
      }
      a.addEventListener('click', copy);
      a.addEventListener('keydown', function (e) { if (e.key === ' ' || e.key === 'Spacebar') copy(e); });
    });
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a || a.getAttribute('role') === 'button') return;
    var h = a.getAttribute('href') || '';
    if (h.indexOf('tel:') === 0) track('Anruf', a);
    else if (h.indexOf('doctolib') > -1) track('Termin Doctolib', a);
    else if (h.indexOf('mailto:') === 0) track('E-Mail', a);
    else if (h === '#erstgespraech') track('Zum Erstgespräch', a);
  });

  // Menü (Tablet/Handy): Fokus ins Menü, Escape gibt ihn an den Button zurück, Klick daneben oder Fokus
  // außerhalb des Headers schließt, beim Wechsel auf die Desktop-Ansicht geht es zu
  var mb = document.querySelector('.menu-btn'), nav = document.getElementById('nav-main'), hdr = document.querySelector('header.site');
  function isOpen() { return root.classList.contains('nav-open'); }
  function navMax() { nav.style.setProperty('--nav-max', Math.max(160, Math.floor(innerHeight - hdr.getBoundingClientRect().bottom)) + 'px'); }
  function menu(open, zurueck) {
    if (open === isOpen()) return;
    root.classList.toggle('nav-open', open);
    mb.setAttribute('aria-expanded', String(open));
    if (open) {
      navMax(); nav.scrollTop = 0;
      var first = [].filter.call(nav.querySelectorAll('a'), function (a) { return a.getClientRects().length > 0; })[0];
      if (first) first.focus({ preventScroll: true });
    } else if (zurueck) mb.focus({ preventScroll: true });
  }
  if (mb && nav && hdr) {
    mb.addEventListener('click', function () { menu(!isOpen()); });
    [].forEach.call(hdr.querySelectorAll('nav.main a, .brand'), function (a) { a.addEventListener('click', function () { menu(false); }); });
    document.addEventListener('keydown', function (e) { if ((e.key === 'Escape' || e.key === 'Esc') && isOpen()) { e.preventDefault(); menu(false, true); } });
    document.addEventListener('click', function (e) { if (isOpen() && !hdr.contains(e.target)) menu(false); });
    hdr.addEventListener('focusout', function (e) { if (isOpen() && e.relatedTarget && !hdr.contains(e.relatedTarget)) menu(false); });
    addEventListener('resize', function () { if (!isOpen()) return; if (getComputedStyle(mb).display === 'none') menu(false); else navMax(); });
  }

  // Aktiver Menüpunkt: aria-current="location" am Link des Abschnitts, der durch die Lesezeile bei 40 % der
  // Fensterhöhe läuft (Desktop-Navigation und Menü). Abschnitte ohne eigenen Menüpunkt lassen keinen Punkt aktiv.
  if (IO && nav) {
    var zuLinks = {}, aktiv = null, inZeile = [];
    [].forEach.call(nav.querySelectorAll('a[href^="#"]'), function (a) {
      var id = a.getAttribute('href').slice(1);
      if (id && document.getElementById(id)) (zuLinks[id] = zuLinks[id] || []).push(a);
    });
    var setze = function (id) {
      if (id === aktiv) return;
      if (aktiv) zuLinks[aktiv].forEach(function (a) { a.removeAttribute('aria-current'); });
      aktiv = id;
      if (aktiv) zuLinks[aktiv].forEach(function (a) { a.setAttribute('aria-current', 'location'); });
    };
    var spy = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        var i = inZeile.indexOf(e.target);
        if (e.isIntersecting) { if (i < 0) inZeile.push(e.target); } else if (i > -1) inZeile.splice(i, 1);
      });
      var s = inZeile[inZeile.length - 1];
      setze(s && zuLinks[s.id] ? s.id : null);
    }, { rootMargin: '-40% 0px -59% 0px' });
    [].forEach.call(document.querySelectorAll('section'), function (s) { spy.observe(s); });
  }

  // Handy-Leiste: nur zeigen, solange kein eigener Anruf-/Termin-Bereich im Bild ist. Beobachtet werden die Buttons
  // im Hero, alles mit data-mcta-hide und der Footer. Der Streifen unter der Leiste zählt nicht als sichtbar, ebenso
  // wenig der Streifen hinter einer festen Kopfzeile (sonst bleibt beim Hochschieben der Hero-Buttons eine Lücke).
  var bar = document.querySelector('.mcta');
  if (bar) {
    if (!IO) root.classList.add('mcta-on');
    else {
      var ziele = document.querySelectorAll('.hero .cta-row, [data-mcta-hide], footer.site'), barIO, rt;
      var watch = function () {
        if (barIO) barIO.disconnect();
        var cs = getComputedStyle(bar), zone = bar.offsetHeight ? Math.round(bar.offsetHeight + (parseFloat(cs.bottom) || 0)) : 0;
        var hp = hdr ? getComputedStyle(hdr).position : '', oben = hp === 'sticky' || hp === 'fixed' ? hdr.offsetHeight : 0;
        var seen = [];
        barIO = new IntersectionObserver(function (es) {
          es.forEach(function (e) {
            var i = seen.indexOf(e.target);
            if (e.isIntersecting) { if (i < 0) seen.push(e.target); } else if (i > -1) seen.splice(i, 1);
          });
          root.classList.toggle('mcta-on', seen.length === 0);
        }, { rootMargin: '-' + oben + 'px 0px -' + zone + 'px 0px' });
        [].forEach.call(ziele, function (el) { barIO.observe(el); });
      };
      watch();
      addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(watch, 250); });
    }
  }

  // Kopfzeile: .scrolled per IntersectionObserver auf einen unsichtbaren Streifen oben (kein Scroll-Listener)
  if (hdr) {
    if (IO) {
      var sen = document.createElement('div');
      sen.setAttribute('aria-hidden', 'true');
      sen.style.cssText = 'position:absolute;left:0;top:0;width:1px;height:' + (parseInt(hdr.getAttribute('data-scrolled'), 10) || 10) + 'px;visibility:hidden;pointer-events:none';
      document.body.insertBefore(sen, document.body.firstChild);
      new IntersectionObserver(function (es) { hdr.classList.toggle('scrolled', !es[es.length - 1].isIntersecting); }).observe(sen);
    } else hdr.classList.add('scrolled');
  }

  // Dezentes Einblenden beim Scrollen (einmalig). Startzustand: CSS über html.js-rv (MOTION_HEAD im <head>), hier nur
  // der Auslöser. Bilder im Block werden eine Bildschirmhöhe vorher geladen und dekodiert, damit sie nicht mitten im
  // Einblenden erscheinen. Verschachtelte Treffer kommen mit dem äußeren Block.
  var wait = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var decode = function (im) {  // lädt ein lazy-Bild sofort und wartet auf die Dekodierung
    if (im.loading === 'lazy') im.loading = 'eager';
    return im.decode ? im.decode().catch(function () {}) : Promise.resolve();
  };
  if (root.classList.contains('js-rv')) {
    window.__rv = true;   // Sicherheitsnetz in MOTION_HEAD: ohne diese Zeile nimmt DOMContentLoaded js-rv wieder weg
    var RV = '__REVEAL__';
    var pre = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { pre.unobserve(e.target); [].forEach.call(e.target.querySelectorAll('img'), decode); } });
    }, { rootMargin: '0px 0px 100% 0px' });
    var rv = new IntersectionObserver(function (es) {
      var n = 0;
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target, d = Math.min(n++, 4) * 80, imgs = [].map.call(el.querySelectorAll('img'), decode);
        rv.unobserve(el);
        Promise.race([Promise.all(imgs), wait(400)]).then(function () {
          requestAnimationFrame(function () { if (d) el.style.transitionDelay = d + 'ms'; el.classList.add('in'); });
        });
      });
    }, { rootMargin: '0px 0px -5% 0px', threshold: 0.06 });
    [].forEach.call(document.querySelectorAll(RV), function (el) {
      if (el.parentElement && el.parentElement.closest(RV)) return;   // verschachtelt: kommt mit dem äußeren Block
      rv.observe(el); pre.observe(el);
    });
    document.addEventListener('transitionend', function (e) {  // Verzögerung nach dem Einblenden wieder entfernen
      var t = e.target; if (e.propertyName === 'transform' && t.classList && t.classList.contains('in')) t.style.transitionDelay = '';
    });
    // Porträt im Hero (data-zoom): sanfter Zoom erst, wenn das Foto dekodiert (höchstens 2,5 s) und zu 20 % zu sehen ist.
    // Die Templates pausieren die Animation bis dahin (.js-rv [data-zoom]:not(.go) ... animation-play-state:paused).
    var hz = document.querySelector('[data-zoom]'), him = hz && hz.querySelector('img');
    if (him) Promise.all([
      Promise.race([decode(him), wait(2500)]),
      new Promise(function (r) {
        var o = new IntersectionObserver(function (es) { if (es[es.length - 1].isIntersecting) { o.disconnect(); r(); } }, { threshold: 0.2 });
        o.observe(hz);
      })
    ]).then(function () { requestAnimationFrame(function () { hz.classList.add('go'); }); });
  }
})();
</script>""".replace("__NUM__", PHONE_DE).replace("__REVEAL__", REVEAL)

# ---------------------------------------------------------------------------
# Bilder: Varianten (bilder.py), srcset und echte Maße
# ---------------------------------------------------------------------------
_BILDER = {}

def bild(pfad):
    """Größte Variante unter pfad, kleinere als <name>-<breite>.webp daneben. Liefert src, w, h, srcset, varianten."""
    if pfad in _BILDER:
        return _BILDER[pfad]
    from PIL import Image
    p = ROOT / pfad
    if not p.exists():
        raise BuildFehler(f"Bild fehlt: {pfad}")
    with Image.open(p) as im:
        W, H = im.size
    var = [(W, pfad)]
    for b in BREITEN:
        if b >= W:
            continue
        vp = p.with_name(f"{p.stem}-{b}{p.suffix}")
        rel = vp.relative_to(ROOT).as_posix()
        if not vp.exists():
            print(f"Hinweis: {rel} fehlt, srcset ohne {b}w (python _src/bilder.py)")
            continue
        with Image.open(vp) as im:
            w, h = im.size
        if w != b or abs(h / w - H / W) > 0.01:
            print(f"Hinweis: {rel} ({w}x{h}) passt nicht zu {pfad} ({W}x{H}), nicht im srcset")
            continue
        var.append((w, rel))
    var.sort()
    info = {"src": pfad, "w": W, "h": H, "varianten": len(var),
            "srcset": ", ".join(f"{s} {w}w" for w, s in var)}
    _BILDER[pfad] = info
    return info

def bild_werte():
    v = {}
    for k, pfad in IMAGES.items():
        i = bild(pfad)
        v.update({k: i["src"], f"{k}_SRCSET": i["srcset"], f"{k}_W": str(i["w"]), f"{k}_H": str(i["h"])})
    i = bild(PORTRAIT)
    v.update({"PORTRAIT": i["src"], "PORTRAIT_JPG": PORTRAIT_JPG, "PORTRAIT_SRCSET": i["srcset"],
              "PORTRAIT_W": str(i["w"]), "PORTRAIT_H": str(i["h"])})
    return v

BILDTYP = {".webp": "image/webp", ".avif": "image/avif", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}

def preload_link(preload):
    """<link rel=preload> für das Bild im ersten Bildschirm (Angaben aus dem Build-Block). Eine Variante: href,
    mehrere: imagesrcset/imagesizes, damit der Browser dieselbe Datei wählt wie am Bild. Immer fetchpriority=high."""
    if not preload:
        return ""
    info = bild(preload["href"])
    typ = BILDTYP.get(pathlib.Path(info["src"]).suffix.lower())
    attr = (f' type="{typ}"' if typ else "") + ' fetchpriority="high"'
    if preload.get("media"):
        attr += f' media="{html.escape(preload["media"])}"'
    if info["varianten"] > 1:
        if not preload.get("sizes"):
            raise BuildFehler(f'{preload["href"]} hat {info["varianten"]} Breiten: im Build-Block fehlt "sizes" für den Preload')
        return f'<link rel="preload" as="image" imagesrcset="{info["srcset"]}" imagesizes="{html.escape(preload["sizes"])}"{attr}>\n'
    return f'<link rel="preload" as="image" href="{info["src"]}"{attr}>\n'

# ---------------------------------------------------------------------------
# Build: Build-Block lesen, Platzhalter füllen, schreiben
# ---------------------------------------------------------------------------
# Template -> Ausgabe. Alles Weitere (Schriften, theme-color, Preload) steht im Build-Block des Templates.
DESIGNS = {
    "entwurf-a.src.html": "entwurf-a-salbei.html",
    "entwurf-b.src.html": "entwurf-b-klarheit.html",
    "entwurf-c.src.html": "entwurf-c-stille.html",
}

BLOCK = re.compile(r"[ \t]*<!--build\s(.*?)-->[ \t]*(?:\r?\n)?", re.S)

def build_block(t, name):
    bl = BLOCK.findall(t)
    if len(bl) != 1:
        raise BuildFehler(f"{name}: {'kein' if not bl else 'mehr als ein'} Build-Block <!--build {{...}} --> im Template")
    m = BLOCK.search(t)
    try:
        cfg = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise BuildFehler(f"{name}: Build-Block ist kein gültiges JSON ({e})")
    if not isinstance(cfg.get("theme"), str) or not cfg["theme"]:
        raise BuildFehler(f'{name}: Build-Block braucht "theme"')
    if not isinstance(cfg.get("fonts"), str):
        raise BuildFehler(f'{name}: Build-Block braucht "fonts" (Google-Fonts-URL, "" bei lokalen Schriften)')
    sch = cfg.setdefault("schriften", [])
    if not (isinstance(sch, list) and all(isinstance(s, str) and s.endswith(".woff2") for s in sch)):
        raise BuildFehler(f'{name}: "schriften" muss eine Liste von .woff2-Pfaden sein, z. B. ["fonts/x.woff2"]')
    fehlt = [s for s in sch if not (ROOT / s).is_file()]
    if fehlt:
        raise BuildFehler(f"{name}: Schriftdatei fehlt: {', '.join(fehlt)}")
    pre = cfg.get("preload")
    if pre is not None and not (isinstance(pre, dict) and pre.get("href")):
        raise BuildFehler(f'{name}: "preload" muss null oder {{"href": ..., "media": ..., "sizes": ...}} sein')
    return cfg, t[:m.start()] + t[m.end():]

def werte():
    """Alle einfachen Platzhalter für die Templates: Stammdaten aus stammdaten.werte() (reiner Text, Liste dort),
    dazu HINWEIS HTML-maskiert, LATIN und die Bildwerte. HEAD, FAQ und SCRIPTS kommen je Entwurf dazu."""
    v = S.werte()
    v.update(HINWEIS=html.escape(S.HINWEIS, quote=False), LATIN=LATIN,
             STREET_NB=STREET_NB)
    v.update(bild_werte())
    return v

def schreibe(ziel, text):
    """Erst in eine eigene Zwischendatei, dann umbenennen: parallele Builds und laufende Prüfungen sehen nie
    eine halb geschriebene Seite."""
    tmp = ziel.with_name(f".{ziel.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for versuch in range(20):
        try:
            os.replace(tmp, ziel); return
        except PermissionError:      # Windows: Datei wird gerade gelesen
            import time; time.sleep(0.1)
    os.replace(tmp, ziel)

def seite(src, modus="entwurf"):
    """Füllt ein Template, ohne etwas zu schreiben. Gibt (HTML, Build-Block) zurück. Der Release nutzt das direkt."""
    p = SRC / src
    if not p.exists():
        raise BuildFehler(f"Template fehlt: {src}")
    cfg, t = build_block(p.read_text(encoding="utf-8"), src)
    pre = cfg.get("preload")
    if pre and pre.get("sizes") and f'sizes="{pre["sizes"]}"' not in t:
        raise BuildFehler(f'{src}: Preload-sizes "{pre.get("sizes")}" steht an keinem Bild im Template '
                          "(Bild und Preload müssen dieselben sizes haben, sonst lädt es doppelt)")
    v = werte()
    v.update(HEAD=head(cfg["fonts"], cfg["theme"], pre, modus, cfg["schriften"]), FAQ=faq_html(), SCRIPTS=SCRIPTS)
    return fill(t, v, src), cfg

def baue(src, out):
    """Entwurf bauen (modus "entwurf") und in den Projektordner schreiben."""
    html_, cfg = seite(src)
    schreibe(ROOT / out, html_)
    return html_, cfg

AUFRUF_RELEASE = "Aufruf: python _src/build.py release a|b|c [--probe] [--ziel ordner]"

def baue_release(args, kuerzel):
    """release a|b|c [--probe] [--ziel ordner]: Seite im Modus release bzw. probe füllen, seo.release baut und prüft."""
    probe, ziel, wahl, i = False, None, [], 0
    while i < len(args):
        a = args[i]
        if a == "--probe":
            probe = True
        elif a == "--ziel":
            if i + 1 >= len(args):
                sys.exit(AUFRUF_RELEASE)
            ziel = args[i + 1]
            i += 1
        elif a.startswith("--"):
            sys.exit(f"Unbekannte Option {a}. {AUFRUF_RELEASE}")
        else:
            wahl.append(a.lower())
        i += 1
    if len(wahl) != 1 or wahl[0] not in kuerzel:
        sys.exit(AUFRUF_RELEASE)
    html_, cfg = seite(kuerzel[wahl[0]][0], "probe" if probe else "release")
    seo.release(wahl[0], html_, cfg["theme"], probe=probe, ziel=ziel)

def main(args):
    kuerzel = {src.split("-")[1][0]: (src, out) for src, out in DESIGNS.items()}   # a, b, c
    try:
        if args[:1] == ["release"]:
            baue_release(args[1:], kuerzel)
            return
        wahl = [a.lower() for a in args]
        falsch = [a for a in wahl if a not in kuerzel]
        if falsch:
            sys.exit(f"Unbekannt: {' '.join(falsch)}. Erlaubt: {' '.join(kuerzel)} (ohne Angabe: alles) "
                     "oder release a|b|c [--probe] [--ziel ordner]")
        gebaut = {}
        for k in (dict.fromkeys(wahl) or kuerzel):
            src, out = kuerzel[k]
            gebaut[k] = baue(src, out)
            print("geschrieben:", out)
        if not wahl:        # nur beim Komplett-Build: gemeinsame Dateien (H1 und Bilder aus Entwurf A), mit Selbsttest
            html_a, cfg_a = gebaut["a"]
            seo.seo_dateien(ROOT, html_a, "entwurf", theme=cfg_a["theme"])
            print("geschrieben: robots.txt, llms.txt, sitemap.xml, index.md, site.webmanifest")
    except BuildFehler as e:
        sys.exit("Build abgebrochen: " + str(e))

if __name__ == "__main__":
    main(sys.argv[1:])
