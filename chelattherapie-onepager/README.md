# Onepager Chelattherapie Berlin (Heilpraxis Nina Klimek)

Stand: 01.10.2026 · nur lokal, noch nicht veröffentlicht

## Inhalt des Ordners

| Datei | Zweck | geht live? |
|---|---|---|
| `index.html` | Vergleichsseite der 3 Entwürfe, nur zum Zeigen (noindex, von Hand gepflegt) | **nein** (der Release schreibt den gewählten Entwurf als `index.html` nach `_release/`) |
| `entwurf-a-salbei.html` | Entwurf A: warm, editorial, Salbeigrün | nur über den Release |
| `entwurf-b-klarheit.html` | Entwurf B: modern, klinisch, Petrol | ″ |
| `entwurf-c-stille.html` | Entwurf C: dunkel, premium, Gold | ″ |
| `robots.txt`, `llms.txt`, `sitemap.xml`, `index.md`, `site.webmanifest` | erzeugt beim Komplett-Build, im Projektordner nur zur Ansicht | über den Release |
| `favicon.svg`, `favicon.ico`, `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` | Icons (die PNG/ICO erzeugt `_src/icons.py` aus `favicon.svg`) | über den Release |
| `assets/` | Porträt (WebP + JPG), Bilder im Text, Social-Media-Vorschaubild | nur was die Seite wirklich nutzt, über den Release |
| `_src/` | Build (`build.py`), Stammdaten (`stammdaten.py`), SEO und Release (`seo.py`), Templates, Vorlagen, Bild-Zuschnitt (`bilder.py`), Prüfwerkzeuge (`pruefen.mjs`, `schriften.mjs`), Vorschaubilder (`vorschau.py`) | nein |
| `_release/` | entsteht erst mit `python _src/build.py release …`: der **einzige** Upload-Ordner | ja, nur sein Inhalt |
| `assets/_roh/` | Rohfotos vor dem Zuschnitt | nein |
| `vorschau/` | Vorschaubilder der Vergleichsseite (`a-desktop.jpg`, `a-handy.jpg` usw., erzeugt mit `_src/vorschau.py`) | nein |
| `_sicherung/` | Stand vor dem Feinschliff | nein |

**Hinweis zur „robots.md“:** Eine Datei mit diesem Namen gibt es nicht als Standard. Für die KI-Optimierung sind **`llms.txt`** (Zusammenfassung für Sprachmodelle) und **`robots.txt`** (Zugriffsfreigabe für KI-Crawler) gebräuchlich. Beide werden erzeugt, dazu die Markdown-Version `index.md`.

## Lokal ansehen

```bash
python -m http.server 8741
```
Danach im Browser http://localhost:8741 öffnen.

## Texte ändern und bauen

Alle Werte stehen an **einer** Stelle: `_src/stammdaten.py` (Domain, Datum, Praxis und Adresse, Telefon, Links, Titel und Beschreibung, FAQ, Pflichthinweis, Bildpfade, Go-live-Schalter). Meta-Tags, strukturierte Daten (JSON-LD), robots.txt, llms.txt, sitemap.xml und index.md baut `_src/seo.py` daraus. Die Seitentexte stehen in `_src/entwurf-*.src.html`. Nach jeder Änderung neu bauen:

```bash
python _src/build.py        # alle Entwürfe + robots.txt, llms.txt, sitemap.xml, index.md, site.webmanifest
python _src/build.py b      # nur Entwurf B (schreibt nur diese eine Datei, mehrere Builds parallel sind sicher)
python _src/icons.py        # nur nach einer Änderung an favicon.svg
```

Die gebauten `entwurf-*.html` und die erzeugten SEO-Dateien nie direkt bearbeiten. Bleibt in einem Template oder einer Vorlage ein Platzhalter `{{…}}` stehen oder ist er unbekannt, bricht der Build mit Meldung ab. Der Komplett-Build prüft die SEO-Dateien danach selbst (siehe unten) und bricht bei einem Fehler ebenfalls ab.

Die Entwürfe im Projektordner tragen immer `noindex, nofollow` und kein Canonical. Werden sie auf einer Vorschau-Adresse gezeigt, landen sie also nicht bei Google. Erst der Release setzt `index, follow` und das Canonical.

### Aufbau der Templates (für alle, die an den Entwürfen arbeiten)

