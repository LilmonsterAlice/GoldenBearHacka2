"""CutScope dashboard shell with the floating AI Copilot."""

import streamlit as st

from components.copilot import render_copilot


st.set_page_config(page_title="CutScope", page_icon="◈", layout="wide")
st.session_state.setdefault("selected_opportunity", "idle-interactive")

st.title("CutScope")
st.caption("GPU cost decisions · Four-month workload sample")
st.info("Layout preview — shared contract and mock data are pending. No analytical results are shown.")

with st.sidebar:
    st.header("Investigation")
    st.selectbox(
        "Opportunity",
        options=["idle-interactive"],
        format_func=lambda _: "Idle interactive sessions",
        key="selected_opportunity",
    )
    st.caption("First iteration: one opportunity, from savings to supporting evidence.")

money, cut, risk = st.columns(3)
with money:
    with st.container(border=True):
        st.subheader("01 · Where money goes")
        st.metric("Allocated GPU-hours", "—")
        st.metric("Estimated allocation cost", "—")
        st.caption("Awaiting outcome breakdown, pricing and source information.")
with cut:
    with st.container(border=True):
        st.subheader("02 · Where to cut")
        st.write("Idle interactive sessions")
        st.metric("Potential savings range", "—")
        st.caption("Awaiting the calculation method, action owner, confidence and caveats.")
with risk:
    with st.container(border=True):
        st.subheader("03 · Cost if wrong")
        st.metric("Estimated downside range", "—")
        st.caption("Awaiting risk assumptions, mitigation and rollback conditions.")

st.divider()
st.subheader("Opportunity & evidence")
detail, jobs, findings = st.tabs(["Method & assumptions", "Job evidence", "MantisGrid findings"])
with detail:
    st.write("Idle interactive sessions")
    st.info("The agreed analysis will explain which hours may be recoverable and why.")
    with st.expander("Scope and interpretation", expanded=True):
        st.write("This view describes a four-month workload sample. Cancelled jobs are not automatically waste.")
        st.write("Savings, confidence and downside estimates will come from the product backend.")
with jobs:
    st.info("No job records connected yet. This does not mean that no jobs are affected.")
with findings:
    st.info("No findings connected yet. Evidence IDs and raw fields will appear after contract integration.")

st.caption("— means unavailable, never zero. Layout preview only; no API requests or savings calculations.")

render_copilot()
