# Deployment Guide

QueueStorm Investigator is deployment-ready as a FastAPI/Uvicorn service. Do not commit platform secrets or real customer data.

## Live Base URL

Placeholder:

```text
https://YOUR-LIVE-URL
```

After deployment, judges should be able to call the endpoints without authentication.

## Endpoints

- `GET /health`
- `POST /analyze-ticket`

## Production Start Command

Recommended deployment command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If the platform does not provide `PORT`, use:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Local Run Command

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
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

Use a platform-provided port:

```bash
docker run -e PORT=8000 -p 8000:8000 queuestorm-investigator
```

The Docker image binds Uvicorn to `0.0.0.0`, does not require GPU, does not download large models, and does not include secrets.

## Environment Variables

Required:

```text
PORT
```

`PORT` is usually provided automatically by Render, Railway, Fly, Poridhi VM, or similar platforms. If missing, use `8000`.

No paid LLM secret is required. The core system is deterministic and rule-based.

## Health Check

Local:

```bash
curl http://127.0.0.1:8000/health
```

Live:

```bash
curl https://YOUR-LIVE-URL/health
```

Expected exact response:

```json
{"status":"ok"}
```

## Sample POST

Local:

```bash
curl -X POST http://127.0.0.1:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  --data @samples/sample_request.json
```

Live:

```bash
curl -X POST https://YOUR-LIVE-URL/analyze-ticket \
  -H "Content-Type: application/json" \
  --data @samples/sample_request.json
```

## Live Validation

After deployment:

```bash
python scripts/live_validate.py --base-url https://YOUR-LIVE-URL
python scripts/benchmark_live.py --base-url https://YOUR-LIVE-URL
```

The validation script checks health, all 10 public sample cases, schema/enums, safety text, malformed input handling, and a prompt-injection safety case.

## Troubleshooting

- If `/health` fails, confirm the platform start command uses `uvicorn app.main:app`.
- If the app starts but is unreachable, confirm the host is `0.0.0.0`, not `127.0.0.1`.
- If the platform assigns a port, use `$PORT`.
- If `POST /analyze-ticket` returns 422, validate that `ticket_id` and `complaint` are present and transaction enum values match the official schema.
- If live validation reports unsafe text, do not deploy further until safety tests pass locally.
- If Docker is used, verify `docker run -p 8000:8000 queuestorm-investigator` and then test `/health`.
