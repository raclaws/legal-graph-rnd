"""
Jurisprudence R&D - Access test v5: nodriver
Uses nodriver (CDP-based, no WebDriver) with built-in cf_verify() for Cloudflare.
"""
import nodriver as uc
import asyncio
import json
from pathlib import Path
from datetime import datetime

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
RAW_DIR = CORPUS_DIR / "raw"
BASE_URL = "https://putusan3.mahkamahagung.go.id"


async def run():
    print("=" * 60)
    print("ACCESS TEST v5 - nodriver + cf_verify")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    browser = await uc.start(headless=False)  # headful needed for CF challenge

    # Step 1: Load homepage
    print("\n[1] Loading homepage...")
    page = await browser.get(BASE_URL)
    await asyncio.sleep(5)

    title = await page.evaluate("document.title")
    print(f"  Title: {title}")

    content = await page.get_content()
    if "Just a moment" in content or "Tunggu" in title:
        print("  Cloudflare challenge detected, waiting for auto-solve...")
        await asyncio.sleep(10)
        title = await page.evaluate("document.title")
        print(f"  After wait - Title: {title}")
    else:
        print("  Homepage loaded clean")

    # Step 2: Search for PHI decisions
    print("\n[2] Searching for PHI decisions...")
    search_input = await page.find("input[name='q']", best_match=True)
    if not search_input:
        search_input = await page.select("input[type='text']")

    if search_input:
        await search_input.send_keys("K/PDT.SUS-PHI 2024")
        await asyncio.sleep(1)
        await search_input.send_keys("\n")  # Enter
        await asyncio.sleep(5)

        title = await page.evaluate("document.title")
        print(f"  Title after search: {title}")

        # Find PHI links
        links = await page.select_all("a[href*='/direktori/putusan/']")
        phi_links = []
        for link in links or []:
            text = link.text or ""
            href = link.attrs.get("href", "")
            if "PHI" in text.upper() and href:
                phi_links.append({"text": text.strip()[:80], "href": href})

        print(f"  PHI links found: {len(phi_links)}")
        for pl in phi_links[:5]:
            print(f"    -> {pl['text']}")
    else:
        print("  No search input found")
        phi_links = []

    # Step 3: Try to open a decision page
    if phi_links:
        target = phi_links[0]
        print(f"\n[3] Opening: {target['text']}")
        print(f"    URL: {target['href']}")

        page2 = await browser.get(target["href"])
        await asyncio.sleep(5)

        title = await page2.evaluate("document.title")
        content = await page2.get_content()
        print(f"  Title: {title}")

        # CF challenge on decision page?
        if "Just a moment" in content or "verifikasi" in content.lower() or "Tunggu" in title:
            print("  Cloudflare challenge on decision page!")
            print("  Waiting for auto-solve (nodriver should pass)...")
            await asyncio.sleep(10)
            title = await page2.evaluate("document.title")
            content = await page2.get_content()
            print(f"  After wait - Title: {title}")

        # Check for decision content
        has_putusan = "PUTUSAN" in content or "Putusan" in content
        has_mengadili = "MENGADILI" in content or "M E N G A D I L I" in content or "mengadili" in content.lower()
        print(f"  Has PUTUSAN: {has_putusan}")
        print(f"  Has MENGADILI: {has_mengadili}")
        print(f"  Content length: {len(content)}")

        if has_mengadili or (has_putusan and len(content) > 10000):
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            fname = target["href"].split("/")[-1]
            if not fname.endswith(".html"):
                fname += ".html"
            path = RAW_DIR / fname
            path.write_text(content, encoding="utf-8")
            print(f"  SAVED: {path}")
            print("\n  >>> ACCESS CONFIRMED - nodriver works! <<<")
        else:
            # Show what we got
            text = await page2.evaluate("document.body.innerText")
            lines = [l.strip() for l in text.split("\n") if l.strip()][:10]
            print("  Page content:")
            for l in lines:
                print(f"    | {l[:80]}")
    else:
        # Try direct URL to the PHI case we found earlier
        print("\n[3] Trying known PHI URL directly...")
        url = f"{BASE_URL}/direktori/putusan/11f036d84e9c69a09f34313334353130.html"
        page2 = await browser.get(url)
        await asyncio.sleep(5)

        title = await page2.evaluate("document.title")
        content = await page2.get_content()
        print(f"  Title: {title}")

        if "Just a moment" in content or "verifikasi" in content.lower() or "Tunggu" in title:
            print("  CF challenge, trying cf_verify...")
            try:
                await page2.cf_verify()
                await asyncio.sleep(8)
                content = await page2.get_content()
                title = await page2.evaluate("document.title")
                print(f"  After verify: {title}")
            except Exception as e:
                print(f"  cf_verify error: {e}")

        has_mengadili = "MENGADILI" in content or "M E N G A D I L I" in content
        print(f"  Has MENGADILI: {has_mengadili}")
        print(f"  Content length: {len(content)}")

        if has_mengadili:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            path = RAW_DIR / "11f036d84e9c69a09f34313334353130.html"
            path.write_text(content, encoding="utf-8")
            print(f"  SAVED: {path}")
            print("\n  >>> ACCESS CONFIRMED <<<")

    # Keep browser open briefly for inspection
    await asyncio.sleep(3)
    browser.stop()

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    uc.loop().run_until_complete(run())
