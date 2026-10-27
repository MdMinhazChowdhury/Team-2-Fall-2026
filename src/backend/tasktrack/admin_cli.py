"""Local management command for promoting the first administrator."""

import argparse

from sqlalchemy import select

from tasktrack.db import SessionLocal
from tasktrack.models import Account


def promote(email: str) -> str:
    normalized = email.strip().casefold()
    with SessionLocal.begin() as db:
        account = db.scalar(select(Account).where(Account.email == normalized).with_for_update())
        if account is None:
            raise SystemExit(f"No account exists for {normalized}")
        account.role = "ADMIN"
        account.active = True
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="TaskTrack account administration")
    subcommands = parser.add_subparsers(dest="command", required=True)
    promote_command = subcommands.add_parser("promote", help="Promote an existing account")
    promote_command.add_argument("email")
    args = parser.parse_args()
    if args.command == "promote":
        print(f"Promoted {promote(args.email)} to ADMIN")


if __name__ == "__main__":
    main()
