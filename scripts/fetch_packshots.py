#!/usr/bin/env python3
"""Laedt Original-Packshots fuer alle 45 Produkte der Hair-App,
verkleinert sie auf max. 300px und legt sie als img/<id>.jpg ab.
Ergebnis-Report: scripts/packshot_report.json
"""
import io
import json
import os
import re
import sys
import time

import requests
from PIL import Image

OUT_DIR = "img"
REPORT = "scripts/packshot_report.json"
MAX_SIDE = 300

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,es;q=0.8,en;q=0.7",
}

# Mercadona: tienda.mercadona.es Produkt-IDs (API liefert Packshot-URLs)
MERCADONA = {
    "p1": 22629, "p2": 52931, "p6": 52932, "p7": 44218, "p8": 52933,
    "p10": 22632, "n1": 22630, "n7": 23195, "n10": 22631, "n11": 23019,
    "n13": 44329, "n16": 86306,
}

# Rossmann: EAN/GTIN (Seite https://www.rossmann.de/de/p/<EAN>; Fallback Open Beauty Facts)
ROSSMANN = {
    "p3": "4068134135490", "p7b": "3600524128500", "p8b": "4305615946733",
    "p11": "4305615612300", "p12": "4068134123459",
    "g1": "3600524074654", "g2": "4015100814750", "g3": "4005900755971",
    "g4": "3600524135805",
    "n2": "4068134071149", "n3": "3600524142612", "n4": "3600542398022",
    "n5": "3600542511049", "n8": "4068134129390", "n12": "4305615835839",
    "n14": "4305615741574",
    "dp1": "3600542656924", "dp4": "3574661876450", "dp5": "3600524251215",
    "dp6": "5037156225525", "dp8": "4063528078469", "dp9": "3600524230746",
    "dp10": "4262505740010",
}

# Shopify-Shops: Titel-Stichwoerter werden gegen /products.json gematcht
SHOPIFY = {
    "p5": ("https://bali-care.com", ["moisturising", "conditioner"]),
    "p9": ("https://bali-care.com", ["hydrating", "curl", "cream"]),
    "n6": ("https://bali-care.com", ["deep", "hydration", "mask"]),
    "n9": ("https://bali-care.com", ["heat", "protection"]),
    "n15": ("https://bali-care.com", ["nourishing", "shampoo"]),
}

# Direkte Produktseiten (og:image), in Kandidaten-Reihenfolge
PAGES = {
    "p4": [
        "https://www.loreal-paris.es/elvive/hidra-hialuronico/acondicionador-72h-de-hidratacion",
        "https://www.carrefour.es/supermercado/acondicionador-para-cabellos-desidratado-hidra-hialuronico-loreal-elvive-300-ml/R-VC4AECOMM-489104/p",
    ],
    "dp2": [
        "https://www.loreal-paris.de/elvital/hydra-hyaluronic/feuchtigkeit-umhuellende-maske-300ml",
    ],
    "dp3": [
        "https://www.redken.com/hair-care/acidic-bonding-concentrate-conditioner-for-damaged-hair.html",
        "https://incidecoder.com/products/redken-acidic-bonding-concentrate-conditioner",
    ],
    "dp7": [
        "https://incidecoder.com/products/redken-one-united-all-in-one-multi-benefit-treatment",
    ],
    "dp11": [
        "https://schwarzkopf.de/de/marken/haarpflege/gliss-kur/liquid-silk/express-repair-spuelung.html",
        "https://www.docmorris.de/schwarzkopf-gliss-expressrepairspuelung-liquid-silk/57TR3TL6",
    ],
    # Fallback-Seiten fuer Produkte, deren Erststrategie scheitern kann
    "dp10": ["https://dejangarz.com/products/hairmask"],
}

session = requests.Session()
session.headers.update(HEADERS)


def get(url, **kw):
    kw.setdefault("timeout", 30)
    return session.get(url, **kw)


def og_image(url):
    r = get(url)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', r.text)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', r.text)
    if not m:
        return None, "kein og:image"
    src = m.group(1)
    if src.startswith("//"):
        src = "https:" + src
    return src, None


