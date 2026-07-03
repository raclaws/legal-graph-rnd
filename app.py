"""HR Compliance Checker — Chat-based UI with Three-Space Output."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from src.compliance import TerminationReason, calculate_severance
from src.compliance.ump_2025 import UMP_2025
from src.compliance.pipeline import run_compliance_pipeline, DocType
from src.compliance.obligations import Verdict
from src.graph import LegalGraph, NEO4J_URI, NEO4J_USER

st.set_page_config(page_title="HR Compliance Checker", layout="wide", initial_sidebar_state="expanded")

# --- Settings loader ---
settings_path = Path(__file__).parent / ".settings.json"
if "settings_loaded" not in st.session_state:
    if settings_path.exists():
        saved = json.loads(settings_path.read_text())
        st.session_state.api_key = saved.get("api_key", "")
        st.session_state.base_url = saved.get("base_url", "https://api.anthropic.com")
        st.session_state.model = saved.get("model", "")
    else:
        st.session_state.setdefault("api_key", "")
        st.session_state.setdefault("base_url", "https://api.anthropic.com")
        st.session_state.setdefault("model", "")
    st.session_state.settings_loaded = True
if "available_models" not in st.session_state:
    st.session_state.available_models = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_questions" not in st.session_state:
    st.session_state.pending_questions = None
if "pending_context" not in st.session_state:
    st.session_state.pending_context = None


# --- LLM System Prompt ---
SYSTEM_PROMPT = """You are an Indonesian HR compliance assistant backed by a legal knowledge graph with 17 parsed regulations and 5,676 provisions.

RESPONSE FORMAT — return JSON:
{
  "hukum": ["fact + citation (Pasal reference)", ...],
  "analisis": "interpretation text or null",
  "perlu_dikonfirmasi": [
    {"question": "...", "type": "select|number|text|file", "options": [...] or null, "key": "unique_key", "why": "reason this matters"}
  ] or null,
  "intent": "severance_calc|ump_check|bpjs_rates|pkwt|phi_dispute|general_hr",
  "params": {
    "years_of_service": <int or null>,
    "monthly_salary": <int or null>,
    "termination_reason": <string or null>,
    "province": <string or null>
  },
  "needs_document": {
    "required": true/false,
    "doc_type": "contract|sk_phk|surat_peringatan|slip_gaji|perjanjian_kerja|other",
    "reason": "why the document is needed for accurate analysis"
  } or null
}

RULES:
- hukum: ONLY graph-backed facts with Pasal citation. If you can't cite it, put in analisis.
- analisis: Your reasoning/advice. Always labeled as interpretation. NEVER before hukum is populated.
- perlu_dikonfirmasi: Structured questions when critical info is missing. Types:
  - "select": multiple choice (provide options array)
  - "number": numeric input
  - "text": free text
  - "file": request document upload
- needs_document: Set when analysis REQUIRES a document for grounding. Cases:
  - PHI dispute risk: needs the employment contract or warning letters
  - Contract review: needs the contract text
  - Termination legality: needs SK PHK or surat peringatan
  - Wage compliance: needs slip gaji
  - PKWT status: needs the PKWT contract to check terms

KNOWLEDGE (from graph — 17 regulations):
- PP 35/2021: PKWT (max 5 tahun, Pasal 8), Alih Daya (Bab III), Waktu Kerja (Bab IV), PHK/Severance (Bab V, Pasal 36-59)
- PP 36/2021: Pengupahan, THR, Overtime, Min wage structure
- PP 37/2021: JKP (0.46%, 6 months benefit)
- PP 51/2023: UMP/UMK formula (amends PP 36/2021)
- PP 34/2021: TKA (foreign workers), RPTKA requirements
- PP 44/2015: JKK (0.24-1.74% risk-based, employer only) + JKM (0.30%, employer only)
- PP 45/2015: JP (3%: employer 2% + worker 1%, ceiling Rp 10,042,300)
- PP 46/2015: JHT (5.7%: employer 3.7% + worker 2%)
- Perpres 64/2020 jo. 19/2024: BPJS Kesehatan (5%: employer 4% + worker 1%, ceiling Rp 12,000,000)
- Permenaker 18/2022: PKWT implementation detail
- Permenaker 6/2023: BPJS TK contribution specifics
- UU 13/2003: Ketenagakerjaan (base, partially amended by Cipta Kerja)
- UU 2/2004: PHI (industrial dispute resolution — bipartite, mediasi, konsiliasi, arbitrase, PHI court)
- Perppu 2/2022 / UU 6/2023: Cipta Kerja
- UMP 2025: 38 provinces (DKI Jakarta Rp 5,396,000; Jawa Tengah Rp 2,169,725)

