from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

REQUIRED_FIELDS = {
    "ticket_id",
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "severity",
    "department",
    "agent_summary",
    "recommended_next_action",
    "customer_reply",
    "human_review_required",
}

OPTIONAL_FIELDS = {"confidence", "reason_codes"}

ENUMS = {
    "evidence_verdict": {"consistent", "inconsistent", "insufficient_data"},
    "case_type": {
        "wrong_transfer",
        "payment_failed",
        "refund_request",
        "duplicate_payment",
        "merchant_settlement_delay",
        "agent_cash_in_issue",
        "phishing_or_social_engineering",
        "other",
    },
    "severity": {"low", "medium", "high", "critical"},
    "department": {
        "customer_support",
        "dispute_resolution",
        "payments_ops",
        "merchant_operations",
        "agent_operations",
        "fraud_risk",
    },
}


def assert_safe_error_response(body: dict) -> None:
    text = str(body).lower()
    assert "traceback" not in text
    assert "stack trace" not in text
    assert "internalerror" not in text
    assert "secret" not in text
    assert "token" not in text


def assert_valid_response(body: dict, ticket_id: str) -> None:
    allowed_fields = REQUIRED_FIELDS | OPTIONAL_FIELDS
    assert REQUIRED_FIELDS.issubset(body)
    assert set(body).issubset(allowed_fields)
    assert REQUIRED_FIELDS.issubset(body)
    assert isinstance(body["ticket_id"], str)
    assert body["ticket_id"] == ticket_id
    assert body["relevant_transaction_id"] != "null"
    assert body["relevant_transaction_id"] is None or isinstance(
        body["relevant_transaction_id"], str
    )
    assert isinstance(body["agent_summary"], str)
    assert isinstance(body["recommended_next_action"], str)
    assert isinstance(body["customer_reply"], str)
    assert isinstance(body["human_review_required"], bool)
    assert body["human_review_required"] not in {"true", "false"}
    assert isinstance(body.get("confidence"), (int, float))
    assert 0 <= body["confidence"] <= 1
    assert isinstance(body.get("reason_codes"), list)
    assert all(isinstance(code, str) for code in body["reason_codes"])
    for field, values in ENUMS.items():
        assert body[field] in values
    assert_safe_error_response(body)


def test_health_returns_exact_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_ticket_response_schema_with_minimal_input() -> None:
    payload = {
        "ticket_id": "TKT-MIN",
        "complaint": "Something is wrong with my money. Please check.",
    }

    response = client.post("/analyze-ticket", json=payload)

    assert response.status_code == 200
    assert_valid_response(response.json(), "TKT-MIN")


def test_response_does_not_include_debug_or_internal_fields() -> None:
    payload = {
        "ticket_id": "TKT-DEBUG",
        "complaint": "I paid 500 taka and payment failed.",
        "transaction_history": [
            {
                "transaction_id": "TXN-DEBUG",
                "timestamp": "2026-04-14T13:00:00Z",
                "type": "payment",
                "amount": 500,
                "counterparty": "MERCHANT-1",
                "status": "failed",
            }
        ],
    }

    response = client.post("/analyze-ticket", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert_valid_response(body, "TKT-DEBUG")
    assert "debug" not in body
    assert "trace" not in body
    assert "stack" not in body
