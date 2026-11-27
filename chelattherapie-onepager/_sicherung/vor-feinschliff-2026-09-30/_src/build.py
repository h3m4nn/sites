# -*- coding: utf-8 -*-
"""
Baut die drei Design-Entwürfe aus den Templates in _src/.
Gemeinsame SEO-Bausteine (Meta-Tags, JSON-LD, FAQ) stehen nur hier -> alle Entwürfe bleiben SEO-identisch.

Aufruf:  python _src/build.py
Platzhalter:  {{HEAD}}  {{FAQ}}  {{YEAR}}  {{UPDATED}}  {{DOMAIN}}
"""
import json, html, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Stammdaten  (DOMAIN ist ein PLATZHALTER -> vor Livegang ersetzen, s. README)
# ---------------------------------------------------------------------------
DOMAIN   = "https://www.chelattherapie-berlin.de"
UPDATED  = "2026-09-30"
UPDATED_DE = "30. September 2026"
TITLE    = "Chelattherapie Berlin | Schwermetallausleitung bei Nina Klimek"
DESC     = ("Chelattherapie in Berlin-Lichtenrade: Schwermetalltest und "
            "individuell geplante Ausleitung bei Heilpraktikerin Nina Klimek. "
            "Kostenloses Erstgespräch.")
PHONE_INTL = "+4915207707704"
PHONE_DE   = "01520 7707704"
EMAIL      = "info@heilpraxis-klimek.com"
DOCTOLIB   = "https://www.doctolib.de/heilpraktiker/berlin/nina-klimek"
MAIN_SITE  = "https://www.heilpraxis-klimek.com"
INSTAGRAM  = "https://www.instagram.com/heilpraxis_klimek/"
# Datenschutzfreundliches Klick-Tracking (Plausible, ohne Cookies). Leer = aus.
# Zum Aktivieren die Live-Domain ohne https eintragen, z. B. "chelattherapie-berlin.de"
ANALYTICS_DOMAIN = ""
MAPS       = "https://www.google.com/maps/search/?api=1&query=Steinstra%C3%9Fe+41D+12307+Berlin"
# Bilder im Text. assets/vorschau/ sind NUR Vorschaubilder (fremde Fotos, Rechte ungeklärt, eins zeigt
# eine Arztpraxis) -> vor dem Go-live durch eigene Fotos ersetzen. Neutrale Platzhalter: assets/platzhalter/*.svg
# Echtes Foto (WebP, ca. 1600 px breit, Motiv mittig) nach assets/ legen, Pfad hier tauschen, neu bauen.
IMAGES = {
    "IMG_INFUSION":      "assets/vorschau/infusion-nina.webp",   # "Was ist eine Chelattherapie?": Nina legt die Infusion, 4:3 (Zuschnitt)
    "IMG_PRAXIS":        "assets/vorschau/praxis-nina.webp",     # "So läuft ... ab": Nina mit Patientin im Praxisflur, 3:2
    "IMG_ERSTGESPRAECH": "assets/vorschau/erstgespraech-nina.webp",  # Erstgespräch: Nina im Gespräch, 3:2 (Zuschnitt)
}

