# Models

QueueStorm Investigator Phase 3 does not require any paid LLM, hosted model, GPU, or external AI service.

## Core Reasoning

The core reasoning is a deterministic Python rule engine in `app/reasoning.py`.

It handles:

- complaint classification
- transaction matching
- evidence verdicts
- department routing
- severity assignment
- human-review escalation
- confidence and reason code generation

## Safety

Final evidence and safety decisions are deterministic. The response text is passed through the sanitizer in `app/safety.py` before the API returns.

The sanitizer blocks or rewrites unsafe phrases related to:

- OTP, PIN, password, or full card number requests
- unauthorized refund promises
- unauthorized reversal or account-unblock confirmations
- suspicious personal-number contact instructions

## Optional LLM Support

There is no optional LLM integration in this phase. `.env.example` includes only placeholder names for possible future integrations. The app works fully without API keys.

## Cost and Reliability

Because the service is rule-based, local tests, benchmark, Docker fallback, and judge runs do not depend on external network calls or model availability.
