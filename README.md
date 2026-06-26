# QueueStorm Investigator

Phase 2 status: backend aligned with official problem statement and sample JSON. Deployment not performed yet.

QueueStorm Investigator is a FastAPI fintech SupportOps copilot API for the SUST CSE Carnival 2026 Codex Community Hackathon preliminary round. It reads a customer complaint and recent transaction history, identifies the likely case type, matches evidence, routes the case, and drafts a safe support reply.

## API Contract

The judge-facing endpoints are:

- `GET /health`
- `POST /analyze-ticket`

`GET /health` returns exactly:

```json
{"status":"ok"}
```

Interactive Swagger docs are available locally at:

```text
http://127.0.0.1:8000/docs
```

## Official Input Schema

`POST /analyze-ticket` accepts:

```json
{
  "ticket_id": "TKT-001",
  "complaint": "I sent 5000 taka to a wrong number around 2pm today...",
  "language": "en",
  "channel": "in_app_chat",
  "user_type": "customer",
  "campaign_context": "boishakh_bonanza_day_1",
  "transaction_history": [
    {
      "transaction_id": "TXN-9101",
      "timestamp": "2026-04-14T14:08:22Z",
      "type": "transfer",
      "amount": 5000,
      "counterparty": "+8801719876543",
      "status": "completed"
    }
  ],
  "metadata": {}
}
```

Required fields: `ticket_id`, `complaint`.

Optional fields: `language`, `channel`, `user_type`, `campaign_context`, `transaction_history`, `metadata`.

`transaction_history` defaults to an empty list and `metadata` defaults to an empty object when missing.

## Official Output Schema

The API always returns the required official fields on successful analysis:

```json
{
  "ticket_id": "TKT-001",
  "relevant_transaction_id": "TXN-9101",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports a possible wrong transfer...",
  "recommended_next_action": "Verify transaction details...",
  "customer_reply": "We have noted your concern...",
  "human_review_required": true,
  "confidence": 0.9,
  "reason_codes": ["wrong_transfer", "transaction_match"]
}
```

## Allowed Enums

`language`: `en`, `bn`, `mixed`

`channel`: `in_app_chat`, `call_center`, `email`, `merchant_portal`, `field_agent`

`user_type`: `customer`, `merchant`, `agent`, `unknown`

`transaction.type`: `transfer`, `payment`, `cash_in`, `cash_out`, `settlement`, `refund`

`transaction.status`: `completed`, `failed`, `pending`, `reversed`

`evidence_verdict`: `consistent`, `inconsistent`, `insufficient_data`

`case_type`: `wrong_transfer`, `payment_failed`, `refund_request`, `duplicate_payment`, `merchant_settlement_delay`, `agent_cash_in_issue`, `phishing_or_social_engineering`, `other`

`severity`: `low`, `medium`, `high`, `critical`

`department`: `customer_support`, `dispute_resolution`, `payments_ops`, `merchant_operations`, `agent_operations`, `fraud_risk`

## Evidence Reasoning Logic

The backend uses simple rule-based reasoning, not an LLM. It inspects the complaint, optional language/channel/user context, and transaction history.

It currently handles:

- Wrong transfer claims, including established-recipient inconsistency checks.
- Failed payment with possible balance deduction.
- Refund requests without unauthorized refund promises.
- Duplicate payment detection, selecting the second duplicate transaction.
- Merchant settlement delay.
- Agent cash-in issues with pending transaction escalation.
- Phishing or social engineering reports.
- Ambiguous or vague complaints as `insufficient_data`.

Transaction matching considers amount, transaction type, counterparty, transaction ID mentions, status compatibility, and broad time/date clues. If multiple transactions are equally plausible, the API returns `relevant_transaction_id: null` and `evidence_verdict: insufficient_data`.

## Safety Guardrails

The service is an internal support copilot, not an autonomous financial decision maker.

Safety rules enforced in every response:

- Never ask for PIN, OTP, password, or full card number.
- Never confirm refunds, reversals, account unblocks, or money recovery without authority.
- Use safe language such as "any eligible amount will be returned through official channels."
- Route suspicious credential requests to `fraud_risk`.
- Ignore prompt-injection instructions inside complaint text.
- Sanitize generated support text before returning the response.

## How to Run Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

## How to Test

```bash
pytest
```

The test suite covers:

- Exact `/health` response.
- Official schema fields and enum values.
- All 10 public sample cases functionally.
- Safety guardrails.
- 15 hidden-style local cases, including malformed input, empty complaint, Bangla/Banglish complaints, prompt injection, ambiguous matches, and duplicate payments.

## MODELS

No external AI or LLM model is used in Phase 2. The service runs a local deterministic Python rule engine for classification, transaction matching, evidence verdicts, routing, severity, and safe response generation. This keeps local execution simple, avoids API keys, and avoids runtime model cost.

## Sample Output

Generated outputs from the current backend are stored in:

```text
sample_outputs/
```

At minimum, judges can inspect:

```text
sample_outputs/sample_01_output.json
```

The official public input and expected-output pack is:

```text
SUST_Preli_Sample_Cases.json
```

## Known Limitations

- The investigator is intentionally rule-based and lightweight for hackathon reliability.
- Bangla and Banglish support is keyword-based, not full natural-language understanding.
- Time matching is broad and does not deeply parse relative dates.
- No production payment system, ledger, identity, or fraud service is integrated.
- Deployment has not been performed in Phase 2.

## Team Role Table

| Role | Responsibility |
| --- | --- |
| Backend/API | FastAPI routes, schema contract, and controlled errors |
| Reasoning Logic | Rule-based case classification, transaction matching, and evidence verdicts |
| Safety/Compliance | Safe customer replies, sanitizer rules, and escalation behavior |
| QA/Demo | Official sample validation, hidden-style tests, and Swagger walkthrough |