# ---------------------------------------------------------------------------
# FAQ: eine Quelle für sichtbares HTML UND FAQPage-Schema
# ---------------------------------------------------------------------------
FAQ = [
    ("Was ist eine Chelattherapie?",
     "Bei der Chelattherapie werden sogenannte Chelatbildner, in meiner Praxis vor allem EDTA "
     "(Ethylendiamintetraessigsäure), als Infusion verabreicht. Sie binden bestimmte Metallionen "
     "zu stabilen, wasserlöslichen Komplexen, die anschließend über die Nieren mit dem Urin "
     "ausgeschieden werden können. Der Name leitet sich vom griechischen „chele“ (Schere) ab, "
     "weil der Wirkstoff das Metall wie eine Zange umschließt."),
    ("Wie wird eine Schwermetallbelastung festgestellt?",
     "Am Anfang steht eine ausführliche Anamnese zu Vorgeschichte, Beschwerden und möglichen "
     "Belastungsquellen. Danach wird je nach Metall und Fragestellung eine gezielte "
     "Labordiagnostik aus Blut und/oder Urin veranlasst. Zusätzlich werden Nierenwerte und "
     "der Mineralstoffstatus geprüft, bevor über eine Ausleitung entschieden wird."),
    ("Was ist ein Schwermetalltest und wo kann ich ihn in Berlin machen lassen?",
     "Ein Schwermetalltest ist eine Laboruntersuchung von Blut und/oder Urin, mit der sich die "
     "Belastung durch bestimmte Metalle einschätzen lässt. Welche Werte sinnvoll sind, hängt von "
     "Ihrer Vorgeschichte und möglichen Belastungsquellen ab. In meiner Praxis in Berlin-Lichtenrade "
     "plane ich den Test nach der Erstanamnese gezielt, die Blutentnahme erfolgt direkt vor Ort."),
    ("Welche Metalle können eine Rolle spielen?",
     "Im Rahmen der Diagnostik betrachte ich unter anderem Quecksilber, Blei, Cadmium, Arsen und "
     "Aluminium sowie, je nach individueller Exposition, weitere relevante Metalle. Mögliche "
     "Quellen sind z. B. Feinstaub, bestimmte Lebensmittel, alte Amalgamfüllungen, "
     "Tätowierfarben, berufliche Belastungen oder alte Bleileitungen in Altbauten."),
    ("Wie läuft eine EDTA-Infusion ab und wie lange dauert sie?",
     "Sie sitzen bequem in einem ruhigen Behandlungsraum, die Infusion läuft langsam über eine "
     "Vene am Arm. Die Dauer hängt von Präparat und Dosierung ab und liegt in der Regel zwischen "
     "etwa einer und drei Stunden. Vorab werden die relevanten Laborwerte kontrolliert."),
    ("Wie viele Infusionen sind notwendig?",
     "Das lässt sich nicht pauschal beantworten. Dosierung, Abstände und Anzahl der Infusionen "
     "richten sich nach den Laborbefunden, Ihrer Ausgangssituation und dem Verlauf. "
     "Kontrolluntersuchungen zeigen, ob und wie die Therapie angepasst wird."),
    ("Wie bereite ich mich auf eine Infusion vor?",
     "Kommen Sie möglichst ausgeruht, trinken Sie im Vorfeld ausreichend und essen Sie vorher eine "
     "leichte Mahlzeit. Bringen Sie aktuelle Befunde sowie eine Liste Ihrer Medikamente und "
     "Nahrungsergänzungsmittel mit. Individuelle Hinweise erhalten Sie mit Ihrem Therapieplan."),
    ("Kann ich nach der Infusion arbeiten oder Auto fahren?",
     "Viele Menschen gehen danach ihrem Alltag wie gewohnt nach. Da sich manche nach einer Infusion "
     "etwas müde fühlen, empfehle ich, sich für den Rest des Tages nichts Anstrengendes vorzunehmen. "
     "Ob Sie direkt danach selbst fahren sollten, besprechen wir nach der ersten Anwendung."),
    ("Welche Nebenwirkungen sind möglich?",
     "Möglich sind unter anderem Müdigkeit, Kopfschmerzen, Reizungen an der Einstichstelle sowie "
     "ein Verlust wichtiger Mineralstoffe wie Zink oder Magnesium, da EDTA auch diese binden kann. "
     "Weil die gebundenen Metalle über die Nieren ausgeschieden werden, kontrolliere ich die "
     "Nierenfunktion vor und während der Therapie und gleiche Mineralstoffe gezielt aus."),
    ("Für wen ist eine Chelattherapie nicht geeignet?",
     "Nicht infrage kommt sie in der Regel bei eingeschränkter Nierenfunktion sowie in "
     "Schwangerschaft und Stillzeit. Auch bestimmte Vorerkrankungen und Medikamente sprechen "
     "dagegen. Ob eine Chelattherapie für Sie sinnvoll und vertretbar ist, klären wir vorab "
     "in der Anamnese und anhand Ihrer Laborwerte."),
    ("Was kostet eine Chelattherapie und zahlt die Krankenkasse?",
     "Die Erstanamnese beginnt ab 150 € (kompakt, 60 Minuten). Die weiteren Kosten für Labor und "
     "Infusionen hängen von der notwendigen Diagnostik und Ihrem individuellen Therapieplan ab und "
     "werden vorab transparent mit Ihnen besprochen. Es handelt sich um Selbstzahlerleistungen; "
     "private Krankenversicherungen, Zusatzversicherungen oder die Beihilfe erstatten je nach "
     "Tarif ganz oder teilweise. Gesetzliche Krankenkassen übernehmen Heilpraktikerleistungen "
     "in der Regel nicht. Erste Fragen dazu klären wir gern im kostenlosen Telefonat."),
    ("Ist die Chelattherapie eine Detox-Kur?",
     "Nein. Die Chelattherapie ist keine allgemeine Entgiftungskur, sondern eine gezielte "
     "therapeutische Maßnahme zur Ausleitung bestimmter Metalle. Sie steht erst am Ende "
     "einer sorgfältigen Diagnostik, nicht am Anfang."),
    ("Wo in Berlin findet die Behandlung statt?",
     "In der Heilpraxis Nina Klimek, Steinstraße 41D, 12307 Berlin-Lichtenrade im Süden Berlins, "
     "gut erreichbar aus Tempelhof, Mariendorf, Marienfelde sowie aus dem angrenzenden "
     "Brandenburg (Mahlow, Blankenfelde, Teltow). Termine können online über Doctolib "
     "gebucht werden; die Erstanamnese ist auch online möglich."),
]

