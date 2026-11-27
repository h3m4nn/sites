# -*- coding: utf-8 -*-
"""
SEO- und Release-Bausteine des Onepagers. Alle Werte kommen aus stammdaten.py, hier stehen keine Stammdaten.

Genutzt von build.py:
  head(fonts_url, theme, preload, modus, css, kopf_skript)   kompletter Inhalt von <head>
  jsonld(kompakt)                                            strukturierte Daten (Schema.org @graph)
  seo_dateien(ordner, seite, modus, theme)                   robots.txt, llms.txt, sitemap.xml, index.md (+ Manifest)
  release(e, seite, theme, probe, ziel)                      _release/ bauen und prüfen
Jeder Fehler löst stammdaten.BuildFehler aus (build.main fängt ihn ab). Ein fehlerhafter Release hinterlässt
FEHLER-NICHT-HOCHLADEN.txt im Zielordner.

Modi:  "entwurf"  Projektordner und Vorschau: noindex, kein Canonical, JSON-LD eingerückt
       "probe"    Test-Hosting (release --probe): noindex, robots.txt sperrt alles, X-Robots-Tag noindex
       "release"  Go-live: index,follow, Canonical, JSON-LD kompakt
"""
import base64, hashlib, html, json, pathlib, re, shutil, struct, urllib.robotparser
import xml.etree.ElementTree as ET

import stammdaten as S

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
MODI = ("entwurf", "probe", "release")
VORLAGEN = {"robots.txt": "robots.src.txt", "llms.txt": "llms.src.txt",
            "sitemap.xml": "sitemap.src.xml", "index.md": "index.src.md"}
ICONS = ("favicon.ico", "favicon.svg", "icon-192.png", "icon-512.png", "apple-touch-icon.png")
GENERIERT = ("index.html", *VORLAGEN, "404.html", "site.webmanifest", "_headers", ".htaccess")
FEHLERDATEI = "FEHLER-NICHT-HOCHLADEN.txt"
BILD_ENDUNGEN = (".webp", ".jpg", ".jpeg", ".png", ".avif", ".gif")
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]|&[nm]dash;|&#82(?:11|12);|&#x201[34];", re.I)   # Gedankenstriche


def _schreibe(pfad, text):
    pfad = pathlib.Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text, encoding="utf-8", newline="\n")   # UTF-8 ohne BOM, LF


# ---------------------------------------------------------------------------
# JSON-LD
# ---------------------------------------------------------------------------
def jsonld(kompakt=False):
    D, P = S.DOMAIN, S.PRAXIS
    pid, nid, tid = f"{D}/#praxis", f"{D}/#nina-klimek", f"{D}/#chelattherapie"
    wid, fid = f"{D}/#website", f"{D}/#faq"
    website = {"@type": "WebSite", "@id": wid, "url": f"{D}/", "name": S.SITE_NAME,
               "alternateName": ["Chelattherapie Berlin", S.host().removeprefix("www.")],
               "inLanguage": "de-DE", "publisher": {"@id": pid}}
    page = {"@type": "MedicalWebPage", "@id": f"{D}/#webpage", "url": f"{D}/",
            "name": S.TITLE, "description": S.DESC, "inLanguage": "de-DE",
            "isPartOf": {"@id": wid}, "about": {"@id": tid}, "hasPart": {"@id": fid},
            "audience": {"@type": "MedicalAudience", "audienceType": "Patient"},
            "primaryImageOfPage": {"@type": "ImageObject", "url": f"{D}/{S.PORTRAIT_JPG}",
                                   "width": S.PORTRAIT_W, "height": S.PORTRAIT_H},
            "dateModified": S.UPDATED, "author": {"@id": nid}}
    if S.PUBLISHED:
        page["datePublished"] = S.PUBLISHED
    if S.REVIEWED:
        page["lastReviewed"] = S.REVIEWED
        page["reviewedBy"] = {"@id": nid}
    praxis = {
        "@type": "MedicalBusiness", "@id": pid,
        "name": P["name"], "alternateName": S.SHORT_NAME,
        "description": ("Heilpraxis in Berlin-Lichtenrade mit Schwerpunkt Schwermetalltest "
                        "und individuell geplanter Chelattherapie (EDTA-Infusionen)."),
        "url": f"{D}/", "telephone": S.PHONE_INTL, "email": S.EMAIL,
        "image": [f"{D}/{S.PORTRAIT_JPG}", f"{D}/{S.OG_IMAGE}"],
        "priceRange": "€€", "currenciesAccepted": "EUR",
        "address": {"@type": "PostalAddress", "streetAddress": P["street"], "postalCode": P["zip"],
                    "addressLocality": P["city"], "addressRegion": "Berlin", "addressCountry": "DE"},
        "hasMap": S.GBP_URL or S.MAPS,
        "areaServed": [{"@type": "City", "name": "Berlin"},
                       {"@type": "Place", "name": "Berlin-Lichtenrade"},
                       {"@type": "Place", "name": "Tempelhof-Schöneberg"},
                       {"@type": "Place", "name": "Blankenfelde-Mahlow"},
                       {"@type": "Place", "name": "Teltow"}],
        "founder": {"@id": nid}, "employee": {"@id": nid},
        "knowsAbout": ["Chelattherapie", "Schwermetalltest", "Schwermetallausleitung", "EDTA-Infusion"],
        "sameAs": [u for u in (S.MAIN_SITE, S.INSTAGRAM, S.GBP_URL) if u],
        "potentialAction": {"@type": "ReserveAction", "name": "Termin buchen",
                            "target": {"@type": "EntryPoint", "urlTemplate": S.DOCTOLIB}},
        "makesOffer": [
            {"@type": "Offer", "name": "Kostenloses Erstgespräch am Telefon (10 Min.)",
             "price": "0", "priceCurrency": "EUR"},
            {"@type": "Offer", "name": "Erstanamnese kompakt (60 Min.)",
             "priceSpecification": {"@type": "PriceSpecification", "minPrice": "150", "priceCurrency": "EUR"}},
            {"@type": "Offer", "itemOffered": {
                "@type": "Service", "@id": f"{D}/#leistung", "name": "Chelattherapie mit EDTA-Infusionen",
                "serviceType": "Chelattherapie", "provider": {"@id": pid},
                "areaServed": {"@type": "City", "name": "Berlin"}}}],
    }
    if S.GEO:
        praxis["geo"] = {"@type": "GeoCoordinates", "latitude": S.GEO[0], "longitude": S.GEO[1]}
    if S.OPENING_HOURS:
        praxis["openingHoursSpecification"] = [{"@type": "OpeningHoursSpecification", **h} for h in S.OPENING_HOURS]
    if S.LOGO:
        praxis["logo"] = f"{D}/{S.LOGO}"
    person = {
        "@type": "Person", "@id": nid, "name": "Nina Klimek", "jobTitle": "Heilpraktikerin",
        "worksFor": {"@id": pid}, "url": S.UEBER_MICH, "image": f"{D}/{S.PORTRAIT_JPG}",
        "hasCredential": [
            {"@type": "EducationalOccupationalCredential",
             "credentialCategory": "Erlaubnis zur Ausübung der Heilkunde nach § 1 Abs. 1 Heilpraktikergesetz",
             "recognizedBy": {"@type": "GovernmentOrganization", "name": "Gesundheitsamt Berlin"},
             "dateCreated": "2024-04-18"},
            {"@type": "EducationalOccupationalCredential", "name": "Mikronährstoffberaterin",
             "recognizedBy": {"@type": "Organization", "name": "Akademie für Mikronährstoffmedizin"}}],
        "memberOf": {"@type": "Organization", "name": "Berufs- und Fachverband Freie Heilpraktiker e.V.",
                     "url": "https://www.freieheilpraktiker.com"},
        "knowsAbout": ["Chelattherapie", "Schwermetallausleitung", "Schwermetalltest", "EDTA-Infusion",
                       "Infusionstherapie", "Orthomolekulare Medizin",
                       "Klinische Psycho-Neuro-Immunologie (kPNI)", "Darmgesundheit"],
        "sameAs": [u for u in (S.DOCTOLIB, S.VERBAND_PROFIL) if u],
    }
    therapie = {
        "@type": "MedicalTherapy", "@id": tid, "name": "Chelattherapie",
        "alternateName": ["Chelat-Therapie", "Schwermetallausleitung", "EDTA-Infusion", "EDTA-Chelattherapie"],
        "description": ("Infusionstherapie mit Chelatbildnern wie EDTA, die bestimmte "
                        "Metallionen binden und deren Ausscheidung über die Nieren ermöglichen. "
                        "Durchführung nach Anamnese und Labordiagnostik mit individueller "
                        "Planung und Verlaufskontrolle."),
        "procedureType": "https://schema.org/PercutaneousProcedure",
        "drug": {"@type": "Drug", "name": "EDTA (Ethylendiamintetraessigsäure)", "nonProprietaryName": "Edetinsäure"},
        "preparation": ("Ausführliche Anamnese, Labordiagnostik (Blut/Urin), Kontrolle der Nierenfunktion "
                        "und des Mineralstoffstatus."),
        "howPerformed": ("Langsame intravenöse Infusion in ruhiger Umgebung; Dosierung, Abstände und Anzahl "
                         "individuell nach Befund."),
        "followup": "Verlaufskontrollen der Laborwerte, Ausgleich von Mineralstoffen, Anpassung des Therapieplans.",
        "contraindication": ["Eingeschränkte Nierenfunktion", "Schwangerschaft und Stillzeit"],
    }
    faq = {"@type": "FAQPage", "@id": fid,
           "mainEntity": [{"@type": "Question", "name": q, "url": f"{D}/#{anker}",
                           "acceptedAnswer": {"@type": "Answer", "text": a}}
                          for (q, a), anker in zip(S.FAQ, S.faq_ids())]}
    daten = {"@context": "https://schema.org", "@graph": [website, page, praxis, person, therapie, faq]}
    if kompakt:
        return json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(daten, ensure_ascii=False, indent=2)


