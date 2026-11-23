# QA: AI interpretation timeout fix (2026-11-23)

## What changed

The OpenAI Responses call used a 10-second per-attempt read timeout with one retry. Web-search-backed responses regularly took 7–10 seconds, and some took longer, so two slow attempts produced `503 AI interpretation is unavailable`. The per-attempt timeout is now 20 seconds and the frontend waits up to 60 seconds for the whole interpretation, matching the two-attempt backend worst case plus nutrition lookup.

## Automated checks

```bash
make check
```

Expected: backend pytest 68 passed, frontend vitest 71 passed, lint, format, mypy, typecheck, migration round trip, and production build all pass.

The focused regression tests are:

```bash
cd backend && .venv/bin/pytest -q tests/test_ai_settings.py tests/test_openai_provider.py
cd frontend && npm run test -- src/api/interpretation.test.ts
```

- `test_interpreter_uses_twenty_second_default_timeout` records the timeout passed to the HTTP client; before the fix it failed with `[10.0] != [20.0]`.
- `test_ai_settings_defaults_and_env_override` pins the configured default.
- The interpretation client test asserts the browser abandons the request only after 60 seconds; before the fix it failed with `30000 != 60000`.

## Live checks (requires OpenAI and USDA keys)

1. Confirm no stale local override is forcing the old timeout:

   ```bash
   grep APP_AI_TIMEOUT_SECONDS backend/.env
   ```

   Expected: `APP_AI_TIMEOUT_SECONDS=20.0`. If it still says `10.0`, change it to `20.0` and restart the backend. The key and model lines must not be changed.

2. Start or restart both servers so the new code is loaded:

   ```bash
   make dev-backend
   make dev-frontend
   ```

3. In the browser, enter each description below, click **Find foods**, and wait for the grouped picker. Each should return match groups without an error banner:

   - `2 eggs and toast`
   - `chicken tikka masala with rice`
   - `chick fil a sandwich`

   These descriptions reproduced the 503 before the fix.

4. For one description, open the browser Network tab and check `POST /api/meals/interpret`:

   - Expected status: `200`.
   - Expected response body: an object with `groups` and `warnings`.
   - If the request is still pending after 60 seconds, the browser shows **Server did not respond**; this is a distinct failure from the 503 and should be reported with the observed duration.

5. Confirm the rest of the flow still works: select one match per group, click **Add selected foods**, review the foods in the meal, and click **Confirm**. Verify the meal appears in history with the source and macros shown in the picker.

6. Confirm the no-key path is unchanged: temporarily unset `APP_OPENAI_API_KEY`, restart the backend, and click **Find foods**.

   - Expected error: `AI interpretation is not configured` with status 503.
   - Manual food search, label entry, preview, and confirmation must still work.
   - Restore the key and restart the backend afterwards.

## If a 503 still appears

1. Check the response body in the Network tab. `AI interpretation is not configured` means the backend has no API key; `AI interpretation is unavailable` means the OpenAI request failed after both attempts.
2. Check the backend server terminal for the underlying `AIServiceError` cause. A `ReadTimeout` after 20 seconds on both attempts means the provider was slower than the configured budget; do not raise the timeout again without measuring the new latency first.
3. Check the OpenAI status page and account quota. An HTTP 429 or 5xx from the provider is not fixed by this timeout change.
4. Manual food search and logging remain available; use them while the provider is unavailable.

## Known limitations

- Live provider latency varies. The 20-second budget is based on observed 6.8–19.7 second responses with web search; it is not a guarantee.
- The frontend still shows the generic `Server responded with 503` text rather than the backend's detail message. Surfacing that detail is a separate follow-up.
- No API keys are committed or exposed to the browser.
