# API and integrity tests

Run `pytest tests/backend` from the root with `TASKTRACK_TEST_DATABASE_URL` explicitly pointing to disposable PostgreSQL. Shared fixtures in `tests/conftest.py` isolate each case in a temporary schema. See `docs/verification.md` and the saved JUnit XML for actual coverage and outcomes.
