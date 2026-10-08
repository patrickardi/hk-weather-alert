# AGENTS.md

## Layout: verify paths before you use them

`main` puts everything at the repo root: `schemas.py`, `wire.py`,
`README.md`, `status.md`, `agents/`. README §2 and §9 describe
`app/wire.py`, `app/schemas.py`, `app/adapters.py`, `app/engine.py`,
`app/probe`, `app/render` and `tests/` — **none of those exist yet**.
`wire.py` imports its sibling flat (`from schemas import ...`),
so run anything from the repo root.
Rules-first. GenAI encodes input and extracts whitelist PDFs only.

## Running

- Always run scripts as `python -m scripts.<name>` from repo root.
- Pydantic is v2. Never use parse_raw / parse_obj / .dict() / .json().

No manifest exists — no `pyproject.toml`, `requirements.txt`, lockfile, CI
or pre-commit. Versions in use: Python 3.12.7, pydantic 2.8.2, pytest 7.4.4.

**`wire.py` does not import. Two stacked causes — fixing only the first
gets you a second, more confusing error.**

1. `from __future__ import annotations` is line 4, after three other
   imports. Hard `SyntaxError`, so `import wire` never even parses.
   
2. After moving it to line 1, `EngPremisesAddress` raises
   `TypeError: unsupported operand type(s) for |: 'NoneType' and 'NoneType'`.
   The fields are named after their own type:

   ```python
   EngStreet: EngStreet | None = None     # wire.py:108
   EngDistrict: EngDistrict | None = None # wire.py:109
   ```

   The class body stores `EngStreet = None` *before* evaluating the
   annotation, so the annotation becomes `None | None`.

   - Moving `from __future__` to line 1 does **not** fix this.
   - Quoting the annotation (`"EngStreet | None"`) does **not** fix this
     either — pydantic evaluates it against the class namespace where the
     shadow already lives.
   - Removing `= None` does fix it, but makes the field required, which
     contradicts README §3 (village houses have no `EngStreet`) and breaks
     the wire contract.
   - **Verified fix:** alias the type at module scope and annotate with the
     alias — `_EngStreetAlias = EngStreet`, then
     `EngStreet: _EngStreetAlias | None = None`. The field name stays
     `EngStreet` (wire must mirror upstream JSON keys exactly) and the
     default stays `None`.

Only fields with *both* a same-named type and a default trip this. The same-named bare annotations (`ChiStreet`, `ChiDistrict`, `PremisesAddress`, `RequestAddress`, …) are fine as written. `schemas.py` compiles and imports cleanly as-is — do not "fix" it while fixing `wire.py`.

## Fixtures

- `fixtures/*.json` is the source of truth for data shape and must stay
  valid against `app/models.py`.
- Do NOT loosen models to make a fixture pass: no changing required fields
  to Optional, no `extra="allow"`, no `Any`, no removing validators.
  If model and fixture disagree, stop and report which side is wrong.
- When fixture and model share the same overall shape but disagree on
  individual fields, the fixture is the intended shape; fix the model.
- If the fixture and model have DIFFERENT top-level keys (i.e. they look
  like two different schemas), STOP. Report the two shapes side by side
  and ask which one is current. Do not rewrite either file.
- Never loosen models to make a fixture pass (no Optional on required
  fields, no extra="allow", no Any).

Today's fixtures are at `agents/fixtures/` (`weather_state.en.json`,
`red_rain_partial.json`) and there is no `app/models.py` yet — the nearest
equivalent is `schemas.py`. `red_rain_partial.json` was moved from the repo
root, so `git status` shows a deletion plus an untracked file: that is the
same file.

## Tests

- `python -m pytest` collects **0 items and exits 5**. There is no `tests/`
  directory, so README §9's "must be green" cannot be satisfied. Exit 5 here
  means *no tests*, not *failing* tests.
- Do not run pytest from a parent directory. With no config file it collects
  from the current working directory, and the home directory yields
  `PermissionError: ~/Library/Accounts`.

## Do not undo (README §3, still true in the code)

- Wire is permissive, domain is strict: `extra="allow"` on wire models,
  `extra="forbid"` on domain models.
- `""` means *no data*, never zero — `warningMessage: list[str] | Literal[""]`
  and `uvindex: UvIndexObject | Literal[""]` encode that.
- Abstain ≠ blank is enforced in `RiskResponse._contract` via
  `FALLBACK_CODES`; `blocks` must list all six `Block`s exactly once, and a
  rendered block must carry advice.
- `Severity.rank` exists. Never order severity by string — alphabetical puts
  `"warning"` above `"danger"`.
- `Provenance` has exactly two members and neither is `generated`. Adding a
  third is a design conversation, not a commit.

## README §3's checklist is partly stale

Already implemented in `schemas.py`: `Block`/`BlockOutcome`, `Severity.rank`,
`retrieved_on` on `AdviceItem`, `HotlineMode`/`ContactBlock`, and the
abstain-never-blank validator. Still genuinely absent: any `Rule` or
`RuleSource` model, and `RainfallRow.main` is still `Literal["FALSE", ""]`
(`wire.py:33`). Re-read the code instead of trusting the checklist.

## Domain rules worth not rediscovering

- GenAI encodes input and extracts whitelist PDFs only.
- HKO empty string means missing data, not 0.
- Never print **"typhoon shelter"** on the card — it is a mooring for
  vessels, not a shelter for people (README §1.3, §6.2).
- `CONTACT` is computed from the active warning set, never hard-coded:
  T8+/landslide/red-or-black rain → 2572 8427 round the clock; very hot
  only → same number, "until midnight"; otherwise 1823. 999 and 992 always.
- An empty `warnsum` does **not** mean no heat risk — the Labour Department
  Heat Stress at Work warning and the Hot Weather Special Advisory are not in
  that API at all.
- Card copy quotes the live web page, never the API sample (the docs label
  themselves "NOT real data"), and always carries `retrieved_on`.
- ALS `DcDistrict` (屯門區) ≠ HKO rainfall `place` (屯門). Use `app/mapping.py`.
- Warning identity is `code`, not warnsum dict key.
- `lang=id` returns HTTP 200 + text/html. Abstain. Do not claim the Observatory refuses minorities.

## `Agents/`

`prompt.yaml` (system prompt), `main_agent.json` (temperature 0.1,
`whitelisted_sources_only: true`), and `fixtures/`. README never mentions
this directory.
