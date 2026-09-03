"""
PDF Export Module for JusticeHelper cases.
Implements ARCHITECTURE.md §2.8 and DATA_SCHEMA.md §7.
Supports WeasyPrint or ReportLab for reliable cross-platform PDF generation.
"""
from io import BytesIO
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from backend.models import CaseObject

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def generate_pdf_bytes(case: CaseObject) -> bytes:
    """
    Renders case summary and drafts into PDF bytes.
    """
    # 1. Try WeasyPrint if available
    try:
        import weasyprint
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
        template = env.get_template("export_html.html")
        rendered_html = template.render(
            case_id=case.case_id,
            created_at=case.created_at,
            status=case.status,
            order_info=case.order_info,
            issue=case.issue,
            generation_output=case.generation_output
        )
        return weasyprint.HTML(string=rendered_html).write_pdf()
    except Exception:
        # Fallback to ReportLab for robust local PDF generation
        return _generate_pdf_reportlab(case)


def _generate_pdf_reportlab(case: CaseObject) -> bytes:
    """
    Generates a clean, structured PDF using reportlab.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1e3a8a'))
    h2_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=13, leading=17, textColor=colors.HexColor('#1e40af'), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#1f2937'))
    cite_style = ParagraphStyle('CiteText', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#065f46'))
    disclaimer_style = ParagraphStyle('DisclaimerText', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#991b1b'))

    story = []

    # Title & Metadata
    story.append(Paragraph("JusticeHelper — Case Summary & Drafts", title_style))
    story.append(Spacer(1, 4))
    meta_text = f"<b>Case ID:</b> {case.case_id} &nbsp;|&nbsp; <b>Date:</b> {case.created_at[:10]} &nbsp;|&nbsp; <b>Status:</b> {case.status}"
    story.append(Paragraph(meta_text, body_style))
    story.append(Spacer(1, 10))

    # 1. Order & Issue
    story.append(Paragraph("1. Order & Issue Details", h2_style))
    if case.order_info:
        p_info = f"<b>Platform:</b> {case.order_info.platform} &nbsp;|&nbsp; <b>Product:</b> {case.order_info.product_name}<br/><b>Price:</b> ₹{case.order_info.price_paid} &nbsp;|&nbsp; <b>Payment Mode:</b> {case.order_info.payment_mode}"
        story.append(Paragraph(p_info, body_style))
    if case.issue:
        iss_info = f"<b>Issue:</b> {case.issue.issue_type.replace('_', ' ').title()}<br/><b>Description:</b> {case.issue.description}"
        story.append(Paragraph(iss_info, body_style))
    story.append(Spacer(1, 10))

    # 2. Rights Summary & Legal Basis
    story.append(Paragraph("2. Legal Rights & Statutory Grounds", h2_style))
    if case.generation_output:
        story.append(Paragraph(case.generation_output.rights_summary, body_style))
        story.append(Spacer(1, 6))
        for item in case.generation_output.legal_basis:
            cite_p = f"• <b>{item.claim}</b><br/>&nbsp;&nbsp;<i>{item.citation}</i> (Ref: {item.snippet_id})"
            story.append(Paragraph(cite_p, cite_style))
            story.append(Spacer(1, 3))
    else:
        story.append(Paragraph("No legal analysis generated yet.", body_style))
    story.append(Spacer(1, 10))

    # 3. Email Draft
    story.append(Paragraph("3. Draft: Seller / Platform Notice", h2_style))
    if case.generation_output and case.generation_output.draft_email:
        em = case.generation_output.draft_email
        story.append(Paragraph(f"<b>Subject:</b> {em.subject}", body_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(em.body.replace("\n", "<br/>"), body_style))
    story.append(Spacer(1, 10))

    # 4. NCH Complaint Draft
    story.append(Paragraph("4. Draft: NCH / Consumer Commission Complaint", h2_style))
    if case.generation_output and case.generation_output.draft_nch_complaint:
        nch = case.generation_output.draft_nch_complaint
        nch_text = (
            f"<b>Complainant:</b> {nch.complainant_details}<br/>"
            f"<b>Opposite Party:</b> {nch.opposite_party_details}<br/><br/>"
            f"<b>Facts:</b><br/>{nch.facts.replace('\n', '<br/>')}<br/><br/>"
            f"<b>Grounds:</b><br/>{nch.grounds.replace('\n', '<br/>')}<br/><br/>"
            f"<b>Relief Sought:</b><br/>{nch.relief_sought}<br/><br/>"
            f"<b>Verification:</b><br/><i>{nch.verification_clause}</i>"
        )
        story.append(Paragraph(nch_text, body_style))
    story.append(Spacer(1, 14))

    # Disclaimer
    disclaimer = case.generation_output.disclaimer if case.generation_output else "Informational drafting aid only. Not legal advice."
    story.append(Paragraph(f"<b>DISCLAIMER:</b> {disclaimer}", disclaimer_style))

    doc.build(story)
    return buffer.getvalue()
