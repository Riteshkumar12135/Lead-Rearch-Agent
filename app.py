"""Streamlit UI for the AI Lead Research and Outreach Agent.

Run with: streamlit run app.py
"""
import streamlit as st

from lead_agent.agent import process_lead
from lead_agent.config import DEFAULT_ICP, ICP

st.set_page_config(page_title="Lead Research & Outreach Agent", page_icon="🎯", layout="wide")

# --- Sidebar: ICP editor -----------------------------------------------
st.sidebar.header("Ideal Customer Profile")
with st.sidebar.form("icp_form"):
    industries = st.text_input(
        "Target industries (comma-separated)",
        value=", ".join(DEFAULT_ICP.target_industries),
    )
    size_min = st.number_input("Min company size", value=DEFAULT_ICP.company_size_min, min_value=1)
    size_max = st.number_input("Max company size", value=DEFAULT_ICP.company_size_max, min_value=1)
    titles = st.text_input(
        "Target buyer titles (comma-separated)", value=", ".join(DEFAULT_ICP.target_titles)
    )
    pains = st.text_area(
        "Pain points you solve (one per line)",
        value="\n".join(DEFAULT_ICP.pain_points_we_solve),
        height=100,
    )
    disqualifiers = st.text_area(
        "Disqualifiers (one per line)",
        value="\n".join(DEFAULT_ICP.disqualifiers),
        height=80,
    )
    submitted = st.form_submit_button("Update ICP")

icp = ICP(
    name="Session ICP",
    target_industries=[s.strip() for s in industries.split(",") if s.strip()],
    company_size_min=int(size_min),
    company_size_max=int(size_max),
    target_titles=[s.strip() for s in titles.split(",") if s.strip()],
    pain_points_we_solve=[s.strip() for s in pains.splitlines() if s.strip()],
    disqualifiers=[s.strip() for s in disqualifiers.splitlines() if s.strip()],
)

# --- Main panel ----------------------------------------------------------
st.title("🎯 Lead Research & Outreach Agent")
st.caption("Enter a company name or website. The agent researches it, scores it against your ICP, and drafts outreach for your review.")

query = st.text_input("Company name or URL", placeholder="e.g. acme.com or 'Acme Inc'")
run_button = st.button("Research lead", type="primary", disabled=not query)

if run_button and query:
    with st.spinner(f"Researching {query}..."):
        result = process_lead(query, icp)

    if result.error:
        st.error(result.error)
    else:
        p, s = result.profile, result.lead_score

        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(p.company_name)
            st.write(p.one_line_summary)
            st.write(
                f"**Industry:** {p.industry}  |  **Size:** {p.estimated_size_band}  |  "
                f"**Profile confidence:** {p.confidence}"
            )
            if p.likely_products_or_services:
                st.write("**Likely products/services:** " + ", ".join(p.likely_products_or_services))
            if p.notable_signals:
                st.write("**Notable signals:** " + ", ".join(p.notable_signals))

        with col2:
            tier_colors = {
                "A - strong fit": "🟢", "B - possible fit": "🟡",
                "C - weak fit": "🟠", "D - disqualify": "🔴",
            }
            st.metric("ICP Score", f"{s.score}/100")
            st.write(f"{tier_colors.get(s.tier, '')} **{s.tier}**")
            if s.disqualifier_hit:
                st.warning(f"Disqualifier flagged: {s.disqualifier_hit}")

        st.markdown("**Scoring reasoning:**")
        for r in s.reasoning:
            st.write(f"- {r}")

        st.divider()

        if result.outreach:
            o = result.outreach
            tab1, tab2, tab3 = st.tabs(["📧 Email", "💼 LinkedIn message", "🧠 Full reasoning trace"])
            with tab1:
                st.text_input("Subject", value=o.email_subject, key="subj")
                st.text_area("Body", value=o.email_body, height=220, key="body")
                st.caption("Personalisation used: " + ", ".join(o.personalisation_used))
            with tab2:
                st.text_area("Message", value=o.linkedin_message, height=150, key="li")
            with tab3:
                st.code("\n".join(result.full_reasoning_trace), language=None)

            st.info("Review both drafts above before sending — nothing here is sent automatically.")
        else:
            st.warning("No outreach drafted (lead was disqualified, or drafting failed).")
            with st.expander("Full reasoning trace"):
                st.code("\n".join(result.full_reasoning_trace), language=None)

st.divider()
st.caption(
    "Batch processing: run `python batch.py leads.csv --column company --out results.csv` "
    "from the command line to process a whole list at once."
)
