"""Turns raw scraped/searched signal into a structured company profile."""
from dataclasses import dataclass, field
from typing import List

from . import llm, search
from .scraper import ScrapedSite, normalise_url, scrape_company_site

PROFILE_SYSTEM_PROMPT = """You are a B2B research analyst. You are given raw \
text scraped from a company's website (and sometimes recent news snippets). \
Infer a factual, conservative company profile from it. Do not invent \
specifics you cannot support from the text — if something is unclear, say \
so explicitly rather than guessing confidently.

Respond with ONLY a JSON object, no markdown fences, no commentary, in \
exactly this shape:
{
  "company_name": string,
  "one_line_summary": string,
  "industry": string,
  "estimated_size_band": one of ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+", "unknown"],
  "likely_products_or_services": [string, ...],
  "likely_pain_points": [string, ...],
  "notable_signals": [string, ...],   // funding, hiring, recent launches, etc.
  "confidence": one of ["low", "medium", "high"],
  "confidence_reason": string
}"""


@dataclass
class CompanyProfile:
    company_name: str
    one_line_summary: str
    industry: str
    estimated_size_band: str
    likely_products_or_services: List[str]
    likely_pain_points: List[str]
    notable_signals: List[str]
    confidence: str
    confidence_reason: str
    source_url: str
    reasoning_trace: List[str] = field(default_factory=list)


def research_company(name_or_url: str) -> CompanyProfile:
    """Full pipeline: resolve -> scrape -> (optional) search -> profile via LLM."""
    trace: List[str] = []

    # Step 1: resolve to a URL
    try:
        url = normalise_url(name_or_url)
        trace.append(f"Interpreted '{name_or_url}' directly as URL: {url}")
    except ValueError:
        trace.append(f"'{name_or_url}' is a bare name — searching for its domain...")
        resolved = search.find_company_domain(name_or_url)
        if not resolved:
            raise RuntimeError(
                f"Could not resolve a domain for '{name_or_url}'. "
                "Try passing the company's URL directly, or set TAVILY_API_KEY "
                "to enable name resolution."
            )
        url = resolved
        trace.append(f"Resolved to: {url}")

    # Step 2: scrape the site
    site: ScrapedSite = scrape_company_site(url)
    if site.fetch_error:
        trace.append(f"Scrape failed: {site.fetch_error}")
    else:
        trace.append(
            f"Scraped homepage (title: '{site.title}') plus up to 2 internal pages."
        )

    # Step 3: optional news/funding search for extra signal
    news = search.find_recent_news(name_or_url)
    if news:
        trace.append(f"Found {len(news)} recent news/search signals.")
    else:
        trace.append("No supplementary web search results (skipped or no API key).")

    # Step 4: build the prompt for the LLM
    news_block = "\n".join(f"- {n['title']}: {n['content'][:300]}" for n in news) or "None found."
    user_prompt = f"""Company (as given by the user): {name_or_url}
Homepage URL: {site.url}
Page title: {site.title}
Meta description: {site.meta_description}
Headings: {', '.join(site.headings) or 'None found'}

Homepage body text (truncated):
{site.body_text or '(none — homepage could not be fetched)'}

Additional internal page text (truncated):
{site.extra_pages_text or '(none)'}

Recent news/search signals:
{news_block}"""

    trace.append("Sending gathered signal to the model to build a structured profile...")
    data = llm.ask_json(PROFILE_SYSTEM_PROMPT, user_prompt)
    trace.append(
        f"Model returned profile with confidence: {data.get('confidence', 'unknown')}"
    )

    return CompanyProfile(
        company_name=data.get("company_name", name_or_url),
        one_line_summary=data.get("one_line_summary", ""),
        industry=data.get("industry", "unknown"),
        estimated_size_band=data.get("estimated_size_band", "unknown"),
        likely_products_or_services=data.get("likely_products_or_services", []),
        likely_pain_points=data.get("likely_pain_points", []),
        notable_signals=data.get("notable_signals", []),
        confidence=data.get("confidence", "low"),
        confidence_reason=data.get("confidence_reason", ""),
        source_url=site.url,
        reasoning_trace=trace,
    )