- **Build-Block** im `<head>` direkt vor `{{HEAD}}`: Schriften-URL, `theme-color` und das Vorladen des Hero-Bilds je Entwurf, als JSON in einem Kommentar `<!--build {…} -->`. Er wird beim Bauen gelesen und entfernt. A lädt das Porträt erst ab 641 px vor (auf dem Handy liegt es unter dem ersten Bildschirm, darum trägt das Bild selbst kein `fetchpriority`), B gar nicht (Porträt erst bei „Über mich“), C immer. Sobald die Schriften lokal liegen, wird `"fonts"` zu `""`, und `"schriften": ["fonts/….woff2"]` lädt die wichtigsten Schnitte vor (siehe Pflicht 5).
- **Platzhalter** für Stammdaten, alle aus `stammdaten.werte()`: Kontakt (`{{PHONE_DE}}`, `{{EMAIL}}`, `{{DOCTOLIB}}` …), Adresse (`{{PRAXIS}}`, `{{STREET}}`, `{{ZIP}}`, `{{CITY}}`, `{{DISTRICT}}` …; `{{STREET_NB}}` ist die Straße mit geschütztem Leerzeichen vor der Hausnummer), Links (`{{IMPRESSUM}}`, `{{DATENSCHUTZ}}`), der Pflichthinweis `{{HINWEIS}}`, das Datum `{{UPDATED_DE}}` (wird aus `UPDATED` abgeleitet) und `{{GEPRUEFT}}`. Letzteres ergibt „ und geprüft“ erst, wenn in `stammdaten.py` bei `REVIEWED` ein Datum steht, also nach Ninas Freigabe. Bis dahin heißt es im Footer nur „Inhaltlich verantwortlich“. Die vollständige Liste steht im Kopf von `_src/build.py`.
- **Bilder** über `{{IMG_…}}`, `{{IMG_…_SRCSET}}`, `{{IMG_…_W}}`, `{{IMG_…_H}}` sowie `{{PORTRAIT…}}`: Dateien, Breitenstufen und echte Maße kommen aus den Bilddateien. Das `sizes`-Attribut steht im Template und gehört zum Layout.
- **Schriften:** Jeder Entwurf hat metrisch angepasste Ersatzschriften (Block `schriften:start … schriften:ende`), damit beim Nachladen der Webfonts nichts springt. Werte nie von Hand ändern, sondern messen lassen: `node _src/schriften.mjs entwurf-a-salbei.html --schreiben`, danach neu bauen. Gemessen: Layout-Sprung (CLS) vorher bis 0,30 (B, 1024 px), jetzt unter 0,01 auf allen Breiten, auch bei Slow 4G (audit 01.10.: höchstens 0,0039).

## Release: der Upload-Ordner

```bash
python _src/build.py release b                  # Go-live: _release/ aus Entwurf B
python _src/build.py release b --probe          # Test-Hosting: noindex, robots.txt sperrt alles, Platzhalter-Domain erlaubt
python _src/build.py release b --ziel <ordner>  # anderer Zielordner: außerhalb des Projekts oder im Projekt mit Namen _release…
```

Der Release nimmt den gewählten Entwurf und

- kopiert nur, was die Seite wirklich braucht (Bilder aus `src`/`srcset`, Icons, og-Bild). README, `_src/`, die Entwürfe, `_roh`, Platzhalter- und ungenutzte Bilder bleiben draußen,
- hängt `?v=<Prüfsumme>` an alle Bilder und Schriften (darum dürfen sie ein Jahr im Browser-Cache liegen, ein geändertes Bild bekommt automatisch eine neue Adresse),
- schreibt `index.html`, `404.html`, robots.txt, llms.txt, sitemap.xml, index.md, `site.webmanifest`, dazu `_headers` (Netlify, Cloudflare Pages) und `.htaccess` (Apache),
- prüft danach alles selbst: keine Platzhalter, keine Gedankenstriche im Text, JSON-LD lesbar, jede FAQ-Sprungmarke vorhanden, robots.txt mit genau einer Gruppe, index.md mit gültigem Kopf, `index, follow` und Canonical nur im echten Release, CSP passt zu den Skripten, Icons in der richtigen Größe, nur erlaubte Dateien.

**Hochladen nur, wenn am Ende „Release OK“ steht**, und dann nur den *Inhalt* von `_release/`. Bei einem Fehler liegt `FEHLER-NICHT-HOCHLADEN.txt` im Ordner. Dateien, die kein Release erzeugt hat, löscht der Build nie: Er bricht ab und nennt sie. Wer ein Bild unter gleichem Namen austauscht, leert `_release/` einmal selbst.

Ohne `--probe` bricht der Release ab, solange `DOMAIN` der Platzhalter ist, in `FREIGABEN` etwas auf `False` steht oder die Schriften noch von Google kommen. Warnungen (etwa Vorschaubilder mit ungeklärten Rechten, leeres `HOSTING`) stehen in der Ausgabe.

## SEO-Dateien und Server-Header

| Datei | Quelle | Zweck |
|---|---|---|
| `_src/stammdaten.py` | von Hand | alle Werte, einmal |
| `_src/seo.py` | von Hand | head, JSON-LD, SEO-Dateien, Release mit Selbsttest |
| `_src/robots.src.txt`, `llms.src.txt`, `sitemap.src.xml`, `index.src.md` | von Hand | Vorlagen mit `{{PLATZHALTERN}}`, Domain und Kontakt stehen nicht darin |
| robots.txt, llms.txt, sitemap.xml, index.md | erzeugt | im Projektordner nur zur Ansicht, live über den Release |

**robots.txt:** eine einzige Gruppe: `User-agent: *` und alle benannten Suchmaschinen und KI-Bots direkt untereinander, ohne Leerzeile, darunter eine gemeinsame Regel. Grund: Nach RFC 9309 folgt ein Bot nur der Gruppe mit seinem Namen und ignoriert dann `*`. In der alten Datei hatte jeder Bot eine eigene Gruppe, dadurch galten die Sperren für `/_src/` und `/vorschau/` für Googlebot, GPTBot und Co. gar nicht (nachgeprüft mit einem RFC-9309-Auswerter). Interne Ordner stehen gar nicht mehr darin, sie werden nicht hochgeladen. `Content-Signal: search=yes, ai-input=yes`; zu `ai-train` bewusst keine Angabe, bis die Bildrechte geklärt sind. Im Probe-Release steht `Disallow: /` für alle.

**llms.txt:** nach llmstxt.org: Überschrift, Kurzbeschreibung als Zitat, Pflichthinweis, Stand und Quelle, dann die Fakten als Liste, Überschriften nur vor Linklisten. Eine llms-full.txt gibt es bewusst nicht (wäre die dritte Kopie desselben Texts).

