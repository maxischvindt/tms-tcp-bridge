"""HTTP -> TCP bridge, so the HappyRobot workflow can reach the legacy TMS.

Run: uvicorn bridge:app --host 0.0.0.0 --port 8080
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from tms_client import TMSError, send_with_retry

load_dotenv()  # no-op on Railway, where the vars come from the environment

REQUIRED = ("TMS_HOST", "TMS_PORT", "TMS_AUTH", "BRIDGE_API_KEY")
missing = [name for name in REQUIRED if not os.environ.get(name)]
if missing:
    # Bare KeyError here reads as a healthcheck timeout in the deploy logs,
    # which says nothing about the actual cause.
    raise RuntimeError(f"missing required environment variables: {', '.join(missing)}")

HOST = os.environ["TMS_HOST"]
PORT = int(os.environ["TMS_PORT"])
AUTH = os.environ["TMS_AUTH"]
API_KEY = os.environ["BRIDGE_API_KEY"]

app = FastAPI()


class LoadQuery(BaseModel):
    origin: str | None = None
    destination: str | None = None
    equipment: str | None = None

class LoadGet(BaseModel):
    id: str | None = None


# The TMS names its filters differently than the workflow-facing API does.
TMS_QUERY_FIELDS = {"origin": "orig_city", "destination": "dest_city", "equipment": "eqtype"}
TMS_GET_FIELDS = {"id": "load_id"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/loads/search")
def search_loads(body: LoadQuery, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(401, "invalid api key")
    filters = {TMS_QUERY_FIELDS[k]: v for k, v in body.model_dump(exclude_none=True).items()}
    if not filters:
        raise HTTPException(400, "at least one of origin, destination, equipment is required")
    try:
        records = send_with_retry(HOST, PORT, "LOAD_QUERY", AUTH, **filters)
    except TMSError as exc:
        raise HTTPException(502, {"code": exc.code, "message": exc.msg})
    return {"loads": records, "count": len(records)}

@app.post("/loads/get")
def get_load(body: LoadGet, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(401, "invalid api key")
    filters = {TMS_GET_FIELDS[k]: v for k, v in body.model_dump(exclude_none=True).items()}
    if not filters:
        raise HTTPException(400, "load_id is required")
    try:
        records = send_with_retry(HOST, PORT, "LOAD_GET", AUTH, **filters)
    except TMSError as exc:
        raise HTTPException(502, {"code": exc.code, "message": exc.msg})
    if not records:
        raise HTTPException(404, "load not found")
    return records[0]