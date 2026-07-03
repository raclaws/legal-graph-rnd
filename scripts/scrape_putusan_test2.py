"""
Jurisprudence R&D — Access test v2
Strategy: navigate like a human (homepage → search) instead of direct URL hits.
Also try: cookies from homepage session, different URL patterns, Google cache.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
RAW_DIR = CORPUS_DIR / "raw"
BASE_URL = "https://putusan3.mahkamahagung.go.id"


async def run():
    print("=" * 60)
    print("ACCESS TEST v2 — Human-like navigation")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="id-ID",
        )
        stealth = Stealth()
        page = await context.new_page()
        await stealth.apply_stealth_async(page)

        # Strategy 1: Load homepage, then navigate to search via form
        print("\n[Strategy 1] Homepage -> search form submission")
        resp = await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        print(f"  Homepage: {resp.status}")
        await asyncio.sleep(3)

        # Look for search form on homepage
        search_input = await page.query_selector("input[name='q']")
        search_form = await page.query_selector("form[action*='search']")
        print(f"  Search input found: {search_input is not None}")
        print(f"  Search form found: {search_form is not None}")

        if search_input:
            await search_input.fill("PKWT")
            await asyncio.sleep(1)
            await search_input.press("Enter")
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            print(f"  After search URL: {page.url}")
            print(f"  After search status: checking content...")
            content = await page.content()
            has_results = "putusan" in content.lower() and "403" not in await page.title()
            print(f"  Has results: {has_results}")
            print(f"  Page title: {await page.title()}")
            results.append({"strategy": "form_submit", "success": has_results, "url": page.url})

        # Strategy 2: Try different URL patterns
        print("\n[Strategy 2] Alternative URL patterns")
        alt_urls = [
            f"{BASE_URL}/direktori/index-putusan.html",
            f"{BASE_URL}/beranda/index/pengadilan/phi.html",
            f"{BASE_URL}/pengadilan/phi",
            f"{BASE_URL}/kategori/index/pengadilan/phi/kategori/perdata-khusus-1/sub/phi-1.html",
        ]
        for url in alt_urls:
            await asyncio.sleep(3)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                status = resp.status if resp else "timeout"
                title = await page.title()
                print(f"  {url.split('.go.id')[1][:50]:50s} → {status} | {title[:40]}")
                if resp and resp.status == 200:
                    content = await page.content()
                    links = await page.query_selector_all("a[href*='putusan']")
                    if links:
                        print(f"    Found {len(links)} putusan links!")
                        for link in links[:3]:
                            href = await link.get_attribute("href")
                            print(f"      → {href}")
                        results.append({"strategy": "alt_url", "url": url, "success": True, "links": len(links)})
                        break
            except Exception as e:
                print(f"  {url.split('.go.id')[1][:50]:50s} → Error: {str(e)[:40]}")

        # Strategy 3: Google referrer (sometimes WAFs allow Google-referred traffic)
        print("\n[Strategy 3] With Google referrer header")
        await asyncio.sleep(3)
        await page.set_extra_http_headers({"Referer": "https://www.google.com/"})
        try:
            resp = await page.goto(
                f"{BASE_URL}/search.html?q=PKWT&cat=putus",
                wait_until="domcontentloaded",
                timeout=15000
            )
            status = resp.status if resp else "timeout"
            print(f"  Search with Google referer: {status}")
            if resp and resp.status == 200:
                links = await page.query_selector_all("a[href*='putusan']")
                print(f"  Links found: {len(links)}")
                results.append({"strategy": "google_referer", "success": len(links) > 0})
        except Exception as e:
            print(f"  Error: {e}")

        # Strategy 4: Check if there's a non-www or alternate subdomain
        print("\n[Strategy 4] Alternate domains")
        alt_domains = [
            "https://putusan.mahkamahagung.go.id",
            "https://www.mahkamahagung.go.id/id/putusan",
        ]
        for url in alt_domains:
            await asyncio.sleep(3)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                status = resp.status if resp else "timeout"
                final_url = page.url
                print(f"  {url[:50]:50s} → {status} (final: {final_url[:60]})")
                results.append({"strategy": "alt_domain", "url": url, "status": status, "final": final_url})
            except Exception as e:
                print(f"  {url[:50]:50s} → {str(e)[:50]}")

        # Strategy 5: Check page source for API endpoints
        print("\n[Strategy 5] Look for API/AJAX endpoints on homepage")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        content = await page.content()
        # Look for XHR/fetch URLs in scripts
        import re
        api_patterns = re.findall(r'(https?://[^"\']+api[^"\']*|/api/[^"\']+|ajax[^"\']+)', content, re.I)
        fetch_patterns = re.findall(r'fetch\(["\']([^"\']+)', content)
        xhr_patterns = re.findall(r'\.open\(["\'](?:GET|POST)["\'],\s*["\']([^"\']+)', content)
        print(f"  API patterns: {api_patterns[:5]}")
        print(f"  Fetch patterns: {fetch_patterns[:5]}")
        print(f"  XHR patterns: {xhr_patterns[:5]}")

        await browser.close()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    any_success = any(r.get("success") for r in results)
    if any_success:
        print("✓ Found a working access path!")
    else:
        print("✗ All strategies returned 403 or no results")
        print("  → Next: try with residential proxy or headful browser")
        print("  → Parallel: start formal MA data request")

    # Save
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    out = CORPUS_DIR / "scrape_results_v2.json"
    out.write_text(json.dumps({"timestamp": datetime.now().isoformat(), "results": results}, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    asyncio.run(run())