**index.md:** der ganze Seitentext als Markdown mit gültigem Kopf (alle Werte in Anführungszeichen, `yaml.safe_load` liest ihn), Pflichthinweis gleich oben, alle 13 Fragen. Die Überschrift ist die H1 des gewählten Entwurfs. „geprueft“ steht erst darin, wenn `REVIEWED` gesetzt ist.

**sitemap.xml:** nur die Startseite mit `lastmod` = `UPDATED`, dazu die Bilder der Seite (je Bild die größte Variante, im Release mit denselben `?v`-Adressen wie im HTML). Ohne `changefreq` und `priority`, die Google und Bing ignorieren.

**Server-Header** (`_headers` bzw. `.htaccess`, beide erzeugt):

- Sicherheit: HSTS, `nosniff`, Referrer-Policy, Permissions-Policy, `X-Frame-Options`, Content-Security-Policy. Die CSP erlaubt nur die eigenen Inline-Skripte über ihre Prüfsummen; Google-Domains stehen nur darin, solange die Schriften noch von Google kommen.
- `index.md` wird als `text/markdown` ausgeliefert, mit `Link: rel="canonical"` auf die Startseite. llms.txt, sitemap.xml und 404.html bekommen `X-Robots-Tag: noindex`, damit sie nicht selbst in den Suchergebnissen stehen. Im Probe-Release gilt `noindex, nofollow` für alles.
- Cache: HTML immer frisch, Bilder und Schriften ein Jahr (dank `?v`), Icons eine Woche, Textdateien eine Stunde.
- `.htaccess` leitet auf https und die eine Domain um, `/index.html` auf `/`, und liefert interne Dateien nie aus, falls sie doch hochgeladen werden. Antwortet Apache mit Fehler 500, die Zeile `Options -Indexes` herausnehmen.
- Welche Datei gebraucht wird, legt `HOSTING` in `stammdaten.py` fest (`"apache"` oder `"pages"`). Leer liegen beide im Release, mit Warnung.

**Strukturierte Daten:** WebSite, MedicalWebPage, MedicalBusiness (mit Angebot „Chelattherapie“ und ReserveAction über Doctolib), Person (Heilpraktikererlaubnis, Verband), MedicalTherapy, FAQPage (13 Fragen, jede mit Sprungmarke `#faq-…`, dieselbe id wie im sichtbaren FAQ). Keine BreadcrumbList, kein speakable, keine geo-Meta-Tags, kein hreflang. `reviewedBy`/`lastReviewed` und `datePublished` erscheinen erst, wenn `REVIEWED` bzw. `PUBLISHED` gesetzt sind; `GEO`, `OPENING_HOURS`, `GBP_URL` und `LOGO` erst mit echten Werten. FAQ-Rich-Results zeigt Google seit Mai 2026 nicht mehr an; das Markup bleibt für andere Systeme. Nebenwirkungen stehen nur im sichtbaren FAQ, nicht als Schema. Im Release ist das JSON-LD ohne Einrückung, also rund ein Fünftel kleiner.

**Hosting:** nicht auf dem Heimserver (robots.txt muss immer mit 200 oder 404 antworten, bei Serverfehlern gilt alles als gesperrt, und ein Ausfall zu Hause träfe die Praxis). Bei Cloudflare „Block AI bots“ auf „Do not block“ und „Managed robots.txt“ aus, danach mit `curl -s https://DOMAIN/robots.txt` prüfen.

**IndexNow (optional, nur von Hand):** `INDEXNOW_KEY` setzen (8 bis 128 Zeichen aus a-z, A-Z, 0-9, -), dann legt der Release `<KEY>.txt` ab. Nach dem Upload einmal im Browser aufrufen:
`https://api.indexnow.org/indexnow?url=https://DOMAIN/&key=<KEY>` (Bing, Yandex, Seznam, Naver; Google nimmt nicht teil). Liegt die Domain bei Cloudflare, geht es auch über „Crawler Hints“.

## Was an SEO und KI-Optimierung eingebaut ist

- **Title** (62 Zeichen) und **Description** (149 Zeichen) in der Länge, die Google vollständig anzeigt; eine H1, klare H2/H3-Struktur
- **Suchbegriffe** im Text: Chelattherapie Berlin, Schwermetallausleitung, Schwermetalltest Berlin, Heilpraktikerin Lichtenrade
- **Stil:** keine Gedankenstriche (lange Striche) im Text, damit er nicht nach KI klingt; der Release prüft das
- **Lokales SEO:** Berlin-Lichtenrade, Tempelhof-Schöneberg, Umland (Mahlow, Blankenfelde, Teltow); Name, Adresse und Telefon kommen für JSON-LD, FAQ, llms.txt, index.md und den sichtbaren Text aller drei Templates (`{{PRAXIS}}`, `{{STREET}}` usw.) aus `stammdaten.py`. Eine Änderung dort reicht.
- **Strukturierte Daten** und **SEO-Dateien:** siehe oben
- **Conversion:** eigener Abschnitt „Erstgespräch“ mit großer, anklickbarer Telefonnummer und „Jetzt anrufen“, dazu die Terminbuchung im Hero und im Kontaktbereich sowie eine feste Anruf-/Termin-Leiste auf dem Handy
- **Antwort zuerst:** Der Block „Auf einen Blick“ steht direkt unter dem Hero. KI-Suchen übernehmen solche Kurzantworten gern als Zitat.
- **Vertrauenssignale (E-E-A-T):** echte Qualifikationen, Stand-Datum, verantwortliche Autorin, Pflichthinweis im Footer, in llms.txt und oben in index.md; „geprüft“ erst nach Ninas Freigabe
- **KI-Crawler ausdrücklich erlaubt** (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot, PerplexityBot, Google-Extended, Applebot-Extended …), alle in einer robots-Gruppe
- **Icons** für Google (ICO und PNG ab 48 px), iPhone (apple-touch-icon ohne Transparenz) und Android (Manifest)
- **Technik:** kein Framework, eine einzige HTML-Datei, Bilder als WebP, das Hero-Bild wird vorgeladen, barrierearm (Skip-Link, Fokus-Stile, Kontraste, `prefers-reduced-motion`), feste Termin-Leiste auf dem Handy

