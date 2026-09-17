import pandas as pd
import plotly.express as px
import streamlit as st

from dashboards.demo_dashboard2 import render_demo_dashboard2


st.set_page_config(
    page_title="Golden Bear Analytics",
    page_icon="🐻",
    layout="wide",
)


@st.cache_data
def load_dummy_data() -> pd.DataFrame:
    """Return temporary data until the hackathon dataset is available."""
    return pd.DataFrame(
        [
            {"month": "Jan", "region": "North", "revenue": 72_000, "orders": 610},
            {"month": "Jan", "region": "South", "revenue": 58_000, "orders": 520},
            {"month": "Jan", "region": "West", "revenue": 81_000, "orders": 680},
            {"month": "Feb", "region": "North", "revenue": 78_000, "orders": 640},
            {"month": "Feb", "region": "South", "revenue": 61_000, "orders": 540},
            {"month": "Feb", "region": "West", "revenue": 86_000, "orders": 710},
            {"month": "Mar", "region": "North", "revenue": 69_000, "orders": 590},
            {"month": "Mar", "region": "South", "revenue": 66_000, "orders": 565},
            {"month": "Mar", "region": "West", "revenue": 93_000, "orders": 755},
            {"month": "Apr", "region": "North", "revenue": 84_000, "orders": 690},
            {"month": "Apr", "region": "South", "revenue": 71_000, "orders": 600},
            {"month": "Apr", "region": "West", "revenue": 98_000, "orders": 790},
        ]
    )


data = load_dummy_data()

st.title("🐻 Golden Bear Analytics")
st.caption("Prototype dashboard using dummy data")

with st.sidebar:
    st.header("Filters")
    selected_regions = st.multiselect(
        "Region",
        options=data["region"].unique(),
        default=list(data["region"].unique()),
    )

filtered_data = data[data["region"].isin(selected_regions)]

if filtered_data.empty:
    st.warning("Select at least one region to display the dashboard.")
    st.stop()

total_revenue = filtered_data["revenue"].sum()
total_orders = filtered_data["orders"].sum()
average_order_value = total_revenue / total_orders
top_region = (
    filtered_data.groupby("region")["revenue"].sum().idxmax()
)

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Total revenue", f"${total_revenue:,.0f}")
metric_2.metric("Total orders", f"{total_orders:,}")
metric_3.metric("Average order value", f"${average_order_value:,.2f}")
metric_4.metric("Top region", top_region)

st.subheader("Monthly revenue by region")
chart = px.line(
    filtered_data,
    x="month",
    y="revenue",
    color="region",
    markers=True,
    category_orders={"month": ["Jan", "Feb", "Mar", "Apr"]},
    labels={"month": "Month", "revenue": "Revenue ($)", "region": "Region"},
)
chart.update_layout(legend_title_text="Region")
st.plotly_chart(chart, width="stretch")

with st.expander("View dummy data"):
    st.dataframe(filtered_data, width="stretch", hide_index=True)

st.info("This dashboard uses temporary data and can be connected to the real dataset later.")

st.divider()
render_demo_dashboard2()
