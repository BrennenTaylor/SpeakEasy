
# Calorie Tracker — Engineering Instructions

## Product
A phone-first, AI-assisted calorie tracking PWA.

Primary objective: accurate, low-friction calorie logging.
Secondary objectives: nutrition analysis and actionable insights.

## Architecture
- React + TypeScript frontend
- FastAPI + Pydantic backend
- SQLAlchemy + Alembic
- SQLite for local development
- External nutrition providers behind adapters
- AI provider behind an abstraction

## Non-negotiable rules
1. Never invent nutritional data.
2. Never let the LLM perform authoritative calorie arithmetic.
3. Preserve source, units, and confidence for nutrition records.
4. Store nutrition snapshots with logged meals.
5. Keep meal logging functional when AI services are unavailable.
6. Require confirmation before committing an AI-interpreted meal.
7. Use Decimal for nutrition calculations.
8. Never expose API keys to the browser.
9. Never silently change database schemas.
10. Never provide insulin-dosing recommendations.

## Engineering workflow
- Inspect existing code before modifying it.
- Propose a short plan before major changes.
- Implement one bounded feature at a time.
- Add automated tests for new business logic.
- Run relevant tests before declaring completion.
- Do not add dependencies without explaining why.
- Do not introduce unrelated refactoring.
- Do not delete user data or reset the database.
- Summarize files changed, tests run, and limitations.

## Quality
- Type-check frontend and backend.
- Validate API input/output.
- Handle loading, empty, and error states.
- Prioritize usability on mobile screens.
- Prefer simple solutions over premature abstractions.