## Gestaltung auf Handy, Tablet und Desktop

Verbindlich sind Positionen, Bildformate und Ausschnitte, Schriften und Schriftgrößen. Texte und Fotos sind Platzhalter. Gemeinsame Mechanik steht in `_src/build.py` (`SHARED_CSS` ohne Designwerte, `SCRIPTS`, `MOTION_HEAD`), alle Gestaltungswerte je Entwurf im Template.

| Bereich | Größe | Was sich ändert |
|---|---|---|
| Handy hochkant | bis 640 px breit | einspaltig, Bilder im Text randlos im Format 4:3, Silbentrennung im Fließtext, Leiste „Anrufen · Termin buchen“ unten |
| Tablet | 641 bis 1020 px | eigenes Raster je Entwurf, Menü-Button, feste Bildausschnitte |
| Desktop | ab 1021 px | volle Navigation (C erst ab 1280 px, darunter Menü-Button), weitere Feinstufen je Entwurf, etwa bei 1200 und 1600 px |
| Handy quer | bis 500 px hoch | eigene Regeln: kleinere Überschriften, H1 und erster Button im ersten Bildschirm (geprüft 667×375, 844×390, 932×430), ab 641 px Breite keine Leiste (der Button im Header reicht) |
| sehr niedrig | bis 640 px breit und bis 520 px hoch (C: bis 340 px hoch) | Header läuft mit, keine Leiste. Offen: bei 568×320 steht in keinem Entwurf ein Button im ersten Bildschirm, bei 640×360 nur in C |

Abgenommen auf 320, 360, 375, 390, 430, 768, 820, 1024, 1280, 1440 und 1920 px Breite sowie 667×375, 844×390, 932×430, 744×1133 und 1366×768. Auf allen Größen gilt laut `audit`: kein waagerechtes Scrollen, kein herausragendes Element, Kontrast nach WCAG AA, Tippflächen ab 44 px, keine Konsolenfehler.

### Gemeinsame Bausteine (in A, B und C gleich)

- **Menü:** bis 1020 px (C bis 1279 px) hinter dem Menü-Button, mit „Kontakt“ und „Termin buchen“. Offen ist die Seite dahinter gesperrt und abgedunkelt, das Menü scrollt in sich (wichtig im Querformat), die Leiste unten verschwindet. Per Tastatur springt der Fokus ins Menü, Escape schließt und setzt den Fokus zurück auf den Button. Tippen daneben oder ein Fokus außerhalb des Headers schließt ebenfalls.
- **Aktiver Menüpunkt:** `aria-current="location"` am Link des Abschnitts, der gerade durch die Lesezeile bei 40 % der Fensterhöhe läuft. Abschnitte ohne eigenen Menüpunkt lassen keinen Punkt aktiv. Aussehen: A Goldlinie (Desktop und Menü), B Kupferlinie, C feine Goldlinie am Desktop und Gold im Menü.
- **Leiste unten (Anrufen · Termin buchen):** nur bis 640 px Breite. Sichtbar, solange weder die Hero-Buttons noch etwas mit `data-mcta-hide` noch der Footer im Bild ist. Was unter der Leiste oder hinter der festen Kopfzeile steckt, zählt nicht als sichtbar (sonst blieb beim Hochschieben der Hero-Buttons eine Lücke ganz ohne Button). A markiert die ganze dunkle Erstgespräch-Karte und den Kontaktbereich, B und C nur Nummer und Buttons. Berücksichtigt den iPhone-Rand (`viewport-fit=cover`, `safe-area-inset`).
- **Kopfzeile:** bekommt `.scrolled` nach 10 px (C nach 30 px), per IntersectionObserver statt Scroll-Listener.
- **Neue Tabs:** Links zu Doctolib und zur Route sagen „öffnet in neuem Tab“ für Screenreader an.
- **FAQ:** 13 Fragen aus `stammdaten.py`, die erste offen, klappt in Chrome und Edge sanft auf, in anderen Browsern wie bisher.
- **Anrufen und Kopieren:** siehe „Anruf-Buttons und Tracking“.

### Umbruch

Überschriften brechen ausgeglichen um (`text-wrap:balance`), Absätze ohne einzelnes Wort in der letzten Zeile (`pretty`), auf dem Handy mit Silbentrennung. Gegen schlechte Umbrüche in den Templates: `.nw`, `&nbsp;` und `{{STREET_NB}}`. In der FAQ setzt `build.py` den Schutz selbst (`NOWRAP`, `BINDEN`, `TRENNEN`): in den Antworten `<span class="nw">`, in den Fragen Wortverbinder (U+2060) und weiche Trennstellen, weil ein Span in Chrome `balance` für die ganze Überschrift abschaltet (gemessen in B). JSON-LD, llms.txt und index.md bleiben davon unberührt.

