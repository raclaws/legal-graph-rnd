"""Find PDF URL and tab content in saved HTML."""
import re
from pathlib import Path

f = Path("corpus/putusan/raw/11f036d84e9c69a09f34313334353130.html")
content = f.read_text(encoding="utf-8", errors="ignore")

# Find all hrefs containing pdf
pdf_hrefs = re.findall(r'href="([^"]*[Pp][Dd][Ff][^"]*)"', content)
print("PDF hrefs:")
for p in pdf_hrefs:
    print(f"  {p}")

# Find src containing pdf
pdf_srcs = re.findall(r'src="([^"]*[Pp][Dd][Ff][^"]*)"', content)
print(f"\nPDF srcs:")
for p in pdf_srcs:
    print(f"  {p}")

# Check what's inside tabs-1 and tabs-2
for tab_id in ["tabs-1", "tabs-2", "content"]:
    idx = content.find(f'id="{tab_id}"')
    if idx > 0:
        snippet = content[idx:idx+800]
        snippet_text = re.sub(r"<[^>]+>", " ", snippet)
        snippet_text = re.sub(r"\s+", " ", snippet_text).strip()
        print(f"\n{tab_id} ({idx}): {snippet_text[:300]}")

# Find where "392" PDF reference is
pdf_area_idx = content.find(".pdf")
if pdf_area_idx > 0:
    area = content[max(0, pdf_area_idx-200):pdf_area_idx+50]
    print(f"\nContext around .pdf:")
    print(f"  {area}")
