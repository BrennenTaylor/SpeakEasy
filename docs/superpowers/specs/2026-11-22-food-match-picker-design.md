# Food Match Picker Design

Date: 2026-11-22

## Intent and why

AI interpretation currently resolves each interpreted food to a single source record before showing it. That worked until the resolver chose a plausible but wrong record: Chick-fil-A nuggets became FDC `170303` Chick-n-Strips, and Chick-fil-A mac and cheese became a Blount Seafood `MAC & CHEESE` entry. The user should choose the record, not silently inherit the resolver's first acceptable guess.

This change turns each interpreted food into a group of source-backed matches. The app ranks them, shows them with provenance, and lets the user pick before anything is saved. A future change can add remembered choices; this one does not.

## Goals

- Return every reasonable source-backed match for each interpreted food, not a hard-coded product `N`.
- Let the user select one match per food group.
- Preserve source, units, confidence, source URL, serving, and completeness for every match.
- Keep manual logging and confirmation-before-save unchanged.
- Give each match a stable ID so a later history/bias feature can refer to it.

## Non-goals

- No personal history, favorites, usage bias, or delete/forget UI in this change.
- No new database table or migration.
- No image/PDF parsing.
- No LLM-calculated nutrition or meal totals.
- No change to manual food creation, meal preview, or meal confirmation semantics.

## Anti-goals

- Hiding a good match because a fixed number of results was already found.
- Replacing a user's choice with a later ranking change.
- Showing a source record without its source URL and completeness state.
- Zero-filling missing nutrients.

## Constraints

- FastAPI + Pydantic backend, React + TypeScript frontend, `Decimal` for nutrition arithmetic.
- USDA FoodData Central and the OpenAI Responses API remain server-side only.
- Current API clients are this frontend and tests; replacing `InterpretResponse.candidates` is acceptable if tests and docs are updated.
- USDA rate limits and latency matter. Retrieval needs a bounded request, but that bound is an engineering control, not a user-facing match count.
- Current manual completion path pre-fills the create-food form for incomplete candidates; it should remain available.

## Approaches

### 1. Add a separate `matches` endpoint

Interpret first, then call a second endpoint to resolve matches. This separates concerns but adds a round trip, duplicated loading/error states, and more client state. Rejected: the extra complexity buys nothing for this flow.

### 2. Extend interpretation with a fixed top-N list

Return, for example, three matches per food. Simple, but the number is arbitrary and hides valid matches. Rejected by the user.

### 3. Extend interpretation with ranked match groups — chosen

`POST /api/meals/interpret` returns one group per interpreted food. Each group contains every match that passes identity checks, ranked. The UI initially shows a few and offers **Show more**; that display limit is not part of the API contract. This keeps one request, preserves provenance, and leaves room for later history.

## Decided design

### API shape

Replace `InterpretResponse.candidates` with `InterpretResponse.groups`.

```text
InterpretResponse {
  groups: FoodMatchGroup[]
  warnings: string[]
}

FoodMatchGroup {
  group_id: string          # "0", "1", ... in AI output order
  label: string             # AI's food label, e.g. "12 ct Chick-fil-A Nuggets"
  quantity: string          # AI's proposed servings for this food, unchanged
  matches: MatchView[]
}

MatchView {
  match_id: string          # "usda:170303" or "web:0"; stable within a group
  source_key: string | null # FDC id for USDA, null for web
  rank: int                 # 1-based order within the group
  rank_reasons: string[]    # short, human-readable signals such as "brand match"
  name: string
  brand: string
  serving_label: string
  serving_grams: string
  source: "usda_fdc" | "web_search"
  source_url: string | null
  confidence: "high" | "low"
  incomplete: boolean
  missing_fields: string[]
  calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg: string | null
}
```

Raw AI output still validates through `RawCandidate`. Nothing is written to the database by interpretation.

`MatchView.name` and `MatchView.brand` come from the source record, not from the AI candidate, so the cards are visibly distinguishable. For USDA matches that means the FDC description and brand owner/name; for the web match it means the AI-sourced web values. The group's `label` still shows what the AI thought the food was.

`match_id`, `source_key`, `rank`, and `rank_reasons` are response-only in this change. They are not persisted on `Food` or `MealItem`, and no migration is added. Saved-food provenance remains limited to the existing `source`, `source_url`, `confidence`, serving, and macro fields.

### Lookup and ranking

