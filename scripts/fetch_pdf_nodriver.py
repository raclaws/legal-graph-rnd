"""
Fetch decision PDFs using nodriver.
The decision text lives in PDFs, not the HTML pages.
"""
import nodriver as uc
import asyncio
import json
from pathlib import Path
from datetime import datetime

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
RAW_DIR = CORPUS_DIR / "raw"
PDF_DIR = CORPUS_DIR / "pdf"
BASE_URL = "https://putusan3.mahkamahagung.go.id"

# Known PDF URLs from our test
TARGETS = [
    {
        "case": "392 K/PDT.SUS-PHI/2025",
        "pdf_url": "https://putusan3.mahkamahagung.go.id/direktori/download_file/11f036d84e9dd786b815313334353130/pdf/11f036d84e9c69a09f34313334353130",
    },
]


async def run():
    print("=" * 60)
    print("PDF FETCH TEST - nodriver")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    browser = await uc.start(headless=False)

    # Load homepage first to establish session
    print("\n[1] Establishing session...")
    page = await browser.get(BASE_URL)
    await asyncio.sleep(5)
    title = await page.evaluate("document.title")
    print(f"  Homepage: {title}")

    # Search and click into a decision page to build cookie state
    print("\n[2] Building session (search + click)...")
    search_input = await page.find("input[name='q']", best_match=True)
    if search_input:
        await search_input.send_keys("K/PDT.SUS-PHI 2024")
        await asyncio.sleep(1)
        await search_input.send_keys("\n")
        await asyncio.sleep(5)

    # Now try to download the PDF
    print("\n[3] Fetching PDF...")
    target = TARGETS[0]
    print(f"  Case: {target['case']}")
    print(f"  URL: {target['pdf_url']}")

    # Method: navigate to PDF URL - browser might render or download it
    page2 = await browser.get(target["pdf_url"])
    await asyncio.sleep(10)

    # Check what happened
    current_url = await page2.evaluate("window.location.href")
    print(f"  Current URL: {current_url}")

    # Try to get content (might be a PDF viewer or download)
    content_type = await page2.evaluate("""
        (async () => {
            try {
                const resp = await fetch(window.location.href);
                return resp.headers.get('content-type');
            } catch(e) {
                return 'error: ' + e.message;
            }
        })()
    """)
    print(f"  Content-Type: {content_type}")

    # Alternative: use CDP to intercept download
    # For now, let's try using page.evaluate with fetch to save as blob
    print("\n[4] Trying fetch API to get PDF bytes...")
    pdf_result = await page2.evaluate("""
        (async () => {
            try {
                const resp = await fetch('%s');
                if (!resp.ok) return {error: resp.status + ' ' + resp.statusText};
                const blob = await resp.blob();
                return {size: blob.size, type: blob.type};
            } catch(e) {
                return {error: e.message};
            }
        })()
    """ % target["pdf_url"])
    print(f"  Result: {pdf_result}")

    # If we can get it, save via download
    if isinstance(pdf_result, dict) and pdf_result.get("size", 0) > 1000:
        print(f"  PDF accessible! Size: {pdf_result['size']} bytes")
        # Download via CDP
        save_path = PDF_DIR / f"{target['case'].replace('/', '_').replace(' ', '_')}.pdf"

        # Use a download approach
        dl_script = """
            (async () => {
                const resp = await fetch('%s');
                const blob = await resp.blob();
                const reader = new FileReader();
                return new Promise((resolve) => {
                    reader.onload = () => resolve(reader.result.split(',')[1]);
                    reader.readAsDataURL(blob);
                });
            })()
        """ % target["pdf_url"]

        b64_data = await page2.evaluate(dl_script)
        if b64_data and len(b64_data) > 100:
            import base64
            pdf_bytes = base64.b64decode(b64_data)
            save_path.write_bytes(pdf_bytes)
            print(f"  SAVED: {save_path} ({len(pdf_bytes)} bytes)")
        else:
            print(f"  Failed to get base64 data")
    else:
        print("  PDF not directly fetchable from this context")
        print("  May need to handle download dialog or use CDP download")

    await asyncio.sleep(3)
    browser.stop()
    print("\nDone.")


if __name__ == "__main__":
    uc.loop().run_until_complete(run())
