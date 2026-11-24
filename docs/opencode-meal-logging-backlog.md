# CalorieApp product backlog for OpenCode

**Product outcome.** On a phone, describe or photograph a meal, answer a short question when needed, review sourced calories, and log it. See today's intake against a chosen goal. At the end of a week or month, see which recurring choices contributed most and what a realistic change would do.

**Starting point.** At `c634356` the repo already has a React meal logger, FastAPI food and meal endpoints, Alembic migrations, Decimal totals, immutable meal nutrition snapshots, manual label entry, AI text interpretation, USDA lookup, a match picker, tests, CI configuration, and QA runbooks. Build on those paths. This handoff assumes a personal, single-user app. Deployment in the last milestone is a private deployment proposal.

| Tasks | Milestone | What you can do when it passes |
| --- | --- | --- |
| 1–8 | Trust the log | Confirm the quantity you reviewed and recover from retries without duplicating meals. |
| 9–16 | Daily tracker | Use the app every day with manual entry, a calorie target, corrections, and history. |
| 17–23 | Conversational entry | Resolve a mixed meal, answer a focused question, and reuse familiar foods. |
| 24–27 | Recipes | Save a sourced batch recipe and log the share you actually ate. |
| 28–32 | Photos | Capture a plate or label, correct the interpretation, and confirm a meal. |
| 33–39 | Reports and insights | Understand weekly and monthly calories, nutrition coverage, and possible changes. |
| 40–44 | Phone and release | Install the app, recover drafts, restore a backup, and run a private release. |

## Prompt to start a session

> Read AGENTS.md and docs/opencode-meal-logging-backlog.md. Pick the first unchecked task unless I name another. Inspect the implementation and existing tests, and identify what is already done. Give a short plan, implement that task only, and test its acceptance example. Use deterministic fixtures for provider calls. Run relevant tests and make check. Add dated manual QA under docs/qa/ and link it in the summary. Report files changed, actual results, and any blocked verification. Mark the task complete after its acceptance criteria pass, then stop for review.

## Milestone 1 · Trust the log

### [ ] 1. Confirm only the quantity the user reviewed

**Reproduce.** Add one serving of a saved food, wait for totals, change the quantity to two, and tap Confirm while the second preview is still pending. The current UI can show the one-serving total and post two servings.

**Start in** `frontend/src/components/MealLogger.tsx`, `MealReview.tsx`, and `MealLogger.test.tsx` in the same directory.

**Accept when**

- Editing quantity, adding a food, or removing a food immediately invalidates the previous totals. Confirm stays disabled until the backend returns totals for the current items.
- A late response from an older preview cannot re-enable Confirm. A failed preview leaves the draft editable and unsaved.
- A component test holds the new preview open, attempts confirmation, verifies zero meal creation requests, then releases it and verifies the saved quantity.

### [ ] 2. Preserve the amount eaten when switching source records

**Reproduce.** Use a fixture for “I ate 100 g.” Offer two records of the same food at the same energy per gram. One defines a serving as 50 g and the other as 100 g. Today the USDA resolver can replace the serving basis while the picker keeps the original serving count.

**Start in** `backend/app/services/nutrition_lookup.py`, `backend/app/services/interpretation.py`, the interpretation schemas on both sides, and `frontend/src/components/MealCandidates.tsx`. Revisit the match-picker design's instruction to keep the group quantity unchanged. Existing tests assert that behavior.

**Accept when**

- The 50 g option proposes two servings and the 100 g option proposes one. Test both paths through preview, save, and history. The amount and calorie total agree across records.
- Conversion uses backend Decimal arithmetic and a known amount eaten. A model-suggested weight for “one bowl” is insufficient evidence for a gram conversion. When the basis is unknown, show the selected record's serving label and ask how much the user ate.
- The user can correct the quantity before confirming. Existing manual entries and historical snapshots continue to work.

### [ ] 3. Keep web nutrition unverified until its values are checked

