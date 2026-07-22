# Backend (FastAPI)

This folder exposes your existing Python debugger/evaluator logic as HTTP APIs.

## Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /health` -> health check
- `POST /debug` -> run one debug session
- `POST /eval/run` -> run evaluator synchronously and return summary + results

## Example `/debug` payload

```json
{
  "code": "print(1/0)",
  "tests": null,
  "max_attempts": 3,
  "timeout": 10,
  "model": "gpt-5-mini"
}
```

