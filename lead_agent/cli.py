"""CLI entry point.

Usage:
    python -m lead_agent.cli "acme.com"
    python -m lead_agent.cli "Acme Inc"
"""
import argparse
import sys

from .agent import process_lead
from .config import DEFAULT_ICP


def main() -> None:
    parser = argparse.ArgumentParser(description="Research a lead and draft outreach.")
    parser.add_argument("company", help="Company name or URL")
    parser.add_argument(
        "--icp", help="Path to a YAML ICP file (defaults to the built-in ICP)", default=None
    )
    parser.add_argument(
        "--show-trace", action="store_true", help="Print the full reasoning trace"
    )
    args = parser.parse_args()

    icp = DEFAULT_ICP
    if args.icp:
        from .config import load_icp_from_yaml
        icp = load_icp_from_yaml(args.icp)

    result = process_lead(args.company, icp)

    if result.error:
        print(f"ERROR: {result.error}", file=sys.stderr)
        sys.exit(1)

    p, s = result.profile, result.lead_score
    print(f"\n=== {p.company_name} ===")
    print(f"Summary: {p.one_line_summary}")
    print(f"Industry: {p.industry} | Size: {p.estimated_size_band} | Confidence: {p.confidence}")
    print(f"\nScore: {s.score}/100 — {s.tier}")
    for r in s.reasoning:
        print(f"  - {r}")

    if result.outreach:
        o = result.outreach
        print(f"\n--- Email ---\nSubject: {o.email_subject}\n\n{o.email_body}")
        print(f"\n--- LinkedIn message ---\n{o.linkedin_message}")
    else:
        print("\n(No outreach drafted — lead was disqualified or drafting failed.)")

    if args.show_trace:
        print("\n--- Reasoning trace ---")
        for line in result.full_reasoning_trace:
            print(line)


if __name__ == "__main__":
    main()