def faq_html():
    out = []
    for i, (q, a) in enumerate(FAQ):
        out.append(
            f'<details class="faq-item"{" open" if i == 0 else ""}>\n'
            f'  <summary><h3>{html.escape(q)}</h3></summary>\n'
            f'  <div class="faq-answer"><p>{html.escape(a)}</p></div>\n'
            f'</details>')
    return "\n".join(out)

# ---------------------------------------------------------------------------
# JSON-LD  (Schema.org @graph)
# ---------------------------------------------------------------------------
def jsonld():
    D = DOMAIN
    g = [
        {
            "@type": "WebSite", "@id": f"{D}/#website", "url": f"{D}/",
            "name": "Chelattherapie Berlin | Heilpraxis Nina Klimek",
            "inLanguage": "de-DE", "publisher": {"@id": f"{D}/#praxis"},
        },
        {
            "@type": "MedicalWebPage", "@id": f"{D}/#webpage", "url": f"{D}/",
            "name": TITLE, "description": DESC, "inLanguage": "de-DE",
            "isPartOf": {"@id": f"{D}/#website"},
            "about": {"@id": f"{D}/#chelattherapie"},
            "audience": {"@type": "MedicalAudience", "audienceType": "Patient"},
            "primaryImageOfPage": {"@type": "ImageObject", "url": f"{D}/assets/og-chelattherapie.jpg"},
            "datePublished": UPDATED, "dateModified": UPDATED, "lastReviewed": UPDATED,
            "reviewedBy": {"@id": f"{D}/#nina-klimek"},
            "author": {"@id": f"{D}/#nina-klimek"},
            "speakable": {"@type": "SpeakableSpecification",
                          "cssSelector": ["#auf-einen-blick", "#faq"]},
        },
        {
            "@type": ["MedicalBusiness", "LocalBusiness"], "@id": f"{D}/#praxis",
            "name": "Heilpraxis Nina Klimek",
            "alternateName": "Heilpraxis Klimek",
            "description": ("Heilpraxis in Berlin-Lichtenrade mit Schwerpunkt Schwermetalltest "
                            "und individuell geplanter Chelattherapie (EDTA-Infusionen)."),
            "url": f"{D}/", "telephone": PHONE_INTL, "email": EMAIL,
            "image": f"{D}/assets/nina-klimek-800.jpg",
            "priceRange": "€€", "currenciesAccepted": "EUR",
            "address": {"@type": "PostalAddress", "streetAddress": "Steinstraße 41D",
                        "postalCode": "12307", "addressLocality": "Berlin",
                        "addressRegion": "Berlin", "addressCountry": "DE"},
            "hasMap": MAPS,
            "areaServed": [{"@type": "City", "name": "Berlin"},
                           {"@type": "Place", "name": "Berlin-Lichtenrade"},
                           {"@type": "Place", "name": "Tempelhof-Schöneberg"},
                           {"@type": "Place", "name": "Blankenfelde-Mahlow"},
                           {"@type": "Place", "name": "Teltow"}],
            "founder": {"@id": f"{D}/#nina-klimek"},
            "employee": {"@id": f"{D}/#nina-klimek"},
            "availableService": {"@id": f"{D}/#chelattherapie"},
            "sameAs": [MAIN_SITE, INSTAGRAM, DOCTOLIB],
            "potentialAction": {"@type": "ReserveAction", "name": "Termin buchen",
                                "target": {"@type": "EntryPoint", "urlTemplate": DOCTOLIB}},
            "makesOffer": [
                {"@type": "Offer", "name": "Kostenloses Erstgespräch am Telefon (10 Min.)",
                 "price": "0", "priceCurrency": "EUR"},
                {"@type": "Offer", "name": "Erstanamnese kompakt (60 Min.)",
                 "priceSpecification": {"@type": "PriceSpecification", "minPrice": "150", "priceCurrency": "EUR"}}],
        },
        {
            "@type": "Person", "@id": f"{D}/#nina-klimek", "name": "Nina Klimek",
            "jobTitle": "Heilpraktikerin", "worksFor": {"@id": f"{D}/#praxis"},
            "image": f"{D}/assets/nina-klimek-800.jpg",
            "hasCredential": {
                "@type": "EducationalOccupationalCredential",
                "credentialCategory": "Erlaubnis zur Ausübung der Heilkunde nach § 1 Abs. 1 Heilpraktikergesetz",
                "recognizedBy": {"@type": "GovernmentOrganization", "name": "Gesundheitsamt Berlin"},
                "dateCreated": "2024-04-18"},
            "memberOf": {"@type": "Organization", "name": "Berufs- und Fachverband Freie Heilpraktiker e.V.",
                         "url": "https://www.freieheilpraktiker.com"},
            "knowsAbout": ["Chelattherapie", "Schwermetallausleitung", "Schwermetalltest", "EDTA-Infusion",
                           "Infusionstherapie", "Orthomolekulare Medizin",
                           "Klinische Psycho-Neuro-Immunologie (kPNI)", "Darmgesundheit"],
            "sameAs": [MAIN_SITE, INSTAGRAM, DOCTOLIB],
        },
        {
            "@type": "MedicalTherapy", "@id": f"{D}/#chelattherapie", "name": "Chelattherapie",
            "alternateName": ["Chelat-Therapie", "Schwermetallausleitung", "EDTA-Infusion",
                              "EDTA-Chelattherapie"],
            "description": ("Infusionstherapie mit Chelatbildnern wie EDTA, die bestimmte "
                            "Metallionen binden und deren Ausscheidung über die Nieren ermöglichen. "
                            "Durchführung nach Anamnese und Labordiagnostik mit individueller "
                            "Planung und Verlaufskontrolle."),
            "procedureType": "https://schema.org/PercutaneousProcedure",
            "drug": {"@type": "Drug", "name": "EDTA (Ethylendiamintetraessigsäure)",
                     "nonProprietaryName": "Edetinsäure"},
            "preparation": "Ausführliche Anamnese, Labordiagnostik (Blut/Urin), Kontrolle der Nierenfunktion und des Mineralstoffstatus.",
            "howPerformed": "Langsame intravenöse Infusion in ruhiger Umgebung; Dosierung, Abstände und Anzahl individuell nach Befund.",
            "followup": "Verlaufskontrollen der Laborwerte, Ausgleich von Mineralstoffen, Anpassung des Therapieplans.",
            "contraindication": ["Eingeschränkte Nierenfunktion", "Schwangerschaft und Stillzeit"],
        },
        {
            "@type": "FAQPage", "@id": f"{D}/#faq",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ],
        },
        {
            "@type": "BreadcrumbList", "@id": f"{D}/#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Heilpraxis Nina Klimek", "item": MAIN_SITE},
                {"@type": "ListItem", "position": 2, "name": "Chelattherapie Berlin", "item": f"{D}/"}],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": g}, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# <head>-Block
