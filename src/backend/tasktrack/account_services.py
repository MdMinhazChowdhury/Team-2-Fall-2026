"""Administrator account-management services.

These services deliberately expose account metadata only. Administrators do not gain
access to another account's lists, tasks, tags, notifications, exports, or history.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from tasktrack.factories import AccountFactory
from tasktrack.models import Account, LoginSession


def account_data(account: Account) -> dict[str, object]:
    """Return account metadata shared by authentication and administration routes."""
    return {
        "id": account.id,
        "email": account.email,
        "role": account.role,
        "active": account.active,
        "timezone": account.timezone,
        "email_reminders": account.email_reminders,
    }


class AccountService:
    def __init__(self, db: Session, factory: AccountFactory | None = None):
        self.db = db
        self.factory = factory or AccountFactory()

    @staticmethod
    def require_admin(actor: Account) -> None:
        if actor.role != "ADMIN" or not actor.active:
            raise HTTPException(403, "Administrator access required")

    def create_account(
        self,
        actor: Account,
        email: str,
        password_hash: str,
        role: str,
        *,
        verified_at,
    ) -> Account:
        self.require_admin(actor)
        normalized = email.strip().casefold()
        if self.db.scalar(select(Account.id).where(Account.email == normalized)):
            raise HTTPException(409, "An account with this email already exists")
        account = self.factory.create(
            normalized,
            password_hash,
            role,
            verified_at=verified_at,
        )
        self.db.add(account)
        self.db.flush()
        return account

    def list_accounts(self, actor: Account) -> list[Account]:
        self.require_admin(actor)
        return list(self.db.scalars(select(Account).order_by(Account.email)))

    def set_active(self, actor: Account, account_id: str, active: bool) -> Account:
        self.require_admin(actor)
        target = self._account(account_id, lock=True)
        if target.id == actor.id and not active:
            raise HTTPException(409, "Administrators cannot disable their own account")
        if not active:
            self._protect_last_admin(target)
        target.active = active
        if not active:
            self.db.execute(delete(LoginSession).where(LoginSession.account_id == target.id))
        return target

    def delete_account(self, actor: Account, account_id: str) -> None:
        self.require_admin(actor)
        target = self._account(account_id, lock=True)
        if target.id == actor.id:
            raise HTTPException(409, "Administrators cannot delete their own account")
        self._protect_last_admin(target)
        self.db.delete(target)

    def _account(self, account_id: str, *, lock: bool = False) -> Account:
        try:
            UUID(account_id)
        except ValueError as error:
            raise HTTPException(404, "Account not found") from error
        query = select(Account).where(Account.id == account_id)
        if lock:
            query = query.with_for_update()
        account = self.db.scalar(query)
        if account is None:
            raise HTTPException(404, "Account not found")
        return account

    def _protect_last_admin(self, target: Account) -> None:
        if target.role != "ADMIN" or not target.active:
            return
        active_admins = self.db.scalar(
            select(func.count())
            .select_from(Account)
            .where(Account.role == "ADMIN", Account.active.is_(True))
        )
        if active_admins == 1:
            raise HTTPException(409, "The last active administrator cannot be removed")
