# -*- coding: utf-8 -*-
"""
Stammdaten des Onepagers: die EINZIGE Quelle aller Werte (Domain, Praxis, Kontakt, Datum, Texte für Kopf und
strukturierte Daten, FAQ, Bildpfade, Go-live-Schalter). build.py, seo.py und alle Vorlagen in _src/ lesen von hier.

Einen Wert nur hier ändern, dann neu bauen:   python _src/build.py
Platzhalter in Vorlagen: {{NAME}} (Liste: werte() unten). fill() ersetzt sie und bricht ab, wenn einer keinen Wert hat.
Leere Konstanten ("", None, []) erscheinen nirgends, auch nicht im JSON-LD. Nichts schätzen, nur echte Angaben.
"""
import re, unicodedata, urllib.parse

# ---------------------------------------------------------------------------
# Domain und Datum
# ---------------------------------------------------------------------------
DOMAIN_PLATZHALTER = "https://www.chelattherapie-berlin.de"
DOMAIN = DOMAIN_PLATZHALTER   # echte Domain (mit https://, ohne / am Ende) eintragen, sonst bricht der Release ab
UPDATED = "2026-09-30"        # letzte INHALTLICHE Änderung: lastmod, dateModified, „Stand“ auf Seite, index.md, llms.txt
PUBLISHED = ""                # Go-live-Datum JJJJ-MM-TT, einmal eintragen und danach nie mehr ändern
REVIEWED = ""                 # Datum, an dem Nina die Texte fachlich freigegeben hat. Bis dahin leer, dann steht
                              # nirgends „geprüft“ (Footer, index.md, JSON-LD reviewedBy und lastReviewed)


def host(domain=None):
    """Host ohne Schema, z. B. www.chelattherapie-berlin.de"""
    return (domain or DOMAIN).split("://", 1)[1].rstrip("/")


HOST = host()

# ---------------------------------------------------------------------------
# Seite: Titel, Beschreibung, Name, Bilder für Vorschau und strukturierte Daten
# ---------------------------------------------------------------------------
TITLE    = "Chelattherapie Berlin | Schwermetallausleitung bei Nina Klimek"
DESC     = ("Chelattherapie in Berlin-Lichtenrade: Schwermetalltest und "
            "individuell geplante Ausleitung bei Heilpraktikerin Nina Klimek. "
            "Kostenloses Erstgespräch.")
SITE_NAME  = "Heilpraxis Nina Klimek"   # WebSite.name und og:site_name: kurz und überall gleich
SHORT_NAME = "Heilpraxis Klimek"        # alternateName der Praxis, short_name im Manifest
OG_TITLE   = "Chelattherapie in Berlin: Schwermetalle erkennen, gezielt ausleiten"
OG_IMAGE   = "assets/og-chelattherapie.jpg"
OG_IMAGE_W, OG_IMAGE_H = 1200, 630
OG_IMAGE_ALT = "Heilpraktikerin Nina Klimek, Berlin"
PORTRAIT     = "assets/nina-klimek.webp"      # Porträt, größte WebP-Variante (Hero A/C, Über mich B/C)
PORTRAIT_JPG = "assets/nina-klimek-800.jpg"   # JPG-Fallback am <img>, Bild der Person, primaryImageOfPage
PORTRAIT_W, PORTRAIT_H = 800, 1200
AUTHOR = "Nina Klimek, Heilpraktikerin"

# Pflichthinweis: eine Quelle für Footer und index.md (aus llms.txt auf Hermanns Wunsch gestrichen, 01.10.2026)
HINWEIS = ("Die beschriebenen Verfahren sind wissenschaftlich umstritten und werden von der Schulmedizin nicht anerkannt. "
           "Beschriebene Wirkungen beruhen auf Erfahrungswissen; eine konkrete Wirkung kann nicht zugesichert werden. "
           "Diese Seite ersetzt keine ärztliche Diagnose oder Behandlung.")

# ---------------------------------------------------------------------------
# Praxis und Kontakt (NAP). ACHTUNG: Das Impressum der Hauptseite nennt eine andere Adresse und Nummer
# (README „Offene Punkte“, Pflicht 3). Erst nach der Klärung FREIGABEN["nap_geklaert"] auf True setzen.
# ---------------------------------------------------------------------------
PRAXIS = {"name": "Heilpraxis Nina Klimek", "street": "Steinstraße 41D", "zip": "12307",
          "city": "Berlin", "district": "Lichtenrade", "bezirk": "Tempelhof-Schöneberg"}
