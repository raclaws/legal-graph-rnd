"""
Collect PHI decision URLs from search results.
Outputs a seeds.json with case numbers and URLs for manual collection.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
BASE_URL = "https://putusan3.mahkamahagung.go.id"

SEARCH_TERMS = [
    "PKWT demi hukum PHI",
    "pemutusan hubungan kerja PHI",
    "K/PDT.SUS-PHI 2024",
    "K/PDT.SUS-PHI 2023",
    "pesangon PHI 2024",
]


async def run():
    print(f"Collecting PHI decision URLs... ({datetime.now().isoformat()})\n")

    all_decisions = {}

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

        # Load homepage first
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        for term in SEARCH_TERMS:
            print(f"  Searching: '{term}'")
            search_input = await page.query_selector("input[name='q']")
            if not search_input:
                search_input = await page.query_selector("input[type='text']")
            if not search_input:
                print("    No search input found, skipping")
                continue

            await search_input.fill("")
            await asyncio.sleep(0.5)
            await search_input.fill(term)
            await asyncio.sleep(1)
            await search_input.press("Enter")
            await asyncio.sleep(5)

            links = await page.query_selector_all("a[href*='/direktori/putusan/']")
            count = 0
            for link in links:
                text = (await link.inner_text()).strip()
                href = await link.get_attribute("href")
                if href and "PHI" in text.upper():
                    key = href.split("/")[-1]
                    if key not in all_decisions:
                        all_decisions[key] = {
                            "text": text[:100],
                            "url": href,
                            "search_term": term,
                        }
                        count += 1
            print(f"    Found {count} new PHI decisions (total: {len(all_decisions)})")

            # Go back to homepage for next search
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

        await browser.close()

    # Save seeds
    seeds = list(all_decisions.values())
    print(f"\nTotal unique PHI decisions: {len(seeds)}")

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    seeds_file = CORPUS_DIR / "seeds.json"
    seeds_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total": len(seeds),
        "decisions": seeds,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {seeds_file}")

    # Print for manual collection
    if seeds:
        print("\nURLs for manual download (open in browser, Ctrl+S):")
        for s in seeds[:20]:
            print(f"  {s['text'][:60]}")
            print(f"    {s['url']}")
            print()


if __name__ == "__main__":
    asyncio.run(run())
