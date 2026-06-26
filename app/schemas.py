from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    event_id: str | None = None
    timestamp: str | None = None
    type: str | None = None
    actor: str | None = None
    queue: str | None = None
    transaction_id: str | None = None
    amount: float | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InvestigationRequest(BaseModel):
    case_id: str
    events: list[Event]


class EvidenceItem(BaseModel):
    rule: str
    detail: str
    event_ids: list[str] = Field(default_factory=list)


class InvestigationResponse(BaseModel):
    case_id: str
    classification: str
    verdict: str
    confidence: float
    matched_transactions: list[str]
    evidence: list[EvidenceItem]
    safety_note: str
