import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from app.adapters import build_card, personal_from_als, weather_from_hko
from app.engine import evaluate
from app.probe import ALS_SHAPES
from app.schemas import (
    ActiveWarning,
    Block,
    HotlineMode,
    PersonalContext,
    Severity,
    WeatherState,
)
from app.wire import parse_als, parse_rhrread

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _warning(code: str, *, name: str, warning_type: str | None = None, action: str = "ISSUE") -> ActiveWarning:
    ts = datetime.fromisoformat("2026-09-25T14:00:00+08:00")
    return ActiveWarning(
        warning_key=code,
        code=code,
        name=name,
        warning_type=warning_type,
        action_code=action,
        issue_time=ts,
        update_time=ts,
    )


def _ctx(**overrides) -> PersonalContext:
    payload = {
        "request_address": "1 Tuen Mun Heung Sze Wui Road",
        "district": "屯門",
        "latitude": 22.39,
        "longitude": 113.97,
        "geocode_score": 70.0,
    }
    payload.update(overrides)
    return PersonalContext.model_validate(payload)


def _rhrread(messages):
    return {
        "rainfall": {
            "data": [{"unit": "mm", "place": "屯門", "max": 0, "main": "FALSE"}],
            "startTime": "2026-09-25T13:45:00+08:00",
            "endTime": "2026-09-25T14:45:00+08:00",
        },
        "warningMessage": messages,
        "updateTime": "2026-09-25T15:02:00+08:00",
        "temperature": {
            "data": [{"place": "屯門", "value": 28, "unit": "C"}],
            "recordTime": "2026-09-25T15:00:00+08:00",
        },
    }


def _outcome(result, block: Block):
    return next(item for item in result.block_outcomes if item.block is block)


def test_severity_rank_orders_danger_above_warning():
    assert Severity.DANGER.rank > Severity.WARNING.rank
    assert Severity.WARNING.rank > Severity.CAUTION.rank
    assert Severity.CAUTION.rank > Severity.ADVISORY.rank


def test_evaluate_rejects_raw_dicts():
    with pytest.raises(TypeError):
        evaluate({"district": "屯門"}, {"warnings": {}})


def test_cancel_is_not_active_and_is_recorded():
    warnsum = {
        "WRAINB": {
            "name": "Black Rainstorm Warning",
            "code": "WRAINB",
            "type": "Black",
            "actionCode": "CANCEL",
            "issueTime": "2026-09-25T14:00:00+08:00",
            "updateTime": "2026-09-25T15:00:00+08:00",
        }
    }
    weather = weather_from_hko(warnsum, _rhrread(""))
    assert "WRAINB" not in weather.warnings
    assert "WRAINB" in weather.cancelled_codes


def test_warnsum_empty_and_rhrread_message_abstains():
    personal = _ctx()
    result = build_card(
        personal=personal,
        warnsum_body="{}",
        warnsum_ctype="application/json",
        rhrread_body=json.dumps(_rhrread(["黑色暴雨警告現正生效。"])),
        rhrread_ctype="application/json",
    )
    assert result.abstained is True
    assert "不一致" in (result.abstain_reason or "")


def test_warnsum_present_and_rhrread_empty_message_abstains():
    warnsum = {
        "WRAINB": {
            "name": "Black Rainstorm Warning",
            "code": "WRAINB",
            "type": "Black",
            "actionCode": "ISSUE",
            "issueTime": "2026-09-25T14:00:00+08:00",
            "updateTime": "2026-09-25T14:00:00+08:00",
        }
    }
    result = build_card(
        personal=_ctx(),
        warnsum_body=json.dumps(warnsum),
        warnsum_ctype="application/json",
        rhrread_body=json.dumps(_rhrread("")),
        rhrread_ctype="application/json",
    )
    assert result.abstained is True
    assert "不一致" in (result.abstain_reason or "")