def mercadona_image(pid):
    r = get(f"https://tienda.mercadona.es/api/products/{pid}/?lang=es")
    if r.status_code != 200:
        return None, f"API HTTP {r.status_code}"
    data = r.json()
    photos = data.get("photos") or []
    if not photos:
        return None, "keine photos im API-JSON"
    p = photos[0]
    return p.get("zoom") or p.get("regular") or p.get("thumbnail"), None


_shopify_cache = {}

def shopify_image(base, words):
    if base not in _shopify_cache:
        r = get(f"{base}/products.json?limit=250")
        _shopify_cache[base] = r.json().get("products", []) if r.status_code == 200 else []
    for prod in _shopify_cache[base]:
        title = prod.get("title", "").lower()
        if all(w in title for w in words):
            imgs = prod.get("images") or []
            if imgs:
                return imgs[0]["src"], None
            return None, f"Produkt '{title}' ohne Bilder"
    return None, f"kein Titel-Match fuer {words}"


def obf_image(ean):
    for host in ("world.openbeautyfacts.org", "world.openfoodfacts.org"):
        r = get(f"https://{host}/api/v2/product/{ean}?fields=image_front_url")
        if r.status_code == 200:
            url = (r.json().get("product") or {}).get("image_front_url")
            if url:
                return url, None
    return None, "nicht in Open (Beauty|Food) Facts"


def download_and_save(img_url, pid):
    r = get(img_url, headers={**HEADERS, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
    if r.status_code != 200:
        return f"Bild-Download HTTP {r.status_code}"
    if len(r.content) < 2000:
        return f"Bild zu klein ({len(r.content)} Bytes)"
    try:
        im = Image.open(io.BytesIO(r.content))
        im.load()
    except Exception as e:
        return f"kein dekodierbares Bild: {e}"
    if im.width < 100 or im.height < 100:
        return f"Aufloesung zu gering ({im.width}x{im.height})"
    # Auf Weiss legen (Transparenz) und auf max. 300px verkleinern
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    im.save(os.path.join(OUT_DIR, f"{pid}.jpg"), "JPEG", quality=82, optimize=True)
    return None


def strategies_for(pid):
    s = []
    if pid in MERCADONA:
        s.append(("mercadona-api", lambda pid=pid: mercadona_image(MERCADONA[pid])))
    if pid in ROSSMANN:
        ean = ROSSMANN[pid]
        s.append(("rossmann-og", lambda ean=ean: og_image(f"https://www.rossmann.de/de/p/{ean}")))
    if pid in SHOPIFY:
        base, words = SHOPIFY[pid]
        s.append(("shopify", lambda base=base, words=words: shopify_image(base, words)))
    for url in PAGES.get(pid, []):
        s.append((f"page:{url.split('/')[2]}", lambda url=url: og_image(url)))
    if pid in ROSSMANN:
        s.append(("openbeautyfacts", lambda ean=ROSSMANN[pid]: obf_image(ean)))
    return s


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_ids = list(dict.fromkeys(
        list(MERCADONA) + list(ROSSMANN) + list(SHOPIFY) + list(PAGES)))
    report = {}
    for pid in all_ids:
        if os.path.exists(os.path.join(OUT_DIR, f"{pid}.jpg")):
            report[pid] = {"ok": True, "source": "bereits vorhanden"}
            continue
        errors = []
        done = False
        for name, fn in strategies_for(pid):
            try:
                img_url, err = fn()
            except Exception as e:
                img_url, err = None, f"Exception: {e}"
            if err or not img_url:
                errors.append(f"{name}: {err}")
                continue
            save_err = download_and_save(img_url, pid)
            if save_err:
                errors.append(f"{name}: {save_err} ({img_url})")
                continue
            report[pid] = {"ok": True, "source": name, "url": img_url}
            done = True
            break
        if not done:
            report[pid] = {"ok": False, "errors": errors}
        time.sleep(0.6)
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    ok = sum(1 for v in report.values() if v["ok"])
    print(f"{ok}/{len(report)} Packshots geladen")
    for pid, v in sorted(report.items()):
        print(pid, "OK" if v["ok"] else "FEHLT", v.get("source", ""), *v.get("errors", []))


if __name__ == "__main__":
    sys.exit(main())
