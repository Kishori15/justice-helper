"""
Streamlit Application Entrypoint for JusticeHelper.
Implements ARCHITECTURE.md §4 and PROJECT_STRUCTURE.md §3.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path when Streamlit runs script from frontend/ directory
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from frontend.api_client import api_client
from frontend.config import APP_DISCLAIMER, APP_SUBTITLE, APP_TITLE

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "case_id" not in st.session_state:
    st.session_state.case_id = None
if "current_case" not in st.session_state:
    st.session_state.current_case = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.title("⚖️ JusticeHelper")
    st.caption("Indian E-Commerce Refund Legal Assistant")
    st.divider()

    if st.session_state.case_id:
        st.success(f"Active Case: `{st.session_state.case_id}`")
        if st.session_state.current_case and st.session_state.current_case.get("order_info"):
            o = st.session_state.current_case["order_info"]
            st.write(f"**Platform:** {o.get('platform') or 'N/A'}")
            st.write(f"**Product:** {o.get('product_name') or 'N/A'}")
        if st.session_state.current_case and st.session_state.current_case.get("issue"):
            iss = st.session_state.current_case["issue"]
            st.write(f"**Issue:** {iss.get('issue_type', '').replace('_', ' ').title()}")
    else:
        st.info("No active case. Start intake below or on the Home page.")

    st.divider()
    backend_status = api_client.health_check()
    if backend_status:
        st.success("🟢 Backend Connected (Port 8000)")
    else:
        st.warning("⚠️ Backend Offline. Make sure FastAPI server is running.")

    st.markdown("---")
    st.caption("Version 1.0 (BGE + BM25 + Gemini RAG)")


# Main Page Content
st.title(f"⚖️ {APP_TITLE}")
st.subheader(APP_SUBTITLE)

st.markdown("""
Welcome to **JusticeHelper**. If you have faced issues getting a refund from an Indian e-commerce platform 
(like Flipkart, Amazon, Myntra, Meesho, Zepto, Blinkit, etc.), JusticeHelper helps you:
1. **Explain your issue in plain language** (English, Hindi, or Hinglish).
2. **Understand your legal rights** under the *Consumer Protection Act, 2019* and *E-Commerce Rules, 2020*.
3. **Collect the right evidence** with a tailored checklist.
4. **Draft formal grievance notices** to the platform's Grievance Officer and the **National Consumer Helpline (NCH)**.
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🚀 Start a New Case")
    st.write("Begin by chatting with our intake assistant to describe what happened.")
    if st.button("Start New Complaint Case", type="primary", use_container_width=True):
        # Reset active session
        st.session_state.case_id = None
        st.session_state.current_case = None
        st.session_state.messages = []
        st.switch_page("pages/2_chat_intake.py")

with col2:
    st.markdown("### 📂 Resume or Load Past Case")
    cases = api_client.list_cases()
    if cases:
        case_options = {f"{c['case_id']} - {c.get('user_name') or 'Anonymous'} ({c.get('created_at', '')[:10]})": c['case_id'] for c in cases}
        selected_label = st.selectbox("Select existing case:", list(case_options.keys()))
        if st.button("Load Case", use_container_width=True):
            cid = case_options[selected_label]
            case_data = api_client.get_case(cid)
            st.session_state.case_id = cid
            st.session_state.current_case = case_data
            st.session_state.messages = [
                {"role": m["role"], "content": m["text"]}
                for m in case_data.get("conversation", [])
            ]
            st.success(f"Loaded case {cid}!")
            st.switch_page("pages/3_case_summary.py")
    else:
        st.info("No saved cases in database yet.")

st.divider()

st.markdown("### 🛡️ Supported Dispute Scenarios")
scenarios = [
    ("📦 Item Not Delivered", "Order prepaid or COD confirmed, but goods never arrived or marked falsely delivered."),
    ("🔄 Wrong Item Delivered", "Received a completely different item, incorrect size, or counterfeit product."),
    ("💥 Defective / Damaged Item", "Product arrived broken, inoperative, expired, or substandard."),
    ("⏳ Refund Initiated But Not Received", "Platform approved refund on app, but bank account was never credited beyond turnaround time."),
    ("⏱️ Refund Delayed / Withheld", "Seller/Platform refused cancellation or delayed refund beyond statutory timelines.")
]

for title, desc in scenarios:
    with st.expander(title):
        st.write(desc)

st.markdown("---")
st.info(APP_DISCLAIMER)
