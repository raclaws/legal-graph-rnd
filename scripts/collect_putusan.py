"""
Jurisprudence - Manual collection helper
Since automated scraping is blocked by Cloudflare's second-layer challenge,
this script helps organize manually-downloaded decisions.

WORKFLOW:
1. Open putusan3.mahkamahagung.go.id in a real browser
2. Search for PHI decisions (PKWT, PHK, upah, etc.)
3. Open each decision, Ctrl+S to save as HTML
4. Drop saved files into corpus/putusan/raw/
5. Run this script to index and validate what you have

The parser (Phase 3) will then work against these files.
"""
import json
import re
from pathlib import Path
from datetime import datetime

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
RAW_DIR = CORPUS_DIR / "raw"
SEEDS_FILE = CORPUS_DIR / "seeds.json"
INDEX_FILE = CORPUS_DIR / "index.json"

# Target case numbers to collect (PHI PKWT/PHK decisions 2022-2025)
# These are discoverable from the search page which loads fine
SEED_CASES = [
    # Format: {"case_number": "...", "court": "...", "year": ..., "dispute_type": "...", "url": "..."}
    # Fill in from search results or legal blogs
]


def scan_raw_files():
    """Scan raw/ directory for downloaded HTML files and extract metadata."""
    if not RAW_DIR.exists():
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created {RAW_DIR} - drop saved HTML files here")
        return []

    files = list(RAW_DIR.glob("*.html"))
    print(f"Found {len(files)} HTML files in {RAW_DIR}")

    indexed = []
    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")

        # Extract case number
        case_num_match = re.search(
            r'Nomor\s*:?\s*([\d]+/[A-Za-z.\-]+/\d{4}/[A-Za-z.]+)',
            content
        )
        if not case_num_match:
            case_num_match = re.search(
                r'Nomor\s+([\d]+ K/[A-Za-z.\-]+/\d{4})',
                content
            )

        # Check structural markers
        has_duduk = "DUDUK PERKARA" in content or "TENTANG DUDUKNYA PERKARA" in content
        has_pertimbangan = "PERTIMBANGAN HUKUM" in content or "Menimbang, bahwa" in content
        has_mengadili = "MENGADILI" in content or "M E N G A D I L I" in content

        entry = {
            "file": f.name,
            "size_kb": f.stat().st_size // 1024,
            "case_number": case_num_match.group(1) if case_num_match else None,
            "has_sections": {
                "duduk_perkara": has_duduk,
                "pertimbangan": has_pertimbangan,
                "mengadili": has_mengadili,
            },
            "parseable": has_mengadili,  # minimum requirement
        }
        indexed.append(entry)

        status = "OK" if has_mengadili else "INCOMPLETE"
        case = entry["case_number"] or "?"
        print(f"  [{status}] {f.name} ({entry['size_kb']}kb) - {case}")

    return indexed


def save_index(indexed):
    """Save index of collected files."""
    INDEX_FILE.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_files": len(indexed),
        "parseable": sum(1 for x in indexed if x["parseable"]),
        "files": indexed,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nIndex saved: {INDEX_FILE}")


def print_collection_guide():
    """Print instructions for manual collection."""
    print("""
===========================================================
MANUAL COLLECTION GUIDE
===========================================================

Target: 30-50 PHI decisions (2022-2025)

Focus areas (in priority order):
  1. PKWT conversion (demi hukum menjadi PKWTT)
  2. PHK disputes (pesangon calculation)
  3. Upah/wage disputes
  4. SP (surat peringatan) procedure violations

How to collect:
  1. Go to putusan3.mahkamahagung.go.id
  2. Search: "PHI PKWT 2024" or "PHK pesangon 2023"
  3. Open a decision page
  4. Ctrl+S -> Save as "Complete webpage" or "HTML only"
  5. Move the .html file to:
     corpus/putusan/raw/

Naming convention (optional but helpful):
  phi_jkt_2024_001.html
  ma_kasasi_2024_001.html

After collecting, run this script again to verify.

Also search Google for case numbers:
  "putusan PHI PKWT 2024 site:putusan3.mahkamahagung.go.id"
  "K/PDT.SUS-PHI/2024"

Or from legal blogs:
  hukumonline.com - often cites specific case numbers
  Legal analysis papers on PKWT disputes
===========================================================
""")


def print_search_terms():
    """Print useful search terms for putusan3."""
    print("""
USEFUL SEARCH TERMS (for putusan3 search box):
  - "PKWT demi hukum"
  - "perjanjian kerja waktu tertentu"
  - "pemutusan hubungan kerja"
  - "pesangon"
  - "upah minimum"
  - "surat peringatan SP"
  - "outsourcing alih daya"
  - "PHI" (in court type filter)

GOOGLE DORKS:
  site:putusan3.mahkamahagung.go.id "PHI" "PKWT" "2024"
  site:putusan3.mahkamahagung.go.id "K/PDT.SUS-PHI" "2023"
  site:putusan3.mahkamahagung.go.id "MENGADILI" "PKWTT"
""")


if __name__ == "__main__":
    print_collection_guide()
    indexed = scan_raw_files()
    if indexed:
        save_index(indexed)
    else:
        print("\nNo files yet. Follow the guide above to start collecting.")
    print_search_terms()
