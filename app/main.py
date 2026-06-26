from fastapi import FastAPI

from app.reasoning import investigate_events
from app.safety import get_safety_note
from app.schemas import InvestigationRequest, InvestigationResponse


app = FastAPI(
    title="QueueStorm Investigator API",
    description="Preliminary queue and transaction event log investigation API.",
    version="0.1.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "QueueStorm Investigator API"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/investigate", response_model=InvestigationResponse)
def investigate(request: InvestigationRequest) -> InvestigationResponse:
    classification, verdict, confidence, matched_transactions, evidence = investigate_events(
        request.events
    )

    return InvestigationResponse(
        case_id=request.case_id,
        classification=classification,
        verdict=verdict,
        confidence=confidence,
        matched_transactions=matched_transactions,
        evidence=evidence,
        safety_note=get_safety_note(),
    )
