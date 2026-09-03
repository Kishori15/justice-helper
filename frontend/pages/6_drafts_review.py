"""
Page 6: Drafts Review ("Draft" & "Review" steps).
Implements PRD.md §6, §7.5 and ARCHITECTURE.md §2.6, §2.8.
"""
import streamlit as st
from frontend.api_client import api_client

st.set_page_config(page_title="Review Drafts - JusticeHelper", page_icon="✍️", layout="wide")

st.title("✍️ Review & Edit Complaint Drafts")
st.caption("Customize your grievance letter to the seller and your formal NCH escalation complaint.")

if not st.session_state.get("case_id"):
    st.warning("No active case. Please start with chat intake.")
    if st.button("← Go to Intake"):
        st.switch_page("pages/2_chat_intake.py")
    st.stop()

case_id = st.session_state.case_id

# Tone Selector for Email
col_tone, col_regen = st.columns([3, 1])
with col_tone:
    tone_choice = st.radio(
        "Email Tone Variant:",
        ["polite_first_notice", "firm_second_notice"],
        index=0,
        format_func=lambda x: "Polite First Notice (Standard initial grievance)" if x == "polite_first_notice" else "Firm Second Notice (Final warning before commission escalation)",
        horizontal=True
    )
with col_regen:
    st.write("")
    if st.button("🔄 Regenerate Drafts"):
        st.session_state.pop("drafts_data", None)

if "drafts_data" not in st.session_state:
    with st.spinner("Drafting seller notice and NCH complaint..."):
        try:
            drafts_res = api_client.generate_drafts(case_id, tone=tone_choice)
            st.session_state.drafts_data = drafts_res
            st.session_state.current_case = api_client.get_case(case_id)
        except Exception as e:
            st.error(f"Error generating drafts: {e}")
            st.stop()

drafts_data = st.session_state.get("drafts_data", {})
email_data = drafts_data.get("draft_email", {})
nch_data = drafts_data.get("draft_nch_complaint", {})

tab1, tab2 = st.tabs(["📧 1. Seller / Platform Grievance Notice", "🏛️ 2. Formal NCH / Consumer Commission Complaint"])

with tab1:
    st.subheader("Grievance Email / Message Draft")
    st.caption("Send this directly to the platform's Grievance Officer or customer support.")

    email_subject = st.text_input("Email Subject Line", value=email_data.get("subject", ""))
    email_body = st.text_area("Email Body", value=email_data.get("body", ""), height=350)

with tab2:
    st.subheader("Formal Complaint for NCH / e-Daakhil Filing")
    st.caption("Use this structured draft when escalating to National Consumer Helpline (1915) or e-Daakhil.")

    col_n1, col_n2 = st.columns(2)
    with col_n1:
        complainant = st.text_input("Complainant Details", value=nch_data.get("complainant_details", ""))
    with col_n2:
        opp_party = st.text_input("Opposite Party Details", value=nch_data.get("opposite_party_details", ""))

    jurisdiction = st.text_input("Jurisdiction Note", value=nch_data.get("jurisdiction_note", ""))
    facts = st.text_area("1. Statement of Facts", value=nch_data.get("facts", ""), height=150)
    grounds = st.text_area("2. Grounds of Complaint & Legal Provisions (Cited)", value=nch_data.get("grounds", ""), height=180)
    relief = st.text_area("3. Relief Sought", value=nch_data.get("relief_sought", ""), height=100)
    verification = st.text_input("4. Verification Clause", value=nch_data.get("verification_clause", ""))

st.divider()

col_save, col_export = st.columns([1, 2])

with col_save:
    if st.button("💾 Save Edited Drafts", use_container_width=True):
        if st.session_state.current_case and "generation_output" in st.session_state.current_case:
            gen = st.session_state.current_case["generation_output"] or {}
            gen["draft_email"] = {"tone": tone_choice, "subject": email_subject, "body": email_body}
            gen["draft_nch_complaint"] = {
                "complainant_details": complainant,
                "opposite_party_details": opp_party,
                "jurisdiction_note": jurisdiction,
                "facts": facts,
                "grounds": grounds,
                "relief_sought": relief,
                "enclosures": nch_data.get("enclosures", ["Invoice", "Payment Proof"]),
                "verification_clause": verification
            }
            st.session_state.current_case["generation_output"] = gen
            api_client.update_case(st.session_state.current_case)
            st.success("Drafts saved successfully!")

with col_export:
    if st.button("Proceed to Export & Download →", type="primary", use_container_width=True):
        st.switch_page("pages/7_export.py")