**Reproduce.** Stub the interpreter with all seven nutrient values and a syntactically valid URL that does not support them. The current web fallback can mark this candidate complete and let the user save its numbers.

**Start in** `backend/app/services/nutrition_lookup.py` (`_web_view`), `frontend/src/components/MealCandidates.tsx`, and the label-entry flow in `FoodSearch.tsx`.

**Accept when**

- The unverified candidate can help identify the food and link to the source. Its numbers cannot enter a saved food through **Add selected foods** solely because the fields are populated.
- For this task, use the existing label-entry path for user verification. The user can enter or correct values, see the serving basis, and explicitly verify the label. Missing data stays missing. The saved record and meal snapshot retain accurate provenance and confidence.
- Cover an unsupported URL claim, a verified label, and a complete USDA result with deterministic fixtures. Direct manual logging still works with AI unavailable.

### [ ] 4. Carry quantity through “Complete with a label”

**Reproduce.** Interpret 2.5 servings of a food. Select an incomplete match, complete its label, and add it to the review. The form currently calls `onAdd(saved)`, which defaults to one serving.

**Start in** `frontend/src/components/MealCandidates.tsx`, `MealLogger.tsx`, and `FoodSearch.tsx`. Build on the serving-basis decision from task 2.

**Accept when**

- Completing missing nutrients with the same serving basis preserves 2.5 servings through review, preview, and save. Changing the serving basis follows task 2's conversion or clarification behavior.
- Canceling label completion adds nothing. Starting a fresh manual food afterward uses the normal manual quantity. Completing one candidate never transfers its quantity to another.
- Extend the existing label-prefill component test through the meal creation request. Checking the food creation payload alone misses this bug.

### [ ] 5. Enforce the stored precision at the API boundary

Meal quantities currently accept more decimal places than the snapshot column stores. Pick a documented Decimal precision policy consistent with storage. **Pass:** a fractional quantity at the supported boundary gives identical preview, POST, and history totals. An unsupported quantity, zero serving weight, or explicit null for a required food field yields a clear validation error before any write. Cover create and patch.

### [ ] 6. Make meal confirmation safe to retry

Give one confirmation attempt a stable client-generated identifier and enforce uniqueness on the server. **Pass:** simulate a successful commit followed by a lost response. Retrying saves one meal and returns its original ID. Concurrent duplicates have the same outcome. An intentional second meal can still be logged. Test reusing the identifier with different content.

### [ ] 7. Discard suggestions for an obsolete description

Bind interpretation results to the draft that requested them. **Pass:** start a slow search for rice, change the text to chicken, then finish the rice request. Rice cannot be added as a suggestion for the chicken draft. A failed second search preserves manually reviewed items.

### [ ] 8. Keep a partial match-picker retry from duplicating foods

Extend the existing in-session retry coverage to a lost food-creation response. Use a stable source record ID where available and keep distinct serving definitions separate. **Pass:** simulate two selected foods, one response lost after persistence, then retry. The library has one copy of each source record and the review contains the user's intended quantities. Two intentionally added portions still work.

## Milestone 2 · Daily tracker

### [ ] 9. Support calories when secondary nutrients are unknown

Let a user log a sourced calorie value and serving amount even when the label omits sugar or fiber. Update schemas, storage, preview, and snapshot reads together with an explicit migration. **Pass:** a known zero survives as zero, an omitted value survives as unknown, and a mixed meal shows complete calories plus the appropriate nutrient coverage. Existing complete records round-trip unchanged.

### [ ] 10. Assign meals to the correct local day

Add a user-selectable logging time and a defined tracking timezone. Document how existing timestamps are interpreted. **Pass:** log yesterday's dinner after midnight. It appears on yesterday's date. Test the local midnight boundary, a daylight-saving transition, and an existing database fixture.

### [ ] 11. Build the daily diary and total

