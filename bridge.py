"""HTTP -> TCP bridge, so the HappyRobot workflow can reach the legacy TMS.

Run: uvicorn bridge:app --host 0.0.0.0 --port 8080
"""

import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, BeforeValidator

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


def _upper(value):
    """The TMS matches LOAD_ID and EQTYPE case-sensitively; cities it does not."""
    return value.upper() if isinstance(value, str) else value


Upper = Annotated[str, BeforeValidator(_upper)]


class LoadQuery(BaseModel):
    origin: str | None = None
    destination: str | None = None
    equipment: Upper | None = None

class LoadGet(BaseModel):
    id: Upper | None = None

class LoadBook(BaseModel):
    id: Upper | None = None
    mc_num: str | None = None
    agreed_rate: int | None = None


# The TMS names its filters differently than the workflow-facing API does.
TMS_QUERY_FIELDS = {"origin": "orig_city", "destination": "dest_city", "equipment": "eqtype"}
TMS_GET_FIELDS = {"id": "load_id"}
TMS_BOOK_FIELDS = {"id": "load_id", "mc_num": "mc_num", "agreed_rate": "agreed_rate"}


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

@app.post("/loads/book")
def book_load(body: LoadBook, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(401, "invalid api key")
    filters = {TMS_BOOK_FIELDS[k]: v for k, v in body.model_dump(exclude_none=True).items()}
    if not filters:
        raise HTTPException(400, "load_id, mc_num and agreed_rate are required")
    try:
        records = send_with_retry(HOST, PORT, "LOAD_BOOK", AUTH, **filters)
    except TMSError as exc:
        raise HTTPException(502, {"code": exc.code, "message": exc.msg})
    if not records:
        raise HTTPException(404, "load not found")
    return records[0]