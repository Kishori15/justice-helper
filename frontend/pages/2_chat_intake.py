"""
Page 2: Chat Intake ("Tell" step).
Implements PRD.md §6, §7.1 and ARCHITECTURE.md §2.1.
"""
import streamlit as st
from frontend.api_client import api_client

st.set_page_config(page_title="Chat Intake - JusticeHelper", page_icon="💬", layout="wide")

st.title("💬 Case Intake Chat")
st.caption("Tell us what happened in plain English, Hindi, or Hinglish.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Check if intake is completed or round cap (3 rounds) reached
current_case = st.session_state.get("current_case") or {}
current_status = current_case.get("status")
intake_round = current_case.get("intake_round", 0)

is_complete = current_status in ["intake_completed", "issue_classified"]

if is_complete:
    st.info("ℹ️ Intake questions complete. Please proceed to the Case Summary page to review your information and fill in any missing details.")
    if st.button("Proceed to Case Summary →", type="primary", use_container_width=True):
        st.switch_page("pages/3_case_summary.py")
else:
    # Example prompts for convenience
    with st.expander("💡 Click to paste example scenario"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Example: Item not delivered (Flipkart)"):
                st.session_state.temp_prompt = "Maine 10 din pehle Flipkart se ₹2,499 ka smartwatch order kiya tha. Order marked delivered dikha raha hai par mujhe koi package nahi mila. Customer care ne koi help nahi ki aur refund deny kar rahe hain."
            if st.button("Example: Wrong item delivered (Amazon)"):
                st.session_state.temp_prompt = "I ordered Sony WH-1000XM5 headphones worth ₹24,990 from Amazon, but received a fake generic speaker inside the box. Return pickup was rejected by delivery agent."
        with col2:
            if st.button("Example: Defective phone (Myntra/Meesho)"):
                st.session_state.temp_prompt = "Received a defective jacket from Meesho worth ₹1,200 with torn sleeves. Seller is refusing to initiate return or refund."
            if st.button("Example: Refund delayed beyond TAT"):
                st.session_state.temp_prompt = "Flipkart accepted my return for running shoes worth ₹3,500 on 12th Aug and promised refund in 3-5 days. It has been 14 days and amount is still not credited to my bank."

    prompt_value = st.session_state.pop("temp_prompt", None)

    # Chat input
    user_input = st.chat_input("Describe your refund dispute here...") or prompt_value

    if user_input:
        # Render user message immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # Call backend intake API
        with st.spinner("Analyzing case and extracting details..."):
            try:
                res = api_client.send_chat_message(
                    message=user_input,
                    case_id=st.session_state.get("case_id"),
                    user_name=st.session_state.get("user_name")
                )
                reply = res["reply"]
                updated_case = res["updated_case_summary"]

                st.session_state.case_id = updated_case["case_id"]
                st.session_state.current_case = updated_case
                st.session_state.messages.append({"role": "assistant", "content": reply})

                with st.chat_message("assistant"):
                    st.write(reply)
                st.rerun()

            except Exception as e:
                st.error(f"Error communicating with backend: {e}")

# Navigation bar at bottom
if current_case and current_case.get("order_info"):
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        o = current_case["order_info"]
        iss = current_case.get("issue")
        st.success(
            f"✅ Captured (Round {current_case.get('intake_round', 0)}/3): "
            f"**Platform:** {o.get('platform') or 'Pending'} | "
            f"**Product:** {o.get('product_name') or 'Pending'} | "
            f"**Price:** ₹{o.get('price_paid', 0)} | "
            f"**Issue:** {iss.get('issue_type', '').replace('_', ' ').title() if iss else 'Pending'}"
        )
    with col2:
        if st.button("Review Case Summary →", type="primary", use_container_width=True):
            st.switch_page("pages/3_case_summary.py")
