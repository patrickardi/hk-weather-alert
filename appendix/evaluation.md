# Appendix E — Evaluation

## E.0 Scope

This document records every test run on [App name] between [date] and [date],
what each test can and cannot show, and which changes resulted. Two of the three
components are automated and reproducible from the repository. The third (reader
testing) is a pilot with a small convenience sample and is reported as such.

Nothing here is evidence that the app is safe to deploy. It is evidence of what
we checked.

## E.1 Source verification (automated)

**Claim tested.** Every advice sentence on every card is a verbatim quote of a
published Hong Kong Government text.

**Method.** The rules engine renders [N] golden cases drawn from real warning
events (slide 11; `fixtures/golden/`). For each card, every sentence in an advice
block is compared byte-for-byte against the source string stored with its
citation (URL, retrieval date). Typography markup is stripped before comparison.
Any deviation fails the test.

**Result.** [N] golden cases, [M] quoted sentences, [0] deviations at commit
[hash]. Run: `[command]`.

**Found during verification — sources conflict.** Government pages disagree on
one fact we print. The Home Affairs Department's emergency-services page states
that hotline 2572 8427 operates round the clock from Typhoon Signal No. 8; the
Hong Kong Observatory's tropical-cyclone advisory page says from Signal No. 3;
HAD heat-shelter notices say until midnight during a Very Hot Weather Warning.
[Before v3, the T8 card printed "until 23:59" — correct for heat, wrong for T8.
/ No card printed wrong hours, but the string was hard-coded rather than
derived.] In v3 the hours string is computed from the warnings in force
(`hotlineHours()`); under Signal No. 3 alone no hours are claimed because the
two departments disagree.

## E.2 Consistency check (automated)

**Claim tested.** No card gives two incompatible instructions.

**Method.** All [N] warning × housing combinations are rendered.
[Option A: a rule table lists sentence pairs that must never co-occur without a
condition (e.g. "stay indoors" with "proceed to a shelter"); the renderer
asserts none do.]
[Option B: each rendered combination was reviewed by two team members
independently; disagreements were resolved against the source text.]

**Result.** [N] combinations, [0] conflicting pairs. [K] combinations trigger
the abstention block because no housing-specific official text exists; these
render only the housing-independent text (slide 12).

## E.3 Reader testing (pilot)

Two rounds. Neither is a validation study. Samples are too small for
percentages; we report raw counts with denominators, and the denominator is
reduced where a question was not put to every reader.

### Round 1 — layout, non-target readers

- **Who.** 8 readers, students and visitors, recruited by convenience. None in
  the target group.
- **How.** Online questionnaire (`appendix/questionnaire.pdf`), card v2 shown as
  an image, self-paced, [language].
- **What it tests.** Whether the layout is readable. It does not test whether
  target readers understand the content.
- **Findings** (count / 8): too dense 6; all phone numbers look equally
  important 5; no emergency (999) line 1; asked how long the warning would last
  1; requested Simplified Chinese 2.
- **Acted on.** Density (bold imperative verb inside each quote, one sentence
  per line, quotes unchanged); hotline hierarchy (999 first on every card, one
  primary hotline per card, purpose labels).
- **Declined.** Duration — HKO publishes no expected duration, so neither do
  we. Simplified Chinese — outside the target readership for this build.

### Round 2 — content, target readers

- **Who.** 2 readers from the target group: Indonesian domestic workers living
  in Kowloon flats. Recruited through personal contacts.
- **How.** One semi-structured interview per reader, conducted by a team member
  [in person / over WeChat], in [language], [date]. Reader A saw the Very Hot
  Weather Warning card. Reader B saw the Very Hot Weather, Black Rainstorm and
  abstention cards. Not every question was put to both; denominators reflect
  who was asked.
- **Findings.**

| Item                                              | Result |
|---------------------------------------------------|--------|
| Language clear, no machine-translation feel       | 2/2    |
| First action recalled unprompted ("stay indoors") | 2/2    |
| Later actions recalled                            | 0/1    |
| Black Rainstorm: danger named ("flooded water")   | 1/1    |
| Emergency scenario → 999                          | 2/2    |
| "Is the heat shelter open?" → 2572 8427           | 1/2 (A chose 999 for both) |
| Noticed the hotline-hours line                    | 0/1    |
| Labour Department block understood or wanted      | 0/1    |
| Abstention block read as "you are safe"           | 1/1    |

- **Most serious finding.** The one reader shown the abstention block read it
  as an all-clear. The block said housing-specific guidance was omitted; the
  reader took the absence of a warning as the presence of safety. This is the
  failure the app exists to prevent (slide 12).
- **Not collected.** Pre/post confidence ratings (questionnaire items 4.8–4.9)
  were not administered in Round 2 for lack of time. No before/after confidence
  comparison is possible.

## E.4 Changes made in response (v3)

| ID | Finding | Change | Status at submission |
|----|---------|--------|----------------------|
| P0 | Abstention block read as safe (R2 1/1) | First block, red, ⚠; rewritten as an instruction: "This does not mean you are safe. In danger now → 999. Where can I go → 2572 8427." | [merged / not merged] |
| P1 | Hours line missed (R2 0/1); hours hard-coded; sources conflict | Hours computed per warning; printed on the same line as the number | [ ] |
| P2 | Numbers same weight (R1 5/8); no 999 (R1 1/8); 2572 vs 999 confused (R2 1/2) | 999 first on every card; one primary hotline; purpose labels; 992 marked "registered" | [ ] |
| P3 | Too dense (R1 6/8); only first action recalled (R2 0/1) | Bold imperative verb inside each quote; one sentence per line; byte-equality test on plain text | [ ] |
| P4 | Labour Dept block not understood / not relevant (R2 0/1) | Shown only when the user says they are at work; employer-responsibility sentence first | [ ] |

Before/after renders of the same golden case for each merged change are in
`appendix/before_after/` (v2 = tag `v2-readers-saw`, v3 = commit [hash]).

## E.5 Limitations

- Round 2 is n = 2. It shows which failures exist, not how often.
- Both samples were recruited by convenience and interviewed by the people who
  wrote the cards. Readers may have been more generous than strangers.
- v3 has not been re-tested with target readers. The claim is "we changed X
  because of Y", not "X now works".
- No test was run during a live warning, on a phone, under stress. Reading a
  card in an interview is easier than reading it when it matters.
- Hotline numbers and hours were checked against official pages on [date]; the
  numbers were not called.
- Cards are in Traditional Chinese and English; Round 2 readers' first language
  is Indonesian. [State which language each reader read in.]

## E.6 What a real evaluation would need

- A main round with [≥20] target readers across the housing types in scope,
  including subdivided units and rooftop structures.
- Comprehension questions scored by someone outside the team, blind to version.
- A specific re-test of the abstention block: does v3 produce "I am not safe,
  I should call" rather than "I am safe"?
- Pre/post confidence measured.
- A test under a live warning, on readers' own phones, with the forwardable
  version.

## E.7 Reproducing the automated tests