`resolve_candidate` becomes a multi-match resolver, for example `resolve_matches(raw, ...)`.

1. Query USDA search with a generous page size, such as 10, and the existing allowed data types. This is a retrieval/cost cap, not a product-level `N`.
2. Filter search hits with the current brand and meaningful-food-token checks. A record with a conflicting brand or no overlapping food word is not shown.
3. Fetch details for accepted FDC IDs concurrently with a small worker pool, then build one `MatchView` per usable record. USDA portions and per-100 g nutrient scaling stay authoritative for that record.
4. Include the AI/web result as a `web_search` match whenever it has a valid `http(s)` URL. Keep its values unchanged and flag missing fields; never discard it just because USDA returned something. If no valid URL exists and no USDA match survives, emit one incomplete URL-less web draft with `source_url` and any missing macros in `missing_fields`; its values are a prefill for human review, never authoritative data.
5. Deduplicate within each source: USDA by stable FDC ID, web by its group-scoped web ID. Never drop the web match because a USDA record has a similar or identical URL; cross-source duplicates stay visible as distinct provenance choices.
6. Rank all matches:
   1. identity quality among records that passed the gate;
   2. complete seven-macro records before incomplete records;
   3. source as a tiebreaker only, not a trump card;
   4. stable `match_id` tie-break so results do not shuffle.
7. Attach `rank_reasons` that explain the win, such as `brand match`, `name match`, `complete macros`, or `USDA source`.

A failed or rate-limited USDA call produces a warning and leaves the web match available. If no valid web URL exists and no USDA match survives, the group keeps one incomplete URL-less web draft for pre-filled manual completion. A group is empty only if no draft can be built at all; then the UI sends the user to manual entry.

### Frontend

`MealCandidates` becomes a grouped picker:

- Render one section per `FoodMatchGroup`.
- Show match cards as radio-style choices with source badge, brand, serving, macros, source link, completeness, and rank reasons.
- Default to the first match, but allow changing the selection per group.
- Show a small number initially and provide **Show more** to reveal the rest. The initial count is a display constant only.
- Provide one **Add selected foods** action. For each selected complete match, call `createFood` and add it to the existing meal review queue using the group's quantity.
- If the selected match is incomplete, disable direct add for that match and keep **Complete with a label**, pre-filling the create-food form from the match while retaining its `source_url`. This also covers the URL-less draft used when no source-backed match survives; its missing URL is shown and it cannot be added directly.
- Keep explicit **Find foods**, loading, error, empty, warning, and abort-on-unmount states.

### Safety and data rules

- Never invent nutrition values.
- Never let the LLM compute authoritative calories or totals.
- Preserve source, units, confidence, and `source_url` from a complete selected match into the saved food and later meal snapshot.
- If an incomplete match is completed through the label form, follow the existing rule: the saved food becomes `user_label` / `low` and retains the match's `source_url`. Completeness is response-only; it is not a new stored field.
- Missing macros remain `null` and appear in `missing_fields`.
- Manual food search and label creation continue to work when AI is unavailable.

### Tests and QA

Backend:

- Multiple ranked USDA matches plus a web match for one raw candidate.
- Mismatched brand/food records are excluded.
- Incomplete records remain selectable only through label completion.
- USDA failure still returns the web match with a warning.
- Stable IDs and deterministic ordering.
- Interpretation writes nothing.

Frontend:

- Groups render with one selected match each.
- Selection changes what **Add selected foods** creates.
- **Show more** reveals remaining matches.
- Incomplete selection opens the prefill form and does not create a food directly.
- Existing manual fallback and confirmation flow still pass.

Update `docs/qa/2026-11-20-ai-meal-interpretation.md` or add a dated follow-up QA file covering the Chick-fil-A example, multiple matches, selection behavior, provenance in saved foods, and no-write interpretation.

## What is left to the builder

- Exact retrieval page size, initially 10, and exact initial visible match count in the UI, initially 3. These are performance/display choices, not guarantees about how many valid matches exist.
- Exact wording of rank reason labels.
- Whether the old `candidates` field is removed immediately or kept as a deprecated alias; default is removal because this frontend and tests are the only consumers.

## Decided behavior for missing sources

If the AI returns a food with no valid `http(s)` source URL and USDA finds no usable match, the group keeps one incomplete, URL-less web draft. It is visibly marked as missing a source URL and opens the pre-filled label form. Its values are never treated as authoritative and it cannot be added directly.