PHONE_INTL = "+4915207707704"      # tel:-Links und JSON-LD
PHONE_DE   = "01520 7707704"       # Anzeige auf der Seite
PHONE_READ = "+49 1520 7707704"    # international lesbar (llms.txt, index.md)
EMAIL      = "info@heilpraxis-klimek.com"
DOCTOLIB   = "https://www.doctolib.de/heilpraktiker/berlin/nina-klimek"
MAIN_SITE  = "https://www.heilpraxis-klimek.com"
INSTAGRAM  = "https://www.instagram.com/heilpraxis_klimek/"
IMPRESSUM   = f"{MAIN_SITE}/impressum"
DATENSCHUTZ = f"{MAIN_SITE}/datenschutz"
UEBER_MICH  = f"{MAIN_SITE}/ueber-mich"
MAPS = ("https://www.google.com/maps/search/?api=1&query="
        + urllib.parse.quote_plus(f"{PRAXIS['street']} {PRAXIS['zip']} {PRAXIS['city']}"))

# Nur echte Angaben eintragen, sonst leer lassen (erscheinen dann nirgends):
GBP_URL        = ""     # Link zum Google-Unternehmensprofil, aus dem Profil kopieren
GEO            = None   # (Breite, Länge) mit mind. 5 Nachkommastellen AUS DEM UNTERNEHMENSPROFIL, nicht schätzen
OPENING_HOURS  = []     # z. B. [{"dayOfWeek": ["Monday", "Thursday"], "opens": "09:00", "closes": "18:00"}]
LOGO           = ""     # z. B. "assets/logo-512.png" (quadratisch), nur wenn es ein Logo gibt
VERBAND_PROFIL = ""     # Profil in der Therapeutensuche des Verbands, falls vorhanden

# Datenschutzfreundliches Klick-Tracking (Plausible, ohne Cookies). Leer = aus.
# Zum Aktivieren die Live-Domain ohne https eintragen, z. B. "chelattherapie-berlin.de"
ANALYTICS_DOMAIN = ""

# ---------------------------------------------------------------------------
# Bilder im Text (Schlüssel = Platzhalter in den Templates). assets/vorschau/ sind NUR Vorschaubilder
# (Rechte ungeklärt), vor dem Go-live durch eigene Fotos ersetzen. Neutrale Platzhalter: assets/platzhalter/*.svg
# Echtes Foto nach assets/_roh/ legen und `python _src/bilder.py` laufen lassen (erzeugt 800/1200/1600 px).
# Der Pfad hier ist immer die größte Variante; kleinere heißen <name>-800.webp usw. und werden automatisch gefunden.
# ---------------------------------------------------------------------------
IMAGES = {
    "IMG_INFUSION":      "assets/vorschau/infusion-nina.webp",       # "Was ist eine Chelattherapie?", 4:3
    "IMG_PRAXIS":        "assets/vorschau/praxis-nina.webp",         # "So läuft ... ab", 3:2
    "IMG_ERSTGESPRAECH": "assets/vorschau/erstgespraech-nina.webp",  # Erstgespräch, 3:2
}

# ---------------------------------------------------------------------------
# Go-live:  python _src/build.py release a|b|c
# Ohne --probe bricht der Release ab, solange DOMAIN der Platzhalter ist oder hier etwas auf False steht.
# ---------------------------------------------------------------------------
FREIGABEN = {
    "nap_geklaert":          False,  # Adresse und Telefon mit Nina geklärt, identisch mit Unternehmensprofil, Doctolib, Hauptseite
    "impressum_datenschutz": False,  # eigenes Impressum und eigene Datenschutzerklärung für die Domain (oder rechtlich geprüft)
    "bildrechte":            False,  # Nutzungsrechte und Einwilligung für alle Bilder, auch für die neue Domain
}
HOSTING = ""          # "apache" (nur .htaccess), "pages" (Netlify oder Cloudflare Pages, nur _headers), "" = beide
INDEXNOW_KEY = ""     # optional, 8 bis 128 Zeichen aus a-z A-Z 0-9 und -; der Release legt dann <KEY>.txt ab
RELEASE_EXTRA = []    # weitere Dateien aus dem Projektordner, die live gehen sollen (z. B. "google1234abcd.html")

# ---------------------------------------------------------------------------
# FAQ: eine Quelle für sichtbares HTML, FAQPage-Schema, index.md und die Zahl in llms.txt
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
     f"In der {PRAXIS['name']}, {PRAXIS['street']}, {PRAXIS['zip']} Berlin-{PRAXIS['district']} im Süden Berlins, "
     "gut erreichbar aus Tempelhof, Mariendorf, Marienfelde sowie aus dem angrenzenden "
     "Brandenburg (Mahlow, Blankenfelde, Teltow). Termine können online über Doctolib "
     "gebucht werden; die Erstanamnese ist auch online möglich."),
]

