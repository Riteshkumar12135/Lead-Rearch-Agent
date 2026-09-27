"""Scores a researched company against the configured ICP."""
from dataclasses import dataclass, field
from typing import List

from . import llm
from .config import ICP
from .research import CompanyProfile

SCORING_SYSTEM_PROMPT = """You are a sales development analyst scoring a lead \
against an Ideal Customer Profile (ICP). Be honest and conservative — a busy \
sales rep is trusting this score to decide where to spend their time. If the \
company profile is low-confidence or thin, reflect that in a lower score and \
say so in the reasoning.

Respond with ONLY a JSON object, no markdown fences, no commentary, in \
exactly this shape:
{
  "score": integer from 0 to 100,
  "tier": one of ["A - strong fit", "B - possible fit", "C - weak fit", "D - disqualify"],
  "reasoning": [string, ...],          // 2-5 short bullet points explaining the score
  "matched_pain_points": [string, ...], // which of our pain points this company likely has
  "disqualifier_hit": string or null    // which disqualifier applies, if any
}"""


@dataclass
class LeadScore:
    score: int
    tier: str
    reasoning: List[str]
    matched_pain_points: List[str]
    disqualifier_hit: str = None
    reasoning_trace: List[str] = field(default_factory=list)


def score_lead(profile: CompanyProfile, icp: ICP) -> LeadScore:
    trace = [
        f"Scoring '{profile.company_name}' (industry: {profile.industry}, "
        f"size: {profile.estimated_size_band}, confidence: {profile.confidence}) against ICP '{icp.name}'."
    ]

    user_prompt = f"""ICP:
{icp.as_prompt_block()}

Company profile to score:
- Name: {profile.company_name}
- Summary: {profile.one_line_summary}
- Industry: {profile.industry}
- Estimated size: {profile.estimated_size_band}
- Likely products/services: {', '.join(profile.likely_products_or_services) or 'unknown'}
- Likely pain points: {', '.join(profile.likely_pain_points) or 'unknown'}
- Notable signals: {', '.join(profile.notable_signals) or 'none'}
- Profile confidence: {profile.confidence} ({profile.confidence_reason})"""

    data = llm.ask_json(SCORING_SYSTEM_PROMPT, user_prompt)
    trace.append(f"Model scored this lead {data.get('score')}/100, tier: {data.get('tier')}")
    if data.get("disqualifier_hit"):
        trace.append(f"Disqualifier flagged: {data['disqualifier_hit']}")

    return LeadScore(
        score=int(data.get("score", 0)),
        tier=data.get("tier", "C - weak fit"),
        reasoning=data.get("reasoning", []),
        matched_pain_points=data.get("matched_pain_points", []),
        disqualifier_hit=data.get("disqualifier_hit"),
        reasoning_trace=trace,
    )
