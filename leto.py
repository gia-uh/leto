import streamlit as st

st.set_page_config(
    page_title="LETO MVP", page_icon="🧠", layout="wide", initial_sidebar_state="auto"
)


from leto import ui

ui.bootstrap()
