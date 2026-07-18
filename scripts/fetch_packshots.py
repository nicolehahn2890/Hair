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
    "n2": "4068134071149", "n4": "3600542398022",
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
    "n15": ("https://bali-care.com", ["nourishing", "shampoo"]),
    "dp10": ("https://dejangarz.com", ["foundation"]),
}

# Shopify-Produkte mit bekanntem Handle (Titel weicht ab / og:image ist Banner)
SHOPIFY_HANDLE = {
    "n6": "https://bali-care.com/products/deep-hydration-mask",
    "n9": "https://bali-care.com/products/leave-in-diffusing-heat-protection-spray",
    "dp10": "https://dejangarz.com/products/hairmask",
    # dp8 NICHT aus dem NEQI-Shop oder via Bing holen — dort nur Bilder mit
    # schwarzem Hintergrund (Nicole will weisse). Reseller-Shops nutzen:
    "dp8": "https://thisisbeauty.us/products/neqi-diamond-glass-styling-spray-all-hair-6-1-fl-oz",
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
        "https://www.schwarzkopf.de/de/marken/haarpflege/gliss-kur/liquid-silk/express-repair-spuelung.html",
        "https://www.schwarzkopf.ch/de/marken/haarpflege/gliss/liquid-silk/express-repair-spuelung.html",
        "https://www.docmorris.de/schwarzkopf-gliss-expressrepairspuelung-liquid-silk/57TR3TL6",
    ],
    # Fallback-Seiten fuer Produkte, deren Erststrategie scheitern kann
    "g2": ["https://www.schwarzkopf.de/marken/haarpflege/gliss/produktlinien/blonde-perfector/purple-aufbau-shampoo.html"],
    # Hersteller-/Drittseiten fuer Produkte, deren Rossmann-Seite den Runner blockt
    "p7b": ["https://www.loreal-paris.de/elvital/glycolic-gloss/5-minuten-haar-laminierung"],
    "g1": ["https://www.loreal-paris.de/elvital/bond-repair/shampoo"],
    "g4": ["https://www.loreal-paris.de/elvital/oel-magique/midnight-serum"],
    "dp5": ["https://www.loreal-paris.de/elvital/collagen-lifter/kraeftigende-pflege-spuelung-200ml"],
    "dp9": ["https://www.loreal-paris.de/elvital/glycolic-gloss/spuelung"],
    "n4": ["https://www.garnier.de/haarpflege/haarpflege-marken/fructis/hair-food/feuchtigkeits-spuelung-mit-aloe-vera"],
    "n5": ["https://www.garnier.de/haarpflege/haarpflege-marken/fructis/hair-food/3in1-maske-fuer-trockenes-haar-angereichert-mit-aloe-vera"],
    "dp1": ["https://www.garnier.de/haarpflege/haarpflege-marken/fructis/locken-methode/spuelung"],
    "g3": [
        "https://www.nivea.ch/de-ch/produkte/fresh-mild-trockenshampoo-blonde-und-helle-haartoene-40059007559710070.html",
        "https://www.nivea.de/produkte/-40059007559710001.html",
    ],
    "dp4": [
        "https://www.ogxbeauty.com/products/pro-growth-peptide-shampoo",
        "https://incidecoder.com/products/ogx-progrowth-peptide-shampoo",
    ],
    "dp6": [
        "https://basler-beauty.de/marken/john-frieda/john-frieda-frizz-ease-taegliche-wunderkur-sofort-pflegespray-200-ml.html",
        "https://www.johnfrieda.com/de-de/produkte/frizz-ease/wunder-reparatur/taegliche-wunderkur-pflegespray/",
    ],
    "s5": ["https://www.loreal-paris.es/elvive/color-vive-violeta/champu-violeta-matizador"],
    "n13": [
        "https://sinsiliconas.club/a-examen-serum-natural-deliplus-mercadona/",
        "https://seatcienfuegos.es/mercadona/serum-natural-deliplus-todo-tipo-de-cabello/",
        "https://1source.com/products/serum-natural-mercadona",
        "https://productosaptos.com/serum-natural-deliplus/",
    ],
}
# Achtung: skinsort.com/products/isana/tiefenreinigung-shampoo liefert ein
# falsches Bild (Silber & Glanz) — nicht verwenden!
PAGES["dp8"] = [
    "https://makeupstore.com/product/850235/",
]
PAGES["p3"] = [
    "https://www.hautschutzengel.de/isana-professional-shampoo-tiefenreinigung-inhaltsstoffe/produkt/377101.html",
]
PAGES["p8b"] = [
    "https://incidecoder.com/products/isana-professional-hyaluron-care-leave-in-conditioner",
    "https://www.hautschutzengel.de/isana-professional-leave-in-conditioner-hyaluron-care-inhaltsstoffe/produkt/246343.html",
]

