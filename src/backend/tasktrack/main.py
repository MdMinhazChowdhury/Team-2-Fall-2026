import asyncio
import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import case, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException

from tasktrack.admin_api import router as admin
from tasktrack.api import router as accounts
from tasktrack.config import settings
from tasktrack.db import SessionLocal
from tasktrack.extras_api import router as extras
from tasktrack.models import RateBucket
from tasktrack.security import sign
from tasktrack.task_api import router as tasks

logger = logging.getLogger("tasktrack")
logging.basicConfig(level=logging.INFO, format="%(message)s")
app = FastAPI(
    title="TaskTrack API", version="0.1.0", docs_url=None if settings().secure else "/api/docs"
)
app.include_router(accounts)
app.include_router(admin)
app.include_router(tasks)
app.include_router(extras)


def rate_limit(key: str):
    window = int(time.time()) // 60
    with SessionLocal.begin() as db:
        statement = insert(RateBucket).values(key=key, window=window, count=1)
        returning = statement.on_conflict_do_update(
            index_elements=[RateBucket.key],
            set_={
                "window": window,
                "count": case((RateBucket.window == window, RateBucket.count + 1), else_=1),
            },
        ).returning(RateBucket.count)
        count = db.scalar(returning)
        return count is not None and count <= settings().rate_limit


def finish(response, request_id, started, method):
    response.headers.update(
        {
            "X-Request-ID": request_id,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; object-src 'none'",
        }
    )
    if settings().secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    logger.info(
        json.dumps(
            {
                "event": "request",
                "request_id": request_id,
                "method": method,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
    )
    return response


@app.middleware("http")
async def request_boundary(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    started = time.monotonic()
    try:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 2 * 1024 * 1024:
                    return finish(
                        JSONResponse(
                            {"detail": "Request exceeds the 2 MiB limit", "request_id": request_id},
                            status_code=413,
                        ),
                        request_id,
                        started,
                        request.method,
                    )
            request._body = bytes(body)
        if request.url.path.startswith("/api/auth/") and request.method == "POST":
            address = request.client.host if request.client else "unknown"
            # Proxy headers must be trusted only from the configured reverse proxy.
            if not await asyncio.to_thread(rate_limit, sign(address)):
                return finish(
                    JSONResponse(
                        {"detail": "Too many attempts. Wait one minute.", "request_id": request_id},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    ),
                    request_id,
                    started,
                    request.method,
                )
        response = await call_next(request)
    except Exception:
        logger.error(json.dumps({"event": "request_failed", "request_id": request_id}))
        response = JSONResponse(
            {
                "detail": "The service is temporarily unavailable. Try again.",
                "request_id": request_id,
            },
            status_code=503,
        )
    return finish(response, request_id, started, request.method)


@app.exception_handler(RequestValidationError)
async def invalid(request: Request, exception: RequestValidationError):
    fields = [
        {"field": ".".join(str(v) for v in item["loc"][1:]), "message": item["msg"]}
        for item in exception.errors()
    ]
    return JSONResponse(
        {
            "detail": "Check the highlighted input fields",
            "fields": fields,
            "request_id": request.state.request_id,
        },
        status_code=422,
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exception: HTTPException):
    return JSONResponse(
        {"detail": exception.detail, "request_id": request.state.request_id},
        status_code=exception.status_code,
        headers=exception.headers,
    )


@app.exception_handler(IntegrityError)
async def conflict(request: Request, exception: IntegrityError):
    return JSONResponse(
        {
            "detail": "This change conflicts with existing data. Refresh and try again.",
            "request_id": request.state.request_id,
        },
        status_code=409,
    )


@app.exception_handler(SQLAlchemyError)
async def storage_error(request: Request, exception: SQLAlchemyError):
    return JSONResponse(
        {
            "detail": "Storage is unavailable. Your change could not be confirmed. Try again.",
            "request_id": request.state.request_id,
        },
        status_code=503,
    )


@app.get("/api/health/live")
def live():
    return {"status": "ok"}


@app.get("/api/health/ready")
def ready():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready"}
