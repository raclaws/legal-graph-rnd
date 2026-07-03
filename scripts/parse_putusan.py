"""
Jurisprudence - Decision parser (Phase 3)
Extracts structured data from PHI court decisions.

Input: raw HTML file from putusan3
Output: structured Case dict ready for Neo4j ingestion
"""
import re
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
RAW_DIR = CORPUS_DIR / "raw"
PDF_DIR = CORPUS_DIR / "pdf"


@dataclass
class ParsedCase:
    file: str
    case_number: Optional[str] = None
    court: Optional[str] = None
    court_type: Optional[str] = None  # phi | ma | pt
    year: Optional[int] = None
    province: Optional[str] = None

    plaintiff_type: Optional[str] = None  # employee | employer | union
    defendant_type: Optional[str] = None

    dispute_type: Optional[str] = None
    facts_summary: Optional[str] = None

    norms_cited: list = None
    provisions_cited: list = None

    outcome: Optional[str] = None  # employee_wins | employer_wins | partial
    outcome_detail: Optional[str] = None
    award_amount: Optional[int] = None

    pertimbangan_summary: Optional[str] = None

    confidence: str = "low"  # high | medium | low

    def __post_init__(self):
        if self.norms_cited is None:
            self.norms_cited = []
        if self.provisions_cited is None:
            self.provisions_cited = []


# Section markers in Indonesian court decisions
SECTION_MARKERS = {
    "header": [
        r"P\s*U\s*T\s*U\s*S\s*A\s*N",
        r"PUTUSAN",
    ],
    "duduk_perkara": [
        r"TENTANG DUDUK(?:NYA)? PERKARA",
        r"DUDUK PERKARA",
        r"Menimbang,?\s*bahwa\s*(?:Penggugat|Pemohon)",
    ],
    "pertimbangan": [
        r"TENTANG (?:PERTIMBANGAN )?HUKUM(?:NYA)?",
        r"PERTIMBANGAN HUKUM",
    ],
    "amar": [
        r"M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I",
        r"MENGADILI",
        r"AMAR PUTUSAN",
    ],
}

# Case number patterns
CASE_NUMBER_PATTERNS = [
    # PHI first instance: 123/Pdt.Sus-PHI/2024/PN.Jkt.Pst
    r'(\d+/Pdt\.Sus-PHI/\d{4}/PN\.[A-Za-z.]+)',
    # MA cassation: 123 K/Pdt.Sus-PHI/2024
    r'(\d+\s*K/Pdt\.Sus-PHI/\d{4})',
    # General: Nomor XX/...
    r'Nomor\s*:?\s*([\d]+/[A-Za-z.\-]+/\d{4}/[A-Za-z.]+)',
    r'Nomor\s+([\d]+ K/[A-Za-z.\-]+/\d{4})',
]

# Provision citation patterns
PROVISION_PATTERNS = [
    # Pasal 59 ayat (1) UU Nomor 13 Tahun 2003
    r'Pasal\s+(\d+)\s*(?:ayat\s*\((\d+)\))?\s*(?:(?:huruf|angka)\s*\w+\s*)?(?:UU|PP|Perpres|Permen)\s*(?:Nomor\s*)?(\d+)\s*(?:Tahun\s*)?(\d{4})',
    # Pasal 59 UU No. 13/2003
    r'Pasal\s+(\d+)\s*(?:UU|PP|Perpres|Permen)\s*(?:No\.?\s*)?(\d+)/(\d{4})',
    # Pasal 81 angka 15 UU 6/2023 (Cipta Kerja style)
    r'Pasal\s+(\d+)\s*angka\s*(\d+)\s*(?:UU|Undang-Undang)\s*(?:Nomor\s*)?(\d+)\s*(?:Tahun\s*)?(\d{4})',
    # "Pasal 151 ... Undang Undang Nomor 13 Tahun 2003" (full text style from PDFs)
    r'Pasal\s+(\d+)\s*(?:ayat\s*\((\d+)\))?\s*(?:juncto\s+Pasal\s+\d+\s*)?(?:Undang[\s-]*Undang|Peraturan\s+Pemerintah|Peraturan\s+Presiden|Peraturan\s+Menteri)\s+Nomor\s+(\d+)\s+Tahun\s+(\d{4})',
    # "Pasal 40 Peraturan Pemerintah Nomor 35 Tahun 2021"
    r'Pasal\s+(\d+)\s*(?:ayat\s*\((\d+)\))?\s*Peraturan\s+Pemerintah\s+Nomor\s+(\d+)\s+Tahun\s+(\d{4})',
]