# Regal-Check (s1-s22, spanischer Supermarkt): Bing-Bildsuche mit praezisen
# spanischen Produktnamen, Ergebnis wird per Kontaktbogen visuell geprueft.
# s1 fehlt bewusst: identisch mit p4 (img/p4.jpg wird kopiert).
SHELF_BING = {
    # s1/s3/s4 wurden als Dubletten in p4/g1/n5 zusammengelegt (18. Juli 2026)
    "s2": "L'Oréal Elvive Color Vive Violeta mascarilla morada",
    "s5": "Elvive Color Vive champú matizador violeta 200 ml packshot botella",
    "s6": "Pantene 3 Minute Miracle Rizos Definidos acondicionador",
    "s7": "Pantene Ondas Naturales crema de peinado",
    "s8": "Garnier Fructis Adiós Daños mascarilla",
    "s9": "Garnier Fructis Vitamin Force Biotina 10 en 1 crema",
    "s10": "Garnier Fructis Hair Food Papaya champú",
    "s11": "babaria champú ondas y rizos definidos 700 ml botella",
    "s12": "babaria nutritive repair mascarilla capilar",
    "s13": "Pantene doma crema rizos definidos",
    "s14": "Pantene coconut infused oil spray aceite de coco",
    "s15": "Pantene Pro-V Rizos Definidos champú",
    "s16": "L'Oréal Elvive Dream Long champú",
    "s17": "L'Oréal Elvive Aceite Extraordinario cabello",
    "s18": "L'Oréal Elvive Total Repair 5 champú",
    "s19": "L'Oréal Elvive Color Vive mascarilla roja",
    "s20": "Garnier Fructis Hair Bomb Liso y Brillo champú",
    "s21": "Revlon Flex Keratina champú 650 ml",
    "s22": "babaria ondas y rizos mascarilla",
}

# Bing-Bildvorschau als allerletzter Fallback (Ergebnis wird manuell geprueft)
BING = {
    "p3": "ISANA Professional Shampoo Tiefenreinigung Rossmann",
    "p11": "ISANA Hitzeschutz Spray 150 ml Rossmann",
    "p8b": "ISANA Professional Leave-In Conditioner Hyaluron Care Rossmann",
    "p12": "ISANA Trockenshampoo Bloom Boost Rossmann",
    "n2": "ISANA Spülung Feuchtigkeit Kokoswasser Rossmann",
    "n8": "Alterra Leave-In Feuchtigkeitsserum Granatapfel Rossmann",
    "n12": "Alterra Nutri-Care Haaröl Rossmann",
    "n14": "Alterra 100% reines Bio-Arganöl Rossmann",
    "dp10": "Dejan Garz The Foundation Hair Treatment Mask",
}
BING.update(SHELF_BING)

PAGES["dp3"] = [
    "https://skinsort.com/products/redken/acidic-bonding-concentrate-conditioner",
] + PAGES["dp3"]
PAGES["dp7"] = [
    "https://skinsort.com/products/redken/one-united-multi-benefit-treatment-spray",
    "https://incidecoder.com/products/redken-all-in-one-multi-benefit-treatment",
] + PAGES["dp7"]

session = requests.Session()
session.headers.update(HEADERS)


def get(url, **kw):
    kw.setdefault("timeout", 30)
    return session.get(url, **kw)