# ---------------------------------------------------------------------------
# Abgeleitete Werte und Hilfen
# ---------------------------------------------------------------------------
MONATE = "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split()


def de_datum(iso):
    """2026-09-30 -> 30. September 2026"""
    j, m, t = map(int, iso.split("-"))
    return f"{t}. {MONATE[m - 1]} {j}"


UPDATED_DE = de_datum(UPDATED)   # nicht getrennt pflegen


FUELLWOERTER = {"und", "oder", "die", "der", "das", "den", "dem", "ein", "eine", "einer", "wo", "wie", "kann",
                "ich", "in", "im", "auf", "mit", "zu", "zur", "zum", "sich", "man"}


def slug(text, woerter=7, zeichen=50):
    """ASCII-Kennung aus einem deutschen Text: "Wie läuft eine EDTA-Infusion ab …" -> wie-laeuft-eine-edta-infusion-ab"""
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    teile = [w for w in re.split(r"[^a-z0-9]+", t) if w][:woerter]
    while len(teile) > 1 and (len("-".join(teile)) > zeichen or teile[-1] in FUELLWOERTER):
        teile.pop()
    return "-".join(teile)


def faq_ids():
    """Stabile, eindeutige ids je Frage (faq-<slug>): id am sichtbaren <details> UND Anker in Question.url (JSON-LD)"""
    ids, seen = [], set()
    for q, _ in FAQ:
        base = i = "faq-" + slug(q)
        n = 2
        while i in seen:
            i = f"{base}-{n}"
            n += 1
        seen.add(i)
        ids.append(i)
    return ids


def werte():
    """Alle Stammdaten-Platzhalter als Text (roh, nicht HTML-maskiert). Bei jedem Aufruf neu berechnet.
    build.py ergänzt für HTML: HINWEIS maskiert, LATIN, Bildwerte, HEAD, FAQ, SCRIPTS."""
    return {
        "DOMAIN": DOMAIN, "HOST": host(), "UPDATED": UPDATED, "UPDATED_DE": de_datum(UPDATED), "YEAR": UPDATED[:4],
        "TITLE": TITLE, "DESC": DESC, "SITE_NAME": SITE_NAME,
        "PHONE_INTL": PHONE_INTL, "PHONE_DE": PHONE_DE, "PHONE_READ": PHONE_READ, "EMAIL": EMAIL,
        "DOCTOLIB": DOCTOLIB, "MAIN_SITE": MAIN_SITE, "MAPS": MAPS, "INSTAGRAM": INSTAGRAM,
        "IMPRESSUM": IMPRESSUM, "DATENSCHUTZ": DATENSCHUTZ, "UEBER_MICH": UEBER_MICH,
        "PRAXIS": PRAXIS["name"], "STREET": PRAXIS["street"], "ZIP": PRAXIS["zip"], "CITY": PRAXIS["city"],
        "DISTRICT": PRAXIS["district"], "BEZIRK": PRAXIS["bezirk"],
        "HINWEIS": HINWEIS, "GEPRUEFT": " und geprüft" if REVIEWED else "",
        "FAQ_COUNT": str(len(FAQ)),
    }


class BuildFehler(Exception):
    """Jeder Fehler beim Bauen. build.py fängt ihn in main() ab und beendet mit der Meldung."""


PH = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
REST = re.compile(r"\{\{[^{}\n]{0,80}\}\}")
PLATZHALTER = PH


def fill(t, v=None, name="Vorlage"):
    """Ersetzt alle {{NAME}} in einem Durchgang (eingesetzte Werte werden nicht erneut durchsucht).
    v: Werte (Standard: werte()). Unbekannte oder übrig gebliebene Platzhalter lösen BuildFehler aus."""
    v = werte() if v is None else v
    unbekannt = sorted({k for k in PH.findall(t) if k not in v})
    if unbekannt:
        raise BuildFehler(f"{name}: unbekannte Platzhalter " + ", ".join("{{%s}}" % k for k in unbekannt))
    t = PH.sub(lambda m: str(v[m.group(1)]), t)
    rest = sorted(set(REST.findall(t)))
    if rest:
        raise BuildFehler(f"{name}: nach dem Ersetzen steht noch " + ", ".join(rest))
    return t
