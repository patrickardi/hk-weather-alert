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


def _advice_items(result):
    return getattr(result, "advice", None) or []


def _safety_critical(item):
    return item["safety_critical"] if isinstance(item, dict) else item.safety_critical


CASES = _load_cases()
CASE_IDS = [case["id"] for case in CASES]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_golden_case(case):
    from tests.helpers import run_evaluate

    assert REQUIRED_IDS.issubset(set(CASE_IDS))
    assert len(CASES) >= 6
    result = run_evaluate(case["personal"], case["weather"])
    expect = case["expect"]

    abstained = result["abstained"] if isinstance(result, dict) else result.abstained
    assert abstained is expect["abstained"]

    reason = (
        result.get("abstain_reason")
        if isinstance(result, dict)
        else result.abstain_reason
    )
    needle = expect.get("abstain_reason_contains")
    if needle:
        assert reason, f"{case['id']} missing abstain_reason"
        assert needle in reason

    fired = result["fired_rules"] if isinstance(result, dict) else result.fired_rules
    for rule_id in expect.get("fired_rules_contains", []):
        assert rule_id in fired, f"{case['id']} missing fired rule {rule_id}"

    advice = _advice_items(result)
    min_advice = expect.get("min_advice")
    if min_advice is not None:
        assert len(advice) >= min_advice

    if expect.get("any_safety_critical"):
        assert any(_safety_critical(item) for item in advice)
