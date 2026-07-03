"""
Fetch PDF via CDP download interception.
Strategy: navigate to decision page (works), then trigger PDF download via CDP.
"""
import nodriver as uc
import asyncio
import base64
import json
from pathlib import Path
from datetime import datetime

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "putusan"
PDF_DIR = CORPUS_DIR / "pdf"
BASE_URL = "https://putusan3.mahkamahagung.go.id"

DECISION_URL = "https://putusan3.mahkamahagung.go.id/direktori/putusan/11f036d84e9c69a09f34313334353130.html"
PDF_URL = "https://putusan3.mahkamahagung.go.id/direktori/download_file/11f036d84e9dd786b815313334353130/pdf/11f036d84e9c69a09f34313334353130"


async def run():
    print("=" * 60)
    print("PDF FETCH v2 - CDP download from decision page")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # Set download path via browser args
    download_path = str(PDF_DIR.resolve())
    browser = await uc.start(
        headless=False,
        browser_args=[f"--download-default-directory={download_path}"]
    )

    # Step 1: Load homepage
    print("\n[1] Homepage...")
    page = await browser.get(BASE_URL)
    await asyncio.sleep(4)

    # Step 2: Navigate to decision page
    print("\n[2] Decision page...")
    page = await browser.get(DECISION_URL)
    await asyncio.sleep(8)
    title = await page.evaluate("document.title")
    print(f"  Title: {title}")

    # Step 3: Enable CDP download behavior
    print("\n[3] Setting download behavior via CDP...")
    try:
        await page.send(uc.cdp.browser.set_download_behavior(
            behavior="allow",
            download_path=download_path
        ))
        print(f"  Download path: {download_path}")
    except Exception as e:
        print(f"  CDP set_download_behavior: {e}")
        # Try alternative CDP method
        try:
            await page.send(uc.cdp.page.set_download_behavior(
                behavior="allow",
                download_path=download_path
            ))
        except Exception as e2:
            print(f"  Alt method also failed: {e2}")

    # Step 4: Find and click PDF link on the page
    print("\n[4] Finding PDF link on page...")
    pdf_link = await page.find("392_K/PDT.SUS-PHI/2025.pdf", best_match=True)
    if pdf_link:
        print(f"  Found PDF link, clicking...")
        await pdf_link.click()
        await asyncio.sleep(10)

        # Check if file appeared
        pdfs = list(PDF_DIR.glob("*.pdf"))
        print(f"  PDFs in download dir: {[p.name for p in pdfs]}")
        if pdfs:
            print(f"  SUCCESS: {pdfs[0].name} ({pdfs[0].stat().st_size} bytes)")
    else:
        print("  PDF link not found by text, trying selector...")
        # Try href selector
        pdf_link = await page.select("a[href*='download_file']")
        if pdf_link:
            print(f"  Found via selector, clicking...")
            await pdf_link.click()
            await asyncio.sleep(10)
            pdfs = list(PDF_DIR.glob("*.pdf"))
            print(f"  PDFs: {[p.name for p in pdfs]}")
        else:
            print("  No PDF link found")

            # Step 5: Try fetch from decision page context (same origin, has cookies)
            print("\n[5] Trying in-page fetch...")
            result = await page.evaluate("""
                (async () => {
                    try {
                        const resp = await fetch('%s', {credentials: 'include'});
                        return {status: resp.status, type: resp.headers.get('content-type'), size: parseInt(resp.headers.get('content-length') || '0')};
                    } catch(e) {
                        return {error: e.message};
                    }
                })()
            """ % PDF_URL)
            print(f"  Fetch result: {result}")

            if isinstance(result, dict) and result.get("status") == 200:
                # Download as base64
                b64 = await page.evaluate("""
                    (async () => {
                        const resp = await fetch('%s', {credentials: 'include'});
                        const blob = await resp.blob();
                        return new Promise(resolve => {
                            const reader = new FileReader();
                            reader.onload = () => resolve(reader.result.split(',')[1]);
                            reader.readAsDataURL(blob);
                        });
                    })()
                """ % PDF_URL)
                if b64 and len(str(b64)) > 100:
                    pdf_bytes = base64.b64decode(b64)
                    save_path = PDF_DIR / "392_K_PDT.SUS-PHI_2025.pdf"
                    save_path.write_bytes(pdf_bytes)
                    print(f"  SAVED: {save_path} ({len(pdf_bytes)} bytes)")

    await asyncio.sleep(3)
    browser.stop()
    print("\nDone.")


if __name__ == "__main__":
    uc.loop().run_until_complete(run())
