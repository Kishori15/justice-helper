"""
Pydantic data models for JusticeHelper.
Mirrors DATA_SCHEMA.md and CORPUS.md field-for-field.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Corpus Schema (CORPUS.md §3)
# ---------------------------------------------------------------------------

SourceType = Literal["act", "rule", "guideline"]

CONTROLLED_TOPICS = {
    "consumer_definition",
    "rights",
    "unfair_trade_practice",
    "deficiency_in_service",
    "redressal_mechanism",
    "ecommerce_entity_duties",
    "grievance_officer",
    "refund",
    "return_cancellation_policy",
    "complaint_timeline",
    "evidence_documentation",
    "jurisdiction_filing",
}


class CorpusEntry(BaseModel):
    id: str
    source_type: SourceType
    source_name: str
    title: str
    section_number: str
    parent_id: Optional[str] = None
    topics: List[str]
    jurisdiction: str = "India"
    url: str
    text: str
    last_verified: str

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: List[str]) -> List[str]:
        for t in v:
            if t not in CONTROLLED_TOPICS:
                raise ValueError(f"Topic '{t}' is not in controlled vocabulary: {CONTROLLED_TOPICS}")
        return v


# ---------------------------------------------------------------------------
# Case Object Components (DATA_SCHEMA.md §1)
# ---------------------------------------------------------------------------

DeliveryStatus = Literal["delivered", "not_delivered", "partially_delivered", "unknown"]
PaymentMode = Literal["upi", "card", "net_banking", "cod", "other"]
IssueType = Literal[
    "not_delivered",
    "wrong_item",
    "defective",
    "refund_not_received",
    "refund_delayed",
]
RefundType = Literal["full", "partial"]
CommunicationChannel = Literal["chat", "email", "call"]
CaseStatus = Literal[
    "intake_in_progress",
    "intake_completed",
    "issue_classified",
    "retrieved",
    "generated",
    "verified",
    "exported",
]


class BasicInfo(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class OrderInfo(BaseModel):
    platform: str
    order_id: Optional[str] = None
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_status: DeliveryStatus = "unknown"
    product_name: str
    product_category: Optional[str] = None
    price_paid: float
    payment_mode: PaymentMode = "other"
    transaction_id: Optional[str] = None

    @field_validator("price_paid")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price_paid must be non-negative")
        return v


class IssueDetails(BaseModel):
    issue_type: IssueType
    description: str
    expected_resolution: str


class CommunicationLog(BaseModel):
    date: Optional[str] = None
    channel: CommunicationChannel
    summary: str


class ActionsTaken(BaseModel):
    contacted_seller: bool = False
    contacted_platform_support: bool = False
    ticket_ids: List[str] = Field(default_factory=list)
    communication_log: List[CommunicationLog] = Field(default_factory=list)


class DesiredOutcome(BaseModel):
    refund_type: RefundType = "full"
    refund_amount: Optional[float] = None
    compensation_requested: bool = False
    compensation_amount: Optional[float] = None
    apology_requested: bool = False

    @field_validator("refund_amount", "compensation_amount")
    @classmethod
    def validate_amounts(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Amount must be non-negative")
        return v


class EvidenceAvailable(BaseModel):
    invoice: bool = False
    order_confirmation: bool = False
    payment_proof: bool = False
    chat_logs: bool = False
    product_photos: bool = False


class ConversationMessage(BaseModel):
    role: Literal["user", "system"]
    text: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Generation Output Components (DATA_SCHEMA.md §5)
# ---------------------------------------------------------------------------

class LegalBasisItem(BaseModel):
    claim: str
    citation: str
    snippet_id: str


class EmailDraft(BaseModel):
    tone: Literal["polite_first_notice", "firm_second_notice"] = "polite_first_notice"
    subject: str
    body: str


class NCHComplaintDraft(BaseModel):
    complainant_details: str
    opposite_party_details: str
    jurisdiction_note: str
    facts: str
    grounds: str
    relief_sought: str
    enclosures: List[str] = Field(default_factory=list)
    verification_clause: str


class GenerationOutput(BaseModel):
    case_id: str
    rights_summary: str
    legal_basis: List[LegalBasisItem] = Field(default_factory=list)
    draft_email: EmailDraft
    draft_nch_complaint: NCHComplaintDraft
    disclaimer: str = (
        "Draft for reference only. Please verify details and adapt to the actual NCH/e-Daakhil form before filing."
    )


# ---------------------------------------------------------------------------
# Canonical Case Object (DATA_SCHEMA.md §1)
# ---------------------------------------------------------------------------

class CaseObject(BaseModel):
    case_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: CaseStatus = "intake_in_progress"
    intake_round: int = 0

    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    order_info: Optional[OrderInfo] = None
    issue: Optional[IssueDetails] = None
    actions_taken: ActionsTaken = Field(default_factory=ActionsTaken)
    desired_outcome: DesiredOutcome = Field(default_factory=DesiredOutcome)
    evidence_available: EvidenceAvailable = Field(default_factory=EvidenceAvailable)

    conversation: List[ConversationMessage] = Field(default_factory=list)
    retrieved_passage_ids: List[str] = Field(default_factory=list)
    generation_output: Optional[GenerationOutput] = None


# ---------------------------------------------------------------------------
# Enriched Query Object (DATA_SCHEMA.md §2)
# ---------------------------------------------------------------------------

class EnrichedQuery(BaseModel):
    case_id: str
    issue_type: IssueType
    entities: Dict[str, Any] = Field(default_factory=dict)
    search_query: str
    topic_filter: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Retrieval Result (DATA_SCHEMA.md §3)
# ---------------------------------------------------------------------------

class RetrievalCandidate(BaseModel):
    id: str
    retrieval_score: float
    retrieval_source: Literal["vector", "keyword", "both"]
    text: str
    title: str
    section_number: str
    source_type: SourceType
    url: str


class RerankedCandidate(BaseModel):
    id: str
    rerank_score: float


class RetrievalResult(BaseModel):
    case_id: str
    candidates: List[RetrievalCandidate] = Field(default_factory=list)
    reranked: List[RerankedCandidate] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Evidence Checklist Object (DATA_SCHEMA.md §4)
# ---------------------------------------------------------------------------

class EvidenceChecklistItem(BaseModel):
    item: str
    how_to: str
    applies_to: List[str]
    checked: bool = False


class EvidenceChecklist(BaseModel):
    case_id: str
    checklist: List[EvidenceChecklistItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Citation Verification (DATA_SCHEMA.md §6)
# ---------------------------------------------------------------------------

class CitationVerificationFlag(BaseModel):
    claim: str
    citation: str
    issue: Literal["citation_not_in_retrieved_set", "claim_not_supported_by_snippet"]
    action: Literal["flagged_for_review", "auto_removed"] = "flagged_for_review"


class CitationVerificationResult(BaseModel):
    case_id: str
    verified: bool
    flags: List[CitationVerificationFlag] = Field(default_factory=list)
