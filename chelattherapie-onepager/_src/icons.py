# -*- coding: utf-8 -*-
"""
Erzeugt aus favicon.svg die Icon-Dateien im Projektordner (ohne Zusatzpakete: Headless-Chrome + Pillow):

  favicon.ico           16, 32 und 48 px (Browser, Programme, die /favicon.ico direkt abfragen)
  icon-192.png          192 x 192 (Google-Suchergebnis, Manifest)
  icon-512.png          512 x 512 (Manifest)
  apple-touch-icon.png  180 x 180, ohne Transparenz, Ecken NICHT gerundet (iOS rundet selbst)

Aufruf nach einer Änderung an favicon.svg:   python _src/icons.py
Chrome läuft dabei mit einem eigenen, temporären Profil (stört ein offenes Chrome nicht).
"""
import os, pathlib, re, shutil, subprocess, sys, tempfile
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SVG = ROOT / "favicon.svg"
CHROME = os.environ.get("CHROME") or next((p for p in (
    r"C:/Program Files/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome") if os.path.exists(p)), None)
N = 512   # Renderauflösung, alles andere wird daraus verkleinert


def render(svg, ziel, tmp):
    """Rendert svg (Text) transparent auf N x N px nach ziel (PNG)."""
    svg = re.sub(r"<svg\b", f'<svg width="{N}" height="{N}"', svg, count=1)
    seite = tmp / (ziel.stem + ".html")
    seite.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent;'
                     f'overflow:hidden}}svg{{display:block}}</style>{svg}', encoding="utf-8")
    profil = tmp / ("profil-" + ziel.stem)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    "--no-default-browser-check", "--disable-extensions", f"--user-data-dir={profil}",
                    "--force-device-scale-factor=1", "--default-background-color=00000000",
                    f"--window-size={N},{N}", f"--screenshot={ziel}", seite.as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    im = Image.open(ziel).convert("RGBA")
    if im.size != (N, N):
        sys.exit(f"Chrome lieferte {im.size} statt {N} x {N}")
    return im


def main():
    if not CHROME:
        sys.exit("Chrome oder Edge nicht gefunden (Umgebungsvariable CHROME setzen).")
    svg = SVG.read_text(encoding="utf-8")
    # iOS legt seine eigene Maske darüber: Hintergrund randlos, sonst entstehen helle Ecken
    svg_voll = re.sub(r'(<rect\b[^>]*?)\s+rx="[^"]*"', r"\1", svg, count=1)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="icons-", dir=os.environ.get("TEMP") or None))
    try:
        rund = render(svg, tmp / "rund.png", tmp)
        voll = render(svg_voll, tmp / "voll.png", tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)    # nur der eigene Temp-Ordner (Bilder liegen schon im Speicher)
    if rund.getpixel((0, 0))[3] != 0:
        sys.exit("Rendern ohne Transparenz: Ecke von favicon.svg ist nicht durchsichtig")
    klein = lambda im, n: im.resize((n, n), Image.LANCZOS)
    rund.save(ROOT / "icon-512.png", optimize=True)
    klein(rund, 192).save(ROOT / "icon-192.png", optimize=True)
    hg = voll.getpixel((N // 2, 4))[:3]           # Hintergrundfarbe des Icons (oberer Rand, Mitte)
    apple = Image.new("RGB", (N, N), hg)
    apple.paste(voll, mask=voll.split()[3])
    klein(apple, 180).save(ROOT / "apple-touch-icon.png", optimize=True)
    groessen = [16, 32, 48]
    bilder = [klein(rund, n) for n in groessen]
    bilder[-1].save(ROOT / "favicon.ico", format="ICO", sizes=[(n, n) for n in groessen], append_images=bilder[:-1])
    for n in ("favicon.ico", "icon-192.png", "icon-512.png", "apple-touch-icon.png"):
        p = ROOT / n
        print(f"geschrieben: {n:22} {p.stat().st_size:>7,} B".replace(",", "."))


if __name__ == "__main__":
    main()
