"""Backend-driven CutScope dashboard. All analytical values come from the API."""
import streamlit as st
import requests

from components.copilot import render_copilot
from services import api_client as api

st.set_page_config(page_title="CutScope", page_icon="◈", layout="wide")


def number(value, unit=""):
    if value is None:
        return "—"
    return f"${value:,.2f}" if unit == "$" else f"{value:,.2f}{unit}"


def interval(data, low, high, unit=""):
    return f"{number(data.get(low), unit)} – {number(data.get(high), unit)}"


@st.cache_data(ttl=30, show_spinner=False)
def cached_get(base_url, resource, identifier=None):
    # Include the server in the cache key so environments cannot share results.
    loaders = {"summary": api.get_summary, "opportunities": api.get_opportunities,
               "opportunity": api.get_opportunity, "job": api.get_job}
    return loaders[resource]() if identifier is None else loaders[resource](identifier)


def load(resource, identifier=None):
    try:
        result = cached_get(api._api_base_url(), resource, identifier)
        if not isinstance(result, dict):
            raise ValueError("Expected an API object")
        return result
    except (requests.RequestException, ValueError, TypeError):
        st.error(f"Unable to load {resource} data. Please check the backend service and use Refresh data to retry.")
        return None


st.title("CutScope")
st.caption("GPU cost decisions · Four-month workload sample")
with st.sidebar:
    st.header("Investigation")
    if st.button("Refresh data"):
        cached_get.clear()

summary = load("summary")
listing = load("opportunities")
items = (listing or {}).get("opportunities") or []
options = {item["id"]: item for item in items}
selected = None
with st.sidebar:
    if options:
        if st.session_state.get("selected_opportunity") not in options:
            st.session_state.selected_opportunity = next(iter(options))
        selected = st.selectbox("Opportunity", list(options),
                                format_func=lambda key: options[key].get("title") or key,
                                key="selected_opportunity")
    elif listing is not None:
        st.info("No opportunities returned by the backend.")
    st.caption("Select an opportunity to inspect its savings and supporting evidence.")

opportunity = options.get(selected, {})
details = load("opportunity", selected) if selected else None
risk_data = (details or {}).get("cost_if_wrong") or {}
money, cut, risk = st.columns(3)
with money, st.container(border=True):
    st.subheader("01 · Where money goes")
    if summary is not None:
        st.metric("Allocated GPU-hours", number(summary.get("total_gpu_hours")))
        st.metric("Estimated allocation cost", number(summary.get("total_cost_usd"), "$"))
        st.metric("Completed capacity", number(summary.get("completed_percent"), "%"))
        st.caption(f"Rate: {number(summary.get('price_per_gpu_hour'), '$')}/GPU-hour · Price book: {summary.get('price_book_version') or 'Unavailable'}")
        st.caption(summary.get("scope_caveat") or "Scope information unavailable")
        if summary.get("outcomes"):
            st.dataframe([{"Outcome": row.get("name"), "Jobs": row.get("jobs"),
                           "GPU-hours": number(row.get("gpu_hours")),
                           "Cost (USD)": number(row.get("cost_usd"), "$"),
                           "Capacity (%)": number(row.get("capacity_percent"), "%")}
                          for row in summary["outcomes"]], hide_index=True)
    else:
        st.info("Allocation data is currently unavailable.")
with cut, st.container(border=True):
    st.subheader("02 · Where to cut")
    if opportunity:
        st.write(opportunity.get("title"))
        st.metric("Potential savings range", interval(opportunity, "savings_usd_low", "savings_usd_high", "$"))
        st.metric("Recoverable GPU-hours", interval(opportunity, "gpu_hours_low", "gpu_hours_high"))
        st.metric("Recoverable capacity", interval(opportunity, "capacity_percent_low", "capacity_percent_high", "%"))
        st.write(opportunity.get("action") or "Action unavailable")
        st.caption(f"Owner: {opportunity.get('owner') or 'Unavailable'} · Confidence: {number(opportunity.get('confidence'))}")
        st.caption(f"Risk: {opportunity.get('risk_level') or 'Unavailable'} · Jobs: {number(opportunity.get('job_count'))}")
    else:
        st.info("Select an available opportunity to view savings.")
with risk, st.container(border=True):
    st.subheader("03 · Cost if wrong")
    if details is not None:
        st.metric("Estimated downside range", interval(risk_data, "usd_low", "usd_high", "$"))
        st.write(risk_data.get("description") or "Downside description unavailable")
        st.write("Mitigation: " + (risk_data.get("mitigation") or "Unavailable"))
        reversible = risk_data.get("reversible")
        st.caption("Reversible: " + ("Unavailable" if reversible is None else "Yes" if reversible else "No"))
    else:
        st.info("Downside data is currently unavailable.")

st.divider()
st.subheader("Opportunity & evidence")
method, jobs, findings = st.tabs(["Method & assumptions", "Job evidence", "MantisGrid findings"])
with method:
    if details is not None:
        st.write(details.get("title") or selected)
        st.write("Method: " + (details.get("method") or "Unavailable"))
        st.write("Basis: " + (details.get("basis") or "Unavailable"))
        for caveat in details.get("caveats") or []:
            st.write(caveat)
    st.caption("Source: Product Backend API. Cancelled jobs are not automatically waste.")
job = None
with jobs:
    job_ids = (details or {}).get("jobs") or []
    if not all(type(job_id) is int for job_id in job_ids):
        st.error("Backend job list does not match API_CONTRACT.md: expected integer job IDs. Please notify the backend owner.")
    elif job_ids:
        job_key = f"evidence_job_{selected}"
        if st.session_state.get(job_key) not in job_ids:
            st.session_state[job_key] = job_ids[0]
        job_id = st.selectbox("Job ID", job_ids, key=job_key)
        job = load("job", job_id)
        if job is not None:
            numeric = {"gpu_count", "gpu_hours", "cost_usd", "sm_util_avg", "sm_util_max", "walltime_hours"}
            st.table([{"Field": field, "Value": number(job.get(field), unit) if field in numeric else str(job.get(field)) if job.get(field) is not None else "—"}
                      for field, unit in [("job_id", ""), ("state", ""), ("gpu_count", ""), ("gpu_hours", ""), ("cost_usd", "$"), ("sm_util_avg", "%"), ("sm_util_max", "%"), ("walltime_hours", " h"), ("primary_node", "")]])
    else:
        st.info("No supporting job IDs are available for this opportunity.")
with findings:
    if job and job.get("findings"):
        st.json(job["findings"])
    else:
        st.info("No findings returned for the selected job.")
st.caption("— means unavailable, never zero. Values are supplied by the backend; savings are not calculated in this page.")
render_copilot()
