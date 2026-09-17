import streamlit as st

from components.dashboard1 import render_dashboard1


st.set_page_config(
    page_title="CutScope",
    page_icon="🐻",
    layout="wide",
)

render_dashboard1()
