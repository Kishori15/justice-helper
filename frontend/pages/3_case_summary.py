"""
Page 3: Case Summary ("Understand" step).
Implements PRD.md §6, §7.1 and DATA_SCHEMA.md §1.
Allows user to review, edit, and confirm extracted fields.
"""
import streamlit as st
from frontend.api_client import api_client

st.set_page_config(page_title="Case Summary - JusticeHelper", page_icon="📋", layout="wide")

st.title("📋 Case Summary & Structured Details")
st.caption("Review the extracted details from your conversation and make any manual corrections.")

if not st.session_state.get("current_case"):
    st.warning("No active case found. Please complete chat intake first.")
    if st.button("← Go to Chat Intake"):
        st.switch_page("pages/2_chat_intake.py")
    st.stop()

case = st.session_state.current_case
order_info = case.get("order_info") or {}
issue = case.get("issue") or {}
outcome = case.get("desired_outcome") or {}
evidence = case.get("evidence_available") or {}

with st.form("case_summary_form"):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🛒 Order Information")
        platform = st.text_input("E-Commerce Platform", value=order_info.get("platform", ""))
        product_name = st.text_input("Product Name", value=order_info.get("product_name", ""))
        price_paid = st.number_input("Price Paid (₹)", min_value=0.0, value=float(order_info.get("price_paid", 0.0)))
        order_id = st.text_input("Order ID (optional)", value=order_info.get("order_id") or "")
        order_date = st.text_input("Order Date (YYYY-MM-DD)", value=order_info.get("order_date") or "")
        payment_mode = st.selectbox(
            "Payment Mode",
            ["upi", "card", "net_banking", "cod", "other"],
            index=["upi", "card", "net_banking", "cod", "other"].index(order_info.get("payment_mode", "other"))
        )

    with col2:
        st.subheader("⚠️ Dispute Details")
        issue_types = ["not_delivered", "wrong_item", "defective", "refund_not_received", "refund_delayed"]
        current_type = issue.get("issue_type")
        idx = issue_types.index(current_type) if current_type in issue_types else 0
        selected_issue_type = st.selectbox(
            "Issue Type",
            issue_types,
            index=idx,
            format_func=lambda x: x.replace("_", " ").title()
        )
        description = st.text_area("Issue Description", value=issue.get("description", ""), height=120)
        expected_resolution = st.text_input("Expected Resolution", value=issue.get("expected_resolution", "Full refund"))

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("💰 Desired Outcome")
        refund_type = st.selectbox("Refund Type", ["full", "partial"], index=0 if outcome.get("refund_type") == "full" else 1)
        comp_req = st.checkbox("Request Compensation for delay / harassment?", value=bool(outcome.get("compensation_requested", False)))
        comp_amount = st.number_input("Compensation Amount (₹)", min_value=0.0, value=float(outcome.get("compensation_amount") or 0.0))

    with col4:
        st.subheader("📁 Evidence Available (Self-Reported)")
        has_inv = st.checkbox("Invoice / Purchase Bill", value=bool(evidence.get("invoice", False)))
        has_conf = st.checkbox("Order Confirmation Email/SMS", value=bool(evidence.get("order_confirmation", True)))
        has_pay = st.checkbox("Payment Proof (UPI Ref / Bank Statement)", value=bool(evidence.get("payment_proof", True)))
        has_chat = st.checkbox("Customer Care Chat Logs / Tickets", value=bool(evidence.get("chat_logs", False)))
        has_photo = st.checkbox("Defect / Unboxing Photos / Videos", value=bool(evidence.get("product_photos", False)))

    submitted = st.form_submit_button("💾 Save Updates", type="secondary", use_container_width=True)

    if submitted:
        # Update local dictionary
        case["order_info"] = {
            "platform": platform,
            "product_name": product_name,
            "price_paid": price_paid,
            "order_id": order_id or None,
            "order_date": order_date or None,
            "payment_mode": payment_mode,
            "delivery_status": order_info.get("delivery_status", "unknown")
        }
        case["issue"] = {
            "issue_type": selected_issue_type,
            "description": description,
            "expected_resolution": expected_resolution
        }
        case["desired_outcome"] = {
            "refund_type": refund_type,
            "refund_amount": price_paid if refund_type == "full" else None,
            "compensation_requested": comp_req,
            "compensation_amount": comp_amount if comp_req else None,
            "apology_requested": False
        }
        case["evidence_available"] = {
            "invoice": has_inv,
            "order_confirmation": has_conf,
            "payment_proof": has_pay,
            "chat_logs": has_chat,
            "product_photos": has_photo
        }

        try:
            saved_case = api_client.update_case(case)
            st.session_state.current_case = saved_case
            st.success("Case summary saved successfully!")
        except Exception as e:
            st.error(f"Failed to update case: {e}")

st.divider()

col_back, col_next = st.columns([1, 2])
with col_back:
    if st.button("← Back to Chat", use_container_width=True):
        st.switch_page("pages/2_chat_intake.py")
with col_next:
    if st.button("Fetch Legal Rights & Basis →", type="primary", use_container_width=True):
        # Validate critical fields
        current_issue = case.get("issue", {}).get("issue_type")
        current_platform = case.get("order_info", {}).get("platform")
        current_product = case.get("order_info", {}).get("product_name")

        if not current_issue or current_issue not in ["not_delivered", "wrong_item", "defective", "refund_not_received", "refund_delayed"]:
            st.error("⚠️ Issue Type is strictly required before proceeding to Legal Rights retrieval. Please select an issue type above and click 'Save Updates'.")
        elif not current_platform or not current_product:
            st.warning("⚠️ Platform and Product Name are recommended to ensure best legal document generation. Click 'Save Updates' after entering them.")
            st.switch_page("pages/4_rights_and_basis.py")
        else:
            st.switch_page("pages/4_rights_and_basis.py")
