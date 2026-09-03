"""
Page 1: New Case Creation.
"""
import streamlit as st

st.set_page_config(page_title="New Case - JusticeHelper", page_icon="⚖️", layout="wide")

st.title("⚖️ Start a New Complaint")
st.write("Reset your current workspace and start describing a fresh refund dispute.")

name_input = st.text_input("Your Name (optional):", placeholder="e.g. Ramesh Kumar")

if st.button("Proceed to Chat Intake →", type="primary"):
    st.session_state.case_id = None
    st.session_state.current_case = None
    st.session_state.messages = []
    st.session_state.user_name = name_input
    st.switch_page("pages/2_chat_intake.py")
