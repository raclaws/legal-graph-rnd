"""Norm Validation — LLM-as-judge with adversarial framing.

Pipeline:
1. Export compiled norms + source Pasal text from Neo4j
2. Batch through LLM judge (adversarial: "find errors")
3. Aggregate verdicts, report pass rate

Guard-rails:
- Judge sees source text alongside extracted norm (can't rubber-stamp)
- Structured verdict: correct / partially_correct / wrong / ambiguous
- Mandatory reasoning field
- Adversarial system prompt ("your job is to find errors")
- Sub-agent batching (5 batches of ~50)

Usage:
  python scripts/validate_norms.py --calibrate   # 10-sample calibration round
  python scripts/validate_norms.py --full        # full 249 norms
  python scripts/validate_norms.py --review      # show results summary
"""

import sys
import json
import random
import asyncio
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import LegalGraph

OUTPUT_DIR = Path(__file__).parent.parent / "corpus" / "validation"
RESULTS_FILE = OUTPUT_DIR / "validation_results.json"
CALIBRATION_FILE = OUTPUT_DIR / "calibration_sample.json"

JUDGE_SYSTEM_PROMPT = """You are a legal accuracy auditor for Indonesian employment law (ketenagakerjaan).

Your job is to FIND ERRORS in automatically-extracted norms. You are adversarial — do not rubber-stamp.

You will receive:
1. SOURCE TEXT: The original Indonesian legal provision (Pasal) text
2. EXTRACTED NORM: What the system claims this provision means (obligation description, severity, subjects, quantities)

Your task: Determine whether the extracted norm ACCURATELY represents what the source text says.

Check specifically:
- Does the obligation/prohibition actually exist in the source text?
- Is the subject (pengusaha/pekerja/etc) correctly identified?
- Are thresholds/quantities (duration, amounts, percentages) correct?
- Is the severity assessment reasonable?
- Is the description a fair characterization, or does it hallucinate/distort?

IMPORTANT: A norm can be PARTIALLY correct — e.g., the obligation exists but the threshold is wrong, or the subject is misidentified.

Respond with ONLY a JSON object (no markdown, no explanation outside the JSON):
{
  "verdict": "correct" | "partially_correct" | "wrong" | "ambiguous",
  "reasoning": "<2-3 sentences explaining your judgment>",
  "errors": ["<specific error if any>"],
  "confidence": "high" | "medium" | "low"
}

Verdicts:
- correct: The norm accurately represents the source text
- partially_correct: Core obligation exists but details are wrong (threshold, subject, scope)
- wrong: The norm does not exist in the source, or fundamentally mischaracterizes it
- ambiguous: Source text is genuinely unclear or the norm is a reasonable but debatable interpretation
"""

JUDGE_USER_TEMPLATE = """## SOURCE TEXT (Pasal {node_id})

{source_text}

---

## EXTRACTED NORM

- **Description:** {description}
- **Severity:** {severity}
- **Subjects:** {subjects}
- **Quantities:** {quantities}
- **Obligation markers:** {markers}
- **Consequence:** {consequence}

---

Is this extraction accurate? Find any errors."""


@dataclass
class NormWithSource:
    node_id: str
    source_text: str
    description: str
    severity: str
    consequence: str
    confidence: str
    subjects: list[str]
    quantities: list[tuple]
    obligation_markers: list[str]


@dataclass
class ValidationResult:
    node_id: str
    verdict: str  # correct / partially_correct / wrong / ambiguous
    reasoning: str
    errors: list[str]
    judge_confidence: str
    batch_id: int = 0


EMPLOYMENT_PREFIXES = [
    "UU/2003/13",
    "UU/2004/2",
    "PP/2021/35",
    "PP/2021/36",
    "PP/2021/37",
    "PP/2021/34",
    "PP/2015/44",
    "PP/2015/45",
    "PP/2015/46",
]


