"""
Jurisprudence - Batch PDF scraper
Downloads PHI decisions from putusan3 via nodriver.

Safety measures:
- Random delays 8-15s between requests
- Session rotation every 10 downloads (new browser context)
- Stop on consecutive 403s (IP flagged)
- Scrape during off-hours where possible
- Save progress incrementally (resume-safe)
"""
import nodriver as uc
import asyncio
import json
import random
import time
from pathlib import Path
from datetime import datetime

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
PDF_DIR = CORPUS_DIR / "pdf"
PROGRESS_FILE = CORPUS_DIR / "scrape_progress.json"
BASE_URL = "https://putusan3.mahkamahagung.go.id"

# Config
MAX_DECISIONS = 30  # first batch target
DELAY_MIN = 8  # seconds between requests
DELAY_MAX = 15
SESSION_ROTATE_EVERY = 10  # new browser every N downloads
MAX_CONSECUTIVE_FAILS = 3  # stop if N consecutive failures
SEARCH_TERMS = [
    "K/PDT.SUS-PHI 2024",
    "K/PDT.SUS-PHI 2023",
    "K/PDT.SUS-PHI 2025",
    "PKWT PHI",
    "pemutusan hubungan kerja PHI 2024",
    "pesangon PHI 2023",
]


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"downloaded": [], "failed": [], "seen_urls": []}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(
        json.dumps(progress, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


async def create_browser():
    """Create a fresh browser instance."""
    browser = await uc.start(headless=False)
    return browser


async def collect_decision_urls(browser, search_term: str, existing_urls: set) -> list:
    """Search and collect decision page URLs."""
    decisions = []

    page = await browser.get(BASE_URL)
    await asyncio.sleep(random.uniform(3, 5))

    search_input = await page.find("input[name='q']", best_match=True)
    if not search_input:
        return decisions

    await search_input.send_keys(search_term)
    await asyncio.sleep(1)
    await search_input.send_keys("\n")
    await asyncio.sleep(random.uniform(5, 8))

    links = await page.select_all("a[href*='/direktori/putusan/']")
    for link in links or []:
        text = link.text or ""
        href = link.attrs.get("href", "")
        if href and "PHI" in text.upper() and href not in existing_urls:
            decisions.append({"text": text.strip()[:100], "url": href})

    return decisions


async def download_decision_pdf(browser, decision_url: str, download_path: str) -> dict:
    """Navigate to decision page and download PDF + extract related decisions."""
    result = {"url": decision_url, "success": False, "related_decisions": []}

    try:
        page = await browser.get(decision_url)
        await asyncio.sleep(random.uniform(5, 8))

        title = await page.evaluate("document.title")

        # Check for CF challenge
        if "Tunggu" in title or "Just a moment" in title:
            # Wait for auto-solve
            await asyncio.sleep(12)
            title = await page.evaluate("document.title")
            if "Tunggu" in title:
                result["error"] = "cloudflare_stuck"
                return result

        # Extract "keputusan terkait" (related decisions = appeal chain)
        try:
            related = await page.evaluate("""
                (() => {
                    const links = [];
                    // Look for related decisions section
                    const allLinks = document.querySelectorAll('a[href*="/direktori/putusan/"]');
                    const mainUrl = window.location.href;
                    for (const a of allLinks) {
                        const href = a.href;
                        if (href && href !== mainUrl && a.innerText.trim().length > 5) {
                            const text = a.innerText.trim();
                            // Only grab links that look like case references (not nav)
                            if (text.includes('Putusan') || text.includes('Nomor') || /\\d+\\//.test(text)) {
                                links.push({url: href, text: text.slice(0, 120)});
                            }
                        }
                    }
                    return links;
                })()
            """)
            if related:
                result["related_decisions"] = related
        except Exception:
            pass

        # Set download behavior
        try:
            await page.send(uc.cdp.browser.set_download_behavior(
                behavior="allow",
                download_path=download_path
            ))
        except Exception:
            pass

        # Find and click PDF link
        pdf_link = await page.find(".pdf", best_match=True)
        if not pdf_link:
            pdf_link = await page.select("a[href*='download_file']")

        if pdf_link:
            # Record existing PDFs before click
            existing = set(f.name for f in Path(download_path).glob("*.pdf"))

            await pdf_link.click()
            await asyncio.sleep(random.uniform(8, 12))

            # Check for new PDF
            current = set(f.name for f in Path(download_path).glob("*.pdf"))
            new_files = current - existing
            if new_files:
                result["success"] = True
                result["file"] = list(new_files)[0]
                result["size"] = (Path(download_path) / result["file"]).stat().st_size
            else:
                result["error"] = "no_download"
        else:
            result["error"] = "no_pdf_link"

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


async def run():
    print("=" * 60)
    print("BATCH PDF SCRAPER")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Target: {MAX_DECISIONS} decisions")
    print(f"Delay: {DELAY_MIN}-{DELAY_MAX}s between requests")
    print(f"Session rotation: every {SESSION_ROTATE_EVERY} downloads")
    print("=" * 60)

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    download_path = str(PDF_DIR.resolve())

    progress = load_progress()
    existing_urls = set(progress["seen_urls"])
    downloaded_count = len(progress["downloaded"])
    consecutive_fails = 0

    if downloaded_count >= MAX_DECISIONS:
        print(f"\nAlready have {downloaded_count} decisions. Done.")
        return

    print(f"\nResuming: {downloaded_count} already downloaded")

    # Phase 1: Collect URLs
    print("\n[Phase 1] Collecting decision URLs...")
    browser = await create_browser()
    all_decisions = []

    for term in SEARCH_TERMS:
        if len(all_decisions) >= MAX_DECISIONS * 2:
            break
        print(f"  Searching: '{term}'")
        new = await collect_decision_urls(browser, term, existing_urls)
        all_decisions.extend(new)
        print(f"    Found {len(new)} new (total queue: {len(all_decisions)})")
        await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    browser.stop()
    print(f"\n  Total in queue: {len(all_decisions)}")

    if not all_decisions:
        print("  No new decisions found. Done.")
        return

    # Phase 2: Download PDFs
    print(f"\n[Phase 2] Downloading PDFs (max {MAX_DECISIONS - downloaded_count} more)...")
    browser = await create_browser()
    session_count = 0

    for i, decision in enumerate(all_decisions):
        if downloaded_count >= MAX_DECISIONS:
            print(f"\n  Reached target ({MAX_DECISIONS}). Stopping.")
            break

        if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
            print(f"\n  {MAX_CONSECUTIVE_FAILS} consecutive failures - IP likely flagged. Stopping.")
            break

        # Session rotation
        if session_count > 0 and session_count % SESSION_ROTATE_EVERY == 0:
            print(f"\n  Rotating session (after {session_count} requests)...")
            browser.stop()
            await asyncio.sleep(random.uniform(10, 20))
            browser = await create_browser()

        url = decision["url"]
        progress["seen_urls"].append(url)

        print(f"\n  [{downloaded_count+1}/{MAX_DECISIONS}] {decision['text'][:60]}")
        result = await download_decision_pdf(browser, url, download_path)

        if result["success"]:
            print(f"    OK: {result['file']} ({result['size']} bytes)")
            if result["related_decisions"]:
                print(f"    Related: {len(result['related_decisions'])} linked decisions (appeal chain)")
            progress["downloaded"].append({
                "url": url,
                "file": result["file"],
                "size": result["size"],
                "related_decisions": result.get("related_decisions", []),
                "timestamp": datetime.now().isoformat(),
            })
            downloaded_count += 1
            consecutive_fails = 0
        else:
            print(f"    FAIL: {result.get('error', 'unknown')}")
            progress["failed"].append({
                "url": url,
                "error": result.get("error"),
                "timestamp": datetime.now().isoformat(),
            })
            consecutive_fails += 1

        session_count += 1
        save_progress(progress)

        # Delay before next request
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        print(f"    Waiting {delay:.1f}s...")
        await asyncio.sleep(delay)

    browser.stop()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Downloaded: {len(progress['downloaded'])}")
    print(f"  Failed: {len(progress['failed'])}")
    print(f"  Total PDFs: {len(list(PDF_DIR.glob('*.pdf')))}")
    if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
        print(f"\n  WARNING: Stopped due to consecutive failures.")
        print(f"  Wait 30+ minutes before retrying, or use a different IP.")
    print("=" * 60)
    save_progress(progress)


if __name__ == "__main__":
    uc.loop().run_until_complete(run())
