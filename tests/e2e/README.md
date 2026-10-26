# Browser acceptance

Run the root Playwright configuration against the isolated `tasktrack_e2e` PostgreSQL database and local API/Vite servers. See the root README for fixed test-clock settings and browser installation. `mailbox.py` is a test-only helper restricted to that database: it reads encrypted verification mail and executes export worker functions without claiming SMTP/Redis coverage. Chrome/Chromium passed locally; Firefox launch remained blocked. See `docs/verification.md` for evidence and limitations.
