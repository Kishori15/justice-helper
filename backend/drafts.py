"""
Draft templating and formatting module.
Implements ARCHITECTURE.md §2.6, §2.8 and DATA_SCHEMA.md §5.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from backend.models import CaseObject, GenerationOutput

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def get_jinja_env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)


def render_email_draft(case: CaseObject, output: GenerationOutput) -> str:
    """
    Renders the email draft using Jinja2 template.
    """
    env = get_jinja_env()
    template = env.get_template("email_draft.txt")
    return template.render(
        case_id=case.case_id,
        order_info=case.order_info,
        issue=case.issue,
        draft_email=output.draft_email,
        disclaimer=output.disclaimer
    )


def render_complaint_draft(case: CaseObject, output: GenerationOutput) -> str:
    """
    Renders the formal NCH / Consumer Commission complaint draft using Jinja2 template.
    """
    env = get_jinja_env()
    template = env.get_template("complaint_draft.txt")
    return template.render(
        case_id=case.case_id,
        order_info=case.order_info,
        issue=case.issue,
        draft_nch_complaint=output.draft_nch_complaint,
        disclaimer=output.disclaimer
    )
