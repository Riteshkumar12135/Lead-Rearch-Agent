"""Stretch goal: batch-process a CSV of leads.

Input CSV needs at least one column with a company name or URL. Output is
written to a new CSV with research, score, and drafted outreach per row.

Usage:
    python batch.py leads.csv --column company --out results.csv
"""
import argparse
import csv
import sys
import time

from lead_agent.agent import process_lead
from lead_agent.config import DEFAULT_ICP, load_icp_from_yaml

OUTPUT_FIELDS = [
    "input", "company_name", "summary", "industry", "size_band", "confidence",
    "score", "tier", "matched_pain_points", "email_subject", "email_body",
    "linkedin_message", "error",
]


def run_batch(input_csv: str, column: str, output_csv: str, icp_path: str = None,
              delay_seconds: float = 1.0) -> None:
    icp = load_icp_from_yaml(icp_path) if icp_path else DEFAULT_ICP

    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if column not in reader.fieldnames:
            print(f"Column '{column}' not found. Available: {reader.fieldnames}", file=sys.stderr)
            sys.exit(1)
        rows = list(reader)

    results = []
    for i, row in enumerate(rows, start=1):
        query = row[column].strip()
        if not query:
            continue
        print(f"[{i}/{len(rows)}] Processing '{query}'...")
        result = process_lead(query, icp)

        out_row = {field: "" for field in OUTPUT_FIELDS}
        out_row["input"] = query
        if result.error:
            out_row["error"] = result.error
        else:
            p, s = result.profile, result.lead_score
            out_row.update({
                "company_name": p.company_name,
                "summary": p.one_line_summary,
                "industry": p.industry,
                "size_band": p.estimated_size_band,
                "confidence": p.confidence,
                "score": s.score,
                "tier": s.tier,
                "matched_pain_points": "; ".join(s.matched_pain_points),
            })
            if result.outreach:
                o = result.outreach
                out_row.update({
                    "email_subject": o.email_subject,
                    "email_body": o.email_body,
                    "linkedin_message": o.linkedin_message,
                })
        results.append(out_row)

        # Be polite to the target sites / APIs between requests.
        if i < len(rows):
            time.sleep(delay_seconds)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nDone. Wrote {len(results)} rows to {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process leads from a CSV.")
    parser.add_argument("input_csv", help="Path to input CSV")
    parser.add_argument("--column", default="company", help="Column with company name/URL")
    parser.add_argument("--out", default="results.csv", help="Path to write output CSV")
    parser.add_argument("--icp", default=None, help="Optional path to a YAML ICP file")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between leads")
    args = parser.parse_args()
    run_batch(args.input_csv, args.column, args.out, args.icp, args.delay)
