"""
Page 7: Export & Download ("Export" step).
Implements PRD.md §6, §7.6, §8 and DATA_SCHEMA.md §7.
"""
import streamlit as st
from frontend.api_client import api_client

st.set_page_config(page_title="Export Case - JusticeHelper", page_icon="📥", layout="wide")

st.title("📥 Export & Download Complaint Package")
st.caption("Download your formatted complaint bundle as PDF or DOCX, or copy text for immediate filing.")

if not st.session_state.get("case_id"):
    st.warning("No active case. Please start with chat intake.")
    if st.button("← Go to Intake"):
        st.switch_page("pages/2_chat_intake.py")
    st.stop()

case_id = st.session_state.case_id

try:
    case = api_client.get_case(case_id)
    st.session_state.current_case = case
except Exception as e:
    st.error(f"Error fetching case data: {e}")
    st.stop()

gen_out = case.get("generation_output") or {}

st.subheader("📄 Download Files")
col1, col2 = st.columns(2)

with col1:
    try:
        pdf_bytes = api_client.get_pdf_bytes(case_id)
        st.download_button(
            label="⬇️ Download Case Summary & Drafts (PDF)",
            data=pdf_bytes,
            file_name=f"JusticeHelper_Complaint_{case_id}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"PDF generation error: {e}")

with col2:
    try:
        docx_bytes = api_client.get_docx_bytes(case_id)
        st.download_button(
            label="⬇️ Download Editable Document (DOCX)",
            data=docx_bytes,
            file_name=f"JusticeHelper_Complaint_{case_id}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"DOCX generation error: {e}")

st.divider()

st.subheader("📋 Copy Drafts to Clipboard")
tab_em, tab_nch = st.tabs(["📧 Copy Seller Email", "🏛️ Copy NCH Complaint Text"])

with tab_em:
    em = gen_out.get("draft_email", {})
    email_text = f"Subject: {em.get('subject', '')}\n\n{em.get('body', '')}"
    st.code(email_text, language="text")

with tab_nch:
    nch = gen_out.get("draft_nch_complaint", {})
    complaint_text = (
        f"COMPLAINANT:\n{nch.get('complainant_details', '')}\n\n"
        f"OPPOSITE PARTY:\n{nch.get('opposite_party_details', '')}\n\n"
        f"JURISDICTION NOTE:\n{nch.get('jurisdiction_note', '')}\n\n"
        f"1. STATEMENT OF FACTS:\n{nch.get('facts', '')}\n\n"
        f"2. GROUNDS OF COMPLAINT:\n{nch.get('grounds', '')}\n\n"
        f"3. RELIEF SOUGHT:\n{nch.get('relief_sought', '')}\n\n"
        f"4. VERIFICATION:\n{nch.get('verification_clause', '')}\n\n"
        f"---\n{gen_out.get('disclaimer', '')}"
    )
    st.code(complaint_text, language="text")

st.divider()

st.subheader("🔒 Data Privacy & Reset")
st.write("In accordance with our minimal-storage policy, you can delete this case from the database at any time.")

col_del, col_new = st.columns([1, 2])

with col_del:
    if st.button("🗑️ Delete My Case Data", type="secondary"):
        deleted = api_client.delete_case(case_id)
        if deleted:
            st.session_state.case_id = None
            st.session_state.current_case = None
            st.session_state.messages = []
            st.success("Case data permanently deleted.")
            st.switch_page("app.py")
        else:
            st.error("Failed to delete case data.")

with col_new:
    if st.button("✨ Start Another Case", use_container_width=True):
        st.session_state.case_id = None
        st.session_state.current_case = None
        st.session_state.messages = []
        st.switch_page("pages/1_new_case.py")