PHI DISPUTE KNOWLEDGE:
- UU 2/2004 Pasal 3-6: Bipartite negotiation (30 days mandatory first step)
- UU 2/2004 Pasal 8-16: Mediasi (by Disnaker mediator)
- UU 2/2004 Pasal 17-28: Konsiliasi (for interest/union disputes)
- UU 2/2004 Pasal 29-54: Arbitrase (binding, for interest/union disputes)
- UU 2/2004 Pasal 55-115: PHI Court (last resort, or for rights/PHK disputes)
- PP 35/2021 Pasal 37: Notice period (14 days for employer, 30 days for worker)
- Surat Peringatan: 3x warning letters required before PHK for misconduct (UU 13/2003 Pasal 161)

Return ONLY valid JSON, no markdown."""


def call_llm(messages: list[dict]) -> dict | None:
    """Call LLM with full conversation history."""
    import anthropic

    try:
        client = anthropic.Anthropic(
            api_key=st.session_state.api_key,
            base_url=st.session_state.base_url,
        )

        api_messages = [{"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{messages[0]['content']}"}]
        for msg in messages[1:]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.messages.create(
            model=st.session_state.model or "claude-sonnet-4-20250514",
            max_tokens=2048,
            timeout=120.0,
            messages=api_messages,
        )

        raw = None
        if hasattr(response, 'content') and response.content:
            raw = response.content[0].text
        elif hasattr(response, 'choices') and response.choices:
            raw = response.choices[0]['message']['content']
        else:
            resp_dict = response.__dict__ if hasattr(response, '__dict__') else {}
            choices = resp_dict.get('choices') or getattr(response, 'choices', None)
            if choices:
                raw = choices[0]['message']['content']

        if not raw:
            return None

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        return json.loads(raw)

    except json.JSONDecodeError:
        st.error("Failed to parse LLM response")
        if raw:
            st.code(raw[:500])
        return None
    except Exception as e:
        st.error(f"API error: {type(e).__name__}: {e}")
        return None


def extract_document_text(uploaded_file) -> str:
    """Extract text content from uploaded file."""
    import pymupdf

    name = uploaded_file.name.lower()
    content = uploaded_file.read()
    uploaded_file.seek(0)

    if name.endswith(".pdf"):
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            if text.strip():
                return text[:8000]
            return "[PDF is scanned/image-based — text extraction not available]"
        except Exception:
            return "[Could not read PDF]"
    elif name.endswith(".txt"):
        try:
            return content.decode("utf-8")[:8000]
        except Exception:
            return content.decode("latin-1")[:8000]
    elif name.endswith((".png", ".jpg", ".jpeg")):
        return f"[Image uploaded: {uploaded_file.name}, {len(content)} bytes — text extraction requires OCR]"
    else:
        return f"[File uploaded: {uploaded_file.name}, {len(content)} bytes]"


def call_llm_simple(prompt: str) -> str | None:
    """Call LLM with a single prompt, return raw text. Used by compliance pipeline."""
    import anthropic

    try:
        client = anthropic.Anthropic(
            api_key=st.session_state.api_key,
            base_url=st.session_state.base_url,
        )
        response = client.messages.create(
            model=st.session_state.model or "claude-sonnet-4-20250514",
            max_tokens=4096,
            timeout=120.0,
            messages=[{"role": "user", "content": prompt}],
        )

        if hasattr(response, 'content') and response.content:
            return response.content[0].text
        elif hasattr(response, 'choices') and response.choices:
            return response.choices[0]['message']['content']
        else:
            resp_dict = response.__dict__ if hasattr(response, '__dict__') else {}
            choices = resp_dict.get('choices') or getattr(response, 'choices', None)
            if choices:
                return choices[0]['message']['content']
        return None
    except Exception:
        return None


def analyze_document(doc_text: str, filename: str) -> tuple:
    """Run deterministic compliance pipeline.

    Returns (ComplianceReport, logs) or (None, logs) on failure.
    """
    return run_compliance_pipeline(doc_text, call_llm_simple, filename)


def render_checklist(report):
    """Render deterministic compliance report with clear visual hierarchy."""
    if isinstance(report, dict):
        _render_checklist_legacy(report)
        return

    score = report.score_pct
    violated = [r for r in report.results if r.verdict == Verdict.VIOLATED]
    not_eval = [r for r in report.results if r.verdict == Verdict.NOT_EVALUATED]
    compliant = [r for r in report.results if r.verdict == Verdict.COMPLIANT]

    # Score badge + summary line
    if score >= 80:
        st.success(f"**{score}%** — {report.doc_type.value.upper()} | {report.compliant} compliant, {report.violated} violations, {report.not_evaluated} unclear")
    elif score >= 50:
        st.warning(f"**{score}%** — {report.doc_type.value.upper()} | {report.compliant} compliant, {report.violated} violations, {report.not_evaluated} unclear")
    else:
        st.error(f"**{score}%** — {report.doc_type.value.upper()} | {report.compliant} compliant, {report.violated} violations, {report.not_evaluated} unclear")

    # Extracted fields — compact row
    fields = report.extracted_fields
    field_parts = []
    if fields.get("company_name"):
        field_parts.append(fields["company_name"])
    if fields.get("province"):
        field_parts.append(fields["province"])
    if fields.get("salary"):
        field_parts.append(f"Rp {fields['salary']:,.0f}")
    if fields.get("position"):
        field_parts.append(fields["position"])
    if fields.get("total_duration_months"):
        field_parts.append(f"{fields['total_duration_months']} bln")
    if field_parts:
        st.caption(" · ".join(field_parts))

    # Violations (critical first, then high, then medium)
    if violated:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        violated.sort(key=lambda r: severity_order.get(r.severity.value, 4))

        st.markdown("---")
        for r in violated:
            sev_icon = "🚨" if r.severity.value == "critical" else "❌" if r.severity.value == "high" else "⚠️"
            st.markdown(f"{sev_icon} **{r.obligation_description}**")
            st.caption(f"`{r.legal_basis}` — {r.detail}")

    # Not evaluated
    if not_eval:
        st.markdown("---")
        with st.expander(f"❓ {len(not_eval)} item tidak dapat dievaluasi (data tidak ditemukan)", expanded=False):
            for r in not_eval:
                st.markdown(f"- {r.obligation_description} — `{r.legal_basis}`")

    # Compliant (collapsed)
    if compliant:
        with st.expander(f"✅ {len(compliant)} item compliant", expanded=False):
            for r in compliant:
                st.markdown(f"- {r.obligation_description}")


def _render_checklist_legacy(analysis: dict):
    """Render old-format dict analysis (backward compat)."""
    doc_type = analysis.get("doc_type", "unknown")
    verdict = analysis.get("verdict", {})
    score = verdict.get("score_pct", 0)
    if score >= 80:
        st.success(f"**{score}%** — {doc_type}")
    elif score >= 50:
        st.warning(f"**{score}%** — {doc_type}")
    else:
        st.error(f"**{score}%** — {doc_type}")
    if verdict.get("top_actions"):
        for i, action in enumerate(verdict["top_actions"], 1):
            st.markdown(f"{i}. {action}")


def auto_continue():
    """Re-call LLM with updated conversation history. Logs steps in chat."""
    logs = []
    logs.append(f"Context: {len(st.session_state.messages)} messages")

    llm_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    total_chars = sum(len(m["content"]) for m in llm_messages)
    logs.append(f"Sending: {total_chars:,.0f} chars to `{st.session_state.model}`")

    import time
    t0 = time.time()
    parsed = call_llm(llm_messages)
    elapsed = time.time() - t0
    logs.append(f"LLM response: {elapsed:.1f}s")

    if parsed:
        logs.append(f"Intent: {parsed.get('intent', 'none')}")
        logs.append(f"Hukum: {len(parsed.get('hukum', []))} items")
        if parsed.get("perlu_dikonfirmasi"):
            logs.append(f"Perlu Dikonfirmasi: {len(parsed['perlu_dikonfirmasi'])} questions")
        if (parsed.get("needs_document") or {}).get("required"):
            logs.append(f"Document needed: {parsed['needs_document'].get('doc_type')}")

        parsed = handle_calculation(parsed)
        log_text = " | ".join(logs)
        st.session_state.messages.append({
            "role": "assistant",
            "content": json.dumps(parsed, ensure_ascii=False),
            "parsed": parsed,
            "logs": log_text,
        })
    else:
        logs.append("FAILED — no valid response")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Error: could not process",
            "parsed": None,
            "logs": " | ".join(logs),
        })

    st.rerun()


def render_response(parsed: dict, msg_index: int = -1):
    """Render response. Order: Analisis → Hukum → Perlu Dikonfirmasi → Document request.

    If perlu_dikonfirmasi or document needed, analisis is suppressed.
    Document request wins priority (rendered last = user's next action).
    """
    uid = msg_index if msg_index >= 0 else len(st.session_state.messages)
    perlu = parsed.get("perlu_dikonfirmasi")
    needs_doc = parsed.get("needs_document")
    hukum = parsed.get("hukum", [])
    analisis = parsed.get("analisis")

    has_blocking = bool(perlu) or (needs_doc and needs_doc.get("required"))

    # 1. Analisis (only if nothing is blocking)
    if analisis and not has_blocking:
        st.markdown("#### :thought_balloon: Analisis")
        st.caption("Interpretasi — bukan hukum. Hasil di pengadilan bisa berbeda.")
        st.markdown(analisis)
        st.divider()

    # 2. Hukum (always shown if available)
    if hukum:
        st.markdown("#### :bookmark: Hukum")
        for item in hukum:
            st.markdown(f"- {item}")
        st.divider()

    # 3. Perlu Dikonfirmasi (only if no document needed — document wins)
    if perlu and not (needs_doc and needs_doc.get("required")):
        st.markdown("#### :red_circle: Perlu Dikonfirmasi")
        answers = {}
        for q in perlu:
            qtype = q.get("type", "text")
            key = q.get("key", q["question"][:20])
            why = q.get("why", "")

            if why:
                st.caption(f"↳ {why}")

            if qtype == "select" and q.get("options"):
                answers[key] = st.selectbox(q["question"], q["options"], key=f"q_{key}_{uid}")
            elif qtype == "number":
                answers[key] = st.number_input(q["question"], min_value=0, key=f"q_{key}_{uid}")
            elif qtype == "file":
                uploaded = st.file_uploader(q["question"], type=["pdf", "png", "jpg", "txt", "docx"], key=f"q_{key}_{uid}")
                answers[key] = f"[Uploaded: {uploaded.name}]" if uploaded else None
            else:
                answers[key] = st.text_input(q["question"], key=f"q_{key}_{uid}")

        if st.button("Lanjutkan", key=f"continue_{uid}"):
            answer_text = "\n".join(f"- {k}: {v}" for k, v in answers.items() if v)
            st.session_state.messages.append({"role": "user", "content": f"Jawaban:\n{answer_text}"})
            auto_continue()

    # 4. Document request (highest priority — always last = user's immediate next action)
    if needs_doc and needs_doc.get("required"):
        st.markdown("#### :page_facing_up: Dokumen Diperlukan")
        st.info(f"**{needs_doc.get('doc_type', 'document')}** — {needs_doc.get('reason', '')}")
        uploaded = st.file_uploader(
            "Upload dokumen (PDF/gambar/teks)",
            type=["pdf", "png", "jpg", "txt", "docx"],
            key=f"doc_upload_{uid}",
        )
        if uploaded:
            import time
            logs = []
            t0 = time.time()

            logs.append(f"Step 1: Extracting from {uploaded.name}")
            doc_text = extract_document_text(uploaded)
            logs.append(f"  → {len(doc_text)} chars ({time.time()-t0:.1f}s)")

            logs.append("Step 2-7: Compliance analysis...")
            t1 = time.time()
            analysis = analyze_document(doc_text, uploaded.name)
            logs.append(f"  → Done ({time.time()-t1:.1f}s)")

            if analysis:
                verdict = analysis.get("verdict", {})
                logs.append(f"  → Score: {verdict.get('score_pct', '?')}%")
                st.session_state.messages.append({"role": "user", "content": f"[Uploaded: {uploaded.name}]"})
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": json.dumps(analysis, ensure_ascii=False),
                    "parsed": None,
                    "analysis": analysis,
                    "logs": "\n".join(logs),
                })
            else:
                st.session_state.messages.append({"role": "user", "content": f"[Dokumen: {uploaded.name}]\n\n{doc_text[:4000]}"})
                logs.append("  → FAILED, falling back to chat")
                st.session_state.messages.append({"role": "assistant", "content": "Fallback...", "parsed": None, "logs": "\n".join(logs)})
            st.rerun()


def handle_calculation(parsed: dict):
    """Handle calculator intents and inject results."""
    intent = parsed.get("intent")
    params = parsed.get("params", {})

    if intent == "severance_calc" and params.get("years_of_service") and params.get("monthly_salary"):
        try:
            reason = TerminationReason(params.get("termination_reason", "efisiensi_tutup"))
        except ValueError:
            reason = TerminationReason.EFFICIENCY_CLOSURE
        result = calculate_severance(params["years_of_service"], params["monthly_salary"], reason)

        hukum = parsed.get("hukum", [])
        hukum.extend([
            f"Pesangon: {result.pesangon_months} bln × Rp {params['monthly_salary']:,.0f} × {result.pesangon_multiplier}x = **Rp {result.pesangon:,.0f}** (PP 35/2021 Pasal 40 Ayat 2)",
            f"Penghargaan: {result.penghargaan_months} bln × Rp {params['monthly_salary']:,.0f} = **Rp {result.penghargaan:,.0f}** (PP 35/2021 Pasal 40 Ayat 3)",
            f"Penggantian Hak: 15% = **Rp {result.penggantian_hak:,.0f}** (PP 35/2021 Pasal 40 Ayat 4)",
            f"**TOTAL: Rp {result.total:,.0f}**",
        ])
        parsed["hukum"] = hukum

    elif intent == "ump_check" and params.get("province"):
        province = params["province"]
        ump_entry = next((u for u in UMP_2025 if u["province"].lower() == province.lower()), None)
        hukum = parsed.get("hukum", [])
        if ump_entry:
            hukum.append(f"UMP {ump_entry['province']} 2025: **Rp {ump_entry['amount']:,.0f}** (PP 51/2023)")
            if params.get("monthly_salary"):
                salary = params["monthly_salary"]
                if salary >= ump_entry["amount"]:
                    hukum.append(f"Gaji Rp {salary:,.0f} ≥ UMP → **COMPLIANT**")
                else:
                    hukum.append(f"Gaji Rp {salary:,.0f} < UMP → **VIOLATION** (PP 36/2021 Pasal 23)")
        parsed["hukum"] = hukum

    return parsed


# === SIDEBAR ===
with st.sidebar:
    st.title("HR Compliance")
    st.caption("Legal Knowledge Graph")

    st.divider()
    st.markdown("#### Quick Tools")

    with st.expander("Pesangon Calculator"):
        s_years = st.number_input("Masa Kerja", 0, 40, 5, key="sb_y")
        s_salary = st.number_input("Gaji (Rp)", 0, value=10_000_000, step=500_000, key="sb_s")
        s_reason = st.selectbox("Alasan", [r.value for r in TerminationReason], key="sb_r")
        if st.button("Hitung", key="sb_calc"):
            r = calculate_severance(s_years, s_salary, TerminationReason(s_reason))
            st.metric("Total", f"Rp {r.total:,.0f}")
            st.caption(f"Pesangon {r.pesangon:,.0f} + Penghargaan {r.penghargaan:,.0f} + Hak {r.penggantian_hak:,.0f}")

    with st.expander("UMP Check"):
        provinces = sorted([u["province"] for u in UMP_2025])
        sb_prov = st.selectbox("Provinsi", provinces, key="sb_prov")
        sb_sal = st.number_input("Gaji (Rp)", 0, value=0, step=500_000, key="sb_ump_sal")
        ump = next(u for u in UMP_2025 if u["province"] == sb_prov)
        st.metric(f"UMP {sb_prov}", f"Rp {ump['amount']:,.0f}")
        if sb_sal > 0:
            if sb_sal >= ump["amount"]:
                st.success("COMPLIANT")
            else:
                st.error(f"VIOLATION (kurang Rp {ump['amount'] - sb_sal:,.0f})")

    with st.expander("BPJS Rates"):
        bpjs_sal = st.number_input("Gaji (Rp)", 0, value=10_000_000, step=500_000, key="sb_bpjs")
        if bpjs_sal > 0:
            jp_base = min(bpjs_sal, 10_042_300)
            jkn_base = min(bpjs_sal, 12_000_000)
            emp = int(bpjs_sal * 0.54/100 + bpjs_sal * 0.30/100 + bpjs_sal * 3.7/100 + jp_base * 2/100 + bpjs_sal * 0.46/100 + jkn_base * 4/100)
            wrk = int(bpjs_sal * 2/100 + jp_base * 1/100 + jkn_base * 1/100)
            st.metric("Employer", f"Rp {emp:,.0f}")
            st.metric("Worker", f"Rp {wrk:,.0f}")
            st.metric("Total", f"Rp {emp + wrk:,.0f}")

    st.divider()
    st.markdown("#### Graph")
    with st.expander("Stats"):
        try:
            g = LegalGraph()
            with g.driver.session() as session:
                r = session.run("MATCH (n) WHERE n:Regulation OR n:Provision OR n:MinimumWage RETURN labels(n)[0] AS l, count(n) AS c ORDER BY c DESC")
                for rec in r:
                    st.text(f"{rec['l']}: {rec['c']}")
            g.close()
        except Exception:
            st.text("Neo4j unavailable")

    st.divider()
    st.markdown("#### Settings")
    with st.expander("LLM Config"):
        new_key = st.text_input("API Key", value=st.session_state.api_key, type="password", key="sb_key")
        new_base = st.text_input("Base URL", value=st.session_state.base_url, key="sb_base")
        new_model = st.text_input("Model", value=st.session_state.model or "claude-sonnet-4-20250514", key="sb_model")
        if st.button("Save", key="sb_save"):
            st.session_state.api_key = new_key
            st.session_state.base_url = new_base
            st.session_state.model = new_model
            settings_path.write_text(json.dumps({"api_key": new_key, "base_url": new_base, "model": new_model}, indent=2))
            st.success("Saved")

    if st.button("Clear Chat", key="clear"):
        st.session_state.messages = []
        st.session_state.pending_questions = None
        st.session_state.pending_context = None
        st.rerun()


# === MAIN CHAT AREA ===
st.title("Tanya HR Compliance")
st.caption("17 regulasi · 5,676 pasal · 38 provinsi — Three-space output (Hukum / Analisis / Perlu Dikonfirmasi)")

# --- Document attachment (compact strip) ---
if "attached_doc" not in st.session_state:
    st.session_state.attached_doc = None

col_upload, col_status = st.columns([3, 2])
with col_upload:
    uploaded = st.file_uploader(
        "Upload dokumen",
        type=["pdf", "png", "jpg", "txt", "docx"],
        key="doc_uploader",
        label_visibility="collapsed",
    )
    if uploaded:
        content = uploaded.read()
        st.session_state.attached_doc = {"name": uploaded.name, "content": content}
with col_status:
    if st.session_state.attached_doc:
        st.info(f"📎 **{st.session_state.attached_doc['name']}** — kirim pesan untuk analisis")
        if st.button("✕", key="remove_doc", help="Hapus lampiran"):
            st.session_state.attached_doc = None
            st.rerun()

# --- Render chat history ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("analysis"):
            render_checklist(msg["analysis"])
            if msg.get("logs"):
                with st.expander("Detail proses", expanded=False):
                    st.code(msg["logs"], language="text")
        elif msg["role"] == "assistant" and isinstance(msg.get("parsed"), dict):
            render_response(msg["parsed"], i)
        elif msg["role"] == "assistant" and msg.get("logs") and "FAILED" in msg.get("logs", ""):
            st.error(msg["content"])
            with st.expander("Error log", expanded=True):
                st.code(msg["logs"], language="text")
        elif msg["role"] == "assistant":
            st.markdown(msg.get("content", ""))
        else:
            st.markdown(msg["content"])

# --- Chat input ---
prompt = st.chat_input("Ketik pertanyaan HR...")

if prompt:
    if not st.session_state.api_key:
        st.warning("Set API key di sidebar Settings.")
    else:
        import time
        doc = st.session_state.attached_doc

        # === WITH DOCUMENT ===
        if doc:
            user_msg = f"{prompt}\n\n[Dokumen: {doc['name']}]"
            st.session_state.messages.append({"role": "user", "content": user_msg})

            with st.chat_message("assistant"):
                with st.status("Menganalisis dokumen...", expanded=True) as status:
                    logs = []
                    t0 = time.time()

                    st.write(f"📄 Membaca {doc['name']}...")
                    import io
                    fake_file = io.BytesIO(doc["content"])
                    fake_file.name = doc["name"]
                    doc_text = extract_document_text(fake_file)
                    logs.append(f"Extracted: {len(doc_text)} chars ({time.time()-t0:.1f}s)")

                    st.write("🔍 Mendeteksi tipe dokumen...")
                    st.write("📋 Mengekstrak data...")
                    t1 = time.time()
                    report, pipeline_logs = analyze_document(doc_text, doc["name"])
                    logs.extend(pipeline_logs)
                    logs.append(f"Pipeline: {time.time()-t1:.1f}s")

                    if report:
                        status.update(label=f"Selesai — Score: {report.score_pct}%", state="complete")
                    else:
                        status.update(label="Gagal menganalisis", state="error")

            if report:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Compliance report: {report.score_pct}%",
                    "parsed": None,
                    "analysis": report,
                    "logs": "\n".join(logs),
                })
            else:
                st.session_state.messages.append({"role": "user", "content": f"Context:\n{doc_text[:4000]}"})
                llm_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                parsed = call_llm(llm_messages)
                if parsed:
                    parsed = handle_calculation(parsed)
                    st.session_state.messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False), "parsed": parsed, "logs": "\n".join(logs)})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "Gagal memproses.", "parsed": None, "logs": "\n".join(logs)})

            st.session_state.attached_doc = None
            st.rerun()

        # === WITHOUT DOCUMENT (normal chat) ===
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            llm_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

            with st.chat_message("assistant"):
                with st.spinner("Memproses..."):
                    logs = []
                    t0 = time.time()
                    parsed = call_llm(llm_messages)
                    elapsed = time.time() - t0
                    logs.append(f"LLM: {elapsed:.1f}s")

            if parsed:
                parsed = handle_calculation(parsed)
                log_text = " | ".join(logs)
                st.session_state.messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False), "parsed": parsed, "logs": log_text})
            else:
                log_text = " | ".join(logs + ["FAILED"])
                st.session_state.messages.append({"role": "assistant", "content": "Tidak dapat memproses. Cek Settings.", "parsed": None, "logs": log_text})

            st.rerun()
