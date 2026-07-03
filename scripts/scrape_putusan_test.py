"""
Jurisprudence R&D — Phase 2: Access test
Try playwright-stealth against putusan3.mahkamahagung.go.id
Goal: validate we can load decision pages through Cloudflare WAF
"""
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
RAW_DIR = CORPUS_DIR / "raw"
RESULTS_FILE = CORPUS_DIR / "scrape_results.json"

SEARCH_URL = "https://putusan3.mahkamahagung.go.id/search.html"
BASE_URL = "https://putusan3.mahkamahagung.go.id"

# PHI PKWT cases — search parameters
SEARCH_QUERIES = [
    {"keyword": "PKWT demi hukum", "court": "PHI"},
    {"keyword": "perjanjian kerja waktu tertentu", "court": "PHI"},
]

# Known decision URLs to try directly (from legal blogs / google)
DIRECT_URLS = [
    # Format: /direktori/putusan/{id}.html
    # We'll discover these from search results
]


async def test_basic_access(page) -> dict:
    """Step 1: Can we even load the homepage?"""
    result = {"test": "homepage", "success": False, "status": None, "title": None}
    try:
        resp = await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        result["status"] = resp.status if resp else None
        result["title"] = await page.title()
        result["success"] = resp is not None and resp.status == 200
        # Check for Cloudflare challenge page
        content = await page.content()
        if "cf-challenge" in content or "Just a moment" in content:
            result["success"] = False
            result["note"] = "Cloudflare challenge detected"
        elif "Direktori Putusan" in content or "Mahkamah Agung" in content:
            result["note"] = "Real content loaded"
    except Exception as e:
        result["error"] = str(e)
    return result


async def test_search(page) -> dict:
    """Step 2: Can we use the search to find PHI decisions?"""
    result = {"test": "search", "success": False, "decisions_found": []}
    try:
        url = f"{SEARCH_URL}?q=PKWT+demi+hukum&cat=putus&tp=PHI"
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        result["status"] = resp.status if resp else None

        if resp and resp.status == 200:
            content = await page.content()
            if "cf-challenge" in content or "Just a moment" in content:
                result["note"] = "Cloudflare challenge on search"
                return result

            # Try to find decision links
            links = await page.query_selector_all("a[href*='/direktori/putusan/']")
            for link in links[:10]:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href:
                    result["decisions_found"].append({
                        "url": href if href.startswith("http") else BASE_URL + href,
                        "text": text.strip()[:100]
                    })

            result["success"] = len(result["decisions_found"]) > 0
            if not result["success"]:
                # Try alternate selectors
                all_links = await page.query_selector_all("a")
                putusan_links = []
                for l in all_links[:100]:
                    h = await l.get_attribute("href")
                    if h and "putusan" in h.lower():
                        putusan_links.append(h)
                result["all_putusan_links"] = putusan_links[:10]
    except Exception as e:
        result["error"] = str(e)
    return result


async def test_fetch_decision(page, url: str) -> dict:
    """Step 3: Can we load a specific decision page and extract content?"""
    result = {"test": "fetch_decision", "url": url, "success": False}
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        result["status"] = resp.status if resp else None

        if resp and resp.status == 200:
            content = await page.content()
            if "cf-challenge" in content or "Just a moment" in content:
                result["note"] = "Cloudflare challenge on decision page"
                return result

            # Check for decision markers
            has_putusan = "PUTUSAN" in content or "putusan" in content.lower()
            has_mengadili = "MENGADILI" in content or "M E N G A D I L I" in content
            has_menimbang = "Menimbang" in content

            result["markers"] = {
                "has_putusan": has_putusan,
                "has_mengadili": has_mengadili,
                "has_menimbang": has_menimbang,
            }
            result["content_length"] = len(content)
            result["success"] = has_putusan or has_mengadili

            if result["success"]:
                # Save raw HTML
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                filename = url.split("/")[-1].replace(".html", "") + ".html"
                filepath = RAW_DIR / filename
                filepath.write_text(content, encoding="utf-8")
                result["saved_to"] = str(filepath)
    except Exception as e:
        result["error"] = str(e)
    return result


async def run_test():
    print("=" * 60)
    print("JURISPRUDENCE ACCESS TEST")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {"timestamp": datetime.now().isoformat(), "tests": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="id-ID",
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        # Test 1: Homepage
        print("\n[1/3] Testing homepage access...")
        r1 = await test_basic_access(page)
        results["tests"].append(r1)
        print(f"  Status: {r1.get('status')} | Success: {r1['success']}")
        if r1.get("note"):
            print(f"  Note: {r1['note']}")

        if not r1["success"]:
            print("\n  BLOCKED at homepage. Cloudflare WAF active.")
            print("  Next steps: try residential proxy or formal MA request.")
            results["conclusion"] = "blocked_at_homepage"
            await browser.close()
            save_results(results)
            return

        # Wait between requests
        await asyncio.sleep(5)

        # Test 2: Search
        print("\n[2/3] Testing search...")
        r2 = await test_search(page)
        results["tests"].append(r2)
        print(f"  Status: {r2.get('status')} | Decisions found: {len(r2.get('decisions_found', []))}")
        if r2.get("decisions_found"):
            for d in r2["decisions_found"][:3]:
                print(f"    → {d['text'][:60]}")

        await asyncio.sleep(5)

        # Test 3: Fetch a decision (if we found any)
        decision_url = None
        if r2.get("decisions_found"):
            decision_url = r2["decisions_found"][0]["url"]

        if decision_url:
            print(f"\n[3/3] Fetching decision: {decision_url[:80]}...")
            r3 = await test_fetch_decision(page, decision_url)
            results["tests"].append(r3)
            print(f"  Status: {r3.get('status')} | Success: {r3['success']}")
            if r3.get("markers"):
                print(f"  Markers: {r3['markers']}")
            if r3.get("saved_to"):
                print(f"  Saved: {r3['saved_to']}")
        else:
            print("\n[3/3] Skipped — no decision URL found from search")
            # Try a direct URL pattern guess
            print("  Trying alternate: direktori listing...")
            alt_url = f"{BASE_URL}/direktori/index/pengadilan/phi.html"
            resp = await page.goto(alt_url, wait_until="domcontentloaded", timeout=30000)
            r3 = {"test": "direktori_listing", "status": resp.status if resp else None}
            content = await page.content()
            links = await page.query_selector_all("a[href*='putusan']")
            r3["links_found"] = len(links)
            results["tests"].append(r3)
            print(f"  Direktori status: {r3['status']} | Links: {r3['links_found']}")

        await browser.close()

    # Conclusion
    all_success = all(t.get("success", False) for t in results["tests"])
    if all_success:
        results["conclusion"] = "full_access"
        print("\n✓ FULL ACCESS — pipeline is viable")
    elif r1["success"]:
        results["conclusion"] = "partial_access"
        print("\n~ PARTIAL ACCESS — homepage works, search/fetch needs tuning")
    else:
        results["conclusion"] = "blocked"
        print("\n✗ BLOCKED — need proxy or formal request")

    save_results(results)


def save_results(results: dict):
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved: {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(run_test())
