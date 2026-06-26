# QueueStorm Investigator

QueueStorm Investigator is a minimal FastAPI backend for reviewing structured queue and transaction event logs during a hackathon demo. It returns a preliminary investigation result that highlights queue storm patterns, transaction inconsistencies, matched transaction IDs, evidence, and a safety note for human review.

## Problem Summary

Queue-backed systems can produce confusing incident trails when failures, retries, and eventual successes happen close together. This API gives judges and operators a quick way to submit event logs and receive an explainable first-pass classification.

## Features

- Accepts structured queue and transaction event logs.
- Detects high retry volume, high failure volume, repeated events from the same queue, and mixed transaction states.
- Returns classification, verdict, confidence score, matched transactions, and evidence.
- Includes a safety warning on every investigation response.
- Exposes Swagger UI for quick testing.

## API Endpoints

- `GET /` - Basic API welcome response.
- `GET /health` - Health check endpoint.
- `POST /investigate` - Analyze submitted event logs and return a preliminary investigation result.

## Local Run Instructions

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open the API locally at:

```text
http://127.0.0.1:8000
```

## Swagger Docs

Use the interactive Swagger docs at:

```text
http://127.0.0.1:8000/docs
```

## Sample Request

A realistic queue-storm sample is available at:

```text
samples/sample_request.json
```

You can submit it to `POST /investigate` through Swagger UI or any API client.

## Safety Statement

QueueStorm Investigator provides automated preliminary analysis only. A human operator should review all evidence before taking operational, financial, or disciplinary action.

## Team Role Table

| Role | Responsibility |
| --- | --- |
| Backend/API | FastAPI routes, request/response schemas, and test coverage |
| Reasoning Logic | Rule-based investigation classifier and evidence generation |
| QA/Demo | Sample request preparation, Swagger testing, and judge walkthrough |
| Safety/Compliance | Human-review language and responsible-use checks |
