"""Generates a personalised cold email and LinkedIn message for a lead."""
from dataclasses import dataclass, field
from typing import List

from . import config, llm
from .research import CompanyProfile
from .scoring import LeadScore

OUTREACH_SYSTEM_PROMPT = """You are an experienced SDR (sales development \
rep) writing outreach on behalf of a sender. Write in a natural, specific, \
non-salesy tone: reference something real and specific about the company, \
tie it to one concrete pain point, and make a low-friction ask (a short call, \
not "let's sign a contract"). Avoid generic filler like "I hope this email \
finds you well," superlatives, and exclamation points. Keep the email under \
150 words and the LinkedIn message under 80 words.

Respond with ONLY a JSON object, no markdown fences, no commentary, in \
exactly this shape:
{
  "email_subject": string,
  "email_body": string,
  "linkedin_message": string,
  "personalisation_used": [string, ...],  // specific facts about the company that were used
  "reasoning": [string, ...]              // why this angle/pain point was chosen
}"""


@dataclass
class OutreachDraft:
    email_subject: str
    email_body: str
    linkedin_message: str
    personalisation_used: List[str]
    reasoning: List[str]
    reasoning_trace: List[str] = field(default_factory=list)


def draft_outreach(profile: CompanyProfile, lead_score: LeadScore) -> OutreachDraft:
    trace = [
        f"Drafting outreach for '{profile.company_name}' "
        f"(tier: {lead_score.tier}, matched pain points: {', '.join(lead_score.matched_pain_points) or 'none'})."
    ]

    if lead_score.disqualifier_hit:
        trace.append(
            f"Note: disqualifier '{lead_score.disqualifier_hit}' was flagged — "
            "drafting anyway, but recommend a human double-check before sending."
        )

    user_prompt = f"""Sender:
- Name: {config.SENDER_NAME}
- Company: {config.SENDER_COMPANY}
- What we offer: {config.SENDER_PRODUCT_PITCH}

Target company:
- Name: {profile.company_name}
- Summary: {profile.one_line_summary}
- Industry: {profile.industry}
- Likely pain points: {', '.join(profile.likely_pain_points) or 'unknown'}
- Notable signals: {', '.join(profile.notable_signals) or 'none'}

Lead scoring context:
- Tier: {lead_score.tier} (score: {lead_score.score}/100)
- Matched pain points we should lead with: {', '.join(lead_score.matched_pain_points) or 'none identified'}

Write the outreach now."""

    data = llm.ask_json(OUTREACH_SYSTEM_PROMPT, user_prompt)
    trace.append("Model drafted email + LinkedIn message.")

    return OutreachDraft(
        email_subject=data.get("email_subject", ""),
        email_body=data.get("email_body", ""),
        linkedin_message=data.get("linkedin_message", ""),
        personalisation_used=data.get("personalisation_used", []),
        reasoning=data.get("reasoning", []),
        reasoning_trace=trace,
    )