# ---------------------------------------------------------------------------
def head(fonts_url, theme_color):
    D = DOMAIN
    analytics = (f'<script defer data-domain="{ANALYTICS_DOMAIN}" src="https://plausible.io/js/script.js"></script>\n'
                 '<script>window.plausible=window.plausible||function(){(window.plausible.q=window.plausible.q||[]).push(arguments)}</script>\n'
                 if ANALYTICS_DOMAIN else "")
    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(TITLE)}</title>
<meta name="description" content="{html.escape(DESC)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<link rel="canonical" href="{D}/">
<link rel="alternate" hreflang="de-DE" href="{D}/">
<link rel="alternate" hreflang="x-default" href="{D}/">
<meta name="author" content="Nina Klimek, Heilpraktikerin">
<meta name="theme-color" content="{theme_color}">
<meta name="geo.region" content="DE-BE">
<meta name="geo.placename" content="Berlin-Lichtenrade">
<!-- KI/LLM: maschinenlesbare Zusammenfassung -->
<link rel="alternate" type="text/markdown" href="{D}/index.md" title="Markdown-Version dieser Seite">
<link rel="help" type="text/plain" href="{D}/llms.txt">
<!-- Open Graph / Social -->
<meta property="og:type" content="website">
<meta property="og:locale" content="de_DE">
<meta property="og:site_name" content="Heilpraxis Nina Klimek">
<meta property="og:title" content="Chelattherapie in Berlin: Schwermetalle erkennen, gezielt ausleiten">
<meta property="og:description" content="{html.escape(DESC)}">
<meta property="og:url" content="{D}/">
<meta property="og:image" content="{D}/assets/og-chelattherapie.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Heilpraktikerin Nina Klimek, Berlin">
<meta name="twitter:card" content="summary_large_image">
<!-- Icons -->
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<!-- Schriften (vor Livegang lokal hosten, DSGVO, s. README) -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts_url}">
<link rel="preload" as="image" href="assets/nina-klimek.webp" type="image/webp">
{analytics}<style>{SHARED_CSS}</style>
<!-- Strukturierte Daten -->
<script type="application/ld+json">
{jsonld()}
</script>"""

# Gemeinsames CSS für alle Entwürfe (steht vor dem Entwurfs-CSS, das Farben und Feinheiten überschreibt):
# Menü-Button, ein-/ausblendende Handy-Leiste, Einblend-Animation, Praxis-Galerie, Silbentrennung
SHARED_CSS = """
html{-webkit-text-size-adjust:100%; text-size-adjust:100%}
.menu-btn{display:none; width:46px; height:46px; margin-left:10px; border-radius:50%; border:1px solid currentColor; background:transparent; color:inherit; cursor:pointer; flex:none; flex-direction:column; align-items:center; justify-content:center; gap:6px; padding:0}
.menu-btn span{display:block; width:18px; height:1.5px; background:currentColor; transition:transform .25s}
html.nav-open .menu-btn span:first-child{transform:translateY(3.75px) rotate(45deg)}
html.nav-open .menu-btn span:last-child{transform:translateY(-3.75px) rotate(-45deg)}
.mcta{transition:transform .35s ease, opacity .35s ease, visibility 0s}
html:not(.mcta-on) .mcta{transform:translateY(calc(100% + 28px)); opacity:0; visibility:hidden; transition:transform .35s ease, opacity .35s ease, visibility 0s .35s}
.js-reveal .rv{opacity:0; transform:translateY(22px); transition:opacity .7s ease, transform .7s cubic-bezier(.2,.7,.2,1)}
.js-reveal .rv.in{opacity:1; transform:none}
/* Bilder im Textfluss: .media (mit Bildunterschrift), .sec-split (Abschnittskopf links, Bild rechts), .call-img */
.media,.call-img{margin:0}
.media .ph,.call-img .ph{position:relative; overflow:hidden; border-radius:var(--r,14px); background:#E6E1D6; aspect-ratio:3/2}
.media img,.call-img img{position:absolute; inset:0; width:100%; height:100%; object-fit:cover}
.media figcaption{font-size:14px; line-height:1.5; margin-top:12px; opacity:.8}
.call-img{margin-bottom:30px}
.sec-split{display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:56px; align-items:end; margin-bottom:60px}
.sec-split .sec-head{margin-bottom:0}
/* Beim Hinscrollen zoomt das Bild sanft heraus, wie das Porträt im Hero */
.js-reveal .rv .ph img{transform:scale(1.1); transition:transform 1.6s cubic-bezier(.2,.7,.2,1)}
.js-reveal .rv.in .ph img{transform:none}
@media (max-width:1020px){
  .sec-split{grid-template-columns:minmax(0,1fr); gap:34px; align-items:start}
}
@media (max-width:640px){
  p,li,dd{-webkit-hyphens:auto; hyphens:auto}
  h1,h2,h3{overflow-wrap:break-word}
  /* Auf dem Handy randlos: klare Unterbrechung im Text */
  .media{margin-left:-16px; margin-right:-16px}
  .media .ph{border-radius:0; aspect-ratio:4/3}
  .media figcaption{padding:0 16px}
  .sec-split{gap:26px; margin-bottom:34px}
  .call-img{margin-bottom:24px}
}
@media (prefers-reduced-motion:reduce){.js-reveal .rv,.js-reveal .rv .ph img{opacity:1; transform:none; transition:none}}
"""

# Anruf-Verhalten (Desktop/Mobil) + Klick-Tracking; ohne ANALYTICS_DOMAIN passiert beim Tracking nichts
SCRIPTS = """<script>
(function () {
  var fine = window.matchMedia && matchMedia('(hover: hover) and (pointer: fine)').matches;
  var NUM = '%s';
  function where(el) {
    if (el.closest('.mcta')) return 'Mobil-Leiste';
    if (el.closest('header')) return 'Header';
    if (el.closest('.strip')) return 'Topbar';
    if (el.closest('footer')) return 'Footer';
    var s = el.closest('section');
    return s ? (s.id || (s.classList.contains('hero') ? 'Hero' : 'Seite')) : 'Seite';
  }
  function track(name, el) { if (window.plausible) window.plausible(name, { props: { Bereich: where(el) } }); }
  // Handy/Tablet: "Kostenloses Erstgespräch" ruft direkt an. Desktop: springt zum Erstgespräch-Abschnitt.
  if (!fine) document.querySelectorAll('[data-tel]').forEach(function (a) { a.href = a.getAttribute('data-tel'); });
  // Desktop: Anruf-Buttons kopieren die Nummer (die Nummer steht groß daneben).
  if (fine && navigator.clipboard) document.querySelectorAll('.js-call').forEach(function (a) {
    var t = a.querySelector('.t'); if (t) t.textContent = 'Nummer kopieren';
    a.addEventListener('click', function (e) {
      e.preventDefault();
      navigator.clipboard.writeText(NUM).then(function () {
        if (!t) return; t.textContent = 'Kopiert \u2713';
        setTimeout(function () { t.textContent = 'Nummer kopieren'; }, 2200);
      });
      track('Nummer kopiert', a);
    });
  });
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a || (fine && a.classList.contains('js-call'))) return;
    var h = a.getAttribute('href') || '';
    if (h.indexOf('tel:') === 0) track('Anruf', a);
    else if (h.indexOf('doctolib') > -1) track('Termin Doctolib', a);
    else if (h.indexOf('mailto:') === 0) track('E-Mail', a);
    else if (h === '#erstgespraech') track('Zum Erstgespräch', a);
  });

  var root = document.documentElement, IO = 'IntersectionObserver' in window;
  // Menü (Tablet/Handy)
  var mb = document.querySelector('.menu-btn');
  function menu(open) {
    root.classList.toggle('nav-open', open);
    if (mb) { mb.setAttribute('aria-expanded', open); mb.setAttribute('aria-label', open ? 'Menü schließen' : 'Menü öffnen'); }
  }
  if (mb) {
    mb.addEventListener('click', function () { menu(!root.classList.contains('nav-open')); });
    document.querySelectorAll('nav.main a').forEach(function (a) { a.addEventListener('click', function () { menu(false); }); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') menu(false); });
  }
  // Handy-Leiste nur zeigen, wenn gerade keine eigenen Anruf-/Termin-Buttons zu sehen sind
  if (document.querySelector('.mcta')) {
    if (IO) {
      var seen = [];
      var bar = new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          var i = seen.indexOf(e.target);
          if (e.isIntersecting && i < 0) seen.push(e.target); else if (!e.isIntersecting && i > -1) seen.splice(i, 1);
        });
        root.classList.toggle('mcta-on', seen.length === 0);
      });
      document.querySelectorAll('.hero, #erstgespraech, #kontakt, footer.site').forEach(function (el) { bar.observe(el); });
    } else root.classList.add('mcta-on');
  }
  // Dezentes Einblenden beim Scrollen (einmalig, aus bei "Bewegung reduzieren")
  if (IO && !(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches)) {
    var els = document.querySelectorAll('.sec-head, .glance-card, .spec, .metal, .mtable, .steps li, .timeline li, .flow > div, .care > div, .care li, .check, .media, div.callnow, section.callnow .wrap > *, .about > *, .faq-item, .contact-grid > *, .contact-card, .statement, .cols > div, .mech-text > div'
      + (matchMedia('(max-width: 640px)').matches ? ', .hero .portrait' : ''));  // Handy: Porträt liegt unter dem ersten Bildschirm
    root.classList.add('js-reveal');
    var rv = new IntersectionObserver(function (es) {
      var n = 0;
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.style.transitionDelay = Math.min(n++, 4) * 90 + 'ms';
        e.target.classList.add('in');
        rv.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -6%% 0px', threshold: 0.08 });
    els.forEach(function (el) { el.classList.add('rv'); rv.observe(el); });
  }
})();
</script>""" % PHONE_DE

# ---------------------------------------------------------------------------
DESIGNS = {
    # template                  -> output,                   fonts,                                                                                                          theme
    "entwurf-a.src.html": ("entwurf-a-salbei.html",
        "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Source+Sans+3:wght@300;400;600&display=swap",
        "#F5F1E8"),
    "entwurf-b.src.html": ("entwurf-b-klarheit.html",
        "https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap",
        "#FFFFFF"),
    "entwurf-c.src.html": ("entwurf-c-stille.html",
        "https://fonts.googleapis.com/css2?family=Marcellus&family=Figtree:wght@300;400;500;600&display=swap",
        "#101814"),
}

def main():
    # Optional nur einzelne Entwürfe bauen:  python _src/build.py a c   (ohne Angabe: alle)
    nur = {a.lower() for a in sys.argv[1:]}
    for src, (out, fonts, theme) in DESIGNS.items():
        if nur and src.split("-")[1][0] not in nur:
            continue
        p = ROOT / "_src" / src
        if not p.exists():
            print("fehlt:", src); continue
        t = p.read_text(encoding="utf-8")
        t = (t.replace("{{HEAD}}", head(fonts, theme))
              .replace("{{FAQ}}", faq_html())
              .replace("{{SCRIPTS}}", SCRIPTS)
              .replace("{{UPDATED}}", UPDATED)
              .replace("{{UPDATED_DE}}", UPDATED_DE)
              .replace("{{DOCTOLIB}}", DOCTOLIB)
              .replace("{{PHONE_INTL}}", PHONE_INTL)
              .replace("{{PHONE_DE}}", PHONE_DE)
              .replace("{{EMAIL}}", EMAIL)
              .replace("{{MAIN_SITE}}", MAIN_SITE)
              .replace("{{MAPS}}", MAPS))
        for k, v in IMAGES.items():
            t = t.replace("{{" + k + "}}", v)
        (ROOT / out).write_text(t, encoding="utf-8")
        print("geschrieben:", out)

    # Markdown-Version für KI-Systeme (index.md), FAQ aus derselben Quelle
    md = (ROOT / "_src" / "index.src.md").read_text(encoding="utf-8")
    faq_md = "\n\n".join(f"### {q}\n\n{a}" for q, a in FAQ)
    md = (md.replace("{{FAQ_MD}}", faq_md).replace("{{UPDATED}}", UPDATED)
            .replace("{{UPDATED_DE}}", UPDATED_DE).replace("{{DOCTOLIB}}", DOCTOLIB)
            .replace("{{PHONE_DE}}", PHONE_DE).replace("{{EMAIL}}", EMAIL))
    (ROOT / "index.md").write_text(md, encoding="utf-8")
    print("geschrieben: index.md")

if __name__ == "__main__":
    main()