Add a date-scoped meal query and backend daily total over confirmed snapshots. Make the diary the phone landing view with an obvious add-meal action. **Pass:** previous/next day works, an empty day says no meals logged, adding a meal updates the total once, and a day with more than 20 meals includes every meal in the total.

### [ ] 12. Set a daily calorie goal

Allow a user-entered target with an effective local date. Show consumed and remaining calories in the diary. **Pass:** a day with no goal still works, exceeding a target displays the excess clearly, and changing tomorrow's goal leaves historical comparisons intact. Test invalid targets and changes on the same date.

### [ ] 13. Inspect a saved meal

Open a diary entry to see food names, amounts eaten, serving definitions, item calories, source, confidence, and the meal total. Snapshot any missing historical display fields with a migration and a truthful fallback for legacy rows. **Pass:** renaming a library food preserves the displayed identity of newly logged items. Entries predating the migration still open.

### [ ] 14. Correct a logged meal

Support editing time, quantities, and included foods with a new preview and explicit save. Use existing item snapshots for retained items. **Pass:** changing a historical quantity after its library food has been edited uses the historical nutrition. Moving the meal across midnight updates both days. Cancel preserves the original.

### [ ] 15. Remove a mistaken entry and undo it

Implement reversible removal from the diary. **Pass:** cancel leaves the entry visible, confirmed removal updates totals, undo restores the same meal and snapshot exactly once, and a reload respects its current state. Exercise only disposable test data in QA.

### [ ] 16. Repeat a frequent meal

Add a repeat action to meal history. Open an editable new draft with the previous foods and portions. **Pass:** repeat yesterday's rice and peas, change only the rice, and confirm today. The original meal stays intact. Cancel creates no entry. The flow works without AI.

## Milestone 3 · Conversational entry

### [ ] 17. Reuse previously verified foods in suggestions

Resolve saved names and aliases before calling external sources for the same identity. Show the serving basis alongside the name. **Pass:** a saved alias retrieves the verified food with provider calls disabled. Two plausible saved matches are offered for selection. Adding a saved match reuses its food ID.

### [ ] 18. Account for every item in a mixed meal

The current interpreter caps candidates at four. Surface any unprocessed remainder and let the user continue or dismiss it. **Pass:** a five-item fixture accounts for all five across review and unresolved items. Removing one suggestion leaves the other four intact and does not re-add it on confirmation.

### [ ] 19. Ask focused portion and identity questions

Keep a draft with resolved and unresolved items. Ask for the specific missing fact and apply the answer to that item only. **Pass:** for “rice, peas, and some butter,” preserve the resolved rice and peas while asking about butter. Support correcting an answer, manual entry, or explicitly skipping that item. Never save on reply alone.

### [ ] 20. Recognize household measures and fractions

Parse common inputs such as “2/3 cup cooked rice,” “½ cup peas,” and “4 pieces.” Extend task 2 with food-specific household measures from a source. **Pass:** equivalent fractional inputs yield the same Decimal result, cooked and dry records stay distinct, and an unsupported cup-to-gram conversion routes to a question.

### [ ] 21. Resolve branded and restaurant foods against reliable sources

Introduce a bounded adapter for one chosen official menu or structured manufacturer source. Keep identity, size, preparation, serving basis, and evidence together. **Pass:** a small and a large menu item remain distinct. A request for “no mayo” with no sourced adjustment prompts for review. A provider outage offers the existing fallback. Use a captured fixture.

### [ ] 22. Limit repeated external lookups

Add caching at the provider adapter with a documented expiry and bounded retry behavior. **Pass:** repeated equivalent lookups reuse a fresh result, differing brands or portions cannot collide, expired entries refresh, and rate limits yield a usable manual path. Keep API keys out of cache keys shown to users and out of logs.

### [ ] 23. Test familiar meals from description through history

Build a deterministic regression set around rice with peas and butter, nuggets with fries, a branded drink, and a multi-item order with a missing size. **Pass:** tests check source, consumed quantity, clarification, and final snapshot totals. Use explicitly labeled test data or captured source records. Run without provider keys.