def jsonld_script(kompakt=False):
    daten = jsonld(kompakt).replace("</", "<\\/")   # "</" maskieren, damit ein Text nie das <script> beendet
    return '<script type="application/ld+json">\n' + daten + "\n</script>"


# ---------------------------------------------------------------------------
# <head>
# ---------------------------------------------------------------------------
def _mime(pfad):
    return {".webp": "image/webp", ".avif": "image/avif", ".png": "image/png",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(pathlib.PurePosixPath(pfad).suffix.lower(), "")


def preload_link(href, media=""):
    """Bild-Preload mit hoher Priorität. media z. B. "(min-width: 641px)", leer = immer."""
    typ = _mime(href)
    return (f'<link rel="preload" as="image" href="{href}"' + (f' type="{typ}"' if typ else "")
            + ' fetchpriority="high"' + (f' media="{media}"' if media else "") + ">")


def analytics():
    if not S.ANALYTICS_DOMAIN:
        return ""
    return (f'<script defer data-domain="{S.ANALYTICS_DOMAIN}" src="https://plausible.io/js/script.js"></script>\n'
            '<script>window.plausible=window.plausible||function(){(window.plausible.q=window.plausible.q||[]).push(arguments)}</script>')


def head(fonts_url, theme_color, preload=None, modus="entwurf", css="", kopf_skript="", schrift_preloads=()):
    """Kompletter <head>-Inhalt.
    preload:           fertiger <link rel="preload"> (z. B. aus build.preload_link, mit imagesrcset) oder
                       (href, media) oder None (nur wo das Bild im ersten Bildschirm steht)
    kopf_skript:       kleines Inline-Skript, das vor dem ersten Zeichnen laufen muss (steht VOR dem Schrift-CSS,
                       sonst wartet es auf dessen Download)
    schrift_preloads:  nach dem lokalen Hosten der Schriften, z. B. ("fonts/manrope-600.woff2",)"""
    if modus not in MODI:
        raise ValueError(f"modus {modus!r}, erlaubt: {MODI}")
    D, e = S.DOMAIN, html.escape
    z = ['<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
         f"<title>{e(S.TITLE)}</title>",
         f'<meta name="description" content="{e(S.DESC)}">']
    if modus == "release":
        z += ['<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">',
              f'<link rel="canonical" href="{D}/">']
    else:   # Entwürfe, Vorschau- und Test-URLs nie indexieren, kein Canonical
        z.append('<meta name="robots" content="noindex, nofollow">')
    z += [f'<meta name="author" content="{e(S.AUTHOR)}">',
          f'<meta name="theme-color" content="{theme_color}">']
    if kopf_skript:
        z.append(kopf_skript.strip())
    if isinstance(preload, str) and preload.lstrip().startswith("<"):
        z.append(preload.strip())
    elif preload:
        z.append(preload_link(*preload) if isinstance(preload, (tuple, list)) else preload_link(preload))
    z += [f'<link rel="preload" as="font" type="font/woff2" href="{h}" crossorigin>' for h in schrift_preloads]
    if fonts_url:
        if fonts_url.startswith("https://fonts.googleapis.com/"):
            z += ['<link rel="preconnect" href="https://fonts.googleapis.com">',
                  '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>']
        z.append(f'<link rel="stylesheet" href="{e(fonts_url)}">')
    z += ['<link rel="alternate" type="text/markdown" href="index.md" title="Diese Seite als Markdown">',
          '<meta property="og:type" content="website">',
          '<meta property="og:locale" content="de_DE">',
          f'<meta property="og:site_name" content="{e(S.SITE_NAME)}">',
          f'<meta property="og:title" content="{e(S.OG_TITLE)}">',
          f'<meta property="og:description" content="{e(S.DESC)}">',
          f'<meta property="og:url" content="{D}/">',
          f'<meta property="og:image" content="{D}/{S.OG_IMAGE}">',
          f'<meta property="og:image:type" content="{_mime(S.OG_IMAGE)}">',
          f'<meta property="og:image:width" content="{S.OG_IMAGE_W}">',
          f'<meta property="og:image:height" content="{S.OG_IMAGE_H}">',
          f'<meta property="og:image:alt" content="{e(S.OG_IMAGE_ALT)}">',
          '<meta name="twitter:card" content="summary_large_image">',
          # ICO mit sizes="32x32" VOR dem SVG, damit Chrome das SVG nimmt; PNG 192 für Google (Vielfaches von 48)
          '<link rel="icon" href="favicon.ico" sizes="32x32">',
          '<link rel="icon" href="favicon.svg" type="image/svg+xml">',
          '<link rel="icon" href="icon-192.png" type="image/png" sizes="192x192">',
          '<link rel="apple-touch-icon" href="apple-touch-icon.png">',
          '<link rel="manifest" href="site.webmanifest">']
    if analytics():
        z.append(analytics())
    if css:
        z.append(f"<style>{css}</style>")
    z.append(jsonld_script(kompakt=(modus != "entwurf")))
    return "\n".join(z)


# ---------------------------------------------------------------------------
# Referenzen, Bilder, Versionen
# ---------------------------------------------------------------------------
ATTR = re.compile(r'\b(src|href|srcset|imagesrcset|poster)\s*=\s*"([^"]*)"', re.I)
CSSURL = re.compile(r"""url\(\s*(['"]?)([^'")]*)\1\s*\)""")


def _lokal(u):
    return bool(u) and not re.match(r"(?:[a-z][a-z0-9+.-]*:|//|#)", u.strip(), re.I)


def _kandidaten(attr, wert):
    if attr.lower() in ("srcset", "imagesrcset"):
        return [t.strip().split()[0] for t in wert.split(",") if t.strip()]
    return [wert.strip()]


def _pfad(u):
    return u.split("#", 1)[0].split("?", 1)[0].lstrip("/")


def referenzen(seite):
    """Alle lokalen Dateien, auf die die Seite verweist (Attribute, CSS url(), absolute DOMAIN-URLs z. B. og:image
    und JSON-LD), in Reihenfolge des ersten Auftretens, ohne ?v und #."""
    out = []
    for attr, wert in ATTR.findall(seite):
        out += [_pfad(u) for u in _kandidaten(attr, wert) if _lokal(u)]
    out += [_pfad(u) for _, u in CSSURL.findall(seite) if _lokal(u)]
    out += [_pfad(u) for u in re.findall(re.escape(S.DOMAIN) + r"/([^\"'\s<>()\\?#]*)", seite)]
    return [p for p in dict.fromkeys(out) if p]


def _groesster(srcset):
    """Adresse mit der größten w-Angabe aus einem srcset"""
    best = (-1, "")
    for t in srcset.split(","):
        if t.strip():
            url, *d = t.split()
            w = int(d[0][:-1]) if d and d[0].endswith("w") and d[0][:-1].isdigit() else 0
            if w >= best[0]:
                best = (w, url)
    return best[1]


def seo_bilder(seite):
    """Bilder, die auf der Seite zu sehen sind, je Bild nur die größte Variante (img src, größte Stufe aus
    <source srcset>, CSS url()), MIT ?v, für die Bild-Sitemap"""
    urls = []
    for m in re.finditer(r"<(img|source)\b([^>]*)>", seite, re.I):
        a = {k.lower(): w for k, w in ATTR.findall(m.group(2))}
        if m.group(1).lower() == "img" and a.get("src"):
            urls.append(a["src"])
        elif m.group(1).lower() == "source" and a.get("srcset"):
            urls.append(_groesster(a["srcset"]))
    urls += [u for _, u in CSSURL.findall(seite)]
    return [u.lstrip("/") for u in dict.fromkeys(urls)
            if _lokal(u) and _pfad(u).startswith("assets/") and _pfad(u).lower().endswith(BILD_ENDUNGEN)]


def _hash8(datei):
    return hashlib.sha256(pathlib.Path(datei).read_bytes()).hexdigest()[:8]


def versioniere(seite, basis):
    """Hängt ?v=<8 Zeichen sha256> an jeden Verweis auf assets/ und fonts/ (Attribute und CSS url()).
    Preload-href und <source srcset> bekommen dieselbe Adresse, der Preload greift also weiter."""
    basis, cache = pathlib.Path(basis), {}

    def v(u):
        if not _lokal(u) or "?" in u:
            return u
        pfad, _, frag = u.partition("#")
        p = pfad.lstrip("/")
        if not p.startswith(("assets/", "fonts/")):
            return u
        if not (basis / p).is_file():
            raise S.BuildFehler(f"versioniere: Datei fehlt: {p}")
        h = cache.setdefault(p, _hash8(basis / p))
        return f"{pfad}?v={h}" + (f"#{frag}" if frag else "")

    def attr(m):
        a, w = m.group(1), m.group(2)
        if a.lower() in ("srcset", "imagesrcset"):
            teile = []
            for t in w.split(","):
                if t.strip():
                    url, *rest = t.split()
                    teile.append(" ".join([v(url), *rest]))
            w = ", ".join(teile)
        else:
            w = v(w)
        return f'{a}="{w}"'

    seite = ATTR.sub(attr, seite)
    return CSSURL.sub(lambda m: f"url({m.group(1)}{v(m.group(2))}{m.group(1)})", seite)


# ---------------------------------------------------------------------------
# SEO-Dateien (robots.txt, llms.txt, sitemap.xml, index.md) und Manifest
# ---------------------------------------------------------------------------
def h1_text(seite):
    """Text der H1 so, wie ihn ein Mensch liest: <small>/<em>/<span> als ": " bzw. Leerzeichen, ohne Schlusspunkt"""
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", seite, re.S | re.I)
    if not m:
        raise S.BuildFehler("Keine <h1> in der Seite")
    inner = re.sub(r"<br\s*/?>", " ", m.group(1), flags=re.I)
    inner = re.sub(r"\s*<small\b[^>]*>", ": ", inner, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", inner)).replace(chr(0xAD), "")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*:(?:\s*:)+", ":", t)
    return t.strip().rstrip(".").strip()


def manifest_datei(theme):
    return json.dumps({
        "name": S.SITE_NAME, "short_name": S.SHORT_NAME, "lang": "de", "dir": "ltr",
        "start_url": "./", "display": "browser", "theme_color": theme, "background_color": theme,
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }, ensure_ascii=False, indent=2) + "\n"


def seo_dateien(ordner, seite, modus="entwurf", theme=None, vorlagen=None):
    """Schreibt robots.txt, llms.txt, sitemap.xml und index.md (und mit theme das Manifest) nach ordner.
    seite = das gebaute HTML, aus dem H1 und Bilder kommen. Prüft danach und bricht bei Fehlern ab."""
    ordner = pathlib.Path(ordner)
    vorlagen = {**VORLAGEN, **(vorlagen or {})}
    probe = modus == "probe"
    h1 = h1_text(seite)
    extra = dict(
        H1=h1,
        FAQ_MD="\n\n".join(f"### {q}\n\n{a}" for q, a in S.FAQ),
        SITEMAP_IMAGES="\n".join(f"    <image:image><image:loc>{html.escape(S.DOMAIN + '/' + b)}</image:loc></image:image>"
                                 for b in seo_bilder(seite)),
        FM_TITLE=json.dumps(h1, ensure_ascii=False), FM_DESC=json.dumps(S.DESC, ensure_ascii=False),
        FM_GEPRUEFT=f'geprueft: "{S.REVIEWED}"\n' if S.REVIEWED else "",
        ROBOTS_REGEL="Disallow: /" if probe else "Allow: /",
        ROBOTS_ZWECK=("# TESTAUFBAU: Diese Adresse dient nur zur Ansicht, alle Crawler sind ausgesperrt." if probe else
                      "# Alle Suchmaschinen, KI-Suchen und KI-Assistenten dürfen die ganze Seite lesen."),
    )
    v = {**S.werte(), **extra}
    texte = {out: S.fill((SRC / src).read_text(encoding="utf-8"), v, src) for out, src in vorlagen.items()}
    for out, t in texte.items():   # erst alles füllen (bricht bei Fehlern ab, bevor etwas geschrieben ist)
        _schreibe(ordner / out, t)
    if theme:
        _schreibe(ordner / "site.webmanifest", manifest_datei(theme))
    fehler = pruefe_seo_dateien(ordner, seite, modus)
    if fehler:
        raise S.BuildFehler("SEO-Dateien fehlerhaft:\n  " + "\n  ".join(fehler))


# ---------------------------------------------------------------------------
# 404, _headers, .htaccess
# ---------------------------------------------------------------------------
def _dunkel(farbe):
    h = farbe.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.5


def seite_404(theme):
    bg = theme
    fg = "#F2EEE6" if _dunkel(theme) else "#1E2721"
    e = html.escape
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Seite nicht gefunden | {e(S.SITE_NAME)}</title>
<meta name="robots" content="noindex">
<meta name="theme-color" content="{bg}">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>
html{{-webkit-text-size-adjust:100%;text-size-adjust:100%}}
body{{margin:0;min-height:100vh;min-height:100svh;display:grid;place-items:center;background:{bg};color:{fg};
  font:17px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
main{{box-sizing:border-box;width:100%;max-width:36rem;padding:48px 16px}}
.klein{{font-size:15px;opacity:.8;margin:0 0 12px}}
h1{{font-size:clamp(28px,7vw,40px);line-height:1.15;font-weight:600;margin:0 0 16px;text-wrap:balance}}
p{{margin:0 0 24px;text-wrap:pretty}}
a{{color:inherit;text-underline-offset:3px}}
.btn{{display:inline-flex;align-items:center;min-height:48px;padding:0 26px;border-radius:999px;background:{fg};color:{bg};
  text-decoration:none;font-weight:600}}
.btn:focus-visible,a:focus-visible{{outline:3px solid currentColor;outline-offset:3px}}
</style>
</head>
<body>
<main>
<p class="klein">Fehler 404</p>
<h1>Diese Seite gibt es leider nicht.</h1>
<p>Vielleicht ist der Link veraltet oder die Adresse wurde nicht ganz richtig eingegeben. Alle Informationen zur Chelattherapie finden Sie auf der Startseite.</p>
<p><a class="btn" href="/">Zur Startseite</a></p>
<p class="klein">{e(S.PRAXIS['name'])} · Telefon <a href="tel:{S.PHONE_INTL}">{e(S.PHONE_DE)}</a> · <a href="{e(S.DOCTOLIB)}" rel="noopener">Termin über Doctolib</a></p>
</main>
</body>
</html>
"""


SICHERHEIT = [
    ("Strict-Transport-Security", "max-age=31536000"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()"),
    ("X-Frame-Options", "SAMEORIGIN"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
]
SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.S | re.I)


def inline_skripte(seite):
    """Inhalte aller ausführbaren Inline-Skripte (ohne src, ohne Daten-Typ wie application/ld+json)"""
    out = []
    for attrs, body in SCRIPT.findall(seite):
        if re.search(r"\bsrc\s*=", attrs, re.I):
            continue
        t = re.search(r"""\btype\s*=\s*["']?([^"'\s>]*)""", attrs, re.I)
        if t and t.group(1).lower() not in ("", "text/javascript", "application/javascript", "module"):
            continue
        out.append(body)
    return out


def skript_hashes(seite):
    return list(dict.fromkeys("'sha256-" + base64.b64encode(hashlib.sha256(b.encode("utf-8")).digest()).decode() + "'"
                              for b in inline_skripte(seite)))


def csp(seite):
    gf = "fonts.googleapis.com" in seite
    pl = " https://plausible.io" if (S.ANALYTICS_DOMAIN or "plausible.io/js" in seite) else ""
    return ("default-src 'self'; script-src 'self' " + " ".join(skript_hashes(seite)) + pl
            + "; style-src 'self' 'unsafe-inline'" + (" https://fonts.googleapis.com" if gf else "")
            + "; img-src 'self' data:; font-src 'self'" + (" https://fonts.gstatic.com" if gf else "")
            + "; connect-src 'self'" + pl
            + "; frame-ancestors 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests")


def headers_datei(seite, probe=False):
    """_headers für Netlify und Cloudflare Pages. Cache-Control nur in Regeln, die sich nicht überschneiden
    (Cloudflare verbindet doppelte Header mit Komma), Sicherheits-Header nur unter /*."""
    D = S.DOMAIN
    z = ["# Erzeugt von _src/build.py release, nicht von Hand ändern.", "/*"]
    z += [f"  {k}: {v}" for k, v in SICHERHEIT]
    z.append(f"  Content-Security-Policy: {csp(seite)}")
    if probe:
        z.append("  X-Robots-Tag: noindex, nofollow")
    regeln = [
        ("/", ["Cache-Control: public, max-age=0, must-revalidate"]),
        ("/index.html", ["Cache-Control: public, max-age=0, must-revalidate"]),
        ("/index.md", ["Content-Type: text/markdown; charset=utf-8"]
         + ([] if probe else [f'Link: <{D}/>; rel="canonical"']) + ["Cache-Control: public, max-age=3600"]),
        ("/llms.txt", ["Content-Type: text/plain; charset=utf-8"] + ([] if probe else ["X-Robots-Tag: noindex"])
         + ["Cache-Control: public, max-age=3600"]),
        ("/robots.txt", ["Content-Type: text/plain; charset=utf-8", "Cache-Control: public, max-age=3600"]),
        ("/sitemap.xml", ["Content-Type: application/xml; charset=utf-8"] + ([] if probe else ["X-Robots-Tag: noindex"])
         + ["Cache-Control: public, max-age=3600"]),
        ("/404.html", [] if probe else ["X-Robots-Tag: noindex"]),
        ("/site.webmanifest", ["Content-Type: application/manifest+json; charset=utf-8", "Cache-Control: public, max-age=86400"]),
        ("/assets/*", ["Cache-Control: public, max-age=31536000, immutable"]),
        ("/fonts/*", ["Cache-Control: public, max-age=31536000, immutable"]),
        ("/favicon.ico", ["Cache-Control: public, max-age=604800"]),
        ("/favicon.svg", ["Cache-Control: public, max-age=604800"]),
        ("/apple-touch-icon.png", ["Cache-Control: public, max-age=604800"]),
        ("/icon-192.png", ["Cache-Control: public, max-age=604800"]),
        ("/icon-512.png", ["Cache-Control: public, max-age=604800"]),
    ]
    for pfad, kopf in regeln:
        if kopf:
            z += ["", pfad] + [f"  {k}" for k in kopf]
    return "\n".join(z) + "\n"


def htaccess_datei(seite, probe=False):
    D, H = S.DOMAIN, S.host()
    hre = H.replace(".", r"\.")
    if probe:
        umleitung = ["  # 1. Nur https (Test-Hosting: Host bleibt, wie er ist)",
                     "  RewriteCond %{HTTPS} !=on",
                     "  RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L,NE]"]
    else:
        umleitung = ["  # 1. Nur eine Adresse: https und " + H,
                     "  RewriteCond %{HTTPS} !=on [OR]",
                     f"  RewriteCond %{{HTTP_HOST}} !^{hre}$ [NC]",
                     f"  RewriteRule ^ https://{H}%{{REQUEST_URI}} [R=301,L,NE]"]
    z = ["# Erzeugt von _src/build.py release, nicht von Hand ändern.",
         "# Falls der Server mit Fehler 500 antwortet: Zeile \"Options -Indexes\" entfernen (manche Hoster erlauben sie nicht).",
         "Options -Indexes",
         "DirectoryIndex index.html",
         "ErrorDocument 404 /404.html",
         "AddDefaultCharset utf-8",
         "AddCharset utf-8 .html .md .txt .xml .webmanifest",
         "AddType text/markdown .md",
         "AddType text/plain .txt",
         "AddType application/xml .xml",
         "AddType application/manifest+json .webmanifest",
         "AddType image/webp .webp",
         "AddType image/avif .avif",
         "AddType font/woff2 .woff2",
         "",
         "<IfModule mod_rewrite.c>",
         "  RewriteEngine On",
         *umleitung,
         "  # 2. /index.html auf / umleiten",
         r"  RewriteCond %{THE_REQUEST} \s/index\.html[\s?]",
         r"  RewriteRule ^index\.html$ / [R=301,L]",
         "  # 3. Sicherheitsnetz: interne Dateien nie ausliefern, falls sie doch hochgeladen werden",
         r"  RewriteRule (^|/)_ - [R=404,L]",
         r"  RewriteRule ^(assets/platzhalter|assets/_roh)(/|$) - [R=404,L,NC]",
         r"  RewriteRule ^(README\.md|entwurf-[^/]*\.html|.*\.(py|mjs))$ - [R=404,L,NC]",
         "  # 4. Optional: Agenten, die ausdrücklich Markdown anfragen, bekommen index.md",
         "  # RewriteCond %{HTTP_ACCEPT} text/markdown [NC]",
         "  # RewriteRule ^$ /index.md [L]",
         "</IfModule>",
         "",
         "<IfModule mod_headers.c>"]
    z += [f'  Header always set {k} "{v}"' for k, v in SICHERHEIT]
    z.append(f'  Header always set Content-Security-Policy "{csp(seite)}"')
    if probe:
        z.append('  Header always set X-Robots-Tag "noindex, nofollow"')
    z += ['  <FilesMatch "\\.html$">',
          '    Header set Cache-Control "public, max-age=0, must-revalidate"',
          "  </FilesMatch>",
          '  <FilesMatch "^(robots\\.txt|llms\\.txt|sitemap\\.xml|index\\.md)$">',
          '    Header set Cache-Control "public, max-age=3600"',
          "  </FilesMatch>",
          '  <FilesMatch "\\.(webp|avif|jpe?g|woff2)$">',
          '    Header set Cache-Control "public, max-age=31536000, immutable"',
          "  </FilesMatch>",
          '  <FilesMatch "\\.(ico|png|svg|webmanifest)$">',
          '    Header set Cache-Control "public, max-age=604800"',
          "  </FilesMatch>"]
    if not probe:
        z += ['  <Files "index.md">',
              f'    Header set Link "<{D}/>; rel=\\"canonical\\""',
              "  </Files>",
              '  <FilesMatch "^(llms\\.txt|sitemap\\.xml|404\\.html)$">',
              '    Header set X-Robots-Tag "noindex"',
              "  </FilesMatch>"]
    z += ["  # Bei aktivierter Markdown-Aushandlung (Punkt 4) zusätzlich:",
          "  # <If \"%{REQUEST_URI} == '/'\">",
          '  #   Header append Vary "Accept"',
          "  # </If>",
          "</IfModule>"]
    return "\n".join(z) + "\n"


# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------
def _intern(p):
    """Pfade, die nie live gehen: alles mit _ am Anfang eines Pfadteils, Quellen, Entwürfe, README"""
    teile = p.split("/")
    name = teile[-1].lower()
    return (any(t.startswith("_") for t in teile) or name == "readme.md" or name.endswith((".py", ".mjs", ".src.html"))
            or re.fullmatch(r"entwurf-.*\.html", name) is not None or ".src." in name)


def _indexnow_datei(rel, f):
    return (re.fullmatch(r"[A-Za-z0-9-]{8,128}\.txt", rel) is not None
            and f.read_text(encoding="utf-8", errors="ignore").strip() == rel[:-4])


def _raeume_auf(ziel):
    """Entfernt NUR Dateien, die ein früherer Release erzeugt oder aus dem Projekt kopiert hat.
    Alles andere (eigene Dateien, ältere Fassungen eines Bildes) führt zum Abbruch, damit nichts verloren geht."""
    ziel = pathlib.Path(ziel).resolve()
    root = ROOT.resolve()
    if ziel == root or ziel in root.parents or (root in ziel.parents and not ziel.name.startswith("_release")):
        raise S.BuildFehler(f"Release-Ziel {ziel} ist nicht erlaubt (Projektordner, darüber oder im Projekt ohne _release im Namen).")
    if not ziel.exists():
        ziel.mkdir(parents=True)
        return
    projekt = {}
    for d in ("assets", "fonts"):
        for q in (root / d).rglob("*") if (root / d).exists() else []:
            if q.is_file():
                projekt.setdefault(_hash8(q), q)
    weg, fremd = [], []
    for f in sorted(p for p in ziel.rglob("*") if p.is_file()):
        rel = f.relative_to(ziel).as_posix()
        q = root / rel
        if rel in GENERIERT or rel == FEHLERDATEI or _indexnow_datei(rel, f):
            weg.append(f)
        elif q.is_file() and q.read_bytes() == f.read_bytes():
            weg.append(f)
        elif rel.startswith(("assets/", "fonts/")) and _hash8(f) in projekt:
            weg.append(f)   # Kopie einer Projektdatei, die inzwischen anders heißt
        else:
            fremd.append(rel)
    if fremd:
        raise S.BuildFehler("In " + str(ziel) + " liegen Dateien, die kein Release erzeugt hat oder die von der "
                 "Projektfassung abweichen:\n  " + "\n  ".join(fremd)
                 + "\nBitte selbst wegräumen (z. B. nach _archiv/_zu_loeschen) oder in stammdaten.RELEASE_EXTRA "
                   "aufnehmen, dann neu starten.")
    for f in weg:
        f.unlink()
    for d in sorted((p for p in ziel.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            d.rmdir()   # nur leere Ordner
        except OSError:
            pass


def release(e, seite, theme, probe=False, ziel=None):
    """Baut den Upload-Ordner aus der gebauten Seite (head mit modus "release" bzw. "probe").
    e: Entwurf a/b/c (nur für die Meldung). Bricht bei jedem Fehler ab. Gibt den Zielordner zurück."""
    modus = "probe" if probe else "release"
    ziel = pathlib.Path(ziel) if ziel else ROOT / "_release"
    if not probe:
        stop = []
        if S.DOMAIN == S.DOMAIN_PLATZHALTER:
            stop.append(f"DOMAIN ist noch der Platzhalter {S.DOMAIN_PLATZHALTER} (stammdaten.py).")
        offen = [k for k, v in S.FREIGABEN.items() if not v]
        if offen:
            stop.append("Go-live-Freigaben offen (stammdaten.FREIGABEN): " + ", ".join(offen))
        if stop:
            raise S.BuildFehler("Release abgebrochen:\n  " + "\n  ".join(stop)
                     + "\nZum Testen auf einer Vorschau-Adresse: python _src/build.py release " + e + " --probe")
    _raeume_auf(ziel)
    try:
        return _baue_release(e, seite, theme, probe, modus, ziel)
    except S.BuildFehler as err:
        if not (ziel / FEHLERDATEI).exists():
            _abbruch(ziel, [str(err)])
        raise


def _baue_release(e, seite, theme, probe, modus, ziel):
    fehler = []
    kopieren = [r for r in dict.fromkeys([*referenzen(seite), *ICONS, S.OG_IMAGE, *S.RELEASE_EXTRA])
                if r not in GENERIERT]
    for r in kopieren:
        q = ROOT / r
        if _intern(r) and r not in S.RELEASE_EXTRA:
            fehler.append(f"Seite verweist auf eine interne Datei: {r}")
        elif not q.is_file():
            fehler.append(f"fehlt im Projektordner: {r}")
        else:
            (ziel / r).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(q, ziel / r)
    if fehler:
        _abbruch(ziel, fehler)
    seite = versioniere(seite, ziel)
    _schreibe(ziel / "index.html", seite)
    seo_dateien(ziel, seite, modus, theme=theme)
    _schreibe(ziel / "404.html", seite_404(theme))
    if S.HOSTING in ("", "pages"):
        _schreibe(ziel / "_headers", headers_datei(seite, probe))
    if S.HOSTING in ("", "apache"):
        _schreibe(ziel / ".htaccess", htaccess_datei(seite, probe))
    if S.INDEXNOW_KEY:
        if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", S.INDEXNOW_KEY):
            _abbruch(ziel, ["INDEXNOW_KEY: 8 bis 128 Zeichen aus a-z, A-Z, 0-9 und -"])
        _schreibe(ziel / f"{S.INDEXNOW_KEY}.txt", S.INDEXNOW_KEY)
    fehler, warnungen = pruefe_release(ziel, modus)
    for w in warnungen:
        print("WARNUNG:", w)
    if fehler:
        _abbruch(ziel, fehler)
    dateien = sorted(p for p in ziel.rglob("*") if p.is_file())
    groesse = sum(p.stat().st_size for p in dateien)
    print(f"Release OK ({modus}, Entwurf {e.upper()}): {ziel}  {len(dateien)} Dateien, {groesse / 1024:.0f} KB")
    for p in dateien:
        print(f"  {p.relative_to(ziel).as_posix():44} {p.stat().st_size:>9,} B".replace(",", "."))
    print("Hochladen: nur den INHALT dieses Ordners." + (" (Test-Hosting, noindex)" if probe else ""))
    return ziel


def _abbruch(ziel, fehler):
    _schreibe(pathlib.Path(ziel) / FEHLERDATEI, "Dieser Release ist fehlerhaft und darf nicht hochgeladen werden:\n"
              + "\n".join(fehler) + "\n")
    raise S.BuildFehler("Release FEHLERHAFT, nicht hochladen:\n  " + "\n  ".join(fehler))


# ---------------------------------------------------------------------------
# Selbsttest
# ---------------------------------------------------------------------------
def _sichtbar(h):
    """HTML ohne script, style und Kommentare (Tags und Attribute bleiben: alt, title, content zählen mit)"""
    h = re.sub(r"<(script|style)\b.*?</\1\s*>", " ", h, flags=re.S | re.I)
    return re.sub(r"<!--.*?-->", " ", h, flags=re.S)


def _robots_pruefen(t, probe):
    f = []
    zeilen = t.splitlines()
    ua = [i for i, z in enumerate(zeilen) if z.strip().lower().startswith("user-agent:")]
    regeln = [i for i, z in enumerate(zeilen) if re.match(r"\s*(allow|disallow)\s*:", z, re.I)]
    bloecke, drin = 0, False
    for z in zeilen:
        s = z.strip()
        if s.startswith("#"):
            continue
        if s.lower().startswith("user-agent:"):
            bloecke += (not drin)
            drin = True
        else:
            drin = False
    if bloecke != 1:
        f.append(f"robots.txt: {bloecke} Gruppen statt genau einer")
    if ua and regeln and any(not zeilen[i].strip() for i in range(ua[0], regeln[-1])):
        f.append("robots.txt: Leerzeile innerhalb der Gruppe")
    if f"Sitemap: {S.DOMAIN}/sitemap.xml" not in zeilen:
        f.append("robots.txt: Sitemap-Zeile mit DOMAIN fehlt")
    if not regeln:
        return f + ["robots.txt: keine Allow- oder Disallow-Regel"]
    bots = [zeilen[i].split(":", 1)[1].strip() for i in ua] + ["IrgendeinBot"]
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(zeilen)
    falsch = [b for b in bots if rp.can_fetch(b, "/") == probe]
    if falsch:
        f.append(f"robots.txt: '/' für {', '.join(falsch[:4])} {'erlaubt' if probe else 'gesperrt'}")
    # Gruppenlogik: eine zusätzliche Sperre muss für JEDEN Bot gelten. Sie steht vor der vorhandenen Regel, damit
    # der First-Match-Parser von Python und der Longest-Match nach RFC 9309 dasselbe Ergebnis liefern.
    r = regeln[0]
    test = zeilen[:r] + ["Disallow: /_gruppentest/"] + zeilen[r:]
    rp2 = urllib.robotparser.RobotFileParser()
    rp2.parse(test)
    durch = [b for b in bots if rp2.can_fetch(b, "/_gruppentest/x")]
    if durch:
        f.append(f"robots.txt: Zusatzregel greift nicht für {', '.join(durch[:4])}")
    return f


def _llms_pruefen(t):
    f, z = [], t.splitlines()
    if not z or not z[0].startswith("# "):
        f.append("llms.txt: erste Zeile ist keine H1")
    if not any(l.startswith("> ") for l in z[1:6]):
        f.append("llms.txt: Blockzitat nach der H1 fehlt")
    h2 = False
    for i, l in enumerate(z):
        if i and l.startswith("# "):
            f.append("llms.txt: zweite H1")
        if l.startswith("## "):
            h2 = True
            continue
        if h2 and l.strip() and not re.fullmatch(r"- \[[^\]]+\]\([^)\s]+\)(: .+)?", l):
            f.append(f"llms.txt: unter H2 nur Linklisten: {l[:60]}")
    return f


def _md_pruefen(t, seite):
    f = []
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    if not m:
        f.append("index.md: Front Matter fehlt")
    else:
        for z in m.group(1).splitlines():
            if not re.fullmatch(r'[a-z_]+: ".*"', z):
                f.append(f"index.md: Front-Matter-Zeile ohne Anführungszeichen: {z}")
    h1 = re.search(r"^# (.+)$", t, re.M)
    if not h1 or h1.group(1).strip() != h1_text(seite):
        f.append("index.md: H1 weicht von der H1 der Seite ab")
    if S.HINWEIS not in t:
        f.append("index.md: Pflichthinweis fehlt")
    if not S.REVIEWED and re.search(r"^geprueft:|verantwortlich und geprüft", t, re.M):
        f.append("index.md: nennt eine fachliche Prüfung, REVIEWED ist leer")
    return f


def pruefe_seo_dateien(ordner, seite, modus):
    """Prüft robots.txt, llms.txt, sitemap.xml, index.md in ordner. Gibt eine Fehlerliste zurück."""
    ordner, f = pathlib.Path(ordner), []
    probe = modus == "probe"
    texte = {n: (ordner / n).read_text(encoding="utf-8") for n in VORLAGEN if (ordner / n).is_file()}
    for n in VORLAGEN:
        if n not in texte:
            f.append(f"{n} fehlt")
    for n, t in texte.items():
        if S.REST.search(t):
            f.append(f"{n}: unersetzter Platzhalter {S.REST.search(t).group(0)}")
        if DASH.search(t):
            f.append(f"{n}: Gedankenstrich (U+2013/U+2014)")
        if t.startswith(chr(0xFEFF)) or "\r" in t:
            f.append(f"{n}: BOM oder CRLF")
    if "robots.txt" in texte:
        f += _robots_pruefen(texte["robots.txt"], probe)
    if "llms.txt" in texte:
        f += _llms_pruefen(texte["llms.txt"])
    if "index.md" in texte:
        f += _md_pruefen(texte["index.md"], seite)
    if "sitemap.xml" in texte:
        try:
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "i": "http://www.google.com/schemas/sitemap-image/1.1"}
            x = ET.fromstring(texte["sitemap.xml"].encode("utf-8"))
            locs = [e.text for e in x.findall("s:url/s:loc", ns)]
            if locs != [f"{S.DOMAIN}/"]:
                f.append(f"sitemap.xml: loc {locs} statt {S.DOMAIN}/")
            if [e.text for e in x.findall("s:url/s:lastmod", ns)] != [S.UPDATED]:
                f.append("sitemap.xml: lastmod ist nicht UPDATED")
            for e in x.findall("s:url/i:image/i:loc", ns):
                if not e.text.startswith(S.DOMAIN + "/"):
                    f.append(f"sitemap.xml: Bild außerhalb der Domain: {e.text}")
        except ET.ParseError as err:
            f.append(f"sitemap.xml: kein gültiges XML ({err})")
    return f


def _png(p):
    """(Breite, Höhe, Farbtyp, hat tRNS) eines PNG. Farbtyp 2 = RGB, 6 = RGBA, 4 = Grau mit Alpha."""
    b = pathlib.Path(p).read_bytes()
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", b[16:24])
    i, chunks = 8, set()
    while i + 8 <= len(b):
        n, typ = struct.unpack(">I4s", b[i:i + 8])
        chunks.add(typ)
        i += 12 + n
    return w, h, b[25], b"tRNS" in chunks


def _ico_groessen(p):
    b = pathlib.Path(p).read_bytes()
    n = struct.unpack("<H", b[4:6])[0]
    return sorted({b[6 + 16 * i] or 256 for i in range(n)})


def _jsonld_pruefen(seite):
    f = []
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', seite, re.S)
    if not m:
        return ["index.html: JSON-LD fehlt"]
    try:
        d = json.loads(m.group(1))
    except ValueError as err:
        return [f"JSON-LD nicht lesbar: {err}"]
    ids, leer, typen = [], [], []

    def lauf(o, pfad):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "@id":
                    ids.append(v)
                if k == "@type":
                    typen.extend(v if isinstance(v, list) else [v])
                if v in ("", None, [], {}):
                    leer.append(f"{pfad}.{k}")
                lauf(v, f"{pfad}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                lauf(v, f"{pfad}[{i}]")

    lauf(d, "")
    txt = m.group(1)
    for verboten in ("BreadcrumbList", "availableService", "speakable", "adverseOutcome", "LocalBusiness"):
        if f'"{verboten}"' in txt:
            f.append(f"JSON-LD enthält {verboten}")
    f += [f"JSON-LD: @id außerhalb der Domain: {i}" for i in ids if not i.startswith(S.DOMAIN + "/")]
    f += [f"JSON-LD: leerer Wert {p}" for p in leer]
    if ("reviewedBy" in txt) != bool(S.REVIEWED) or ("datePublished" in txt) != bool(S.PUBLISHED):
        f.append("JSON-LD: reviewedBy/datePublished passen nicht zu REVIEWED/PUBLISHED")
    fragen = [q for g in d.get("@graph", []) if g.get("@type") == "FAQPage" for q in g["mainEntity"]]
    if len(fragen) != len(S.FAQ):
        f.append(f"JSON-LD: {len(fragen)} Fragen statt {len(S.FAQ)}")
    ids_html = set(re.findall(r'\bid="([^"]+)"', seite))
    for q in fragen:
        anker = q.get("url", "").partition("#")[2]
        if anker not in ids_html:
            f.append(f"JSON-LD: Question.url #{anker} hat kein Ziel auf der Seite (id im FAQ fehlt)")
    return f


def pruefe_release(ziel, modus="release"):
    """Selbsttest des Upload-Ordners. Gibt (fehler, warnungen) zurück."""
    ziel = pathlib.Path(ziel)
    probe = modus == "probe"
    f, w = [], []
    seite = (ziel / "index.html").read_text(encoding="utf-8")
    s404 = (ziel / "404.html").read_text(encoding="utf-8")
    f += pruefe_seo_dateien(ziel, seite, modus)
    # Platzhalter und Domain in allen Textdateien
    textdateien = [p for p in ziel.rglob("*") if p.is_file()
                   and (p.suffix.lower() in (".html", ".md", ".txt", ".xml", ".webmanifest") or p.name in ("_headers", ".htaccess"))]
    for p in textdateien:
        t = p.read_text(encoding="utf-8", errors="ignore")
        rel = p.relative_to(ziel).as_posix()
        if S.REST.search(t):
            f.append(f"{rel}: unersetzter Platzhalter {S.REST.search(t).group(0)}")
        if S.DOMAIN != S.DOMAIN_PLATZHALTER and S.host(S.DOMAIN_PLATZHALTER) in t:
            f.append(f"{rel}: enthält noch die Platzhalter-Domain")
    # Stilregel: keine Gedankenstriche im sichtbaren Text
    for n, t in (("index.html", seite), ("404.html", s404)):
        if DASH.search(_sichtbar(t)):
            f.append(f"{n}: Gedankenstrich im Text")
    # Indexierung
    idx = re.search(r'<meta name="robots" content="([^"]+)"', seite)
    can = re.search(r'<link rel="canonical" href="([^"]+)"', seite)
    if probe:
        if not idx or "noindex" not in idx.group(1) or can:
            f.append("index.html: Probe-Build muss noindex tragen und darf kein Canonical haben")
    else:
        if not idx or not idx.group(1).startswith("index, follow") or not can or can.group(1) != f"{S.DOMAIN}/":
            f.append("index.html: braucht index, follow und Canonical auf DOMAIN/")
    if 'name="robots" content="noindex' not in s404:
        f.append("404.html: noindex fehlt")
    # Inhalte, die überall gleich sein müssen
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", _sichtbar(seite))).split())
    if " ".join(S.HINWEIS.split()) not in text:
        f.append("index.html: Pflichthinweis (stammdaten.HINWEIS) fehlt oder weicht ab")
    if not S.REVIEWED and re.search(r"verantwortlich und gepr(ü|&uuml;)ft", seite):
        f.append("index.html: nennt „geprüft“, REVIEWED ist leer")
    f += _jsonld_pruefen(seite)
    # Verweise, Versionen, erlaubte Dateien
    refs = referenzen(seite) + referenzen(s404)
    for r in dict.fromkeys(refs):
        if not (ziel / r).is_file():
            f.append(f"Verweis ohne Datei im Release: {r}")
    for pfad, h in re.findall(r"""((?:assets|fonts)/[^"'\s?#),]+)\?v=([0-9a-f]+)""", seite):
        if (ziel / pfad).is_file() and _hash8(ziel / pfad) != h:
            f.append(f"?v passt nicht zum Inhalt: {pfad}")
    erlaubt = set(GENERIERT) | set(ICONS) | set(refs) | set(S.RELEASE_EXTRA) | {S.OG_IMAGE}
    if S.INDEXNOW_KEY:
        erlaubt.add(f"{S.INDEXNOW_KEY}.txt")
    for p in ziel.rglob("*"):
        if p.is_file():
            rel = p.relative_to(ziel).as_posix()
            if rel not in erlaubt:
                f.append(f"nicht erlaubte Datei im Release: {rel}")
            elif _intern(rel) and rel not in GENERIERT and rel not in S.RELEASE_EXTRA:
                f.append(f"interne Datei im Release: {rel}")
    # Bilder: Platzhalter und Vorschaubilder
    platz = [r for r in refs if r.startswith("assets/platzhalter/")]
    vorschau = [r for r in refs if r.startswith("assets/vorschau/")]
    if platz:
        (w if probe else f).append("Platzhalterbilder im Release: " + ", ".join(platz))
    if vorschau:
        w.append("Vorschaubilder (Rechte ungeklärt) im Release: " + ", ".join(vorschau))
    # Schriften, Skripte, CSP
    if "fonts.googleapis.com" in seite:
        (w if probe else f).append("Schriften kommen noch von Google Fonts (DSGVO, README Pflicht 5): lokal hosten")
    if re.search(r"\son[a-z]+\s*=", _sichtbar(seite).split("</head>", 1)[-1], re.I) or "javascript:" in seite:
        f.append("index.html: Inline-Eventhandler oder javascript:-Link (von der CSP blockiert)")
    hashes = skript_hashes(seite)
    for n in ("_headers", ".htaccess"):
        if (ziel / n).is_file():
            t = (ziel / n).read_text(encoding="utf-8")
            fehlend = [h for h in hashes if h not in t]
            if fehlend:
                f.append(f"{n}: CSP-Hash fehlt für {len(fehlend)} Inline-Skript(e)")
            if ("fonts.googleapis.com" in seite) != ("fonts.googleapis.com" in t):
                f.append(f"{n}: CSP und Google Fonts passen nicht zusammen")
            if probe != ("X-Robots-Tag: noindex, nofollow" in t or 'X-Robots-Tag "noindex, nofollow"' in t):
                f.append(f"{n}: X-Robots-Tag passt nicht zum Modus")
    if not S.HOSTING:
        w.append('HOSTING ist leer: _headers UND .htaccess liegen im Release. In stammdaten.py "apache" oder "pages" eintragen.')
    # Manifest und Icons
    try:
        man = json.loads((ziel / "site.webmanifest").read_text(encoding="utf-8"))
        for i in man["icons"]:
            info = _png(ziel / i["src"]) if (ziel / i["src"]).is_file() else None
            if not info or f"{info[0]}x{info[1]}" != i["sizes"]:
                f.append(f"Manifest-Icon {i['src']} fehlt oder hat nicht {i['sizes']}")
    except (OSError, ValueError, KeyError) as err:
        f.append(f"site.webmanifest: {err}")
    at = _png(ziel / "apple-touch-icon.png") if (ziel / "apple-touch-icon.png").is_file() else None
    if not at or at[:2] != (180, 180) or at[2] in (4, 6) or at[3]:
        f.append("apple-touch-icon.png: muss 180 x 180 und ohne Transparenz sein")
    if (ziel / "favicon.ico").is_file() and _ico_groessen(ziel / "favicon.ico") != [16, 32, 48]:
        f.append("favicon.ico: muss 16, 32 und 48 px enthalten")
    # Bildmaße, die in JSON-LD und og:image als Zahl stehen
    try:
        from PIL import Image
        for rel, soll in ((S.PORTRAIT_JPG, (S.PORTRAIT_W, S.PORTRAIT_H)), (S.OG_IMAGE, (S.OG_IMAGE_W, S.OG_IMAGE_H))):
            if (ziel / rel).is_file():
                with Image.open(ziel / rel) as im:
                    if im.size != soll:
                        f.append(f"{rel}: {im.size[0]} x {im.size[1]} statt {soll[0]} x {soll[1]} (stammdaten.py anpassen)")
    except ImportError:
        w.append("Pillow fehlt: Bildmaße für JSON-LD und og:image nicht geprüft")
    # Hinweise
    if not probe and not S.REVIEWED:
        w.append("REVIEWED ist leer: Seite, index.md und JSON-LD nennen keine fachliche Prüfung (bis Nina freigibt).")
    if not probe and not S.PUBLISHED:
        w.append("PUBLISHED ist leer: beim ersten Go-live das Datum eintragen (danach nie mehr ändern).")
    neuer = [p.relative_to(ROOT).as_posix() for p in _inhaltsquellen() if _datum(p) > S.UPDATED]
    if neuer:
        w.append(f"{len(neuer)} Inhaltsquelle(n) jünger als UPDATED ({S.UPDATED}), z. B. {neuer[0]}. "
                 "Inhalt geändert? Dann UPDATED in stammdaten.py anpassen (lastmod muss ehrlich sein).")
    return f, w


def _inhaltsquellen():
    """Dateien, deren Änderung den Seiteninhalt ändert: Vorlagen, Stammdaten (mit FAQ), Bilder (ohne _roh)"""
    q = [p for p in SRC.glob("*") if p.is_file() and (".src." in p.name or p.name == "stammdaten.py")]
    if (ROOT / "assets").exists():
        q += [p for p in (ROOT / "assets").rglob("*") if p.is_file() and "_roh" not in p.parts]
    return q


def _datum(p):
    import datetime
    return datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()
