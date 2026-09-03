"""
Page 4: Rights & Grounded Legal Basis ("Retrieve" & "Explain" steps).
Implements PRD.md §6, §7.2, §7.3 and ARCHITECTURE.md §2.4–2.7.
"""
import streamlit as st
from frontend.api_client import api_client

st.set_page_config(page_title="Legal Rights & Basis - JusticeHelper", page_icon="📜", layout="wide")

st.title("📜 Your Legal Rights & Grounded Statutory Basis")
st.caption("All legal principles below are strictly grounded in retrieved provisions of Indian consumer protection law.")

if not st.session_state.get("case_id"):
    st.warning("No active case. Please start with chat intake.")
    if st.button("← Go to Intake"):
        st.switch_page("pages/2_chat_intake.py")
    st.stop()

case_id = st.session_state.case_id

# Fetch or generate rights
if st.button("🔄 Refresh Retrieval & Analysis", type="secondary"):
    st.session_state.pop("retrieval_data", None)
    st.session_state.pop("explanation_data", None)
    st.session_state.pop("verification_data", None)

if "retrieval_data" not in st.session_state or "explanation_data" not in st.session_state:
    with st.spinner("Retrieving relevant sections and generating rights summary..."):
        try:
            retrieval_res = api_client.retrieve_passages(case_id)
            st.session_state.retrieval_data = retrieval_res

            expl_res = api_client.generate_explanation(case_id)
            st.session_state.explanation_data = expl_res

            # Run verification critic
            try:
                verif_res = api_client.verify_citations(case_id)
                st.session_state.verification_data = verif_res
            except Exception:
                st.session_state.verification_data = None

            # Refresh local case object
            st.session_state.current_case = api_client.get_case(case_id)
        except Exception as e:
            st.error(f"Error during legal retrieval: {e}")
            st.stop()

retrieval_data = st.session_state.get("retrieval_data", {})
explanation_data = st.session_state.get("explanation_data", {})
verification_data = st.session_state.get("verification_data")

# Verification status badge
col_v1, col_v2 = st.columns([3, 1])
with col_v1:
    st.subheader("💡 Plain-Language Summary of Your Rights")
with col_v2:
    if verification_data and verification_data.get("verified"):
        st.success("🛡️ Citations Verified 100%")
    elif verification_data and verification_data.get("flags"):
        st.warning(f"⚠️ {len(verification_data['flags'])} Flag(s) in Critic Review")
    else:
        st.info("ℹ️ Grounded in Verified Corpus")

st.markdown(f"> {explanation_data.get('rights_summary', 'No summary available.')}")

st.divider()

# Grounded Legal Basis Cards
st.subheader("⚖️ Grounded Legal Grounds & Statutory Citations")
legal_basis = explanation_data.get("legal_basis", [])

if legal_basis:
    for idx, item in enumerate(legal_basis, 1):
        with st.container():
            st.markdown(f"#### {idx}. {item.get('claim')}")
            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                st.markdown(f"**Statutory Provision:** `{item.get('citation')}`")
            with col_c2:
                st.caption(f"Corpus Ref ID: `{item.get('snippet_id')}`")
            st.markdown("---")
else:
    st.info("General consumer principles apply to this dispute.")

# Transparent Retrieval Inspection
with st.expander("🔍 Inspect Retrieved Legal Passages (RAG Transparency)"):
    st.write(f"The hybrid retrieval module surfaced {len(retrieval_data.get('candidates', []))} relevant statutory passages:")
    for c in retrieval_data.get("candidates", []):
        st.markdown(f"**[{c.get('source_type', '').upper()}] {c.get('title')} ({c.get('section_number')})**")
        st.write(c.get("text"))
        st.markdown(f"🔗 [Official Source Link]({c.get('url')}) &nbsp;|&nbsp; Score: `{c.get('retrieval_score')}`")
        st.divider()

st.divider()

col_prev, col_next = st.columns([1, 2])
with col_prev:
    if st.button("← Back to Case Summary", use_container_width=True):
        st.switch_page("pages/3_case_summary.py")
with col_next:
    if st.button("View Evidence Checklist →", type="primary", use_container_width=True):
        st.switch_page("pages/5_evidence_checklist.py")
