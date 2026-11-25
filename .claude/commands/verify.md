Run in order and report pass/fail for each, fixing failures before reporting:
1. cd backend && ruff check . && mypy app && pytest -q
2. cd frontend && npm run lint && npm test -- --run && npm run build
3. grep the backend for any repository function missing a business_id parameter and report it.
4. grep for hard-coded secrets (API keys, passwords, DATABASE_URL literals).
