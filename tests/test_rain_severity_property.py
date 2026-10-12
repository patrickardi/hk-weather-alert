from copy import deepcopy

from app.schemas import Severity

RAIN_NAMES = {
    "WRAINA": "Amber Rainstorm Warning",
    "WRAINR": "Red Rainstorm Warning",
    "WRAINB": "Black Rainstorm Warning",
}

PERSONAL = {
    "request_address": "1 Tuen Mun Heung Sze Wui Road",
    "district": "屯門",
    "latitude": 22.39,
    "longitude": 113.97,
    "geocode_score": 70.0,
    "is_domestic_helper": False,
    "has_pets": False,
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


def _peak_severity(result) -> int:
    assert result.abstained is False
    situational = [item for item in result.advice if item.code == "rainstorm_level"]
    assert situational, "same situation must still produce rain advice"
    return max(item.tier.rank for item in situational)


def test_black_rain_severity_gt_yellow_same_situation():
    from tests.helpers import run_evaluate

    black = _peak_severity(run_evaluate(PERSONAL, _weather_with_rain("WRAINB")))
    red = _peak_severity(run_evaluate(PERSONAL, _weather_with_rain("WRAINR")))
    yellow = _peak_severity(run_evaluate(PERSONAL, _weather_with_rain("WRAINA")))
    assert black >= red >= yellow
    assert black > yellow
    assert Severity.DANGER.rank > Severity.WARNING.rank > Severity.CAUTION.rank
