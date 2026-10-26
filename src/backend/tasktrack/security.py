import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from tasktrack.config import settings
from tasktrack.db import database, now
from tasktrack.models import Account, LoginSession

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
DB = Annotated[Session, Depends(database, scope="function")]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def check_password(password: str, hashed: str) -> bool:
    try:
        return hasher.verify(hashed, password)
    except VerificationError:
        return False


def sign(value: str) -> str:
    return hmac.new(settings().session_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def cookie(response: Response, name: str, value: str, max_age: int) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        httponly=True,
        secure=settings().secure,
        samesite="lax",
        path="/",
    )


def issue_csrf(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    cookie(response, "tasktrack_csrf", token + "." + sign(token), 86400)
    return token


def csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if origin != settings().public_origin:
        raise HTTPException(403, "Request origin is not allowed")
    raw = request.cookies.get("tasktrack_csrf", "")
    token, _, signature = raw.partition(".")
    if (
        not token
        or not hmac.compare_digest(signature, sign(token))
        or not hmac.compare_digest(token, request.headers.get("x-csrf-token", ""))
    ):
        raise HTTPException(403, "Refresh the page and try again (CSRF check failed)")


def current_session(request: Request, db: DB) -> LoginSession:
    raw = request.cookies.get("tasktrack_session", "")
    session = db.scalar(
        select(LoginSession).where(
            LoginSession.secret_hash == digest(raw), LoginSession.expires_at > now()
        )
    )
    if not session:
        raise HTTPException(401, "Log in to continue")
    return session


CurrentSession = Annotated[LoginSession, Depends(current_session)]


def current_account(session: CurrentSession, db: DB) -> Account:
    account = db.get(Account, session.account_id)
    if not account or not account.verified_at:
        raise HTTPException(401, "Log in with a verified account")
    return account


CurrentAccount = Annotated[Account, Depends(current_account)]


def new_session(db: Session, account: Account, request: Request, response: Response) -> None:
    previous = request.cookies.get("tasktrack_session")
    if previous:
        old = db.scalar(select(LoginSession).where(LoginSession.secret_hash == digest(previous)))
        if old:
            db.delete(old)
    secret = secrets.token_urlsafe(48)
    db.add(
        LoginSession(
            account_id=account.id,
            secret_hash=digest(secret),
            expires_at=now() + timedelta(hours=settings().session_hours),
            user_agent=request.headers.get("user-agent", "")[:200],
        )
    )
    cookie(response, "tasktrack_session", secret, settings().session_hours * 3600)