def export_norms_with_source(graph: LegalGraph) -> list[NormWithSource]:
    """Export compiled norms paired with their source Pasal text (employment scope only)."""
    from src.compliance.norm_compiler import (
        compile_norms,
        build_consequence_map,
        resolve_consequence_map,
        extract_signals,
        classify,
    )

    with graph.driver.session() as session:
        result = session.run(
            """
            MATCH (p:Provision)
            WHERE p.text IS NOT NULL AND p.text <> ''
            RETURN p.node_id AS node_id, p.text AS text
            ORDER BY p.node_id
            """
        )
        all_provisions = [{"node_id": r["node_id"], "text": r["text"]} for r in result]

    # Filter to employment scope
    provisions = [p for p in all_provisions if any(p["node_id"].startswith(pfx) for pfx in EMPLOYMENT_PREFIXES)]

    all_node_ids = [p["node_id"] for p in provisions]
    raw_cmap = build_consequence_map(provisions)
    cmap = resolve_consequence_map(raw_cmap, all_node_ids)
    candidates = compile_norms(provisions, cmap)

    # Pair each candidate with its source text
    text_map = {p["node_id"]: p["text"] for p in provisions}
    norms = []
    for c in candidates:
        source = text_map.get(c.source, "")
        if source:
            norms.append(NormWithSource(
                node_id=c.source,
                source_text=source,
                description=c.description,
                severity=c.severity,
                consequence=c.consequence,
                confidence=c.confidence,
                subjects=c.subjects,
                quantities=c.quantities,
                obligation_markers=c.obligation_markers,
            ))

    return norms


def build_judge_prompt(norm: NormWithSource) -> str:
    """Build the user message for the judge."""
    return JUDGE_USER_TEMPLATE.format(
        node_id=norm.node_id,
        source_text=norm.source_text[:1500],
        description=norm.description,
        severity=norm.severity,
        subjects=", ".join(norm.subjects) if norm.subjects else "(none detected)",
        quantities=str(norm.quantities) if norm.quantities else "(none detected)",
        markers=", ".join(norm.obligation_markers) if norm.obligation_markers else "(none)",
        consequence=norm.consequence or "(none linked)",
    )


async def judge_single(norm: NormWithSource, client, model: str) -> ValidationResult:
    """Run LLM judge on a single norm."""
    user_msg = build_judge_prompt(norm)

    try:
        response = await client.chat.completions.create(
            model=model,
            max_tokens=500,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )

        text = response.choices[0].message.content.strip()

        # Parse JSON response
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.rstrip("`").strip()

        result = json.loads(text)
        return ValidationResult(
            node_id=norm.node_id,
            verdict=result.get("verdict", "ambiguous"),
            reasoning=result.get("reasoning", ""),
            errors=result.get("errors", []),
            judge_confidence=result.get("confidence", "medium"),
        )
    except json.JSONDecodeError as e:
        return ValidationResult(
            node_id=norm.node_id,
            verdict="ambiguous",
            reasoning=f"JSON parse error: {str(e)[:50]}. Raw: {text[:150]}",
            errors=["json_parse_failed"],
            judge_confidence="low",
        )
    except Exception as e:
        return ValidationResult(
            node_id=norm.node_id,
            verdict="ambiguous",
            reasoning=f"Judge error: {type(e).__name__}: {str(e)[:100]}",
            errors=["judge_failed"],
            judge_confidence="low",
        )


async def judge_batch(norms: list[NormWithSource], batch_id: int, client, model: str) -> list[ValidationResult]:
    """Judge a batch sequentially (rate-limit friendly)."""
    results = []
    for i, norm in enumerate(norms):
        print(f"  [{batch_id}] {i+1}/{len(norms)} - {norm.node_id[:40]}...", end=" ", flush=True)
        result = await judge_single(norm, client, model)
        result.batch_id = batch_id
        results.append(result)
        print(f"-> {result.verdict}")
        await asyncio.sleep(0.5)  # gentle rate limit
    return results


def print_summary(results: list[ValidationResult]):
    """Print validation summary."""
    total = len(results)
    if total == 0:
        print("No results.")
        return

    verdicts = {}
    for r in results:
        verdicts[r.verdict] = verdicts.get(r.verdict, 0) + 1

    print(f"\n{'='*50}")
    print(f"VALIDATION SUMMARY ({total} norms)")
    print(f"{'='*50}")
    for v in ["correct", "partially_correct", "wrong", "ambiguous"]:
        count = verdicts.get(v, 0)
        pct = count / total * 100
        bar = "#" * int(pct / 2)
        print(f"  {v:20s}: {count:3d} ({pct:5.1f}%) {bar}")

    # Pass rate (correct + partially_correct)
    passing = verdicts.get("correct", 0) + verdicts.get("partially_correct", 0)
    pass_rate = passing / total * 100
    print(f"\n  Pass rate (correct + partial): {passing}/{total} = {pass_rate:.1f}%")
    print(f"  Strict pass rate (correct only): {verdicts.get('correct', 0)}/{total} = {verdicts.get('correct', 0)/total*100:.1f}%")

    gate = "PASS" if pass_rate >= 80 else "FAIL"
    print(f"\n  Gate (>=80%): {gate}")
    print(f"{'='*50}")

    # Show errors
    wrong = [r for r in results if r.verdict == "wrong"]
    if wrong:
        print(f"\nWRONG ({len(wrong)}):")
        for r in wrong[:10]:
            print(f"  - {r.node_id}")
            print(f"    {r.reasoning}")
            if r.errors:
                print(f"    Errors: {r.errors}")