### Bewegung ohne Ruckeln

- **Einblenden beim Scrollen:** Abschnittsköpfe, Karten, Schritte, die FAQ als Ganzes usw. (Liste `REVEAL` in `build.py`) schieben sich einmalig leicht nach oben ein, nur über `opacity` und `transform`, also auf der Grafikkarte. Den Startzustand setzt `MOTION_HEAD` vor dem ersten Zeichnen und ohne Übergang. Beim Laden laufen dadurch statt 86 bis 93 nur noch 1 bis 6 Animationen. Ohne JavaScript oder bei einem Skriptfehler ist alles sofort sichtbar.
- **Bilder im Text** zoomen nicht, weil Chrome gezoomte Bilder am Ende sichtbar scharf zieht (gemessen). Sie kommen mit ihrem Block und werden eine Bildschirmhöhe vorher geladen und dekodiert.
- **Porträt beim Laden (A, C):** nur ein sanftes Herauszoomen, kein Seitwärtsgleiten und kein Ausblenden (LCP). Der Zoom startet erst, wenn das Foto dekodiert und zu 20 % zu sehen ist. Die Ebene bleibt danach bestehen (`will-change:transform`), am Ende wird also nichts neu gerastert. In B erscheinen die Periodensystem-Kacheln nacheinander, nur über `opacity` und `translateY`.
- **„Bewegung reduzieren“:** keine Einblendung, kein Zoom, keine Übergänge, auch nicht an Pseudo-Elementen. Dafür steht in allen drei Templates `*,*::before,*::after{transition:none!important}`. Vorher liefen in A und C Header-Linie, FAQ-Pfeil und Navigations-Unterstrich weiter.
- **Gemessen** (30.09./01.10., Software-Rendering mit 60 Hz): beim Scrollen kein Frame über 50 ms, bei vierfach gedrosselter CPU höchstens 16,8 ms je Frame, Layouts beim Scrollen von 45 bis 49 auf 3 bis 6 gesenkt.
- **Bekannt:** Unter Slow 4G kommen FCP und LCP 110 bis 300 ms später als vor dem Feinschliff. Ursache ist der größere `<head>` (Inline-CSS rund 45 KB), mit dem sich das Porträt-Preload die Bandbreite teilt, nicht die Bewegung. Siehe „Technik“ bei den offenen Punkten.

## Prüfen

Alle Werkzeuge steuern Headless-Chrome über das DevTools-Protokoll, ohne Zusatzpakete (Node ab 22). Immer nur einen Lauf gleichzeitig starten, die Läufe brauchen spürbar Rechenleistung.

`node _src/pruefen.mjs <befehl> <seite.html> [Optionen]` (Einzelheiten im Kopfkommentar der Datei)

| Befehl | prüft | Ergebnis im Ausgabeordner |
|---|---|---|
| `shots` | ganze Seite und Bildschirm für Bildschirm | `<breite>-ganz.jpg`, `<breite>-tNN.jpg` |
| `audit` | Überlauf, herausragende Elemente, Kontrast, Tippflächen, kleine Schrift, Bildschärfe und `sizes`, doppelte ids, tote Anker, Links ohne Namen, Konsole, 404, CLS, LCP | `audit.json` |
| `jank` | Ruckeln: Trace beim Laden und beim Scrollen, lange Frames, Animationen ohne Grafikkarte | `jank.json` |
| `menue` | Menü per Tippen und Tastatur: Fokus, Tab-Reihenfolge, Escape, Klick daneben, Scrollen im Menü, Leiste, Abdunklung | `menue.json` und Screenshots |
| `mechanik` | Leiste an jeder Scroll-Position, Kopfzeile `.scrolled`, `data-tel`, Nummer kopieren, aktiver Menüpunkt je Abschnitt | `mechanik.json` |
| `cls` | nur Ladeverhalten, mehrfach: CLS mit den einzelnen Verschiebungen, FCP, LCP | `cls*.json` |

| Option | Wirkung |
|---|---|
| `--w 375,1440` | Breiten. Unter 1024 px emuliert das Werkzeug ein Touch-Gerät (kein Hover, grober Zeiger, Tippen), ab 1024 px Desktop mit Maus |
| `--h 812,390` | Fensterhöhe (Standard 812 Handy, 1024 Tablet, 900 Desktop). Mehrere Werte gelten paarweise zu `--w` |
| `--out <ordner>` | Ausgabe, darin ein Unterordner je Seite (Standard `%TEMP%/chelat-pruefung`) |
| `--root <ordner>` | anderer Wurzelordner für den Testserver, etwa ein Release |
| `--reduced` | „Bewegung reduzieren“ emulieren |
| `--no-tiles`, `--max-tiles <n>` | `shots`: nur die ganze Seite bzw. höchstens n Bildschirme von oben |
| `--klick <css>` | `shots`: nach dem Laden auf das Element tippen oder klicken, dann nur das Fenster aufnehmen (`<breite>-klick.jpg`) |
| `--vorher <js>`, `--nachher <js>` | JavaScript vor bzw. nach dem Klick, `await` ist erlaubt. Beim Scrollen `behavior: 'instant'` angeben, die Entwürfe scrollen sonst sanft und ein zweiter Befehl bricht den ersten ab |
| `--netz slow4g`, `--netz fast4g` | Netz drosseln (150 ms und 1,6 Mbit/s bzw. 40 ms und 9 Mbit/s) |
| `--cpu <n>` | CPU n-fach verlangsamen (4 entspricht einem Mittelklasse-Handy) |
| `--runs <n>` | `cls`: Ladevorgänge je Breite (Standard 3) |
| `--dpr <n>` | Pixeldichte (Standard 1) |

