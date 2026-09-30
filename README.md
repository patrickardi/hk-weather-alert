# HK Extreme-Weather Personal Risk Card

A one-page, forwardable emergency card for individuals who need official Hong Kong weather guidance and cannot get it from the channels, in a clear, accurate and personal form they can act on. Rules decide. GenAI filters and interprets the information but never decides.

---

## 1. Why this exists

Three findings from reading the official sources. All three are verbatim, all
three are dated, none are invented.

### 1.1 Four current official documents disagree about which number to call

| Number | Source | What it says | Hours |
|---|---|---|---|
| 2572 8427 | hko.gov.hk `informtc/advisorye.htm` | "When a **No. 3 Signal** is issued, the Home Affairs Department (HAD) will activate the Emergency Hotline (Tel. 2572 8427) with manning **round the clock**" | 24h |
| 2572 8427 | info.gov.hk GIA, 29 & 30 Sep 2026 | "please call the department's hotline **before midnight** on 2572 8427" | until midnight |
| 2835 1473 | sb.gov.hk *Simple Guidelines in the Event of Major Mishaps* (EN + ZH) | "Home Affairs Department **Emergency Hotline** 2835 1473" | not stated |
| 2835 2500 | had.gov.hk | Telephone Enquiry Centre | office hours |

Also unresolved: HKO says the hotline is activated at **Signal No. 3**;
had.gov.hk says the Emergency Co-ordination Centre is activated at
**Signal No. 8 or above, landslip warning, or red/black rainstorm warning**.

➡️ **Design consequence:** hotline hours are a *function of the currently
active warning*, not a static fact. The `CONTACT` block must be computed, not
hard-coded. See §5.

### 1.2 The Government's own address service does not recognise its own shelter

`101 Wu Shan Road, Tuen Mun` is **Wu Shan Road Community Hall**, one of 19
temporary heat shelters (info.gov.hk GIA, 29 and 30 Sep 2026; it is the
temporary replacement for Butterfly Bay Community Centre per the footnote on
had.gov.hk).

Fed to the Address Lookup Service, it returns:

```
BuildingName : CASTLE PEAK WHOLESALE FISH MARKET / 青山魚類批發市場
Score        : 88.75
candidates   : 1
```

➡️ High confidence, single candidate, wrong answer, and no second option to
prompt doubt. See `tests/` — this is a permanent regression case, not a bug to
be "fixed" away.

### 1.3 "Typhoon shelter" is not a shelter for residents

hko.gov.hk: "Typhoon shelters are normally open at all times" — these are
moorings for **vessels**; the Marine Department monitors mooring space.
The place for **people** is a *temporary shelter* / *temporary heat shelter*,
opened "at the discretion of District Officer(s)" (had.gov.hk).

➡️ Two near-identical English names, opposite meanings, one of them is a body
of water. The card must never print the words "typhoon shelter" as advice.

---

## 2. Architecture: three layers, one sentence each

> **Wire is permissive and dumb. Adapter is strict and loud. Domain is total.**

| Layer | File | Job | Forbidden |
|---|---|---|---|
| wire | `app/wire.py` | Mirror upstream JSON exactly. Keep `""`, keep stringified numbers. Every field optional unless the whole document is meaningless without it. | Unit conversion, `""`→`None`, `Literal[...]` over observed values |
| adapter | `app/adapters.py` | The only wire→domain mapping. Decides what is missing and says so. | Business rules |
| domain | `app/schemas.py` | Rule inputs and outputs. No field may silently mean "you are fine". | Upstream field names, `""` as missing, defaults that assume safety |
| engine | `app/engine.py` | Whitelisted rules over domain models only | Reading raw dicts |

### The two rules that follow from this

1. **A field you never read must never be able to abstain the card.**
   Make it optional in wire.
2. **A field you do read, when missing, must always abstain the block that
   reads it.** Never substitute a default.

---

## 3. Current status

### Done and correct — do not undo

- `extra="allow"` in wire, `extra="forbid"` in domain. Right direction.
- `warningMessage: list[str] | Literal[""]` and `uvindex: UvIndexObject | Literal[""]`
  encode the fact that `""` means *no data*, not zero.
- `ActiveWarning` carries both `warning_key` and `code` (live data has
  `key=WFIRE`, `code=WFIREY`).
- `looks_like_json()` checks content-type **and** first byte — catches
  HTTP 200 with an HTML body.
- `stale_as_of` uses `min()`. The card prints the **oldest** source time.
- `Provenance` has exactly two members and **neither of them is
  "generated"**. Keep it that way. See §7.

### Blocking, in order

- [ ] **`RiskResponse.abstained: bool` is too coarse.** Add block-level
      outcomes (§5.1). This is a prerequisite for the 101 Wu Shan Road case
      and it currently contradicts `test_rain_severity_*`.
