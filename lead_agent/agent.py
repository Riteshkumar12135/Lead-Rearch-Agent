"""Orchestrates the full pipeline: research -> score -> draft outreach.

This is the single entry point both the CLI and the Streamlit app call.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from .config import DEFAULT_ICP, ICP
from .outreach import OutreachDraft, draft_outreach
from .research import CompanyProfile, research_company
from .scoring import LeadScore, score_lead


@dataclass
class LeadResult:
    input_query: str
    profile: Optional[CompanyProfile] = None
    lead_score: Optional[LeadScore] = None
    outreach: Optional[OutreachDraft] = None
    error: Optional[str] = None

    @property
    def full_reasoning_trace(self) -> List[str]:
        trace: List[str] = []
        if self.profile:
            trace += ["## Research", *self.profile.reasoning_trace]
        if self.lead_score:
            trace += ["## Scoring", *self.lead_score.reasoning_trace]
        if self.outreach:
            trace += ["## Outreach drafting", *self.outreach.reasoning_trace]
        return trace


def process_lead(name_or_url: str, icp: ICP = DEFAULT_ICP) -> LeadResult:
    """Run the full pipeline for a single lead. Never raises — errors are
    captured on the result so batch runs don't die on one bad company."""
    result = LeadResult(input_query=name_or_url)
    try:
        result.profile = research_company(name_or_url)
    except Exception as exc:
        result.error = f"Research failed: {exc}"
        return result

    try:
        result.lead_score = score_lead(result.profile, icp)
    except Exception as exc:
        result.error = f"Scoring failed: {exc}"
        return result

    # Skip drafting outreach for hard disqualifications to save API cost —
    # a human can still override via the UI if they disagree with the tier.
    if result.lead_score.tier == "D - disqualify":
        return result

    try:
        result.outreach = draft_outreach(result.profile, result.lead_score)
    except Exception as exc:
        result.error = f"Outreach drafting failed: {exc}"

    return result