**Ersatzschriften:** `node _src/schriften.mjs <seite.html> [--schreiben] [--w 1024,1280,1440,1920] [--alle] [--out <ordner>]` misst die metrisch angepassten Ersatzschriften gegen die Webfonts (Breite, Ober- und Unterlänge, Zeilenabstand) und zählt Elemente, die beim Nachladen ihre Höhe ändern würden. Mit `--schreiben` ersetzt es den Block zwischen `schriften:start` und `schriften:ende` im Template, danach neu bauen. `--alle` misst je Schnitt statt je Familie (genauer, langsamer). Nach jeder Änderung an Schriften oder Schriftgrößen erneut laufen lassen.

```bash
python _src/build.py
node _src/pruefen.mjs audit entwurf-a-salbei.html --w 320,375,390,430,768,820,1024,1280,1440,1920
node _src/pruefen.mjs audit entwurf-a-salbei.html --w 667,844,1366 --h 375,390,768    # quer und Laptop
node _src/pruefen.mjs shots entwurf-c-stille.html --w 375,820,1440 --max-tiles 3
node _src/pruefen.mjs shots entwurf-b-klarheit.html --w 375 --klick .menu-btn         # offenes Menü
node _src/pruefen.mjs mechanik entwurf-b-klarheit.html --w 375,820,1440,844 --h 812,1180,900,390
node _src/pruefen.mjs menue entwurf-a-salbei.html --w 375,844 --h 812,390
node _src/pruefen.mjs jank entwurf-a-salbei.html --w 375,1440
node _src/pruefen.mjs cls entwurf-b-klarheit.html --w 375,1024,1440 --netz slow4g --runs 5
node _src/pruefen.mjs audit index.html --root _release --w 375,1440                   # einen Release prüfen
node _src/schriften.mjs entwurf-a-salbei.html --schreiben
```

**Messhinweis:** Ist die Windows-Sitzung gesperrt oder der Bildschirm aus, drosselt Windows den Grafikprozess von Headless-Chrome. `jank` liefert dann Frames bis über 2 s oder läuft in die Zeitüberschreitung, und Beobachter im Skript melden verspätet. `mechanik` wartet deshalb auf zwei echte Frames statt auf feste Pausen. Ruckel-Messungen nur am entsperrten PC werten.

## Vergleichsseite und Vorschaubilder

`index.html` ist nur zum Zeigen (noindex, nicht Teil des Release). Sie zeigt je Entwurf den ersten Bildschirm am Desktop und auf dem Handy, eine kurze Charakterisierung, Schriften, Farben und den Link. Ändert sich der erste Bildschirm, die Bilder neu erzeugen:

```bash
python _src/build.py
python _src/vorschau.py        # alle drei; python _src/vorschau.py b nur Entwurf B
```

`vorschau.py` nimmt mit `pruefen.mjs shots` im Klick-Modus 1440×900 und 390×844 auf (2,5 s nach dem Laden, wenn der Hero fertig ist) und schneidet mit PIL auf `vorschau/<a|b|c>-desktop.jpg` (rund 105 KB) und `-handy.jpg` (rund 50 bis 65 KB) zu. Die älteren `vorschau/a.jpg`, `b.jpg`, `c.jpg` und `mobil-vorher-nachher.png` nutzt die Seite nicht mehr.

## Bilder im Text

Die Bilder stehen bewusst verteilt im Textfluss, nicht als Galerie. Sie lockern lange Textstrecken auf und zeigen, worum es im jeweiligen Abschnitt geht. Auf dem Handy laufen sie randlos über die volle Breite.

| Stelle | Motiv | Schlüssel in `stammdaten.py` |
|---|---|---|
| „Was ist eine Chelattherapie?“ (A, C) bzw. „Wirkprinzip“ (B) | Nina legt einem Patienten die Infusion (Zuschnitt 4:3) | `IMG_INFUSION` |
| Kopf von „So läuft die Chelattherapie ab“ | Nina mit Patientin im Praxisflur | `IMG_PRAXIS` |
| Abschnitt Erstgespräch | Nina im Gespräch am Schreibtisch (Zuschnitt 3:2) | `IMG_ERSTGESPRAECH` |

**Bilder aktualisieren:** Rohfotos nach `assets/_roh/` legen (Stichwort im Dateinamen: `infusion`, `praxis`/`flur`, `erstgespraech`/`gespraech`), dann `python _src/bilder.py` und `python _src/build.py`. Das Skript schneidet mit festen, relativen Ausschnitten zu, funktioniert also mit jeder Auflösung desselben Motivs. Es speichert jedes Motiv in 800, 1200 und 1600 px Breite, aber nie breiter als das Rohbild (die größte Stufe unter dem bisherigen Namen, kleinere als `name-800.webp` usw.). Der Browser lädt dann nur die passende Größe (`srcset`). Die jetzigen Vorschau-Rohbilder sind nur 682 bzw. 1024 px breit, echte Fotos sollten mindestens 1600 px haben, das Porträt ebenfalls (Rohbild mit `portrait` im Namen). `assets/_roh/` geht nicht live. Alt-Texte und Bildunterschriften stehen in den Templates. Ändern sich die Maße des Porträt-JPG oder des og-Bilds, `PORTRAIT_W/H` bzw. `OG_IMAGE_W/H` in `stammdaten.py` anpassen (der Release prüft das).

