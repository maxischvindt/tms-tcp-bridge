# TMS TCP Bridge

HTTP -> TCP bridge so the HappyRobot workflow can reach the legacy TMS.

- `tms_client.py` — client for the TMS line protocol (one request per connection, CRLF-delimited, retries on `SERVER_ERROR`).
- `bridge.py` — FastAPI app exposing `POST /loads/search`, guarded by an `x-api-key` header.

## Local

```bash
uv venv
uv pip install -r requirements.txt
cp .env.example .env    # then fill in TMS_AUTH and BRIDGE_API_KEY
.venv/bin/uvicorn bridge:app --reload --port 8080
```

Smoke-test the raw TCP client without the HTTP layer:

```bash
set -a; . ./.env; set +a
.venv/bin/python tms_client.py
```

## API

```bash
KEY=$(grep BRIDGE_API_KEY .env | cut -d= -f2)

curl localhost:8080/health

curl -X POST localhost:8080/loads/search \
  -H "x-api-key: $KEY" -H 'content-type: application/json' \
  -d '{"origin":"Atlanta","destination":"Fort Worth","equipment":"FLATBED"}'
```

At least one of `origin`, `destination`, `equipment` is required (the TMS rejects an
unfiltered query). Responses are `{"loads": [...], "count": n}`; TMS-level failures
surface as `502` with the original `code`/`message`.

## Deploy (Railway)

```bash
railway login
railway init
railway variables --set TMS_HOST=tramway.proxy.rlwy.net \
                  --set TMS_PORT=17159 \
                  --set TMS_AUTH=... \
                  --set BRIDGE_API_KEY=...
railway up
railway domain
```

`railway.json` pins the start command (`$PORT` is injected by Railway) and points the
healthcheck at `/health`.
