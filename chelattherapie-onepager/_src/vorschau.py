# -*- coding: utf-8 -*-
"""
Vorschaubilder für die Vergleichsseite index.html: je Entwurf der erste Bildschirm am Desktop (1440x900) und auf dem
Handy (390x844, Touch-Emulation), als JPG nach vorschau/<a|b|c>-desktop.jpg und -handy.jpg.

Aufruf:  python _src/vorschau.py          alle drei Entwürfe (nacheinander, immer nur ein Chrome)
         python _src/vorschau.py b        nur Entwurf B

Vorher bauen (python _src/build.py). Aufgenommen wird mit _src/pruefen.mjs im Klick-Modus: Seite laden, 2,5 s warten
(Hero-Zoom und Einblenden sind dann fertig), auf die H1 tippen (ändert nichts), nach oben, Fokus weg, Screenshot nur
des Fensters. Rohbilder landen in %TEMP%/chelat-vorschau, PIL schneidet exakt auf das Fenster zu und speichert
progressiv (Desktop Qualität 80, Handy 84 ohne Farb-Unterabtastung, weil die Schrift dort klein ist).
"""
import pathlib, subprocess, sys, tempfile
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
ZIEL = ROOT / "vorschau"
SEITEN = {"a": "entwurf-a-salbei", "b": "entwurf-b-klarheit", "c": "entwurf-c-stille"}
GROESSEN = (("desktop", 1440, 900, 80), ("handy", 390, 844, 84))
WARTEN = "await new Promise(r => setTimeout(r, 2500))"
DANACH = ("scrollTo({ top: 0, behavior: 'instant' }); document.activeElement && document.activeElement.blur && "
          "document.activeElement.blur(); await new Promise(r => setTimeout(r, 900))")

def main(args):
    wahl = [a.lower() for a in args] or list(SEITEN)
    falsch = [a for a in wahl if a not in SEITEN]
    if falsch:
        sys.exit(f"Unbekannt: {' '.join(falsch)}. Erlaubt: a b c (ohne Angabe: alle)")
    roh = pathlib.Path(tempfile.gettempdir()) / "chelat-vorschau"
    ZIEL.mkdir(exist_ok=True)
    for k in wahl:
        seite = SEITEN[k]
        if not (ROOT / f"{seite}.html").exists():
            sys.exit(f"{seite}.html fehlt: erst python _src/build.py")
        breiten = ",".join(str(w) for _, w, _, _ in GROESSEN)
        hoehen = ",".join(str(h) for _, _, h, _ in GROESSEN)
        cmd = ["node", str(ROOT / "_src" / "pruefen.mjs"), "shots", f"{seite}.html", "--w", breiten, "--h", hoehen,
               "--out", str(roh), "--vorher", WARTEN, "--klick", "h1", "--nachher", DANACH]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            sys.exit(f"pruefen.mjs ist bei {seite} fehlgeschlagen:\n{r.stdout}\n{r.stderr}")
        for name, w, h, q in GROESSEN:
            quelle = roh / seite / f"{w}x{h}-klick.jpg"
            with Image.open(quelle) as im:
                if im.width < w or im.height < h:
                    sys.exit(f"{quelle} ist {im.width}x{im.height}, erwartet {w}x{h}")
                bild = im.convert("RGB").crop((0, 0, w, h))
            datei = ZIEL / f"{k}-{name}.jpg"
            bild.save(datei, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0 if name == "handy" else 2)
            print(f"geschrieben: vorschau/{datei.name} ({w}x{h}, {datei.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    main(sys.argv[1:])