# Outcome signals
OUTCOME_SIGNALS = {
    "employee_wins": [
        r"[Mm]engabulkan\s+gugatan\s+(?:Penggugat|pemohon)",
        r"[Mm]enyatakan\s+.*demi\s+hukum\s+menjadi\s+PKWTT",
        r"[Mm]enyatakan\s+putus\s+hubungan\s+kerja",
        r"[Mm]enghukum\s+Tergugat\s+(?:untuk\s+)?membayar",
    ],
    "employer_wins": [
        r"[Mm]enolak\s+gugatan",
        r"[Gg]ugatan\s+(?:Penggugat\s+)?tidak\s+dapat\s+diterima",
        r"[Mm]enyatakan\s+gugatan\s+(?:Penggugat\s+)?ditolak",
    ],
    "partial": [
        r"[Mm]engabulkan\s+.*untuk\s+sebagian",
        r"[Mm]engabulkan\s+.*sebagian",
    ],
}


def clean_text(html: str) -> str:
    """Strip HTML tags, normalize whitespace."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&[a-z]+;', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_sections(text: str) -> dict:
    """Split decision text into major sections."""
    sections = {"header": "", "duduk_perkara": "", "pertimbangan": "", "amar": ""}

    # Find section boundaries
    boundaries = []
    for section_name, patterns in SECTION_MARKERS.items():
        for pattern in patterns:
            for m in re.finditer(pattern, text):
                boundaries.append((m.start(), section_name))
                break  # first match per pattern set
            if any(b[1] == section_name for b in boundaries):
                break

    boundaries.sort(key=lambda x: x[0])

    # Extract text between boundaries
    for i, (start, name) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        sections[name] = text[start:end]

    # If no boundaries found, put everything in header
    if not boundaries:
        sections["header"] = text

    return sections


def extract_case_number(text: str) -> Optional[str]:
    """Extract case number from decision text."""
    for pattern in CASE_NUMBER_PATTERNS:
        m = re.search(pattern, text[:3000])  # case number is always near the top
        if m:
            return m.group(1)
    return None


def classify_court(case_number: str) -> tuple:
    """Determine court type and details from case number."""
    if not case_number:
        return None, None, None

    court_type = None
    court = None
    year = None

    if "Pdt.Sus-PHI" in case_number:
        if " K/" in case_number or case_number.startswith(tuple(str(i) for i in range(10))):
            # Check if it's MA (starts with number + K/)
            if re.match(r'\d+\s*K/', case_number):
                court_type = "ma"
                court = "Mahkamah Agung"
            else:
                court_type = "phi"
                # Extract court from PN.Xxx.Yyy
                pn_match = re.search(r'PN\.([A-Za-z.]+)', case_number)
                if pn_match:
                    court = f"PHI {pn_match.group(1)}"
                else:
                    court = "PHI"

    year_match = re.search(r'/(\d{4})(?:/|$)', case_number)
    if year_match:
        year = int(year_match.group(1))

    return court_type, court, year


def extract_provisions(text: str) -> list:
    """Extract legal provision citations from text."""
    provisions = []
    seen = set()

    for pattern in PROVISION_PATTERNS:
        for m in re.finditer(pattern, text):
            # Normalize to a consistent format
            groups = m.groups()
            key = m.group(0)
            if key not in seen:
                seen.add(key)
                provisions.append({
                    "raw": m.group(0),
                    "pasal": groups[0],
                    "groups": groups,
                })

    return provisions


def extract_outcome(amar_text: str) -> tuple:
    """Determine outcome from MENGADILI section."""
    if not amar_text:
        return None, None, None

    # Check patterns in order: partial first (most specific)
    for outcome, patterns in [("partial", OUTCOME_SIGNALS["partial"]),
                               ("employee_wins", OUTCOME_SIGNALS["employee_wins"]),
                               ("employer_wins", OUTCOME_SIGNALS["employer_wins"])]:
        for pattern in patterns:
            if re.search(pattern, amar_text):
                # Try to extract award amount
                amount = None
                amount_match = re.search(
                    r'Rp\.?\s*([\d.,]+)',
                    amar_text
                )
                if amount_match:
                    amount_str = amount_match.group(1).replace(".", "").replace(",", "")
                    try:
                        amount = int(amount_str)
                    except ValueError:
                        pass

                # Get outcome detail (first sentence of amar)
                detail = amar_text[:200].strip()

                return outcome, detail, amount

    return None, None, None


def parse_decision(filepath: Path) -> ParsedCase:
    """Parse a single court decision HTML file into structured data."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    text = clean_text(content)

    case = ParsedCase(file=filepath.name)

    # Case number
    case.case_number = extract_case_number(text)
    case.court_type, case.court, case.year = classify_court(case.case_number)

    # Split into sections
    sections = split_sections(text)

    # Provisions cited (from pertimbangan section mainly)
    pertimbangan = sections.get("pertimbangan", "")
    case.provisions_cited = extract_provisions(pertimbangan or text)

    # Outcome
    amar = sections.get("amar", "")
    case.outcome, case.outcome_detail, case.award_amount = extract_outcome(amar)

    # Confidence scoring
    has_case_num = case.case_number is not None
    has_sections = bool(sections.get("amar"))
    has_outcome = case.outcome is not None

    if has_case_num and has_sections and has_outcome:
        case.confidence = "high"
    elif has_case_num and (has_sections or has_outcome):
        case.confidence = "medium"
    else:
        case.confidence = "low"

    return case


