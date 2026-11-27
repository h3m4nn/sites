# -*- coding: utf-8 -*-
"""
Schneidet die Rohfotos zu und speichert sie als WebP in mehreren Breiten (responsive Bilder).

Rohfotos nach assets/_roh/ legen (Dateiname egal, Zuordnung unten per Stichwort im Namen), dann:
    python _src/bilder.py
    python _src/build.py
Ausschnitte sind relativ angegeben und gelten daher für jede Auflösung desselben Motivs.

Ausgabe je Motiv (nie hochskaliert, nur bis zur Breite des Rohbilds):
    <ziel>.webp            größte Variante (min(Rohbreite, 1600) px), unter diesem Namen steht das Bild in build.py
    <ziel>-800.webp ...    kleinere Stufen aus BREITEN, die schmaler als die größte Variante sind
    optional ein JPG-Fallback (Porträt), max. 800 px breit
build.py liest die vorhandenen Dateien und ihre echten Maße (PIL) und baut daraus srcset, width und height.
Veraltete Dateien löscht das Skript nicht, es nennt sie nur.
"""
import pathlib, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROH = ROOT / "assets" / "_roh"
ASSETS = ROOT / "assets"
BREITEN = (800, 1200, 1600)      # Stufen für srcset; die letzte ist zugleich die Obergrenze
QUALITAET = 84

# Ziel (relativ zu assets/): (Stichwörter im Dateinamen, Seitenverhältnis oder None = unverändert,
#                             Oberkante als Anteil der Bildhöhe, JPG-Fallback oder None)
MOTIVE = {
    "vorschau/erstgespraech-nina.webp": (("erstgespr", "gespraech", "schreibtisch"), 3 / 2, 235 / 1024, None),
    "vorschau/infusion-nina.webp":      (("infusion",), 4 / 3, 190 / 1024, None),
    "vorschau/praxis-nina.webp":        (("praxis", "flur", "empfang"), None, 0, None),
    # Porträt (Hero A/C, Über mich B/C). Bisher ohne Rohbild in _roh: dann bleiben die vorhandenen Dateien stehen.
    "nina-klimek.webp":                 (("portrait", "portraet", "porträt", "nina-klimek"), None, 0, "nina-klimek-800.jpg"),
}


def stufen(breite):
    """Breiten der Varianten für ein Bild dieser Breite: alle Stufen darunter plus die größte (nie hochskaliert)."""
    groesste = min(breite, BREITEN[-1])
    return sorted({b for b in BREITEN if b < groesste} | {groesste})


def variante_pfad(ziel, breite):
    """Dateiname einer kleineren Variante: infusion-nina.webp -> infusion-nina-800.webp"""
    return ziel.with_name(f"{ziel.stem}-{breite}{ziel.suffix}")


def skaliert(im, breite):
    if im.width == breite:
        return im
    return im.resize((breite, round(im.height * breite / im.width)), Image.LANCZOS)


def zuschneiden(src, ziel_rel, ratio, top, jpg):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if ratio:
        ch = min(round(w / ratio), h)
        y = min(round(top * h), h - ch)
        im = im.crop((0, max(y, 0), w, max(y, 0) + ch))
    ziel = ASSETS / ziel_rel
    ziel.parent.mkdir(parents=True, exist_ok=True)
    breiten = stufen(im.width)
    for b in breiten:
        out = ziel if b == breiten[-1] else variante_pfad(ziel, b)
        v = skaliert(im, b)
        v.save(out, "WEBP", quality=QUALITAET, method=6)
        print(f"{src.name} -> {out.relative_to(ROOT).as_posix()} {v.size[0]}x{v.size[1]}")
    if jpg:
        v = skaliert(im, min(800, im.width))
        v.save(ASSETS / jpg, "JPEG", quality=86, optimize=True, progressive=True)
        print(f"{src.name} -> assets/{jpg} {v.size[0]}x{v.size[1]} (Fallback)")
    # Varianten aus früheren Läufen, die zu diesem Rohbild nicht mehr passen (breiter als die größte Variante)
    for b in BREITEN:
        alt = variante_pfad(ziel, b)
        if b not in breiten[:-1] and alt.exists():
            print(f"  Hinweis: {alt.relative_to(ROOT).as_posix()} ist veraltet (Rohbild schmaler), "
                  "build.py ignoriert die Datei; bitte von Hand nach _archiv/_zu_loeschen verschieben.")


def main():
    dateien = [p for p in ROH.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")] if ROH.exists() else []
    if not dateien:
        sys.exit(f"Keine Bilder in {ROH}")
    for ziel, (woerter, ratio, top, jpg) in MOTIVE.items():
        treffer = [p for p in dateien if any(w in p.stem.lower() for w in woerter)]
        if treffer:
            zuschneiden(treffer[0], ziel, ratio, top, jpg)
        else:
            print(f"übersprungen: {ziel} (keine Datei mit {', '.join(woerter)} im Namen, vorhandene Dateien bleiben)")


if __name__ == "__main__":
    main()
