"""
Jurisprudence R&D - Access test v4
Strategy: click links instead of goto (preserve session/cookies),
try captcha solve, try waiting for JS to execute.
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
    print("ACCESS TEST v4 - Click navigation + captcha check")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

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
        await asyncio.sleep(3)

        # Step 2: Check cookies set by homepage
        cookies = await context.cookies()
        print(f"\n[2] Cookies after homepage: {len(cookies)}")
        for c in cookies:
            print(f"  {c['name']}: {c['value'][:30]}...")

        # Step 3: Look for captcha and try to handle it
        print("\n[3] Checking for captcha...")
        content = await page.content()

        # Check if there's a captcha challenge we need to solve first
        captcha_frame = await page.query_selector("iframe[src*='captcha']")
        turnstile = await page.query_selector("[class*='turnstile'], [class*='cf-turnstile']")
        print(f"  Captcha iframe: {captcha_frame is not None}")
        print(f"  Turnstile widget: {turnstile is not None}")

        # Check if there's a captcha modal or overlay
        import re
        captcha_refs = re.findall(r'captcha[^"\'<>\s]{0,50}', content, re.I)
        print(f"  Captcha references in page: {captcha_refs[:5]}")

        # Step 4: Try clicking a PHI link directly from search results
        print("\n[4] Searching and clicking PHI link...")
        search_input = await page.query_selector("input[name='q']")
        if search_input:
            await search_input.fill("PHI PKWT")
            await asyncio.sleep(1)
            await search_input.press("Enter")
            await asyncio.sleep(5)

            # Find a PHI link
            links = await page.query_selector_all("a[href*='/direktori/putusan/']")
            print(f"  Found {len(links)} decision links")

            phi_link = None
            for link in links:
                text = await link.inner_text()
                if "PHI" in text:
                    phi_link = link
                    print(f"  Target: {text.strip()[:70]}")
                    break

            if not phi_link and links:
                phi_link = links[0]
                text = await phi_link.inner_text()
                print(f"  Fallback target: {text.strip()[:70]}")

            if phi_link:
                # Click instead of goto - preserves session
                print("\n[5] Clicking link (same tab)...")
                href = await phi_link.get_attribute("href")
                print(f"  href: {href}")

                # Method A: click the link directly
                try:
                    await phi_link.click()
                    await asyncio.sleep(5)
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)

                    current_url = page.url
                    title = await page.title()
                    print(f"  Navigated to: {current_url}")
                    print(f"  Title: {title}")

                    content = await page.content()

                    # Check if we hit cloudflare
                    if "Just a moment" in content or "cf-challenge" in content:
                        print("  Got Cloudflare challenge page")
                        # Wait for challenge to auto-solve
                        print("  Waiting 10s for challenge auto-solve...")
                        await asyncio.sleep(10)
                        content = await page.content()
                        title = await page.title()
                        print(f"  After wait - Title: {title}")

                    has_putusan = "PUTUSAN" in content or "Nomor" in content
                    has_mengadili = "MENGADILI" in content or "M E N G A D I L I" in content
                    print(f"  Has PUTUSAN: {has_putusan}")
                    print(f"  Has MENGADILI: {has_mengadili}")
                    print(f"  Content length: {len(content)}")

                    if has_mengadili or (has_putusan and len(content) > 5000):
                        RAW_DIR.mkdir(parents=True, exist_ok=True)
                        fname = current_url.split("/")[-1]
                        if not fname.endswith(".html"):
                            fname += ".html"
                        path = RAW_DIR / fname
                        path.write_text(content, encoding="utf-8")
                        print(f"  SAVED: {path}")
                        decisions_fetched.append({"url": current_url, "file": str(path)})
                    else:
                        # Dump first 500 chars to see what we got
                        text = await page.inner_text("body")
                        print(f"\n  Page content preview:")
                        for line in text.split("\n")[:15]:
                            line = line.strip()
                            if line:
                                print(f"    | {line[:80]}")

                except Exception as e:
                    print(f"  Click error: {e}")

                # Method B: open in new tab (different cookie context test)
                if not decisions_fetched:
                    print("\n[6] Trying: new page with same context...")
                    page2 = await context.new_page()
                    await stealth.apply_stealth_async(page2)
                    try:
                        url = href if href.startswith("http") else BASE_URL + href
                        resp2 = await page2.goto(url, wait_until="domcontentloaded", timeout=30000)
                        print(f"  Status: {resp2.status if resp2 else 'none'}")
                        if resp2 and resp2.status == 200:
                            content = await page2.content()
                            print(f"  Content length: {len(content)}")
                            if "MENGADILI" in content:
                                print("  SUCCESS via new page!")
                    except Exception as e:
                        print(f"  Error: {e}")
                    await page2.close()

        await browser.close()

    # Summary
    print("\n" + "=" * 60)
    if decisions_fetched:
        print(f"SUCCESS: {len(decisions_fetched)} decisions fetched!")
    else:
        print("BLOCKED: Decision pages still 403")
        print("Next steps:")
        print("  1. Try headful browser (visible window)")
        print("  2. Try with residential proxy")
        print("  3. Manual seed: download via real browser, feed to parser")
        print("  4. Formal MA data request (parallel track)")
    print("=" * 60)

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    out = CORPUS_DIR / "scrape_results_v4.json"
    out.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "decisions_fetched": decisions_fetched,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run())
