# QueueStorm Investigator Runbook

This runbook is for judges or teammates who need to run the service from a fresh checkout.

## Local Python Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Production-compatible local start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Deployment start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Analyze a sample ticket:

```bash
curl -X POST http://127.0.0.1:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  --data @samples/sample_request.json
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Tests

```bash
pytest
```

## Benchmark

```bash
python scripts/benchmark.py
```

## Preflight

```bash
python scripts/preflight_check.py
```

The preflight script runs schema tests, sample-case tests, hidden-style tests, safety tests, the benchmark, documentation checks, sample-output checks, and a simple secret scan.

## Live Endpoint Validation

After deployment, replace the placeholder with the live base URL:

```bash
python scripts/live_validate.py --base-url https://YOUR-LIVE-URL
python scripts/benchmark_live.py --base-url https://YOUR-LIVE-URL
```

## Docker Fallback

Build:

```bash
docker build -t queuestorm-investigator .
```

Run:

```bash
docker run -p 8000:8000 queuestorm-investigator
```

Then test:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  --data @samples/sample_request.json
```

## Notes

- No real customer data is included.
- No secrets are required.
- No external LLM call is required.
- No deployment was performed in Phase 3.
- Phase 4 adds deployment-readiness tooling but still does not perform deployment without platform access.
