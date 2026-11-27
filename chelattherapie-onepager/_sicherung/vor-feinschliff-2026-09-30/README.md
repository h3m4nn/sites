# Onepager Chelattherapie Berlin (Heilpraxis Nina Klimek)

Stand: 30.09.2026 · nur lokal, noch nicht veröffentlicht

## Inhalt des Ordners

| Datei | Zweck | geht live? |
|---|---|---|
| `index.html` | Übersicht zum Vergleichen der 3 Entwürfe | **nein** (wird durch den gewählten Entwurf ersetzt) |
| `entwurf-a-salbei.html` | Entwurf A: warm, editorial, Salbeigrün | nur der gewählte Entwurf, dann als `index.html` |
| `entwurf-b-klarheit.html` | Entwurf B: modern, klinisch, Petrol | ″ |
| `entwurf-c-stille.html` | Entwurf C: dunkel, premium, Gold | ″ |
| `robots.txt` | Crawler-Freigabe inkl. aller KI-Bots | ja |
| `llms.txt` | Fakten-Zusammenfassung für KI-Assistenten ([llmstxt.org](https://llmstxt.org)) | ja |
| `index.md` | kompletter Seiteninhalt als Markdown für KI-Systeme | ja |
| `sitemap.xml` | für Google Search Console und Bing | ja |
| `favicon.svg`, `assets/` | Icon, Porträt (WebP + JPG), Social-Media-Vorschaubild | ja |
| `_src/` | Build-Script, Templates, Bild-Zuschnitt (`bilder.py`) | nein |
| `assets/_roh/` | Rohfotos vor dem Zuschnitt | nein |
| `_vorschau/` | Vorschaubilder für die Übersicht | nein |

**Hinweis zur „robots.md“:** Eine Datei mit diesem Namen gibt es nicht als Standard. Für die KI-Optimierung sind **`llms.txt`** (Zusammenfassung für Sprachmodelle) und **`robots.txt`** (Zugriffsfreigabe für KI-Crawler) gebräuchlich. Beide liegen hier, dazu die Markdown-Version `index.md`.

## Lokal ansehen

```bash
python -m http.server 8741
```
Danach im Browser http://localhost:8741 öffnen.

## Texte ändern

Meta-Tags, strukturierte Daten (JSON-LD) und die FAQ werden zentral in `_src/build.py` gepflegt. Die Seitentexte stehen in `_src/entwurf-*.src.html`. Nach jeder Änderung neu bauen:

```bash
python _src/build.py
```

## Was an SEO und KI-Optimierung eingebaut ist

- **Title** (62 Zeichen) und **Description** (149 Zeichen) in der Länge, die Google vollständig anzeigt; eine H1, klare H2/H3-Struktur
- **Suchbegriffe** im Text: Chelattherapie Berlin, Schwermetallausleitung, Schwermetalltest Berlin, Heilpraktikerin Lichtenrade
- **Stil:** keine Gedankenstriche (–) im Text, damit er nicht nach KI klingt
- **Lokales SEO:** Berlin-Lichtenrade, Tempelhof-Schöneberg, Umland (Mahlow, Blankenfelde, Teltow), Geo-Meta-Tags
- **Strukturierte Daten (Schema.org):** MedicalBusiness, Person (mit Heilpraktikererlaubnis und Verband), MedicalTherapy, MedicalWebPage (mit `reviewedBy`/`lastReviewed`), FAQPage (10 Fragen), Angebot „Kostenloses Erstgespräch“, BreadcrumbList, ReserveAction (Doctolib)
- **Conversion:** eigener Abschnitt „Erstgespräch“ mit großer, anklickbarer Telefonnummer und „Jetzt anrufen“, dazu die Terminbuchung im Hero und im Kontaktbereich sowie eine feste Anruf-/Termin-Leiste auf dem Handy
- **Antwort zuerst:** Der Block „Auf einen Blick“ steht direkt unter dem Hero. KI-Suchen übernehmen solche Kurzantworten gern als Zitat.
- **Vertrauenssignale (E-E-A-T):** echte Qualifikationen, Stand-Datum, verantwortliche Autorin, Pflichthinweis im Footer
- **KI-Crawler ausdrücklich erlaubt** (GPTBot, OAI-SearchBot, ClaudeBot, Claude-SearchBot, PerplexityBot, Google-Extended …)
- **Technik:** kein Framework, eine einzige HTML-Datei, Bilder als WebP, das Hero-Bild wird vorgeladen, barrierearm (Skip-Link, Fokus-Stile, Kontraste, `prefers-reduced-motion`), feste Termin-Leiste auf dem Handy

## Handy-Ansicht und Animationen

Gemeinsame Bausteine stehen in `_src/build.py` (`SHARED_CSS`, `SCRIPTS`), die Feinheiten je Entwurf im jeweiligen Template unter `@media (max-width:640px)`.

- **Menü:** Unter 1020/1060 px (C: 1200 px) klappt die Navigation hinter einen Menü-Button, inkl. „Kontakt“ und „Termin buchen“.
- **Leiste unten (Anrufen · Termin buchen):** erscheint erst, wenn der Hero aus dem Bild ist, und blendet sich im Erstgespräch-, Kontakt- und Footer-Bereich aus, wo dieselben Buttons ohnehin groß stehen. Berücksichtigt den iPhone-Rand (`viewport-fit=cover`, `safe-area-inset`).
- **Einblenden beim Scrollen:** Abschnittsköpfe, Karten, Schritte, FAQ usw. schieben sich einmalig leicht nach oben ein, Bilder zoomen dabei sanft heraus. Ohne JavaScript und bei „Bewegung reduzieren“ ist alles sofort sichtbar.
- **Porträt beim Laden (A, C):** nur ein sanftes Herauszoomen, kein Seitwärtsgleiten (das hat geruckelt) und kein Ausblenden, damit das Foto sofort sichtbar ist (LCP). In B erscheinen die Periodensystem-Kacheln nacheinander.
- **Prüfen:** Screenshots im Handy-Format lassen sich per Headless-Chrome erzeugen; wichtig ist, dass `scrollWidth` 375 bleibt (kein seitliches Scrollen).

## Bilder im Text

Die Bilder stehen bewusst verteilt im Textfluss, nicht als Galerie. Sie lockern lange Textstrecken auf und zeigen, worum es im jeweiligen Abschnitt geht. Auf dem Handy laufen sie randlos über die volle Breite.

| Stelle | Motiv | Schlüssel in `build.py` |
|---|---|---|
| „Was ist eine Chelattherapie?“ (A, C) bzw. „Wirkprinzip“ (B) | Nina legt einem Patienten die Infusion (Zuschnitt 4:3) | `IMG_INFUSION` |
| Kopf von „So läuft die Chelattherapie ab“ | Nina mit Patientin im Praxisflur | `IMG_PRAXIS` |
| Abschnitt Erstgespräch | Nina im Gespräch am Schreibtisch (Zuschnitt 3:2) | `IMG_ERSTGESPRAECH` |

**Bilder aktualisieren:** Rohfotos nach `assets/_roh/` legen (Stichwort im Dateinamen: `infusion`, `praxis`/`flur`, `erstgespraech`/`gespraech`), dann `python _src/bilder.py` und `python _src/build.py`. Das Skript schneidet mit festen, relativen Ausschnitten zu, funktioniert also mit jeder Auflösung desselben Motivs (Ausgabe max. 1600 px breit). `assets/_roh/` geht nicht live. Alt-Texte und Bildunterschriften stehen in den Templates.

**Vor dem Go-live:** Die Bilder zeigen Nina. Sind sie KI-generiert, braucht es Ninas Einverständnis, und die Räume sollten ihrer echten Praxis entsprechen. Außerdem prüfen, ob eine Kennzeichnung als KI-Bild nötig ist (EU-KI-Verordnung, Transparenzpflicht bei KI-Bildern realer Personen). Nicht mehr verwendet: `assets/vorschau/infusion.webp`, `praxis-empfang.webp`, `gespraech.webp` (fremde Stockfotos) und `assets/platzhalter/`.

## Anruf-Buttons und Tracking

- **Handy:** „Kostenloses Erstgespräch“ und „Jetzt anrufen“ rufen direkt an.
- **Desktop:** „Kostenloses Erstgespräch“ springt zum Erstgespräch-Abschnitt. Die Anruf-Buttons heißen dort „Nummer kopieren“ und kopieren die Nummer (sie steht groß daneben).
- **Tracking** ist vorbereitet, aber **aus**. Gezählt werden: *Anruf*, *Nummer kopiert*, *Termin Doctolib*, *E-Mail*, *Zum Erstgespräch*, jeweils mit dem Bereich der Seite (Hero, Erstgespräch, Kontakt, Mobil-Leiste …).
  - Aktivieren: ein Konto bei [Plausible](https://plausible.io) anlegen (EU-Server, keine Cookies, ca. 9 €/Monat), die Domain in `_src/build.py` bei `ANALYTICS_DOMAIN` eintragen, neu bauen.
  - In Plausible die Ziele (Goals) mit genau diesen Eventnamen anlegen.
  - Kein Cookie-Banner nötig, aber Plausible in der Datenschutzerklärung nennen.

## Offene Punkte vor dem Go-live (bitte mit Nina klären)

### Pflicht
1. **Domain festlegen.** `https://www.chelattherapie-berlin.de` ist nur ein **Platzhalter**. Die echte Domain an einer Stelle in `_src/build.py` (`DOMAIN`) sowie in `robots.txt`, `llms.txt`, `sitemap.xml` und `_src/index.src.md` ersetzen, danach neu bauen.
2. **Eigenes Impressum und eigene Datenschutzerklärung** für die neue Domain. Aktuell verlinkt der Footer auf die Hauptwebsite. Das reicht bei einer eigenen Domain rechtlich meist nicht.
3. **Widerspruch im Impressum der Hauptseite:** Dort stehen *Buckower Damm 95, 12349 Berlin*, Tel. *030 36440736* und *n.d.klimek@gmail.com*. Auf der Website stehen dagegen *Steinstraße 41D, 12307* und *01520 7707704*. Der Onepager verwendet die Praxisdaten (Steinstraße). Bitte klären, welche Angaben stimmen. Für Google müssen Name, Adresse und Telefon überall identisch sein.
4. **Heilmittelwerbegesetz (HWG):** Die Texte sind bewusst ohne Heilversprechen und ohne Krankheitsbezüge formuliert. Nina sollte sie trotzdem fachlich und rechtlich freigeben, idealerweise mit einem Blick ihres Berufsverbands.
5. **Google Fonts lokal einbinden** (DSGVO, vgl. Urteil des LG München von 2022). Zurzeit werden die Schriften zur Vorschau von Google geladen.
6. **Bildrechte:** Das Porträt stammt von der Fotografin Grit Siwonia (laut Impressum). Die Nutzungsrechte müssen auch die neue Domain abdecken.

### Inhaltlich prüfen
- **Du oder Sie?** Die Hauptseite duzt. Der Onepager siezt, weil das seriöser wirkt. Das lässt sich leicht umstellen.
- **Infusionsdauer** („etwa eine bis drei Stunden“, FAQ): Stimmt das mit Ninas Praxis überein?
- **Neue praktische FAQ** (Vorbereitung auf die Infusion, Arbeiten und Autofahren danach, Schwermetalltest mit Blutentnahme vor Ort) sind allgemein formuliert und müssen von Nina bestätigt werden.
- **Preise:** Der Honorar-Abschnitt ist entfernt. Als Kompromiss nennen die FAQ „Was kostet …?“, die strukturierten Daten und `llms.txt` nur „Erstanamnese ab 150 €“.
- **Hinweis im Erstgespräch-Abschnitt:** „Während einer Behandlung bin ich nicht immer direkt erreichbar – schreiben Sie mir dann gern …“. Passt das zu Ninas Erreichbarkeit (z. B. Anrufbeantworter, Rückrufzeiten)?
- **Quellenbeispiele** zu den einzelnen Metallen (Thunfisch, Reis usw.) fachlich gegenlesen lassen.

### Nach dem Go-live
- **Doppelte Inhalte vermeiden:** Die Hauptseite hat eine eigene Seite `/Chelattherapie`. Die Onepager-Texte sind neu formuliert. Trotzdem sollte die Hauptseite entweder auf die neue Domain verlinken („Mehr zur Chelattherapie“) oder ihre Seite kürzen.
- **Google Search Console und Bing Webmaster Tools** einrichten und `sitemap.xml` einreichen (Bing speist auch ChatGPT und Copilot).
- **Google-Unternehmensprofil** pflegen: Website-Link und Leistung „Chelattherapie“ ergänzen.
- **Doctolib-Profil** um einen Link zur neuen Seite ergänzen.
- **Strukturierte Daten testen:** https://validator.schema.org und https://search.google.com/test/rich-results
- **Hosting:** statische Dateien, also jedes einfache Hosting (Netlify, Cloudflare Pages, All-Inkl, IONOS …). HTTPS ist Pflicht.

## Quellen (Recherche)
- Originalseite: https://www.heilpraxis-klimek.com/Chelattherapie (sowie /kontakt, /ueber-mich, /impressum)
- Verschreibungspflicht der Chelatbildner (DMSA seit 2017 verschreibungspflichtig; für Heilpraktiker bleiben EDTA und DTPA): https://heilpraktikerverband.de/aktuelles/aktuelle-meldungen/463-chelattherapie-dmsa-succimer-seit-2017-verschreibungspflichtig