- [ ] **`Rule.tier: Provenance` vs `AdviceItem.tier: Severity`** — same field
      name, opposite meaning, and the two models map to each other.
      Rename `Rule.tier` → `Rule.provenance`.
- [ ] **`Severity` has no ordering.** It is a `str` Enum, so string
      comparison puts `"warning"` above `"danger"`. Add `.rank`. Then delete
      the duplicate `TIER_RANK` table that the tests were forced to invent.
- [ ] **Loosen wire.** `RainfallRow.main` must not be a `Literal` over two
      observed values. `tcmessage`, `mintempFrom00To09`, `rainfallFrom00To12`,
      `rainfallLastMonth`, `rainfallJanuaryToLastMonth`, `icon` are read by
      zero rules and are all currently required.
- [ ] **Loosen the ALS models.** They were reverse-engineered from one
      address. Village houses and estates very likely have no `EngStreet` or
      no `BuildingNoFrom`. `SuggestedAddress` must default to `[]` — "no
      match" is a domain fact, not an upstream failure.
- [ ] **Probe three more ALS shapes before trusting the model**: a village
      house, a public estate (e.g. `Long Ping Estate, Yuen Long`, which is on
      the shelter list), and a deliberately non-existent address.
- [ ] **Add `geocode_candidate_count` and `geocode_alternatives`.** Without
      them the rule "one candidate is more dangerous than many" cannot be
      written, and §1.2 stays an anecdote instead of a test.
- [ ] **Add `retrieved_on` to `RuleSource` and `AdviceItem`**, required when
      `safety_critical`. This is what makes the SPF-15-vs-SPF-30 class of
      error visible in review, and it is the only way to express "both quotes
      are official, one is newer".
- [ ] **Replace the four assume-safe defaults** with tri-state
      (§5.2). `has_bedridden: bool = False` currently means "nobody asked, so
      assume nobody is bedridden".
- [ ] **Filter `actionCode == "CANCEL"`** in the adapter, and record the
      filtering. A cancellation is a published event — we have seen
      `Labour Department Notification No.018 - Cancellation of Heat Stress at
      Work Warning` on GIA.
- [ ] **Enforce abstain ≠ blank in the schema** (§5.3).
- [ ] **Cross-check warnsum against rhrread** (§6.3). `{}` currently cannot be
      distinguished from a broken upstream.
- [ ] **Delete every `isinstance(result, dict)` branch in the tests** (§8.1).

---

## 4. Data sources, and what is NOT in them

| Warning | Issued by | Channel | In `warnsum`? |
|---|---|---|---|
| Very Hot / Cold / Rainstorm / Landslip / Tropical Cyclone | Hong Kong Observatory | `warnsum` API | ✅ |
| **Heat Stress at Work Warning (Amber/Red/Black)** | **Labour Department** | GIA press notices | 🔴 **No** |
| **Hot Weather Special Advisory** | HKO | web / broadcast, *below* Very Hot Weather Warning threshold | 🔴 **No** |
| Shelter opening status | Home Affairs Department | had.gov.hk + GIA | 🔴 No |
| Daytime-only refuge halls (a **second, different** list) | HAD | `List_CH_CC_Day_E.pdf` | 🔴 No |

On 29 Sep 2026 the GIA page carried, on the same day, nine Labour Department
notifications about one Heat Stress at Work Warning **and** a separate HKO
Very Hot Weather Warning. Two systems, two departments, one afternoon.

➡️ **Consequences:**
- The card must not imply it covers rest breaks at work. Either say so
  explicitly or add the Labour Department source.
- "No active warning" from `warnsum` does **not** mean "no heat risk".
  The Hot Weather Special Advisory sits below the API's threshold entirely.

🟡 The API documentation's `WHOT` sample says `SPF 15`; the current HKO page
says `SPF 30 or higher`. The documentation labels itself "**NOT real data**".
➡️ **Rule: card copy always quotes the live web page, never the API sample,
and always carries `retrieved_on`.**

---

## 5. Domain contracts

### 5.1 Block-level outcomes, not one boolean

`abstained=True` means **the whole card is unusable**: upstream was not JSON,
the district is outside Hong Kong, or two sources contradict each other.

Address-level uncertainty suppresses **blocks**:

```python
class Block(str, Enum):
    ACTIVE_WARNINGS   = "active_warnings"     # territory-wide
    LOCAL_OBSERVATION = "local_observation"   # district-level
    SHELTER           = "shelter"             # address-level
    HOUSING_RISK      = "housing_risk"        # address-level
    WORK              = "work"
    CONTACT           = "contact"

class BlockOutcome(BaseModel):
    block: Block
    rendered: bool
    omitted_reason: str | None = None   # required when rendered is False
```