**Vor dem Go-live:** Die Bilder zeigen Nina. Sind sie KI-generiert, braucht es Ninas Einverständnis, und die Räume sollten ihrer echten Praxis entsprechen. Außerdem prüfen, ob eine Kennzeichnung als KI-Bild nötig ist (EU-KI-Verordnung, Transparenzpflicht bei KI-Bildern realer Personen). Nicht mehr verwendet: `assets/vorschau/infusion.webp`, `praxis-empfang.webp`, `gespraech.webp` (fremde Stockfotos) und `assets/platzhalter/`; sie kommen nicht in den Release. Wird das og-Bild getauscht, bitte unter neuem Dateinamen (es hat kein `?v` und liegt ein Jahr im Cache).

## Anruf-Buttons und Tracking

- **Handy:** „Kostenloses Erstgespräch“ und „Jetzt anrufen“ rufen direkt an.
- **Desktop:** „Kostenloses Erstgespräch“ springt zum Erstgespräch-Abschnitt. Die Anruf-Buttons heißen dort „Nummer kopieren“ und kopieren die Nummer (sie steht groß daneben).
- **Tracking** ist vorbereitet, aber **aus**. Gezählt werden: *Anruf*, *Nummer kopiert*, *Termin Doctolib*, *E-Mail*, *Zum Erstgespräch*, jeweils mit dem Bereich der Seite (Hero, Erstgespräch, Kontakt, Mobil-Leiste …).
  - Aktivieren: ein Konto bei [Plausible](https://plausible.io) anlegen (EU-Server, keine Cookies, ca. 9 €/Monat), die Domain in `_src/stammdaten.py` bei `ANALYTICS_DOMAIN` eintragen, neu bauen. Die CSP nimmt Plausible dann automatisch auf.
  - In Plausible die Ziele (Goals) mit genau diesen Eventnamen anlegen.
  - Kein Cookie-Banner nötig, aber Plausible in der Datenschutzerklärung nennen.

## Go-live-Prüfliste

1. **Entwurf wählen** (A, B oder C).
2. **In `_src/stammdaten.py` eintragen:** `DOMAIN` (echte Domain mit `https://`, ohne `/` am Ende), `HOSTING` (`"apache"` oder `"pages"`), `PUBLISHED` (Go-live-Datum, danach nie mehr ändern), `UPDATED` bei jeder inhaltlichen Änderung. `REVIEWED` erst nach Ninas fachlicher Freigabe. Optional und nur mit echten Werten: `GBP_URL`, `GEO` (aus dem Unternehmensprofil), `OPENING_HOURS`, `LOGO`, `INDEXNOW_KEY`.
3. **`FREIGABEN` erst auf `True`, wenn geklärt:** Adresse und Telefon (Pflicht 3), eigenes Impressum und Datenschutz (Pflicht 2), Bildrechte (Pflicht 6).
4. **Schriften lokal** (Pflicht 5), sonst bricht der Release ab.
5. **Bauen:** `python _src/build.py release <a|b|c>`. Nur bei „Release OK“ weiter. Die Warnungen lesen (etwa Vorschaubilder).
6. **Vorher auf einer Test-Adresse ansehen:** `python _src/build.py release <a|b|c> --probe --ziel <ordner>` hochladen; die Seite ist dort gesperrt (noindex, robots sperrt alles).
7. **Hochladen:** nur den Inhalt von `_release/`, bei Apache inklusive der unsichtbaren `.htaccess`.
8. **Nach dem Upload prüfen:** `https://DOMAIN/robots.txt`, `/llms.txt`, `/sitemap.xml`, `/index.md` und eine unbekannte Adresse (muss die 404-Seite mit Status 404 zeigen). Bei Cloudflare die KI-Bot-Sperre prüfen (siehe Hosting).
9. **Anmelden:** Google Search Console und Bing Webmaster Tools, dort `sitemap.xml` einreichen (Bing speist auch ChatGPT und Copilot). Strukturierte Daten testen: https://validator.schema.org und https://search.google.com/test/rich-results

## Offene Punkte vor dem Go-live (bitte mit Nina klären)

### Pflicht
1. **Domain festlegen.** `https://www.chelattherapie-berlin.de` ist nur ein **Platzhalter**. Die echte Domain nur in `_src/stammdaten.py` bei `DOMAIN` eintragen; robots.txt, llms.txt, sitemap.xml, index.md, Canonical und JSON-LD übernehmen sie beim Bauen. Solange der Platzhalter drinsteht, bricht der Release ab.
2. **Eigenes Impressum und eigene Datenschutzerklärung** für die neue Domain. Aktuell verlinkt der Footer auf die Hauptwebsite (`IMPRESSUM`, `DATENSCHUTZ` in `stammdaten.py`). Das reicht bei einer eigenen Domain rechtlich meist nicht. Danach `FREIGABEN["impressum_datenschutz"]` auf `True`.
3. **Widerspruch im Impressum der Hauptseite:** Dort stehen *Buckower Damm 95, 12349 Berlin*, Tel. *030 36440736* und *n.d.klimek@gmail.com*. Auf der Website stehen dagegen *Steinstraße 41D, 12307* und *01520 7707704*. Der Onepager verwendet die Praxisdaten (Steinstraße). Bitte klären, welche Angaben stimmen. Für Google müssen Name, Adresse und Telefon überall identisch sein (Website, Unternehmensprofil, Doctolib, Hauptseite). Danach `PRAXIS` und Telefon in `stammdaten.py` prüfen und `FREIGABEN["nap_geklaert"]` auf `True`.
4. **Heilmittelwerbegesetz (HWG):** Die Texte sind bewusst ohne Heilversprechen und ohne Krankheitsbezüge formuliert. Nina sollte sie trotzdem fachlich und rechtlich freigeben, idealerweise mit einem Blick ihres Berufsverbands. Mit dem Datum ihrer Freigabe `REVIEWED` setzen.
5. **Google Fonts lokal einbinden** (DSGVO, vgl. Urteil des LG München von 2022). Zurzeit werden die Schriften zur Vorschau von Google geladen; der echte Release bricht deshalb ab. Umstellen: die woff2-Dateien nach `fonts/` legen, `@font-face` mit `url(fonts/….woff2)` ins Template, im Build-Block `"fonts": ""` und `"schriften": [...]` mit den Schnitten von H1 und Fließtext, danach `node _src/schriften.mjs` erneut laufen lassen. Release, `?v` und CSP (dann ohne Google) stellen sich von selbst darauf ein.
6. **Bildrechte:** Das Porträt stammt von der Fotografin Grit Siwonia (laut Impressum). Die Nutzungsrechte müssen auch die neue Domain abdecken, ebenso für alle Bilder im Text. Danach `FREIGABEN["bildrechte"]` auf `True`; erst dann auch über `ai-train` im Content-Signal der robots.txt entscheiden.

### Inhaltlich prüfen
- **Du oder Sie?** Die Hauptseite duzt. Der Onepager siezt, weil das seriöser wirkt. Das lässt sich leicht umstellen.
- **Infusionsdauer** („etwa eine bis drei Stunden“, FAQ): Stimmt das mit Ninas Praxis überein?
- **Neue praktische FAQ** (Vorbereitung auf die Infusion, Arbeiten und Autofahren danach, Schwermetalltest mit Blutentnahme vor Ort) sind allgemein formuliert und müssen von Nina bestätigt werden.
- **Preise:** Der Honorar-Abschnitt ist entfernt. Als Kompromiss nennen die FAQ „Was kostet …?“, die strukturierten Daten und `llms.txt` nur „Erstanamnese ab 150 €“.
- **Hinweis im Erstgespräch-Abschnitt:** „Während einer Behandlung bin ich nicht immer direkt erreichbar. Schreiben Sie mir dann gern …“. Passt das zu Ninas Erreichbarkeit (z. B. Anrufbeantworter, Rückrufzeiten)?
- **Quellenbeispiele** zu den einzelnen Metallen (Thunfisch, Reis usw.) fachlich gegenlesen lassen.

### Technik
- **Echte Fotos:** Die Platzhalter sind ab 1024 px und auf Retina-Displays weich (Rohbilder nur 682 bis 1024 px breit, `audit` meldet `sharpAt2x false`). Nötig sind Originale ab 1600 px, das Porträt für C ab etwa 1850×2312 px.
- **Ladezeit unter Slow 4G:** FCP und LCP sind durch den größeren `<head>` 110 bis 300 ms langsamer als vor dem Feinschliff. Auf dem Hosting gzip oder Brotli einschalten (das HTML schrumpft dann von rund 100 auf rund 30 KB), das Inline-CSS auf Doppelungen prüfen und in C das Porträt-Preload nur dort setzen, wo das Bild das LCP ist. Danach mit `pruefen.mjs cls --netz slow4g` nachmessen.
- **Sehr niedrige Querformate** (568×320, 640×360, ältere Geräte): kein Button im ersten Bildschirm und keine Leiste, siehe Tabelle oben. Entscheiden, ob dort die kompakte Leiste wie in C erscheint oder der Hero weiter verdichtet wird.
- **Ruckel-Messung mit Grafikkarte** am entsperrten PC wiederholen: `node _src/pruefen.mjs jank <seite> --w 375,1440` je Entwurf.
- **Safari und Firefox** sind nicht gemessen (runde Bildmasken, `-webkit-`-Präfixe, Lazy-Loading unter iOS). Vor dem Go-live auf echten Geräten ansehen.

### Nach dem Go-live
- **Doppelte Inhalte vermeiden:** Die Hauptseite hat eine eigene Seite `/Chelattherapie`. Die Onepager-Texte sind neu formuliert. Trotzdem sollte die Hauptseite entweder auf die neue Domain verlinken („Mehr zur Chelattherapie“) oder ihre Seite kürzen.
- **Google-Unternehmensprofil** pflegen: Website-Link und Leistung „Chelattherapie“ ergänzen, den Profil-Link als `GBP_URL` eintragen.
- **Doctolib-Profil** um einen Link zur neuen Seite ergänzen.
- **Bei jeder inhaltlichen Änderung** `UPDATED` anpassen und neu releasen (der Release warnt, wenn Vorlagen oder Bilder jünger sind als `UPDATED`).

## Quellen (Recherche)
- Originalseite: https://www.heilpraxis-klimek.com/Chelattherapie (sowie /kontakt, /ueber-mich, /impressum)
- Verschreibungspflicht der Chelatbildner (DMSA seit 2017 verschreibungspflichtig; für Heilpraktiker bleiben EDTA und DTPA): https://heilpraktikerverband.de/aktuelles/aktuelle-meldungen/463-chelattherapie-dmsa-succimer-seit-2017-verschreibungspflichtig
- robots.txt: RFC 9309 (https://www.rfc-editor.org/rfc/rfc9309.html) und Google, How Google interprets robots.txt
- llms.txt: https://llmstxt.org
