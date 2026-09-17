import pandas as pd
import plotly.express as px
import streamlit as st


def render_dashboard1() -> None:
    """Render a temporary Track 2 dashboard while real analysis is developed."""
    st.title("CutScope — AI GPU Efficiency Command Center")
    st.caption("Dummy dashboard · Placeholder values only · Not analysis results")

    st.info(
        "This prototype demonstrates the final layout. All values below are "
        "clearly marked dummy data and will be replaced by verified Track 2 results."
    )

    money, cut, risk = st.columns(3)

    with money:
        st.subheader("Where the money is going")
        st.metric("Sample GPU spend", "$1.49M")
        st.write("594,004 GPU-hours × $2.50/GPU-hour")
        st.caption("Official sample total; outcome allocation is still being verified.")

    with cut:
        st.subheader("Where to cut")
        st.metric("Illustrative opportunity", "$42K–$68K")
        st.write("Introduce warnings and timeouts for idle interactive sessions.")
        st.caption("Dummy range — not a submitted claim.")

    with risk:
        st.subheader("Cost if we are wrong")
        st.metric("Illustrative downside", "$8K–$20K")
        st.write("Productive interactive work could be interrupted by a strict policy.")
        st.caption("Mitigation: warn first, allow extensions, and roll back quickly.")

    st.divider()
    st.subheader("Outcome breakdown — dummy layout")

    outcomes = pd.DataFrame(
        {
            "outcome": ["Completed", "Cancelled", "Timeout", "Failed"],
            "gpu_hours": [229_041, 203_930, 107_952, 52_061],
        }
    )
    chart = px.bar(
        outcomes,
        x="outcome",
        y="gpu_hours",
        color="outcome",
        labels={"outcome": "Job outcome", "gpu_hours": "GPU-hours"},
    )
    chart.update_layout(showlegend=False)
    st.plotly_chart(chart, width="stretch")

    st.subheader("Ranked opportunities — placeholders")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "rank": 1,
                    "opportunity": "Idle interactive sessions",
                    "owner": "Platform Operations",
                    "confidence": "TBD",
                },
                {
                    "rank": 2,
                    "opportunity": "GPU not needed",
                    "owner": "Scheduling Policy",
                    "confidence": "TBD",
                },
                {
                    "rank": 3,
                    "opportunity": "GPU card imbalance",
                    "owner": "Workload Engineering",
                    "confidence": "TBD",
                },
            ]
        ),
        width="stretch",
        hide_index=True,
    )