## Milestone 4 · Recipes

### [ ] 24. Create a recipe from confirmed ingredients

Resolve recipe text into an editable ingredient list using the existing match and clarification flow. **Pass:** a pasta recipe preserves each confirmed ingredient and source. An unresolved amount is visible, removing an ingredient updates the batch preview, and cancel creates no recipe.

### [ ] 25. Record batch yield and calculate portions

Support a yield in servings or measured finished weight. Compute batch and per-portion nutrition on the backend. **Pass:** a four-serving recipe logs one quarter of batch calories for one serving. Logging 150 g of a 600 g finished batch gives the same result. A missing or zero yield cannot produce a portion total.

### [ ] 26. Save and revise reusable recipes

Persist confirmed ingredients, source snapshots, yield, and a recipe revision. **Pass:** a saved recipe reopens after restart. Changing an ingredient creates an identifiable revision. A later food-library edit cannot silently change the saved recipe's nutrition.

### [ ] 27. Log a recipe alongside other foods

Make a recipe portion selectable in the normal meal review. **Pass:** log 1.5 portions plus a separate drink and compare preview to saved history. Editing the recipe later leaves the earlier meal unchanged. Repeat the meal with AI unavailable.

## Milestone 5 · Photos

### [ ] 28. Capture or choose an image on a phone

Add camera/file selection, local preview, replace, cancel, and a backend upload boundary. Document supported formats, size limit, and retention. Default to temporary processing. **Pass:** accept a supported image, reject an invalid or oversized file clearly, and preserve typed meal text after cancel or upload failure.

### [ ] 29. Extract a nutrition label for review

Add image input behind the AI abstraction and return editable label fields with serving basis and units. **Pass:** a fixture with per-serving and per-package columns keeps each value with its header. An unreadable digit stays unknown. The user verifies values before creating a food.

### [ ] 30. Identify foods in a plate photo

Return possible food identities and unresolved quantities through the existing picker. **Pass:** a rice-and-chicken fixture yields editable candidates, asks for uncertain portions, and obtains nutrition through the existing source lookup. A failed interpretation permits manual logging.

### [ ] 31. Combine text and photo in one draft

Let a caption resolve image ambiguity and let the user merge or reject duplicate candidates. **Pass:** “two-thirds cup cooked rice” plus a photo of the same rice produces one review item. A caption adding a drink produces a second item. Neither input commits a meal.

### [ ] 32. Verify the photo path on a real phone

Exercise capture, orientation, replacement, interrupted upload, and a return from the camera app in the target mobile browser. **Pass:** one confirmed meal appears after a retry, canceled images follow the documented retention policy, and failures leave text/manual entry usable. Record device, browser, and results in QA.

## Milestone 6 · Reports and insights

### [ ] 33. Track whether a day was fully logged

Add an explicit day-complete control and expose coverage in the diary and report queries. **Pass:** a partial day, a day with no entries, and an explicitly completed day remain distinguishable. Reopening a day updates coverage. Report averages state their denominator.

### [ ] 34. Build the weekly calorie report

Aggregate confirmed snapshots by local calendar week. Show daily totals, applicable targets, period total, average for completed days, and data coverage. **Pass:** a seven-day fixture with missing days and a midweek target change reconciles exactly to the diary. Empty and partially logged weeks have clear states.

### [ ] 35. Build the monthly calorie report

Reuse the reporting arithmetic for calendar months. **Pass:** February, leap February, a 31-day month, and the current partial month have correct boundaries. The report distinguishes month-to-date from a complete month and can open the underlying diary days.

### [ ] 36. Identify recurring calorie contributors

Group foods and repeat meals using stable identities and historical amounts. Rank by total contribution and expose frequency and typical logged portion. **Pass:** a frequent small addition and a single large meal show their distinct effects. Each reported contribution drills down to the entries behind it.

### [ ] 37. Add secondary nutrient summaries