def parse_pdf_decision(filepath: Path) -> ParsedCase:
    """Parse a PDF court decision into structured data."""
    try:
        import fitz
    except ImportError:
        print("  pymupdf not installed, skipping PDF")
        return ParsedCase(file=filepath.name)

    doc = fitz.open(str(filepath))
    text = ""
    for page in doc:
        text += page.get_text()

    case = ParsedCase(file=filepath.name)

    # Case number
    case.case_number = extract_case_number(text)
    case.court_type, case.court, case.year = classify_court(case.case_number)

    # Split into sections
    sections = split_sections(text)

    # Provisions cited
    pertimbangan = sections.get("pertimbangan", "")
    case.provisions_cited = extract_provisions(pertimbangan or text)

    # Outcome
    amar = sections.get("amar", "")
    case.outcome, case.outcome_detail, case.award_amount = extract_outcome(amar)

    # Confidence scoring
    has_case_num = case.case_number is not None
    has_sections = bool(sections.get("amar"))
    has_outcome = case.outcome is not None

    if has_case_num and has_sections and has_outcome:
        case.confidence = "high"
    elif has_case_num and (has_sections or has_outcome):
        case.confidence = "medium"
    else:
        case.confidence = "low"

    return case


def parse_all(raw_dir: Path = RAW_DIR, pdf_dir: Path = PDF_DIR) -> list:
    """Parse all HTML and PDF files."""
    results = []

    # Parse HTML files
    if raw_dir.exists():
        files = list(raw_dir.glob("*.html"))
        if files:
            print(f"Parsing {len(files)} HTML files...")
            for f in files:
                case = parse_decision(f)
                results.append(case)
                conf = {"high": "+", "medium": "~", "low": "-"}[case.confidence]
                print(f"  [{conf}] {f.name}: {case.case_number or '?'} -> {case.outcome or '?'} ({len(case.provisions_cited)} provisions)")

    # Parse PDF files
    if pdf_dir.exists():
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if pdf_files:
            print(f"Parsing {len(pdf_files)} PDF files...")
            for f in pdf_files:
                case = parse_pdf_decision(f)
                results.append(case)
                conf = {"high": "+", "medium": "~", "low": "-"}[case.confidence]
                print(f"  [{conf}] {f.name}: {case.case_number or '?'} -> {case.outcome or '?'} ({len(case.provisions_cited)} provisions)")

    # Summary
    high = sum(1 for r in results if r.confidence == "high")
    med = sum(1 for r in results if r.confidence == "medium")
    low = sum(1 for r in results if r.confidence == "low")
    print(f"\nConfidence: {high} high, {med} medium, {low} low")
    print(f"Outcomes: {sum(1 for r in results if r.outcome)} / {len(results)} extracted")

    return results


if __name__ == "__main__":
    results = parse_all()
    if results:
        out = CORPUS_DIR / "parsed_results.json"
        out.write_text(
            json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\nSaved: {out}")
    else:
        print("\nNo files to parse. Run collect_putusan.py for instructions.")