For the 101 Wu Shan Road case this gives the right answer rather than a convenient one:

| Block | Outcome |
|---|---|
| ACTIVE_WARNINGS | ✅ rendered — territory-wide, address irrelevant |
| LOCAL_OBSERVATION | ✅ rendered — the **district** (Tuen Mun) is correct |
| SHELTER | 🔴 omitted — "we cannot confirm your address; this would have sent you to wrong locations" |
| HOUSING_RISK | 🔴 omitted — same reason |
| CONTACT | ✅ rendered — address-independent |

➡️ A card that is 70% useful beats a blank card in a rainstorm.
Suppress the blocks that are wrong, not the ones that happen to sit next to them.

### 5.2 Nothing may default to safe

```python
is_domestic_helper: bool | None = None
has_pets:           bool | None = None
has_bedridden:      bool | None = None
housing:            Housing | None = None
```

`None` means **nobody asked**. The engine must *say* it did not consider that factor.
It must never render as though the answer were "no".

This is the same bug as `""`-treated-as-`0`, which we already fixed in wire.
Defaults reintroduce it one layer down. Also: `bool` cannot represent "not sure", which makes the GenAI abstention contract (§7) unrepresentable.

`housing` must be an Enum — a typo like `"roof_top"` currently downgrades a
rooftop-hut resident to a generic card in silence.

### 5.3 Abstain is never blank

Enforced in `RiskResponse`, not left to the engine:

```python
FALLBACK_CODES = {"emergency_999", "emergency_sms_992", "where_to_ask"}
# abstained=True  → advice must intersect FALLBACK_CODES
# abstained=False → abstain_reason must be None
```

### 5.4 Severity has an explicit rank

`Severity` is a `str` Enum, so the default comparison is alphabetical, which
ranks `"warning"` above `"danger"`. Add `.rank` on the enum and use it everywhere. Do not keep a second ranking table in the tests.

---

## 6. Help channels

Every row needs a source and a retrieval date. Two rows are unresolved.

| Situation | Number | Hours | Source |
|---|---|---|---|
| Emergency | 999 | 24h | — |
| Emergency, hearing/speech impaired (fax/SMS) | **992** | 24h | sb.gov.hk *Simple Guidelines* |
| General government enquiry | 1823 | 24h | 1823.gov.hk |
| Very Hot Weather / heat shelters | 2572 8427 | ⚠️ **until midnight** | GIA 29–30 Sep 2026 |
| T8+ / landslip / red or black rain | 2572 8427 | ✅ round-the-clock | hko.gov.hk advisory page |
| HAD general | 2835 2500 | office hours, **caller ID withheld** | had.gov.hk |
| ⚠️ HAD "Emergency Hotline" per Security Bureau | **2835 1473** | not stated | sb.gov.hk (2019 edition) |

⚠️ **Open question 1:** 2572 8427 or 2835 1473? Both are currently published
as HAD's emergency line. Must be confirmed by phone.

⚠️ **Open question 2:** activation threshold — HKO says Signal No. 3, HAD says
No. 8 or above. The gap can be several hours.

⚠️ **Open question 3:** is HAD among 1823's 23 participating departments? The
list we retrieved was truncated and did not include it. 1823's own 2023
figures show 24.84% of enquiries (461,720) were for non-participating
departments.

🔑 **Card design note:** had.gov.hk warns that 2835 2500 does not display a
caller number, and separately warns about impersonation scams. A person in an
emergency receiving a call from a withheld number has good reason to hang up.
If the card tells someone to expect a call back, it must say this.

### 6.1 CONTACT is computed, not constant

```
active warnings ⊇ {T8, T9, T10} | landslip | red rain | black rain
    → 2572 8427, describe as round-the-clock
active warnings ⊇ {very hot}  and nothing above
    → 2572 8427, describe as "until midnight only"
    → and print the midnight boundary as a time, not as a word
neither
    → 1823
always
    → 999, and 992 for fax/SMS
```

### 6.2 Never print "typhoon shelter"

See §1.3. Whitelist the phrase out of all card copy and add a test for it.
Keywords of "shelter" in the API open to the public is "Community Service Hall".

### 6.3 Sources must reconcile

```
warnsum == {} AND rhrread.warningMessage is non-empty  → abstained=True
warnsum non-empty AND rhrread.warningMessage == ""     → abstained=True
```
An empty `warnsum` body is indistinguishable from a broken upstream.
The only available check is agreement between two sources. Needs a golden case.

---

## 7. Where GenAI is allowed

✅ Turning what a user says out loud into a `PersonalContext`.
   **Not sure → leave the field `None`. Never guess.**
✅ Selecting relevant sentences from a whitelisted source document,
   **verbatim, no rewriting.**

