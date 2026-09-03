"""
Page 5: Evidence Checklist ("Collect Evidence" step).
Implements PRD.md §6, §7.4, ARCHITECTURE.md §2.6a, and PROMPTS.md §4.
"""
import streamlit as st
from frontend.api_client import api_client

st.set_page_config(page_title="Evidence Checklist - JusticeHelper", page_icon="📁", layout="wide")

st.title("📁 Tailored Evidence Collection Checklist")
st.caption("Gather these documents and screenshots to ensure your grievance cannot be dismissed.")

if not st.session_state.get("case_id"):
    st.warning("No active case. Please start with chat intake.")
    if st.button("← Go to Intake"):
        st.switch_page("pages/2_chat_intake.py")
    st.stop()

case_id = st.session_state.case_id

try:
    checklist_data = api_client.get_checklist(case_id)
    items = checklist_data.get("checklist", [])
except Exception as e:
    st.error(f"Error fetching evidence checklist: {e}")
    st.stop()

if "checked_items" not in st.session_state:
    st.session_state.checked_items = {}

total_items = len(items)
checked_count = sum(1 for i, it in enumerate(items) if st.session_state.checked_items.get(f"chk_{case_id}_{i}", False))
progress = checked_count / total_items if total_items > 0 else 0.0

st.progress(progress, text=f"Evidence Readiness: {checked_count}/{total_items} items collected ({int(progress*100)}%)")

st.divider()

for i, item in enumerate(items):
    key = f"chk_{case_id}_{i}"
    col1, col2 = st.columns([1, 15])
    with col1:
        checked = st.checkbox("", key=key, value=st.session_state.checked_items.get(key, False))
        st.session_state.checked_items[key] = checked
    with col2:
        st.markdown(f"**{item.get('item')}**")
        st.caption(f"💡 *How to obtain:* {item.get('how_to')}")
    st.markdown("---")

col_prev, col_next = st.columns([1, 2])
with col_prev:
    if st.button("← Back to Legal Rights", use_container_width=True):
        st.switch_page("pages/4_rights_and_basis.py")
with col_next:
    if st.button("Proceed to Generate Drafts →", type="primary", use_container_width=True):
        st.switch_page("pages/6_drafts_review.py")