def og_image(url):
    r = get(url)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    html = r.text
    patterns = [
        r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)(?::src)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)(?::src)?["\']',
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)',
        r'"image"\s*:\s*\[?\s*"(https?:[^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            src = m.group(1).replace(r"\/", "/")
            if src.startswith("//"):
                src = "https:" + src
            return src, None
    return None, "kein og:image"


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
    # OFF/OBF verlangen einen identifizierenden User-Agent (Browser-UA von
    # Datacenter-IPs wird geblockt)
    ua = {"User-Agent": "HairAppPackshots/1.0 (personal hair-care app; github.com/nicolehahn2890/Hair)",
          "Accept": "application/json"}
    last = None
    for host in ("world.openbeautyfacts.org", "world.openfoodfacts.org"):
        r = requests.get(f"https://{host}/api/v2/product/{ean}?fields=image_front_url",
                         headers=ua, timeout=30)
        last = r.status_code
        if r.status_code == 200:
            url = (r.json().get("product") or {}).get("image_front_url")
            if url:
                return url, None
    return None, f"nicht in Open (Beauty|Food) Facts (HTTP {last})"


def shopify_handle_image(product_url):
    r = get(product_url + ".json", headers={**HEADERS, "Accept": "application/json"})
    if r.status_code != 200:
        return og_image(product_url)
    imgs = (r.json().get("product") or {}).get("images") or []
    if not imgs:
        return None, "Shopify-Produkt ohne Bilder"
    return imgs[0]["src"], None


def jina_rossmann_image(ean):
    """Holt die Rossmann-Produktseite ueber den r.jina.ai-Lesedienst (rendert
    im Browser, umgeht IP-Blocks) und fischt eine media.rossmann.de-Bild-URL
    aus dem Markdown."""
    r = requests.get(f"https://r.jina.ai/https://www.rossmann.de/de/p/{ean}",
                     headers={"User-Agent": HEADERS["User-Agent"],
                              "X-With-Images-Summary": "true"},
                     timeout=90)
    if r.status_code != 200:
        return None, f"r.jina.ai HTTP {r.status_code}"
    urls = re.findall(r'https?://media\.rossmann\.de[^\s\)"\']+', r.text)
    # Marketing-Banner ("Neu bei uns" etc.) aussortieren; Packshot-URLs
    # enthalten normalerweise die EAN oder liegen unter article/products
    junk = ("marketing", "teaser", "banner", "kampagne", "content", "logo", "icon")
    candidates = [u for u in urls if ean in u]
    if not candidates:
        candidates = [u for u in urls
                      if ("article" in u or "product" in u.lower())
                      and not any(j in u.lower() for j in junk)]
    if not candidates:
        return None, f"kein Packshot mit EAN unter {len(urls)} media.rossmann.de-URLs"
    return candidates[0], None


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
    # Schmale Flaschen-Packshots (z.B. 94x400) sind ok — nur echte Thumbnails ablehnen
    if min(im.width, im.height) < 60 or max(im.width, im.height) < 200:
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
    if pid in SHOPIFY_HANDLE:
        s.append(("shopify-handle", lambda url=SHOPIFY_HANDLE[pid]: shopify_handle_image(url)))
    for url in PAGES.get(pid, []):
        s.append((f"page:{url.split('/')[2]}", lambda url=url: og_image(url)))
    if pid in ROSSMANN:
        ean = ROSSMANN[pid]
        s.append(("incibeauty", lambda ean=ean: og_image(f"https://incibeauty.com/en/produit/{ean}")))
        # jina (offizieller Rossmann-Packshot) vor OBF (oft Amateurfotos)
        s.append(("jina-rossmann", lambda ean=ean: jina_rossmann_image(ean)))
        obf = ("openbeautyfacts", lambda ean=ean: obf_image(ean))
    else:
        obf = None
    if pid in BING:
        # Bing-Packshot vor OBF (dort oft Amateurfotos)
        q = requests.utils.quote(BING[pid])
        s.append(("bing-thumb", lambda q=q: (f"https://tse2.mm.bing.net/th?q={q}&w=600&h=600", None)))
    if obf:
        s.append(obf)
    return s


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_ids = list(dict.fromkeys(
        list(MERCADONA) + list(ROSSMANN) + list(SHOPIFY)
        + list(SHOPIFY_HANDLE) + list(PAGES) + list(BING)))
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
