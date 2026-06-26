from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.reasoning import analyze_ticket
from app.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse


app = FastAPI(
    title="QueueStorm Investigator API",
    description="Fintech SupportOps copilot API for complaint and transaction evidence review.",
    version="0.2.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request body. Check required fields and enum values."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal error while analyzing ticket."},
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "QueueStorm Investigator API",
        "status": "running",
        "health": "/health",
        "docs": "/docs",
        "analyze_ticket": "/analyze-ticket",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
def analyze_ticket_route(request: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    return analyze_ticket(request)
