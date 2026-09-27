"""Fetches and extracts readable text/signals from a company's website."""
import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (compatible; LeadResearchAgent/0.1; "
    "+https://example.com/bot-info)"
)
TIMEOUT = 10
# Common internal pages worth checking for extra context, tried best-effort.
CANDIDATE_PATHS = ["/about", "/about-us", "/company", "/careers", "/pricing"]


@dataclass
class ScrapedSite:
    url: str
    title: str
    meta_description: str
    headings: List[str]
    body_text: str
    extra_pages_text: str
    fetch_error: Optional[str] = None


def normalise_url(name_or_url: str) -> str:
    """Turn 'Acme Inc' or 'acme.com' or 'https://acme.com' into a fetchable URL."""
    candidate = name_or_url.strip()
    if candidate.startswith("http://") or candidate.startswith("https://"):
        return candidate
    if "." in candidate and " " not in candidate:
        # looks like a bare domain, e.g. "acme.com"
        return f"https://{candidate}"
    # It's a plain company name with no domain — caller should resolve this
    # via search.py before falling back to scraping.
    raise ValueError(
        f"'{name_or_url}' doesn't look like a URL or domain. "
        "Resolve it to a domain first (see search.py: find_company_domain)."
    )


def _clean_text(soup: BeautifulSoup, limit: int = 4000) -> str:
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def _fetch(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException:
        return None


def scrape_company_site(url: str) -> ScrapedSite:
    """Fetch the homepage plus a few likely internal pages for extra signal."""
    soup = _fetch(url)
    if soup is None:
        return ScrapedSite(
            url=url,
            title="",
            meta_description="",
            headings=[],
            body_text="",
            extra_pages_text="",
            fetch_error=f"Could not fetch {url} (network error, blocked, or invalid URL).",
        )

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_tag["content"].strip() if meta_tag and meta_tag.get("content") else ""
    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2"]) if h.get_text(strip=True)][:15]
    body_text = _clean_text(soup)

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    extra_texts = []
    for path in CANDIDATE_PATHS:
        page_soup = _fetch(urljoin(base, path))
        if page_soup is not None:
            extra_texts.append(f"[{path}] {_clean_text(page_soup, limit=1500)}")
        if len(extra_texts) >= 2:
            break  # keep it fast — two extra pages is plenty of signal

    return ScrapedSite(
        url=url,
        title=title,
        meta_description=meta_description,
        headings=headings,
        body_text=body_text,
        extra_pages_text="\n\n".join(extra_texts),
    )
