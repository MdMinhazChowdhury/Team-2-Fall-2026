"""Account administration endpoints."""

from fastapi import APIRouter, Depends, Response

from tasktrack import schemas as s
from tasktrack.account_services import AccountService, account_data
from tasktrack.db import now
from tasktrack.security import DB, CurrentAdmin, csrf, hasher

router = APIRouter(prefix="/api/admin", dependencies=[Depends(csrf)])


@router.get("/accounts")
def accounts(admin: CurrentAdmin, db: DB):
    return [account_data(account) for account in AccountService(db).list_accounts(admin)]


@router.post("/accounts", status_code=201)
def create_account(data: s.AdminAccountCreate, admin: CurrentAdmin, db: DB):
    account = AccountService(db).create_account(
        admin,
        str(data.email),
        hasher.hash(data.password),
        data.role,
        verified_at=now(),
    )
    return account_data(account)


@router.patch("/accounts/{account_id}/status")
def update_status(account_id: str, data: s.AdminAccountStatus, admin: CurrentAdmin, db: DB):
    return account_data(AccountService(db).set_active(admin, account_id, data.active))


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(
    account_id: str,
    data: s.AdminAccountDeletion,
    admin: CurrentAdmin,
    db: DB,
):
    AccountService(db).delete_account(admin, account_id)
    return Response(status_code=204)