Show protein, carbohydrate, fat, fiber, sugar, and sodium with units and coverage for the chosen period. **Pass:** adding one entry with unknown fiber preserves calorie accuracy and marks the fiber result as partial. Color and labels reflect the user's stated goal without treating a high carbohydrate share as automatically favorable.

### [ ] 38. Generate actionable changes grounded in logged foods

Offer one or two changes using familiar meals, logged portions, and sourced alternatives. Calculate scenario differences with backend Decimal operations. **Pass:** a suggested smaller portion identifies the original entries, frequency assumption, and reproducible calorie difference. Sparse data yields a coverage message. Optional AI wording cannot change the numbers or provide insulin advice.

### [ ] 39. Browse reports and apply goal changes

Provide week/month navigation, contributor drill-down, and an explicit action to edit a future goal. **Pass:** reopening a historical period reproduces its figures, corrections refresh affected periods, and viewing a suggestion never changes a goal. Verify the full flow at phone width.

## Milestone 7 · Phone and release

### [ ] 40. Finish the installable mobile shell

Extend the existing manifest with install assets and a working app-shell cache. Prioritize diary, log, and reports in navigation. **Pass:** install and launch on the target phone, open each main view, and load the shell after loss of connectivity. Show an offline state for unavailable server data.

### [ ] 41. Recover an interrupted draft

Persist pending draft text, reviewed items, quantities, and clarification progress locally with a clear discard action. **Pass:** reload halfway through logging or regain connectivity after a failed save. The draft is recoverable and an explicit retry creates at most one meal using task 6. Document whether temporary photos require reselection.

### [ ] 42. Export and restore personal data

Provide a versioned export and a restore path into a fresh database. Include foods, recipes, effective goals, meals, snapshots, and day coverage. **Pass:** a round trip preserves IDs or documented mappings, exact Decimal values, and report totals. Invalid imports fail atomically. Test against temporary databases.

### [ ] 43. Document and verify a private deployment

Choose a personal deployment target, configure persistent storage, server-only secrets, access control for remote use, explicit migrations, and backups. **Pass:** a fresh install works from the documented commands, restarts retain meals, and the phone can log with AI disabled. Test recovery on a separate instance. Provisioning a paid or public service is a separate user decision.

### [ ] 44. Run the release acceptance journey

Use a disposable account or database and a real phone. Log a manual meal, a clarified text meal, a recipe, and a photo meal. Correct yesterday's dinner, retry one interrupted save, and inspect both reporting periods. **Pass:** independently reconcile diary and report totals to saved snapshots, check keyboard navigation and accessible labels, run `make check`, and record any remaining failures before release.

## Running the checks

Use the repository's documented Python 3.12 and Node 24 environment. From a configured checkout, run the relevant focused tests first. From the repository root, run `make check` before marking a task done. It includes lint, both type-checks, tests, migration checks, and the frontend build. Use a disposable test database for manual QA.

| Task | Focused checks |
| --- | --- |
| 1 | From `frontend`, run `npm test -- src/components/MealLogger.test.tsx`. In a browser, throttle the preview request and attempt to confirm during the delay. |
| 2 | From `backend` with its virtual environment active, run `pytest -q tests/test_nutrition_lookup.py tests/test_interpretation_api.py tests/test_meals_api.py`. From `frontend`, run `npm test -- src/components/MealCandidates.test.tsx src/components/MealLogger.test.tsx`. Exercise both serving records and the unknown-basis case. |
| 3 | Run the same focused checks as task 2 with a mocked interpreter and USDA client. Inspect saved source, URL, serving basis, and confidence for the verified-label case. |
| 4 | Run the frontend checks from task 2. Inspect the confirmed quantity after label completion and again after canceling and starting a new manual entry. |

For a Big Pickle comparison, give two agents task 2 from the same starting commit. Compare their saved results for both serving sizes, their handling of “one bowl,” and how much unrelated code each changes.
