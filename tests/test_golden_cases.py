from pathlib import Path

import pytest
import yaml

GOLDEN_PATH = Path(__file__).parent / "golden_cases.yaml"
REQUIRED_IDS = {
    "domestic_helper_black_rain_pets",
    "rooftop_landslip",
    "bedridden_black_rain",
    "no_active_warning_normal_card",
    "out_of_scope_must_abstain",
    "incomplete_data_must_abstain",
}


def _load_cases():
    payload = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))
    return payload["cases"]


CASES = _load_cases()
CASE_IDS = [case["id"] for case in CASES]


def test_golden_catalog_covers_required_ids():
    assert REQUIRED_IDS.issubset(set(CASE_IDS))
    assert len(CASES) >= 6


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_golden_case(case):
    from tests.helpers import run_evaluate

    result = run_evaluate(case["personal"], case["weather"])
    expect = case["expect"]

    assert result.abstained is expect["abstained"]

    needle = expect.get("abstain_reason_contains")
    if needle:
        assert result.abstain_reason, f"{case['id']} missing abstain_reason"
        assert needle in result.abstain_reason

    for rule_id in expect.get("fired_rules_contains", []):
        assert rule_id in result.fired_rules, f"{case['id']} missing fired rule {rule_id}"

    min_advice = expect.get("min_advice")
    if min_advice is not None:
        assert len(result.advice) >= min_advice

    if expect.get("any_safety_critical"):
        assert any(item.safety_critical for item in result.advice)

    if expect.get("not_considered_contains"):
        for item in expect["not_considered_contains"]:
            assert item in result.not_considered

    if expect.get("contact_hours_contains"):
        assert result.contact is not None
        assert expect["contact_hours_contains"] in (result.contact.had_hours or "")

    if expect.get("contact_mode"):
        assert result.contact is not None
        assert result.contact.mode.value == expect["contact_mode"]
