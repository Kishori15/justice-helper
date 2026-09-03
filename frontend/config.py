"""
Configuration settings for JusticeHelper Streamlit frontend.
"""
import os

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")

# Primary branding colors and typography
APP_TITLE = "JusticeHelper"
APP_SUBTITLE = "AI-Assisted Indian E-Commerce Refund Complaint Drafting Tool"
APP_DISCLAIMER = (
    "⚖️ **Disclaimer:** JusticeHelper provides informational assistance and reference drafts only. "
    "It does not constitute legal advice and does not guarantee outcome."
)
