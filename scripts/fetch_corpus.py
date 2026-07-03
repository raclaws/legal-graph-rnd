"""HTML fetcher for peraturan.go.id corpus."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from bs4 import BeautifulSoup


CORPUS_DIR = Path(__file__).parent.parent.parent / "corpus" / "raw"


async def fetch_regulation_html(url: str, filename: str) -> Path:
    """Fetch a regulation page and save the HTML."""
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = CORPUS_DIR / filename

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    output_path.write_text(response.text, encoding="utf-8")
    return output_path


def extract_body_text(html_path: Path) -> str:
    """Extract the main regulation text from saved HTML."""
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    # peraturan.go.id typically wraps content in specific divs
    # This will need adjustment based on actual page structure
    content = soup.find("div", class_="content") or soup.find("article") or soup.body
    if content is None:
        return ""

    return content.get_text(separator="\n", strip=True)


# Example URLs for first session corpus
SAMPLE_CORPUS = [
    {
        "url": "https://peraturan.go.id/peraturan/view?id=UU-Nomor-6-Tahun-2023",
        "filename": "uu_6_2023.html",
        "description": "UU 6/2023 (Cipta Kerja ratification)",
    },
    {
        "url": "https://peraturan.go.id/peraturan/view?id=PP-Nomor-21-Tahun-2024",
        "filename": "pp_21_2024.html",
        "description": "PP 21/2024 (sample implementing PP)",
    },
]


async def fetch_sample_corpus():
    """Fetch the initial sample regulations."""
    tasks = [fetch_regulation_html(s["url"], s["filename"]) for s in SAMPLE_CORPUS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for item, result in zip(SAMPLE_CORPUS, results):
        if isinstance(result, Exception):
            print(f"FAILED: {item['description']} — {result}")
        else:
            print(f"OK: {item['description']} → {result}")


if __name__ == "__main__":
    asyncio.run(fetch_sample_corpus())
