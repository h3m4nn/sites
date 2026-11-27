# -*- coding: utf-8 -*-
"""
Schneidet die Rohfotos zu und speichert sie als WebP für die Seite.

Rohfotos nach assets/_roh/ legen (Dateiname egal, Zuordnung unten per Stichwort im Namen
oder als Argument), dann:   python _src/bilder.py
Ausschnitte sind relativ angegeben und gelten daher für jede Auflösung desselben Motivs.
"""
import pathlib, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROH = ROOT / "assets" / "_roh"
OUT = ROOT / "assets" / "vorschau"
MAX_W = 1600

# Ziel: (Stichwörter im Dateinamen, Seitenverhältnis oder None = unverändert, Oberkante als Anteil der Bildhöhe)
MOTIVE = {
    "erstgespraech-nina.webp": (("erstgespr", "gespraech", "schreibtisch"), 3 / 2, 235 / 1024),
    "infusion-nina.webp":      (("infusion",), 4 / 3, 190 / 1024),
    "praxis-nina.webp":        (("praxis", "flur", "empfang"), None, 0),
}

def zuschneiden(src, ziel, ratio, top):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if ratio:
        ch = round(w / ratio)
        y = min(round(top * h), h - ch)
        im = im.crop((0, max(y, 0), w, max(y, 0) + ch))
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    im.save(OUT / ziel, "WEBP", quality=84, method=6)
    print(f"{src.name} -> {ziel} {im.size[0]}x{im.size[1]}")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dateien = [p for p in ROH.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")] if ROH.exists() else []
    if not dateien:
        sys.exit(f"Keine Bilder in {ROH}")
    for ziel, (woerter, ratio, top) in MOTIVE.items():
        treffer = [p for p in dateien if any(w in p.stem.lower() for w in woerter)]
        if treffer:
            zuschneiden(treffer[0], ziel, ratio, top)
        else:
            print(f"übersprungen: {ziel} (keine Datei mit {', '.join(woerter)} im Namen)")

if __name__ == "__main__":
    main()
