import json
from pathlib import Path

from app.adapters import build_card, personal_from_als, to_weather, weather_from_hko
from app.engine import evaluate
from app.mapping import to_hko_place
from app.schemas import PersonalContext, WeatherState
from app.wire import (
    looks_like_json,
    parse_als,
    parse_rhrread,
    parse_warnsum,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_live_warnsum_is_empty_object():
    payload = json.loads(_load("warnsum_en_live.json"))
    assert payload == {}
    assert parse_warnsum(payload).root == {}


def test_wire_keeps_empty_string_and_false_apart():
    payload = json.loads(_load("rhrread_tc_live.json"))
    assert payload["warningMessage"] == ""
    assert payload["uvindex"] == ""
    parsed = parse_rhrread(payload)
    assert parsed.warningMessage == ""
    assert parsed.uvindex == ""
    by_place = {row.place: row for row in parsed.rainfall.data}
    assert by_place["屯門"].main == "FALSE"
    assert by_place["深水埗"].main == ""
    assert by_place["九龍城"].main == ""


def test_adapter_maps_unknown_main_to_none_not_false():
    weather = weather_from_hko(
        json.loads(_load("warnsum_en_live.json")),
        json.loads(_load("rhrread_tc_live.json")),
    )
    assert isinstance(weather, WeatherState)
    assert weather.warning_messages == []
    assert weather.uv_index is None
    by_place = {row.place: row for row in weather.rainfall}
    assert by_place["屯門"].is_main is False
    assert by_place["深水埗"].is_main is None
    assert by_place["九龍城"].is_main is None
    assert by_place["屯門"].max_mm == 0.0


def test_als_nested_district_maps_to_hko_place():
    personal = personal_from_als(json.loads(_load("als_101_wu_shan_road.json")))
    assert isinstance(personal, PersonalContext)
    assert personal.district == "屯門區"
    assert to_hko_place(personal.district) == "屯門"
    assert personal.geocode_score == 88.75
    assert isinstance(personal.latitude, float)
    assert personal.building_name_zh == "青山魚類批發市場"
    wire = parse_als(json.loads(_load("als_101_wu_shan_road.json")))
    geo = wire.SuggestedAddress[0].Address.PremisesAddress.GeospatialInformation
    assert isinstance(geo.Latitude, str)


def test_lang_id_is_http_json_lie():
    body = _load("upstream_200_html.txt")
    assert looks_like_json("text/html; charset=utf-8", body) is False
    result = build_card(
        personal={"request_address": "x", "district": "屯門", "latitude": 1, "longitude": 1, "geocode_score": 90},
        warnsum_body=body,
        warnsum_ctype="text/html; charset=utf-8",
        rhrread_body=_load("rhrread_tc_live.json"),
        rhrread_ctype="application/json",
    )
    assert result.abstained is True
    assert "不完整" in (result.abstain_reason or "")


def test_warning_identity_is_code_not_dict_key():
    warnsum = {
        "WFIRE": {
            "name": "Fire Danger Warning",
            "code": "WFIREY",
            "type": "Yellow",
            "actionCode": "ISSUE",
            "issueTime": "2026-09-25T06:00:00+08:00",
            "updateTime": "2026-09-25T06:00:00+08:00",
        }
    }
    parsed = parse_warnsum(warnsum)
    item = parsed.root["WFIRE"]
    assert item.code == "WFIREY"
    weather = to_weather(parsed, parse_rhrread(json.loads(_load("rhrread_tc_live.json"))))
    assert weather.warnings["WFIRE"].code == "WFIREY"
    assert weather.warnings["WFIRE"].warning_key == "WFIRE"


def test_live_fixtures_build_no_warning_card():
    personal = personal_from_als(json.loads(_load("als_101_wu_shan_road.json")))
    result = build_card(
        personal=personal,
        warnsum_body=_load("warnsum_en_live.json"),
        warnsum_ctype="application/json",
        rhrread_body=_load("rhrread_tc_live.json"),
        rhrread_ctype="application/json",
    )
    assert result.abstained is False
    assert "no_active_warning_status" in result.fired_rules


def test_weather_from_hko_merges_empty_warnsum():
    weather = weather_from_hko(
        json.loads(_load("warnsum_en_live.json")),
        json.loads(_load("rhrread_tc_live.json")),
    )
    assert weather.warnings == {}
    assert weather.observed_at is not None
    assert isinstance(weather.rainfall, list)


def test_mapping_does_not_strip_suffix():
    assert to_hko_place("屯門區") == "屯門"
    assert to_hko_place("屯門") == "屯門"
    assert to_hko_place("福田") is None
    assert to_hko_place("TUEN MUN DISTRICT") == "屯門"


def test_engine_reads_domain_models_not_raw_dicts():
    ctx = PersonalContext(
        request_address="101 Wu Shan Road",
        district="屯門",
        latitude=22.37693,
        longitude=113.96868,
        geocode_score=88.75,
    )
    state = WeatherState(rainfall=[], warnings={})
    result = evaluate(ctx, state)
    assert result.abstained is False
    assert "no_active_warning_status" in result.fired_rules
