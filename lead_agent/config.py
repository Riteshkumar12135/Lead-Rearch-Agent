"""Configuration: API keys, model settings, and the Ideal Customer Profile (ICP).

Edit ICP below (or load one from a YAML file with `load_icp_from_yaml`)
to match who you actually sell to. Everything downstream — scoring,
pain-point framing, email tone — is driven by this definition.
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

# --- API keys -----------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")  # optional, for web search signals

# --- Model settings -------------------------------------------------------
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 2000

# --- Sender identity (used in the drafted messages) ------------------------
SENDER_NAME = os.getenv("SENDER_NAME", "Your Name")
SENDER_COMPANY = os.getenv("SENDER_COMPANY", "Your Company")
SENDER_PRODUCT_PITCH = os.getenv(
    "SENDER_PRODUCT_PITCH",
    "a tool that helps teams do X faster / cheaper / with less manual work",
)


@dataclass
class ICP:
    """Ideal Customer Profile — the rubric leads are scored against."""

    name: str = "Default ICP"
    target_industries: List[str] = field(default_factory=lambda: [
        "SaaS", "e-commerce", "fintech"
    ])
    company_size_min: int = 10
    company_size_max: int = 500
    target_titles: List[str] = field(default_factory=lambda: [
        "VP Sales", "Head of Growth", "Founder", "CEO", "COO"
    ])
    pain_points_we_solve: List[str] = field(default_factory=lambda: [
        "manual, repetitive sales prospecting",
        "low reply rates on generic outreach",
        "sales reps spending too much time researching leads instead of selling",
    ])
    disqualifiers: List[str] = field(default_factory=lambda: [
        "company is a direct competitor",
        "company has fewer than 5 employees",
        "company is a non-profit with no sales team",
    ])
    notes: Optional[str] = None

    def as_prompt_block(self) -> str:
        """Render the ICP as text to inject into an LLM prompt."""
        lines = [
            f"ICP name: {self.name}",
            f"Target industries: {', '.join(self.target_industries)}",
            f"Target company size: {self.company_size_min}-{self.company_size_max} employees",
            f"Target buyer titles: {', '.join(self.target_titles)}",
            "Pain points we solve:",
            *[f"  - {p}" for p in self.pain_points_we_solve],
            "Disqualifiers (score very low if any apply):",
            *[f"  - {d}" for d in self.disqualifiers],
        ]
        if self.notes:
            lines.append(f"Notes: {self.notes}")
        return "\n".join(lines)


def load_icp_from_yaml(path: str) -> ICP:
    """Load an ICP definition from a YAML file (see icp_example.yaml)."""
    import yaml

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    return ICP(**data)


DEFAULT_ICP = ICP()
