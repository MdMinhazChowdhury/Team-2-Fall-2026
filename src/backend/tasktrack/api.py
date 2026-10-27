import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select

from tasktrack import schemas as s
from tasktrack.account_services import account_data
from tasktrack.adapters import queue_mail
from tasktrack.config import settings
from tasktrack.db import now
from tasktrack.factories import AccountFactory
from tasktrack.models import Account, LoginSession, Token
from tasktrack.security import (
    DB,
    CurrentAccount,
    CurrentSession,
    check_password,
    csrf,
    digest,
    dummy_hash,
    hasher,
    issue_csrf,
    new_session,
)

router = APIRouter(prefix="/api", dependencies=[Depends(csrf)])


def queue_token(db, account, purpose):
    secret = secrets.token_urlsafe(48)
    db.add(
        Token(
            account_id=account.id,
            secret_hash=digest(secret),
            purpose=purpose,
            expires_at=now() + timedelta(hours=1),
        )
    )
    # Fragment keeps the token out of access logs and Referer headers.
    url = f"{settings().public_origin}/#{purpose}={secret}"
    queue_mail(
        db,
        account.id,
        account.email,
        "TaskTrack " + purpose,
        "Use this link within one hour:\n" + url,
    )


def consume(db, value, purpose):
    token = db.scalar(
        select(Token)
        .where(Token.secret_hash == digest(value), Token.purpose == purpose)
        .with_for_update()
    )
    if token is None or token.consumed_at or token.expires_at <= now():
        raise HTTPException(400, "This link is invalid or expired. Request a new one.")
    token.consumed_at = now()
    return db.get(Account, token.account_id)


@router.get("/auth/csrf")
def csrf_token(response: Response):
    return {"token": issue_csrf(response)}


@router.post("/auth/register", status_code=202)
def register(data: s.Registration, db: DB):
    email = str(data.email).casefold()
    account = db.scalar(select(Account).where(Account.email == email))
    if not account:
        account = AccountFactory().create(email, hasher.hash(data.password))
        db.add(account)
        db.flush()
        queue_token(db, account, "verify")
    return {
        "message": "If this address can be registered, a verification email will arrive shortly."
    }


@router.post("/auth/verify")
def verify(data: s.TokenInput, db: DB):
    account = consume(db, data.token, "verify")
    account.verified_at = now()
    return {"message": "Email verified. You can now log in."}


@router.post("/auth/verification", status_code=202)
def resend(data: s.EmailInput, db: DB):
    account = db.scalar(select(Account).where(Account.email == str(data.email).casefold()))
    if account and not account.verified_at:
        queue_token(db, account, "verify")
    return {"message": "If verification is needed, an email will arrive shortly."}


@router.post("/auth/login")
def login(data: s.Credentials, request: Request, response: Response, db: DB):
    account = db.scalar(select(Account).where(Account.email == str(data.email).casefold()))
    correct = check_password(data.password, account.password_hash if account else dummy_hash)
    if not account or not correct:
        raise HTTPException(401, "Invalid email or password")
    if not account.active:
        raise HTTPException(403, "Account is disabled")
    if not account.verified_at:
        raise HTTPException(403, "Verify your email before logging in")
    if hasher.check_needs_rehash(account.password_hash):
        account.password_hash = hasher.hash(data.password)
    new_session(db, account, request, response)
    return account_data(account)


@router.post("/auth/logout")
def logout(session: CurrentSession, response: Response, db: DB):
    db.delete(session)
    response.delete_cookie("tasktrack_session", path="/")
    return {"message": "Logged out"}


@router.post("/auth/forgot", status_code=202)
def forgot(data: s.EmailInput, db: DB):
    account = db.scalar(select(Account).where(Account.email == str(data.email).casefold()))
    if account:
        queue_token(db, account, "reset")
    return {"message": "If the account exists, a password reset email will arrive shortly."}


@router.post("/auth/reset")
def reset(data: s.Recovery, db: DB):
    account = consume(db, data.token, "reset")
    account.password_hash = hasher.hash(data.password)
    db.execute(delete(LoginSession).where(LoginSession.account_id == account.id))
    db.execute(delete(Token).where(Token.account_id == account.id))
    return {"message": "Password reset. Log in with your new password."}


@router.get("/me")
def me(account: CurrentAccount):
    return account_data(account)


@router.patch("/me")
def preferences(data: s.Preferences, account: CurrentAccount):
    account.timezone = data.timezone
    account.email_reminders = data.email_reminders
    return account_data(account)


@router.post("/me/password")
def change_password(
    data: s.PasswordChange, account: CurrentAccount, db: DB, request: Request, response: Response
):
    if not check_password(data.current_password, account.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    account.password_hash = hasher.hash(data.new_password)
    db.execute(delete(LoginSession).where(LoginSession.account_id == account.id))
    db.execute(delete(Token).where(Token.account_id == account.id))
    new_session(db, account, request, response)
    return {"message": "Password changed; other sessions revoked"}


@router.get("/me/sessions")
def sessions(account: CurrentAccount, session: CurrentSession, db: DB):
    return [
        {
            "id": item.id,
            "created_at": item.created_at,
            "expires_at": item.expires_at,
            "user_agent": item.user_agent,
            "current": item.id == session.id,
        }
        for item in db.scalars(
            select(LoginSession).where(
                LoginSession.account_id == account.id, LoginSession.expires_at > now()
            )
        )
    ]


@router.delete("/me/sessions/{session_id}")
def revoke(session_id: str, account: CurrentAccount, db: DB):
    from tasktrack.services import owned

    item = owned(db, LoginSession, session_id, account.id)
    db.delete(item)
    return {"message": "Session revoked"}


@router.delete("/me/sessions")
def revoke_all(account: CurrentAccount, response: Response, db: DB):
    db.execute(delete(LoginSession).where(LoginSession.account_id == account.id))
    response.delete_cookie("tasktrack_session", path="/")
    return {"message": "All sessions revoked"}


@router.delete("/me")
def delete_account(data: s.AccountDeletion, account: CurrentAccount, db: DB, response: Response):
    if not check_password(data.current_password, account.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    db.delete(account)
    response.delete_cookie("tasktrack_session", path="/")
    return {"message": "Account and private data deleted"}
