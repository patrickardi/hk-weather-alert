# HK weather-risk card

Rules-first. GenAI encodes input and extracts whitelist PDFs only.

- HKO empty string means missing data, not 0.
- ALS `DcDistrict` (屯門區) ≠ HKO rainfall `place` (屯門). Use `app/mapping.py`.
- Warning identity is `code`, not warnsum dict key.
- `lang=id` returns HTTP 200 + text/html. Abstain. Do not claim the Observatory refuses minorities.
- Safety-critical advice must quote a source. No TODO. No machine Indonesian.
