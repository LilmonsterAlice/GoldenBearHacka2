import pandas as pd
import plotly.express as px
import streamlit as st


def render_demo_dashboard2() -> None:
    """Render a second dashboard using temporary marketing data."""
    campaign_data = pd.DataFrame(
        [
            {"channel": "Email", "spend": 12_000, "leads": 940, "conversions": 188},
            {"channel": "Search", "spend": 24_000, "leads": 1_320, "conversions": 264},
            {"channel": "Social", "spend": 18_000, "leads": 1_080, "conversions": 173},
            {"channel": "Partners", "spend": 9_000, "leads": 510, "conversions": 128},
        ]
    )
    campaign_data["conversion_rate"] = (
        campaign_data["conversions"] / campaign_data["leads"]
    )
    campaign_data["cost_per_conversion"] = (
        campaign_data["spend"] / campaign_data["conversions"]
    )

    st.header("Marketing Performance")
    st.caption("Second prototype dashboard using dummy campaign data")

    total_spend = campaign_data["spend"].sum()
    total_leads = campaign_data["leads"].sum()
    total_conversions = campaign_data["conversions"].sum()
    overall_conversion_rate = total_conversions / total_leads

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Campaign spend", f"${total_spend:,.0f}")
    metric_2.metric("Leads", f"{total_leads:,}")
    metric_3.metric("Conversions", f"{total_conversions:,}")
    metric_4.metric("Conversion rate", f"{overall_conversion_rate:.1%}")

    chart = px.bar(
        campaign_data,
        x="channel",
        y="conversions",
        color="conversion_rate",
        text="conversions",
        color_continuous_scale="Blues",
        labels={
            "channel": "Channel",
            "conversions": "Conversions",
            "conversion_rate": "Conversion rate",
        },
        title="Conversions by marketing channel",
    )
    chart.update_traces(textposition="outside")
    st.plotly_chart(chart, width="stretch")

    with st.expander("View campaign data"):
        display_data = campaign_data.copy()
        display_data["conversion_rate"] = display_data["conversion_rate"].map(
            lambda value: f"{value:.1%}"
        )
        display_data["cost_per_conversion"] = display_data[
            "cost_per_conversion"
        ].map(lambda value: f"${value:,.2f}")
        st.dataframe(display_data, width="stretch", hide_index=True)
