import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.test_schema import assert_valid_response


client = TestClient(app)
SAMPLE_CASES = json.loads(Path("SUST_Preli_Sample_Cases.json").read_text(encoding="utf-8"))[
    "cases"
]
FUNCTIONAL_FIELDS = {
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "department",
    "severity",
    "human_review_required",
}


def test_all_official_sample_cases_pass_functionally() -> None:
    for case in SAMPLE_CASES:
        response = client.post("/analyze-ticket", json=case["input"])
        body = response.json()
        expected = case["expected_output"]

        assert response.status_code == 200, case["id"]
        assert_valid_response(body, case["input"]["ticket_id"])
        for field in FUNCTIONAL_FIELDS:
            assert body[field] == expected[field], f"{case['id']} field {field}"
