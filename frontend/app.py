"""CutScope dashboard backed by the real analytics product API."""

import pandas as pd
import plotly.express as px
import streamlit as st

from components.copilot import render_copilot
from services.api_client import (
    APIError,
    get_job,
    get_opportunities,
    get_opportunity,
    get_summary,
)


st.set_page_config(page_title="MantisGrid GPU Usage Analytics", page_icon="◈", layout="wide")


def money(value):
    return "Unavailable" if value is None else rf"\${value:,.0f}"


def money_plain(value):
    return "Unavailable" if value is None else f"${value:,.0f}"


def hours(value):
    return "Unavailable" if value is None else f"{value:,.0f} GPU-hours"


def percent(value):
    return "Unavailable" if value is None else f"{value:.1f}%"


def value_range(low, high, formatter):
    if low is None or high is None:
        return "Not quantified"
    return f"{formatter(low)} – {formatter(high)}"


@st.cache_data(ttl=30)
def load_dashboard_data():
    return get_summary(), get_opportunities()


@st.cache_data(ttl=30)
def load_opportunity(opportunity_id):
    return get_opportunity(opportunity_id, limit=10)


@st.cache_data(ttl=30)
def load_job(job_id):
    return get_job(job_id)


st.title("MantisGrid GPU Usage Analytics")
st.caption("GPU cost decisions · Four-month workload sample")

try:
    summary, opportunities = load_dashboard_data()
except APIError as exc:
    st.error(f"The analytics backend is unavailable: {exc}")
    render_copilot()
    st.stop()

if not opportunities:
    st.warning("The analytics snapshot contains no opportunities.")
    render_copilot()
    st.stop()

opportunity_by_id = {item["id"]: item for item in opportunities}
default_id = next(iter(opportunity_by_id))
if st.session_state.get("selected_opportunity") not in opportunity_by_id:
    st.session_state.selected_opportunity = default_id

with st.sidebar:
    st.header("Investigation")
    selected_id = st.selectbox(
        "Opportunity",
        options=list(opportunity_by_id),
        format_func=lambda item_id: opportunity_by_id[item_id]["title"],
        key="selected_opportunity",
    )
    st.caption("Select a ranked opportunity to inspect its method, risk and evidence.")

try:
    selected = load_opportunity(selected_id)
except APIError as exc:
    st.error(f"Could not load the selected opportunity: {exc}")
    render_copilot()
    st.stop()

st.success(
    f"Real analytics loaded · {len(opportunities)} opportunities · "
    f"{summary['scope_caveat']}"
)

money_column, cut_column, risk_column = st.columns(3)
with money_column:
    with st.container(border=True):
        st.subheader("01 · Where money goes")
        st.metric("Allocated GPU-hours", hours(summary.get("total_gpu_hours")))
        st.metric("Estimated allocation cost", money(summary.get("total_cost_usd")))
        st.caption(
            f"Completed work: {percent(summary.get('completed_percent'))} of capacity · "
            rf"\${summary.get('price_per_gpu_hour', 0):,.2f}/GPU-hour"
        )
with cut_column:
    with st.container(border=True):
        st.subheader("02 · Where to cut")
        st.write(f"**{selected['title']}**")
        st.metric(
            "Potential savings range",
            value_range(selected.get("savings_usd_low"), selected.get("savings_usd_high"), money),
        )
        st.caption(
            f"Owner: {selected.get('owner') or 'Unassigned'} · "
            f"Confidence: {percent((selected.get('confidence') or 0) * 100)}"
        )
with risk_column:
    with st.container(border=True):
        st.subheader("03 · Cost if wrong")
        downside = selected.get("cost_if_wrong", {})
        st.metric(
            "Estimated downside range",
            value_range(downside.get("usd_low"), downside.get("usd_high"), money),
        )
        st.write(downside.get("description") or "Counterfactual cost is not measured.")
        st.caption(f"Risk: {selected.get('risk_level', 'unknown').title()} · Reversible: {'Yes' if downside.get('reversible') else 'Unknown'}")

st.subheader("Capacity allocation by outcome")
outcomes = pd.DataFrame(summary.get("outcomes", []))
if not outcomes.empty:
    chart = px.bar(
        outcomes,
        x="name",
        y="gpu_hours",
        color="name",
        hover_data=["jobs", "cost_usd", "capacity_percent"],
        labels={"name": "Outcome", "gpu_hours": "GPU-hours"},
    )
    chart.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(chart, width="stretch")

st.subheader("Ranked opportunities")
ranked = pd.DataFrame(
    [
        {
            "Opportunity": item["title"],
            "Owner": item.get("owner"),
            "Savings low": money_plain(item.get("savings_usd_low")),
            "Savings high": money_plain(item.get("savings_usd_high")),
            "GPU-hours high": round(item.get("gpu_hours_high") or 0),
            "Capacity high": percent(item.get("capacity_percent_high")),
            "Confidence": percent((item.get("confidence") or 0) * 100),
            "Jobs": item.get("job_count"),
        }
        for item in sorted(
            opportunities,
            key=lambda item: item.get("savings_usd_high") or 0,
            reverse=True,
        )
    ]
)
st.dataframe(ranked, width="stretch", hide_index=True)

st.divider()
st.subheader("Opportunity & evidence")
detail_tab, jobs_tab, findings_tab = st.tabs(
    ["Method & assumptions", "Job evidence", "MantisGrid findings"]
)
with detail_tab:
    st.write(f"**Action:** {selected.get('action') or 'Unavailable'}")
    st.write(f"**Basis:** {selected.get('basis') or 'Unavailable'}")
    st.write(f"**Method:** {selected.get('method') or 'Unavailable'}")
    st.write(f"**Mitigation:** {downside.get('mitigation') or 'Unavailable'}")
    st.markdown("**Caveats**")
    for caveat in selected.get("caveats", []):
        st.markdown(f"- {caveat}")

job_ids = selected.get("jobs", [])
jobs_data = []
for job_id in job_ids:
    try:
        jobs_data.append(load_job(job_id))
    except APIError:
        continue

with jobs_tab:
    if jobs_data:
        st.caption(
            f"Showing {len(jobs_data)} of {selected.get('job_count', len(jobs_data)):,} affected jobs."
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Job ID": job["job_id"],
                        "State": job.get("state"),
                        "GPUs": job.get("gpu_count"),
                        "GPU-hours": job.get("gpu_hours"),
                        "Cost": money_plain(job.get("cost_usd")),
                        "Avg util %": job.get("sm_util_avg"),
                        "Max util %": job.get("sm_util_max"),
                        "Walltime h": job.get("walltime_hours"),
                        "Node": job.get("primary_node"),
                    }
                    for job in jobs_data
                ]
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No job evidence is available for this opportunity.")

with findings_tab:
    findings = [
        (job["job_id"], finding)
        for job in jobs_data
        for finding in job.get("findings", [])
    ]
    if findings:
        for job_id, finding in findings[:20]:
            with st.expander(
                f"Job {job_id} · {finding.get('shortDescription') or finding.get('id')}"
            ):
                st.write(finding.get("longDescription") or finding.get("shortDescription"))
                st.write(f"**Impact:** {finding.get('impactDescription') or 'Unavailable'}")
                st.caption(
                    f"Detector: {finding.get('detectorId', 'unknown')} · "
                    f"Severity: {finding.get('severity', 'unknown')} · "
                    f"Confidence: {finding.get('confidence', 'unknown')}"
                )
    else:
        st.info("No MantisGrid findings are available for the displayed jobs.")

st.caption("Unavailable means the analysis did not estimate that value; it never means zero.")
render_copilot()
