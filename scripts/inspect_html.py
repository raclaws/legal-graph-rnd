"""Inspect the saved HTML to find how decision content is loaded."""
import re
from pathlib import Path

f = Path("corpus/putusan/raw/11f036d84e9c69a09f34313334353130.html")
content = f.read_text(encoding="utf-8", errors="ignore")

print(f"File size: {len(content)} bytes")

# iframes
iframes = re.findall(r"iframe[^>]*src=['\"]([^'\"]+)", content, re.I)
print(f"\niframes: {iframes[:5]}")

# API references
apis = re.findall(r"api_v3[^'\"\s<>]{0,80}", content, re.I)
print(f"\napi_v3 refs: {apis[:10]}")

# PDF links
pdfs = re.findall(r"[^'\"\s<>]+\.pdf[^'\"\s<>]*", content, re.I)
print(f"\nPDFs: {pdfs[:5]}")

# Tab/accordion elements
tabs = re.findall(r'id="([^"]*tab[^"]*)"', content, re.I)
print(f"\ntab IDs: {tabs[:10]}")

# Content divs
divs = re.findall(r'id="([^"]*(?:content|putusan|detail|text|isi)[^"]*)"', content, re.I)
print(f"\ncontent div IDs: {divs[:10]}")

# direktori sub-paths
dirs = re.findall(r"direktori/[^'\"\s<>]{5,80}", content)
print(f"\ndirektori paths: {dirs[:10]}")

# Any XHR/fetch patterns
fetches = re.findall(r"url\s*:\s*['\"]([^'\"]+)['\"]", content)
print(f"\nAJAX urls: {fetches[:10]}")

# Look for onclick or data-src patterns
onclicks = re.findall(r"onclick=['\"]([^'\"]{0,100})['\"]", content, re.I)
print(f"\nonclick handlers: {onclicks[:5]}")

# Check for "Putusan" in visible text sections
text = re.sub(r"<[^>]+>", "\n", content)
lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 20]
# Find lines with legal keywords
legal_lines = [l for l in lines if any(k in l for k in ["Nomor", "Penggugat", "Tergugat", "Tanggal", "Klasifikasi"])]
print(f"\nLegal metadata lines:")
for l in legal_lines[:15]:
    print(f"  {l[:100]}")
