"""Norm Compiler R&D Spike — extract obligations from Pasal text mechanically.

Hypothesis: Indonesian legal text uses predictable linguistic patterns for obligations.
If we can detect these signals, we can compile norms without LLM.

Benchmark: run against PP 35/2021, compare output to 15 hand-crafted PKWT norms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# === Signal Extraction ===

OBLIGATION_MARKERS = [
    # Explicit obligations
    (r'\bwajib\b', 'wajib', 1.0),
    (r'\bharus\b', 'harus', 0.9),
    (r'\bdilarang\b', 'dilarang', 1.0),
    (r'\btidak boleh\b', 'tidak_boleh', 0.9),
    (r'\btidak dapat\b', 'tidak_dapat', 0.8),
    (r'\btidak dapat mensyaratkan\b', 'prohibition', 1.0),
    (r'\btidak dapat memuat\b', 'prohibition', 0.9),
    (r'\btidak dapat diadakan\b', 'prohibition', 0.9),
    # Format/content requirements
    (r'\bdibuat secara\b', 'format_requirement', 0.8),
    (r'\bhanya dapat dibuat\b', 'restriction', 0.9),
    (r'\bhanya dapat dilakukan\b', 'restriction', 0.8),
    (r'\bpaling sedikit memuat\b', 'content_requirement', 0.9),
    (r'\bmenggunakan bahasa\b', 'format_requirement', 0.8),
    # Thresholds (explicit limits)
    (r'\bdilaksanakan paling lama\b', 'duration_limit', 0.8),
    (r'\bdilakukan paling lama\b', 'duration_limit', 0.8),
    (r'\bpaling lama\s+\d+\s*\(\w+\)\s*(tahun|bulan|hari)', 'duration_limit', 0.85),
    (r'\bberhak\b', 'berhak', 0.7),
    (r'\bsekurang-kurangnya\b', 'minimum', 0.8),
    (r'\bpaling sedikit\b', 'minimum', 0.8),
    (r'\bpaling lama\b', 'maximum', 0.8),
    (r'\bpaling banyak\b', 'maximum', 0.8),
    (r'\bpaling lambat\b', 'deadline', 0.8),
    (r'\bpaling tinggi\b', 'maximum', 0.7),
    (r'\bpaling rendah\b', 'minimum', 0.7),
    # Step 3: Passive-constraint patterns (factual limits with legal force)
    (r'\bdilaksanakan\b.{0,30}\bpaling\b', 'passive_constraint', 0.75),
    (r'\bdilakukan\b.{0,30}\bpaling\b', 'passive_constraint', 0.75),
    (r'\bdiberikan\b.{0,30}\bpaling\b', 'passive_constraint', 0.75),
    (r'\bberlaku\b.{0,30}\bpaling\b', 'passive_constraint', 0.75),
    (r'\bberakhir\b.{0,20}\b(apabila|jika|pada saat)\b', 'termination_condition', 0.7),
    (r'\bdilaksanakan\b.{0,40}\b\d+\s*\(\w+\)\s*(tahun|bulan|hari)', 'passive_duration', 0.8),
    (r'\bdilakukan\b.{0,40}\b\d+\s*\(\w+\)\s*(tahun|bulan|hari)', 'passive_duration', 0.8),
    (r'\bdiberikan\b.{0,40}\b\d+\s*\(\w+\)\s*(tahun|bulan|hari)', 'passive_duration', 0.8),
    (r'\btidak lebih dari\b', 'maximum', 0.85),
    (r'\btidak kurang dari\b', 'minimum', 0.85),
    (r'\btidak melebihi\b', 'maximum', 0.85),
]

CONSEQUENCE_MARKERS = [
    (r'\bpidana\b', 'criminal', 1.0),
    (r'\bdenda\b', 'fine', 0.9),
    (r'\bsanksi\b', 'sanction', 0.9),
    (r'\bsanksi administratif\b', 'admin_sanction', 0.8),
    (r'\bbatal demi hukum\b', 'void', 1.0),
    (r'\bdemi hukum\b', 'by_law', 0.9),
    (r'\btidak sah\b', 'invalid', 0.8),
    (r'\bberakhir\b', 'terminated', 0.5),
    (r'\bdicabut\b', 'revoked', 0.7),
]

SUBJECT_MARKERS = [
    (r'\bpengusaha\b', 'employer'),
    (r'\bperusahaan\b', 'company'),
    (r'\bpekerja\b', 'worker'),
    (r'\bburuh\b', 'worker'),
    (r'\bpemberi kerja\b', 'employer'),
    (r'\bpemerintah\b', 'government'),
    (r'\bmenteri\b', 'minister'),
    (r'\bgubernur\b', 'governor'),
]

QUANTITY_PATTERN = re.compile(
    r'(\d+)\s*\(([^)]+)\)\s*(tahun|bulan|hari|jam|persen|%|hari kerja)',
    re.IGNORECASE,
)

DEFINITION_MARKERS = [
    r'^dalam\s+(peraturan|undang-undang)',
    r'yang\s+dimaksud\s+dengan',
    r'^ketentuan\s+sebagaimana\s+dimaksud',
]


@dataclass
class Signal:
    obligation_markers: list[tuple[str, float]] = field(default_factory=list)
    consequence_markers: list[tuple[str, float]] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    quantities: list[tuple[str, str, str]] = field(default_factory=list)  # (number, text, unit)
    is_definition: bool = False
    is_reference_only: bool = False
    text_length: int = 0
    has_numbered_list: bool = False

    @property
    def obligation_score(self) -> float:
        if not self.obligation_markers:
            return 0.0
        return max(score for _, score in self.obligation_markers)

    @property
    def consequence_score(self) -> float:
        if not self.consequence_markers:
            return 0.0
        return max(score for _, score in self.consequence_markers)

    @property
    def severity_signal(self) -> str:
        if any(t == 'criminal' for t, _ in self.consequence_markers):
            return 'critical'
        if any(t == 'void' or t == 'by_law' for t, _ in self.consequence_markers):
            return 'high'
        if any(t == 'fine' or t == 'sanction' for t, _ in self.consequence_markers):
            return 'high'
        if any(t == 'admin_sanction' for t, _ in self.consequence_markers):
            return 'medium'
        if self.obligation_score >= 0.9:
            return 'high'
        return 'medium'


def extract_signals(text: str) -> Signal:
    """Extract linguistic signals from provision text."""
    if not text:
        return Signal()

    text_lower = text.lower()
    signals = Signal(text_length=len(text))

    # Obligation markers
    for pattern, marker_type, weight in OBLIGATION_MARKERS:
        if re.search(pattern, text_lower):
            signals.obligation_markers.append((marker_type, weight))

    # Consequence markers
    for pattern, marker_type, weight in CONSEQUENCE_MARKERS:
        if re.search(pattern, text_lower):
            signals.consequence_markers.append((marker_type, weight))

    # Subjects
    for pattern, subject in SUBJECT_MARKERS:
        if re.search(pattern, text_lower):
            if subject not in signals.subjects:
                signals.subjects.append(subject)

    # Quantities
    for match in QUANTITY_PATTERN.finditer(text):
        signals.quantities.append((match.group(1), match.group(2), match.group(3)))

    # Definition check
    for pattern in DEFINITION_MARKERS:
        if re.search(pattern, text_lower):
            signals.is_definition = True
            break

    # Reference-only check (mostly "sebagaimana dimaksud" without own content)
    if re.search(r'sebagaimana\s+dimaksud\s+dalam\s+pasal', text_lower):
        if signals.text_length < 100 and not signals.obligation_markers:
            signals.is_reference_only = True

    # Numbered list
    if re.search(r'^[a-z]\.\s', text, re.MULTILINE):
        signals.has_numbered_list = True

    return signals


# === Classification ===

class ProvisionType:
    NORM = "NORM"
    SOFT_NORM = "SOFT_NORM"
    DEFINITION = "DEFINITION"
    PROCEDURAL = "PROCEDURAL"
    REFERENCE = "REFERENCE"
    THRESHOLD = "THRESHOLD"


def classify(signals: Signal) -> str:
    """Decision tree: classify provision by signal pattern."""

    if signals.is_definition:
        return ProvisionType.DEFINITION

    if signals.is_reference_only:
        return ProvisionType.REFERENCE

    # Strong obligation + consequence in same provision
    if signals.obligation_score >= 0.8 and signals.consequence_score >= 0.7:
        return ProvisionType.NORM

    # Strong obligation without consequence (consequence elsewhere)
    if signals.obligation_score >= 0.8:
        return ProvisionType.SOFT_NORM

    # Has consequence markers but no obligation (penalty provision)
    if signals.consequence_score >= 0.8 and not signals.obligation_markers:
        return ProvisionType.PROCEDURAL

    # Quantities with a subject = implicit constraint
    if signals.quantities and signals.subjects:
        return ProvisionType.THRESHOLD

    return ProvisionType.PROCEDURAL


# === Candidate Norm ===

@dataclass
class CandidateNorm:
    source: str  # node_id
    description: str
    severity: str
    consequence: str
    confidence: str  # high, medium, low
    provision_type: str = ""
    subjects: list[str] = field(default_factory=list)
    quantities: list[tuple[str, str, str]] = field(default_factory=list)
    obligation_markers: list[str] = field(default_factory=list)


def extract_obligation_text(text: str) -> str:
    """Extract the core obligation statement from provision text."""
    # Take first sentence that contains an obligation marker
    sentences = re.split(r'[.;]\s*', text)
    for sent in sentences:
        sent_lower = sent.lower()
        for pattern, _, _ in OBLIGATION_MARKERS:
            if re.search(pattern, sent_lower):
                return sent.strip()[:200]
    return text[:200]


def extract_consequence_text(text: str) -> str:
    """Extract consequence/penalty from provision text."""
    sentences = re.split(r'[.;]\s*', text)
    for sent in sentences:
        sent_lower = sent.lower()
        for pattern, _, _ in CONSEQUENCE_MARKERS:
            if re.search(pattern, sent_lower):
                return sent.strip()[:200]
    return ""


# === Compiler ===

def compile_norms(provisions: list[dict], consequence_map: dict[str, str] | None = None) -> list[CandidateNorm]:
    """Compile candidate norms from a list of provisions.

    Args:
        provisions: list of dicts with 'node_id' and 'text' keys
        consequence_map: optional dict mapping node_id prefix -> consequence text
                         (built by build_consequence_map from penalty provisions)

    Returns:
        list of CandidateNorm objects (filtered: no empty/meaningless candidates)
    """
    candidates = []

    for p in provisions:
        text = p.get("text", "")
        node_id = p.get("node_id", "")

        if not text or len(text) < 20:
            continue

        signals = extract_signals(text)
        ptype = classify(signals)

        if ptype == ProvisionType.NORM:
            candidates.append(CandidateNorm(
                source=node_id,
                description=extract_obligation_text(text),
                severity=signals.severity_signal,
                consequence=extract_consequence_text(text),
                confidence="high",
                provision_type=ptype,
                subjects=signals.subjects,
                quantities=signals.quantities,
                obligation_markers=[m for m, _ in signals.obligation_markers],
            ))
        elif ptype == ProvisionType.SOFT_NORM:
            # Try cross-provision consequence lookup
            consequence = ""
            if consequence_map:
                consequence = _find_consequence(node_id, consequence_map)

            confidence = "high" if consequence else "medium"
            candidates.append(CandidateNorm(
                source=node_id,
                description=extract_obligation_text(text),
                severity=signals.severity_signal if not consequence else _severity_from_consequence(consequence),
                consequence=consequence,
                confidence=confidence,
                provision_type=ptype,
                subjects=signals.subjects,
                quantities=signals.quantities,
                obligation_markers=[m for m, _ in signals.obligation_markers],
            ))
        elif ptype == ProvisionType.THRESHOLD:
            consequence = ""
            if consequence_map:
                consequence = _find_consequence(node_id, consequence_map)

            candidates.append(CandidateNorm(
                source=node_id,
                description=extract_obligation_text(text),
                severity="medium",
                consequence=consequence,
                confidence="medium" if consequence else "low",
                provision_type=ptype,
                subjects=signals.subjects,
                quantities=signals.quantities,
                obligation_markers=[m for m, _ in signals.obligation_markers],
            ))

    return candidates


def _find_consequence(node_id: str, consequence_map: dict[str, str]) -> str:
    """Find consequence for a provision by checking the map.

    Tries exact match first, then Pasal-level match (without Ayat).
    """
    if node_id in consequence_map:
        return consequence_map[node_id]

    # Try Pasal-level (strip Ayat)
    pasal_match = re.match(r'(.+/Pasal/\d+[A-Z]?)', node_id)
    if pasal_match:
        pasal_id = pasal_match.group(1)
        if pasal_id in consequence_map:
            return consequence_map[pasal_id]

    return ""


def _severity_from_consequence(consequence: str) -> str:
    """Derive severity from consequence text."""
    lower = consequence.lower()
    if 'pidana' in lower:
        return 'critical'
    if 'batal demi hukum' in lower or 'demi hukum' in lower:
        return 'high'
    if 'denda' in lower or 'sanksi' in lower:
        return 'high'
    if 'administratif' in lower:
        return 'medium'
    return 'medium'


# === Step 4: Cross-provision consequence map ===

# Patterns that reference other Pasal in penalty clauses
RE_PASAL_REF = re.compile(r'Pasal\s+(\d+[A-Z]?(?:\s+ayat\s+\(\d+\))?)', re.IGNORECASE)


def build_consequence_map(provisions: list[dict]) -> dict[str, str]:
    """Build a map of node_id -> consequence text from penalty provisions.

    Scans all provisions for consequence markers. When found, extracts
    which Pasal they reference and maps those Pasal to the consequence text.

    Example: "Pelanggaran terhadap Pasal 12 dikenai sanksi administratif"
    -> {"PP/2021/35/Bab/II/Pasal/12": "sanksi administratif"}
    """
    consequence_provisions = []
    for p in provisions:
        text = p.get("text", "")
        if not text:
            continue
        signals = extract_signals(text)
        if signals.consequence_score >= 0.7:
            consequence_provisions.append(p)

    cmap: dict[str, str] = {}

    for p in consequence_provisions:
        text = p.get("text", "")
        node_id = p.get("node_id", "")
        consequence_text = extract_consequence_text(text) or text[:200]

        # Find which Pasal this penalty applies to
        refs = RE_PASAL_REF.findall(text)
        if refs:
            # Derive base path from this provision's node_id
            # e.g. PP/2021/35/Bab/V/Pasal/60 -> base is PP/2021/35
            base_match = re.match(r'([^/]+/\d+/\d+)', node_id)
            base = base_match.group(1) if base_match else ""

            for ref in refs:
                # ref is like "12" or "12 ayat (1)"
                pasal_num = re.match(r'(\d+[A-Z]?)', ref)
                if pasal_num and base:
                    # We don't know which Bab it's in — store with wildcard search later
                    # For now, just store the pasal number reference
                    ref_key = f"{base}/*/Pasal/{pasal_num.group(1)}"
                    cmap[ref_key] = consequence_text

        # Also: if this provision itself IS the consequence for the previous Pasal
        # Pattern: Ayat 2 with "batal demi hukum" following Ayat 1 with obligation
        if 'batal demi hukum' in text.lower() or 'demi hukum' in text.lower():
            # The consequence applies to the same Pasal
            pasal_match = re.match(r'(.+/Pasal/\d+[A-Z]?)', node_id)
            if pasal_match:
                cmap[pasal_match.group(1)] = consequence_text

    return cmap


def resolve_consequence_map(cmap: dict[str, str], all_node_ids: list[str]) -> dict[str, str]:
    """Resolve wildcard keys in consequence map against actual node_ids.

    Turns "PP/2021/35/*/Pasal/12" into "PP/2021/35/Bab/II/Pasal/12" by
    matching against known node_ids.
    """
    resolved = {}

    # Direct entries (no wildcard)
    for key, val in cmap.items():
        if '*' not in key:
            resolved[key] = val

    # Wildcard entries
    wildcard_entries = [(k, v) for k, v in cmap.items() if '*' in k]
    for wkey, val in wildcard_entries:
        # Convert "PP/2021/35/*/Pasal/12" to regex
        pattern = re.escape(wkey).replace(r'\*', r'[^/]+(/[^/]+)*')
        pattern = f"^{pattern}$"
        try:
            regex = re.compile(pattern)
            for nid in all_node_ids:
                if regex.match(nid):
                    resolved[nid] = val
        except re.error:
            continue

    return resolved


# === Benchmark ===

def benchmark_against_handcrafted(candidates: list[CandidateNorm], handcrafted_bases: list[str]) -> dict:
    """Compare compiled norms against hand-crafted norm legal_basis values.

    Returns recall metrics.
    """
    compiled_sources = {c.source for c in candidates}

    # Normalize handcrafted bases (some have Ayat/huruf levels we don't parse)
    handcrafted_pasal = set()
    for basis in handcrafted_bases:
        # Extract up to Pasal level
        match = re.match(r'(.+/Pasal/\d+)', basis)
        if match:
            handcrafted_pasal.add(match.group(1))

    compiled_pasal = set()
    for src in compiled_sources:
        match = re.match(r'(.+/Pasal/\d+)', src)
        if match:
            compiled_pasal.add(match.group(1))

    found = handcrafted_pasal & compiled_pasal
    missed = handcrafted_pasal - compiled_pasal
    extra = compiled_pasal - handcrafted_pasal

    return {
        "handcrafted_total": len(handcrafted_pasal),
        "compiled_total": len(compiled_pasal),
        "found": len(found),
        "missed": len(missed),
        "extra": len(extra),
        "recall_pct": int(len(found) / len(handcrafted_pasal) * 100) if handcrafted_pasal else 0,
        "found_list": sorted(found),
        "missed_list": sorted(missed),
        "extra_list": sorted(extra)[:20],
    }