def test_als_zero_candidates_omits_shelter_and_housing():
    personal = personal_from_als(
        {"RequestAddress": {"AddressLine": ["nowhere"]}, "SuggestedAddress": []}
    )
    assert personal.geocode_candidate_count == 0
    weather = WeatherState(warnings={"WRAINR": _warning("WRAINR", name="Red Rainstorm Warning", warning_type="Red")})
    result = evaluate(personal, weather)
    assert result.abstained is False
    assert _outcome(result, Block.SHELTER).rendered is False
    assert _outcome(result, Block.HOUSING_RISK).rendered is False
    assert _outcome(result, Block.ACTIVE_WARNINGS).rendered is True


def test_als_two_candidates_omits_shelter():
    payload = json.loads(_load("als_101_wu_shan_road.json"))
    payload["SuggestedAddress"].append(deepcopy(payload["SuggestedAddress"][0]))
    personal = personal_from_als(payload)
    assert personal.geocode_candidate_count == 2
    weather = WeatherState(warnings={"WRAINR": _warning("WRAINR", name="Red Rainstorm Warning", warning_type="Red")})
    result = evaluate(personal, weather)
    assert _outcome(result, Block.SHELTER).rendered is False
    assert _outcome(result, Block.ACTIVE_WARNINGS).rendered is True


def test_wu_shan_rain_rendered_shelter_omitted():
    personal = personal_from_als(json.loads(_load("als_101_wu_shan_road.json")))
    assert personal.geocode_candidate_count == 1
    weather = WeatherState(warnings={"WRAINR": _warning("WRAINR", name="Red Rainstorm Warning", warning_type="Red")})
    result = evaluate(personal, weather)
    assert result.abstained is False
    assert "rainstorm_level" in result.fired_rules
    assert _outcome(result, Block.ACTIVE_WARNINGS).rendered is True
    assert _outcome(result, Block.SHELTER).rendered is False
    assert "庇护所" in (_outcome(result, Block.SHELTER).omitted_reason or "")


def test_very_hot_contact_until_midnight():
    result = evaluate(
        _ctx(),
        WeatherState(warnings={"WHOT": _warning("WHOT", name="Very Hot Weather Warning")}),
    )
    assert result.contact.mode is HotlineMode.HAD_UNTIL_MIDNIGHT
    assert result.contact.had_hotline == "2572 8427"
    assert "午夜" in (result.contact.had_hours or "")


def test_t8_contact_round_the_clock():
    result = evaluate(
        _ctx(),
        WeatherState(
            warnings={
                "WTCSGNL": _warning(
                    "WTCSGNL",
                    name="Tropical Cyclone Warning Signal",
                    warning_type="TC8NE",
                )
            }
        ),
    )
    assert result.contact.mode is HotlineMode.HAD_ROUND_THE_CLOCK
    assert result.contact.had_hours == "24小时"


def test_housing_none_is_stated():
    result = evaluate(_ctx(), WeatherState(warnings={}))
    assert "housing" in result.not_considered
    assert _outcome(result, Block.HOUSING_RISK).rendered is False


def test_als_suggested_address_defaults_to_empty_list():
    parsed = parse_als({"RequestAddress": {"AddressLine": ["x"]}})
    assert parsed.SuggestedAddress == []


def test_rainfall_main_accepts_values_other_than_false():
    payload = _rhrread("")
    payload["rainfall"]["data"] = [
        {"unit": "mm", "place": "屯門", "max": 3, "main": "TRUE"},
        {"unit": "mm", "place": "北區", "max": 1, "main": "OTHER"},
    ]
    parsed = parse_rhrread(payload)
    assert parsed.rainfall.data[0].main == "TRUE"
    assert parsed.rainfall.data[1].main == "OTHER"


def test_probe_als_shapes_are_the_three_required():
    assert set(ALS_SHAPES) == {"village", "estate", "nonexistent"}
    assert "Long Ping Estate" in ALS_SHAPES["estate"]
