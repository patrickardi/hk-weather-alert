from copy import deepcopy

TIER_RANK = {
    "advisory": 1,
    "caution": 2,
    "warning": 3,
    "danger": 4,
}

RAIN_NAMES = {
    "WRAINA": "Amber Rainstorm Warning",
    "WRAINR": "Red Rainstorm Warning",
    "WRAINB": "Black Rainstorm Warning",
}

PERSONAL = {
    "request_address": "101 Wu Shan Road",
    "district": "屯門",
    "latitude": 22.37693,
    "longitude": 113.96868,
    "northing": 826429.0,
    "easting": 814827.0,
    "building_name_zh": "青山魚類批發市場",
    "building_name_en": "CASTLE PEAK WHOLESALE FISH MARKET",
    "geocode_score": 88.75,
    "is_domestic_helper": True,
    "has_pets": True,
    "housing": "standard",
    "has_bedridden": False,
}

BASE_WEATHER = {
    "observed_at": "2026-09-25T15:02:00+08:00",
    "icon_codes": [53],
    "icon_update_time": "2026-09-25T15:02:00+08:00",
    "warning_messages": ["暴雨警告現正生效。"],
    "rainfall_start_time": "2026-09-25T13:45:00+08:00",
    "rainfall_end_time": "2026-09-25T14:45:00+08:00",
    "rainfall": [{"place": "屯門", "max_mm": 30, "is_main": False}],
    "temperatures": [{"place": "屯門", "value_c": 28}],
    "temperature_record_time": "2026-09-25T15:00:00+08:00",
    "humidity": {
        "place": "香港天文台",
        "value_percent": 90,
        "record_time": "2026-09-25T15:00:00+08:00",
    },
    "uv_index": {
        "place": "京士柏",
        "value": 1,
        "desc": "低",
        "record_desc": "過去一小時",
    },
}


def _weather_with_rain(code: str) -> dict:
    weather = deepcopy(BASE_WEATHER)
    color = {"WRAINA": "Amber", "WRAINR": "Red", "WRAINB": "Black"}[code]
    weather["warnings"] = {
        code: {
            "warning_key": code,
            "code": code,
            "name": RAIN_NAMES[code],
            "warning_type": color,
            "action_code": "ISSUE",
            "issue_time": "2026-09-25T14:00:00+08:00",
            "update_time": "2026-09-25T14:00:00+08:00",
        }
    }
    return weather


def _tier_value(tier) -> str:
    if hasattr(tier, "value"):
        return tier.value
    return str(tier)


def _peak_severity(result) -> int:
    abstained = result["abstained"] if isinstance(result, dict) else result.abstained
    assert abstained is False
    advice = result["advice"] if isinstance(result, dict) else result.advice
    situational = []
    for item in advice:
        code = item["code"] if isinstance(item, dict) else item.code
        if code == "emergency_999":
            continue
        situational.append(item)
    assert situational, "same situation must still produce rain advice"
    ranks = []
    for item in situational:
        tier = item["tier"] if isinstance(item, dict) else item.tier
        ranks.append(TIER_RANK[_tier_value(tier)])
    return max(ranks)


def test_black_rain_severity_gte_red_gte_yellow_same_situation():
    from tests.helpers import run_evaluate

    black = _peak_severity(run_evaluate(PERSONAL, _weather_with_rain("WRAINB")))
    red = _peak_severity(run_evaluate(PERSONAL, _weather_with_rain("WRAINR")))
    yellow = _peak_severity(run_evaluate(PERSONAL, _weather_with_rain("WRAINA")))
    assert black >= red >= yellow
