# Milestone 2 — Manual meal logging and reusable food records

**Status:** Approved 2026-11-19. You delegated the open scope decisions to me.
**Date:** 2026-11-19

## Intent

You want to open the app on your phone, read "What did you eat?", type a sentence the way you would message someone, and end up with a logged meal that carries every macro. You want an exact branded item to stay identifiable across later meals, so "those Costco nuggets" resolves to the food you already identified.

This milestone builds the food record and the logging path that feeds it. You type your sentence, pick or save the foods behind it, review the macros, and confirm. The backend computes totals with `Decimal` from values that come from a label or a future provider. AI parsing and branded web lookup arrive in Milestone 3 on the same tables.

**Success looks like:** create a food from a package label, log two foods against a free-text sentence, see calories and all macros, confirm, and see the meal in a recent list. Edit the food later and the logged meal keeps the values it had at log time. Repeat the food name or an alias and the search finds that same food. None of this needs an AI service.

## Goals

1. A reviewed Alembic revision that adds food, meal, meal item, and nutrition snapshot tables.
2. Food records with name, brand, serving, all macros, source, units, confidence, and aliases.
3. A logging flow that works with no AI service present.
4. Backend-only nutrition arithmetic using `Decimal`, with values serialized as strings to avoid float drift.
5. Confirmation in the UI before a meal reaches the database.
6. Snapshots copied into each meal item so later food edits do not rewrite history.
7. Deterministic food search by name, brand, and alias for reuse.
8. Tests for arithmetic, alias matching, snapshot immutability, and the API contract.

## Non-goals

- AI interpretation of your sentence.
- Web search, nutrition provider adapters, and brand lookup.
- Photo upload.
- Accounts, authentication, sync, and multi-user tables.
- Daily totals, charts, and insights.
- Service worker, offline caching, and deployment.

## Anti-goals

- Inventing nutrition values or letting AI supply authoritative numbers.
- Floats in nutrition calculations or storage.
- A meal saved before you confirm it.
- Editing a logged meal's snapshot when its food changes.
- Schema edits that bypass Alembic.

## Constraints

- Stack from `AGENTS.md`: React + TypeScript + Vite + Tailwind, FastAPI + Pydantic, SQLAlchemy + Alembic, SQLite.
- Python 3.12 and Node 24. `make check` must stay green.
- No new dependencies. `Decimal`, SQLAlchemy `Numeric`, and Pydantic already cover the work.
- Single-user local database. No ownership column until you choose accounts.
- Source, units, and confidence stay on every food and every snapshot.
- Natural language text is stored as you wrote it. Milestone 3 will parse it.

## Approaches considered

### A. Manual selection behind the sentence (chosen)

Keep the text prompt, then have you pick or create the foods it mentions. A saved food carries aliases, so the next search by name or alias finds the same record. The backend computes totals from label values that you enter and confirm. This gives you the logging flow and the reusable food record now, works without any AI service, and leaves Milestone 3 to automate the food picking.

### B. AI-first parsing now

Send your sentence to a provider and show its candidate foods. This matches your end goal sooner, but it needs a provider abstraction, server-side keys, and a second pass for branded lookup. Without a provider that returns the exact Costco item, the app still needs manual label entry, so this adds cost and failure modes without removing the manual path.

### C. Free text with macros later

Store only the sentence and attach macros in a later milestone. This fails your requirement to see all macros at log time.

## Decisions

| Area | Decision |
| --- | --- |
| Scope | Manual food selection and saved foods; AI parsing and web lookup in Milestone 3 |
| Ownership | Single-user local database, no `user_id` column |
| Macro set | Calories, protein, carbs, fat, fiber, sugar, sodium, each with a unit |
| Value type | `Decimal` in the backend, `Numeric(12, 4)` in SQLite, JSON strings on the wire |
| Source | `user_label` in this milestone; `provider` reserved for Milestone 3 |
| Confidence | `high` for values copied from a label, `low` for estimates; you choose at entry |
| Reuse | Normalized search over name, brand, and aliases; no fuzzy matching yet |
| Snapshot | Every logged item copies the food's nutrition, serving, source, and confidence |
| Confirmation | Frontend draft with a Confirm button; backend writes only on `POST /api/meals` |
| Dependencies | None added |

## Schema sketch

**foods**: `id`, `name`, `brand`, `serving_label`, `serving_grams`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`, `sugar_g`, `sodium_mg`, `source`, `confidence`, `aliases` as JSON text, `created_at`.

**meals**: `id`, `raw_input`, `eaten_at`, `created_at`.

**meal_items**: `id`, `meal_id`, `food_id`, `quantity`, `unit`, a snapshot of every nutrition field from the food, `source`, `confidence`, `created_at`.

The migration runs after `0001_baseline` and stays reversible. `make check-migrations` upgrades, downgrades, and re-upgrades a temporary database.

## API surface

- `POST /api/foods` creates a user-sourced food after validation.
- `GET /api/foods?q=...` searches name, brand, and aliases, returning candidates.
- `PATCH /api/foods/{food_id}` edits a saved food; logged meal snapshots stay unchanged.
- `POST /api/meals/preview` accepts the same meal payload and returns totals without writing rows, so the review step shows backend-calculated macros.
- `POST /api/meals` accepts `raw_input`, `eaten_at`, and items with `food_id`, `quantity`, and `unit`, then writes snapshots and returns the saved meal with totals.
- `GET /api/meals?limit=20` returns recent meals with items and totals.

All routes keep the `/api` prefix. Pydantic validates request and response bodies. The frontend treats returned strings as display values and never recalculates totals.

## Frontend flow

```
What did you eat?
[ two eggs and those Costco nuggets        ]
[ Add foods ]

Search foods
[ nuggets                                  ]
  Kirkland Signature Chicken Nuggets, Costco  [ Add ]
  [ + Create a food from a label ]

Review before saving
  eggs, 2 large             values from saved food
  Costco nuggets, 4 pieces  values from saved food
  Totals: calories and all macros
  [ Edit ]   [ Confirm ]
```

A saved food created from a label stores the brand and an alias such as "Costco nuggets". A later sentence containing that alias finds the same food through search.

## Test strategy

- Backend tests use in-memory SQLite and `TestClient(create_app())`.
- Arithmetic tests use `Decimal` inputs with fractional quantities and assert exact totals and per-macro values.
- Snapshot test edits a food after logging and asserts the meal item still has the original values.
- Search test creates a food with an alias and finds it by that alias with different casing.
- API tests cover validation errors, empty item lists, and the confirm boundary: an invalid meal leaves no rows.
- Frontend tests stub `fetch`, cover search, quick-create, draft review, and confirm, and keep the 390 px layout check.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Label values entered with the wrong unit | Store serving label and grams on the food, and show both in the review step |
| Food edits changing past meals | Copy values into each meal item at log time and test immutability |
| Search returning the wrong branded food | Show brand and source in results; you pick the item |
| No account ownership yet | Keep the single-user decision visible in the spec and defer user-scoped tables |
| Free-text sentence parsed too early | Store raw input unchanged and add parsing in Milestone 3 |
| Decimal values lost through JSON | Serialize as strings and parse for display only in the frontend |

## What is left to the plan

Task order, exact file paths, interface signatures, the migration content, and the commands that prove each step. The implementation plan will follow this document.