def get_llm_client():
    """Create OpenAI-compatible client using project env (gateway)."""
    from openai import AsyncOpenAI
    import os
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    return AsyncOpenAI(api_key=api_key, base_url=base_url), model


async def run_calibration():
    """Run 10-sample calibration round for human review."""

    print("Exporting norms from Neo4j...")
    g = LegalGraph()
    norms = export_norms_with_source(g)
    g.close()
    print(f"  Got {len(norms)} norms with source text")

    # Pick 10 random with good spread
    high_conf = [n for n in norms if n.confidence == "high"]
    med_conf = [n for n in norms if n.confidence == "medium"]

    SAMPLE_SIZE = 50
    sample = []
    if high_conf:
        sample.extend(random.sample(high_conf, min(SAMPLE_SIZE // 2, len(high_conf))))
    if med_conf:
        sample.extend(random.sample(med_conf, min(SAMPLE_SIZE // 2, len(med_conf))))
    if len(sample) < SAMPLE_SIZE:
        remaining = [n for n in norms if n not in sample]
        sample.extend(random.sample(remaining, min(SAMPLE_SIZE - len(sample), len(remaining))))
    sample = sample[:SAMPLE_SIZE]

    print(f"\nCalibration sample: {len(sample)} norms")
    print(f"  High confidence: {sum(1 for s in sample if s.confidence == 'high')}")
    print(f"  Medium confidence: {sum(1 for s in sample if s.confidence == 'medium')}")

    # Run judge
    client, model = get_llm_client()

    print(f"\nRunning judge (model: {model})...")
    results = await judge_batch(sample, batch_id=0, client=client, model=model)

    # Save for human review
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "sample_size": len(sample),
        "model": model,
        "norms": [asdict(n) for n in sample],
        "results": [asdict(r) for r in results],
    }
    CALIBRATION_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved calibration to: {CALIBRATION_FILE}")

    print_summary(results)
    print("\nReview the file above. If the judge is too lenient/strict, we adjust the prompt before full run.")


async def run_full():
    """Full validation run — 5 parallel batches."""

    print("Exporting norms from Neo4j...")
    g = LegalGraph()
    norms = export_norms_with_source(g)
    g.close()
    print(f"  Got {len(norms)} norms with source text")

    # Split into 5 batches
    batch_size = len(norms) // 5 + 1
    batches = [norms[i:i+batch_size] for i in range(0, len(norms), batch_size)]
    print(f"  Split into {len(batches)} batches of ~{batch_size}")

    client, model = get_llm_client()

    print(f"\nRunning {len(batches)} judge batches (model: {model})...")
    tasks = [judge_batch(batch, i, client, model) for i, batch in enumerate(batches)]
    batch_results = await asyncio.gather(*tasks)

    all_results = []
    for batch in batch_results:
        all_results.extend(batch)

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "total_norms": len(norms),
        "model": model,
        "results": [asdict(r) for r in all_results],
    }
    RESULTS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved results to: {RESULTS_FILE}")

    print_summary(all_results)


def review():
    """Show saved results."""
    if RESULTS_FILE.exists():
        data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        results = [ValidationResult(**r) for r in data["results"]]
        print(f"Full run ({data['model']}):")
        print_summary(results)
    elif CALIBRATION_FILE.exists():
        data = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        results = [ValidationResult(**r) for r in data["results"]]
        print(f"Calibration ({data['model']}):")
        print_summary(results)
    else:
        print("No results found. Run --calibrate first.")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--calibrate" in args:
        asyncio.run(run_calibration())
    elif "--full" in args:
        asyncio.run(run_full())
    elif "--review" in args:
        review()
    else:
        print("Usage:")
        print("  python scripts/validate_norms.py --calibrate   # 10-sample for tuning")
        print("  python scripts/validate_norms.py --full        # full validation run")
        print("  python scripts/validate_norms.py --review      # show saved results")