❌ Fetching data from the Internet
❌ Deciding whether a warning is in force
❌ Resolving a district or an address
❌ Filling a missing value
❌ Writing safety copy
❌ Translating

`Provenance` has two members and neither is "generated". Adding a third is a
design decision that requires a conversation, not a commit — which is what
`test_provenance_enum_has_not_grown_silently` exists to force.

```text

   The Three-Stage Principle

     Situational Input             Rule Engine                  Output
  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
  │ Fuzzy allowed       │ →  │ Fully deterministic │ →  │ Finite set          │
  │ Typos allowed       │    │ YAML rules          │    │ Pre-rendered PNG    │
  │ Voice allowed       │    │ Zero LLM            │    │ Pre-rendered MP3    │
  └─────────────────────┘    └─────────────────────┘    └─────────────────────┘
      fuzzy front door            ↑ auditable               ↑ reproducible
```

---

## 8. Test rules

### 8.1 One return type

The suite currently accepts either dicts or models throughout
(`result["abstained"] if isinstance(result, dict) else result.abstained`).
That is why the `schemas.py` validators are not protecting anything: there is always a path around them.

Fix in this order:
1. `tests/helpers.run_evaluate` validates its dict arguments into
   `PersonalContext` / `WeatherState` and returns a `RiskResponse`.
   YAML fixtures stay as dicts; that is fine.
2. Add `test_evaluate_rejects_raw_dicts`.
3. Delete every `isinstance(..., dict)` branch. Anything that breaks was relying on the gap.

### 8.2 A test that cannot fail is worse than no test

Two currently cannot fail:

- `ALLOWED_SAFETY_CRITICAL_TIERS == {"quote_only", "template"}` is the entire
  `Provenance` enum. Tautology.
- `if not source:` — `source` is a pydantic model. Models have no
  `__bool__`, so they are always truthy. Meanwhile `RuleSource.url` defaults
  to `""`, so a `safety_critical` rule with no URL passes every test and
  raises at runtime instead.

### 8.3 Monotonic is not enough

`assert black >= red >= yellow` passes when all three are equal 
— including the exact bug it was written to catch. Add `assert black > yellow`.

### 8.4 One concern per test

`test_rain_severity_*` is about rainstorm ordering. It does not need the
fish-market address. Give it a clean address and keep the 101 Wu Shan Road
fixture for the block-suppression test.

### 8.5 Quotes must exist in their sources

For every rule with `provenance == quote_only`, assert `rule.source.quote` is
a substring of a stored local snapshot of the source page.
This is the only real defence against paraphrase drift (what `retrieved_on` is for).

### 8.6 Golden cases still missing

- [ ] `warnsum {}` + non-empty `rhrread.warningMessage` → whole-card abstain
- [ ] `actionCode: "CANCEL"` → must **not** count as active
- [ ] ALS returns zero `SuggestedAddress` → SHELTER/HOUSING_RISK omitted
- [ ] ALS returns 2+ candidates → ambiguous, blocks omitted with reason
- [ ] `101 Wu Shan Road` → rain advice **rendered**, shelter block **omitted**
- [ ] Very Hot Weather only → CONTACT says "until midnight"
- [ ] T8 → CONTACT says round-the-clock
- [ ] `housing=None` → card states it did not consider housing
- [ ] Card copy contains the phrase "typhoon shelter" → fail

### 8.7 Move coverage assertions out of the parametrised test

`REQUIRED_IDS.issubset(...)` and `len(CASES) >= 6` currently run once per case, and never run at all if `cases:` is empty.

---

## 9. Run

```bash
python -m app.probe            # refresh live fixtures
python -m app.probe --als      # three new ALS shapes, see §3
python -m pytest               # must be green
python -m app.render           # renders the card, offline, no GenAI
```

---

## 10. Reference dates

All quotes in this repo carry `retrieved_on`. The sources currently cited:

| Source | Retrieved |
|---|---|
| hko.gov.hk `wservice/warning/coldhot.htm` | 2026-09-28 |
| hko.gov.hk `informtc/advisorye.htm` | 2026-09-28 |
| had.gov.hk `public_services/emergency_services/emergency.htm` | 2026-09-28 |
| info.gov.hk GIA heat shelter notices | 2026-09-29, 2026-09-30 |
| sb.gov.hk *Simple Guidelines in the Event of Major Mishaps* | 2026-09-28 (document dated Sep 2019) |
| HKO Open Data API Documentation | 2026-09-28 (samples labelled NOT real data) |

Reference event for all scenario work: **Typhoon Wipha, Sunday 20 July 2025.**
T8 00:20 → T9 07:20 → T10 09:20 (≈7 hours) → T8 16:10 → T3 19:40. Red
rainstorm warning 15:10–18:10. About 214 people went to government shelters.
It was a Sunday (the rest day).
