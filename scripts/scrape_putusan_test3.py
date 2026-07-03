"""
Jurisprudence R&D - Access test v3
Strategy: use the working path (homepage form submit), extract decision links,
then fetch actual decisions.
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
    print("ACCESS TEST v3 - Form submit + decision fetch")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    decisions_found = []
    decisions_fetched = []

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

        # Step 1: Load homepage
        print("\n[1] Loading homepage...")
        resp = await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        print(f"  Status: {resp.status}")
        await asyncio.sleep(2)

        # Step 2: Fill search and submit
        print("\n[2] Submitting search: 'PKWT hubungan industrial'")
        search_input = await page.query_selector("input[name='q']")
        if not search_input:
            # Try other selectors
            search_input = await page.query_selector("input[type='text']")
            print(f"  Fallback search input: {search_input is not None}")

        if search_input:
            await search_input.fill("PKWT hubungan industrial")
            await asyncio.sleep(1)

            # Check for category/court select
            selects = await page.query_selector_all("select")
            for sel in selects:
                name = await sel.get_attribute("name")
                print(f"  Found select: name={name}")

            await search_input.press("Enter")
            await asyncio.sleep(5)
            await page.wait_for_load_state("domcontentloaded", timeout=15000)

            print(f"  Current URL: {page.url}")
            print(f"  Title: {await page.title()}")

            # Step 3: Check for captcha
            content = await page.content()
            if "captcha" in content.lower():
                print("  CAPTCHA detected on page!")
                # Look for captcha element
                captcha_el = await page.query_selector("[class*='captcha'], #captcha, .g-recaptcha")
                print(f"  Captcha element: {captcha_el is not None}")

            # Step 4: Extract result links
            print("\n[3] Extracting decision links...")

            # Try various selectors for results
            selectors = [
                "a[href*='/direktori/putusan/']",
                "a[href*='putusan']",
                ".result a",
                ".search-result a",
                "table a",
                "#searchResult a",
                ".resultSearch a",
            ]
            for sel in selectors:
                links = await page.query_selector_all(sel)
                if links:
                    print(f"  Selector '{sel}': {len(links)} links")
                    for link in links[:5]:
                        href = await link.get_attribute("href")
                        text = (await link.inner_text()).strip()[:80]
                        if href and ("putusan" in href.lower() or "direktori" in href.lower()):
                            decisions_found.append({"href": href, "text": text})
                            print(f"    -> {text[:60]} | {href[:60]}")
                    break

            if not decisions_found:
                # Dump page structure for debugging
                print("\n  No decisions found. Page structure:")
                body = await page.query_selector("body")
                if body:
                    inner = await body.inner_text()
                    lines = [l.strip() for l in inner.split("\n") if l.strip()][:30]
                    for line in lines:
                        print(f"    | {line[:80]}")

                # Also dump all links
                all_links = await page.query_selector_all("a")
                print(f"\n  Total <a> tags: {len(all_links)}")
                for link in all_links[:20]:
                    href = await link.get_attribute("href") or ""
                    text = (await link.inner_text()).strip()[:40]
                    if href and href != "#" and text:
                        print(f"    [{text}] -> {href[:70]}")

        # Step 5: If we found decisions, try to fetch one
        if decisions_found:
            print(f"\n[4] Attempting to fetch first decision...")
            target = decisions_found[0]
            url = target["href"]
            if not url.startswith("http"):
                url = BASE_URL + url

            await asyncio.sleep(5)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                print(f"  URL: {url}")
                print(f"  Status: {resp.status if resp else 'none'}")

                if resp and resp.status == 200:
                    content = await page.content()
                    has_mengadili = "MENGADILI" in content or "M E N G A D I L I" in content
                    has_putusan = "PUTUSAN" in content
                    print(f"  Has PUTUSAN marker: {has_putusan}")
                    print(f"  Has MENGADILI marker: {has_mengadili}")
                    print(f"  Content length: {len(content)}")

                    if has_putusan or has_mengadili:
                        RAW_DIR.mkdir(parents=True, exist_ok=True)
                        fname = url.split("/")[-1]
                        if not fname.endswith(".html"):
                            fname += ".html"
                        path = RAW_DIR / fname
                        path.write_text(content, encoding="utf-8")
                        print(f"  SAVED: {path}")
                        decisions_fetched.append({"url": url, "file": str(path), "size": len(content)})
            except Exception as e:
                print(f"  Error: {e}")

        await browser.close()

    # Summary
    print("\n" + "=" * 60)
    print(f"Decisions found in search: {len(decisions_found)}")
    print(f"Decisions fetched: {len(decisions_fetched)}")
    if decisions_fetched:
        print("ACCESS CONFIRMED - pipeline viable!")
    elif decisions_found:
        print("Search works but fetch blocked - need session continuity or delay")
    else:
        print("Search returns no parseable links - needs captcha solve or different approach")
    print("=" * 60)

    # Save
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    out = CORPUS_DIR / "scrape_results_v3.json"
    out.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "decisions_found": decisions_found,
        "decisions_fetched": decisions_fetched,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    asyncio.run(run())
