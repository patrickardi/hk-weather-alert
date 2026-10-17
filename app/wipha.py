from datetime import datetime

from app.engine import evaluate
from app.schemas import ActiveWarning, PersonalContext, WeatherState

SCENES = (
    {
        "id": "vhww_fdh_1400",
        "signal": "WHOT",
        "when": "2026-09-27T14:00:00+08:00",
        "issue_time": "2026-09-27T06:45:00+08:00",   # 与 when 不同，active_warning 块应显示 06:45
        "diff_label": "外傭 · English · 中環 · 酷熱警告 · 星期日休息日 14:00",
        "filename": "vhww_fdh_1400.png",
        "personal": PersonalContext(
            request_address="1 Queen's Road Central",
            district="中西區",
            latitude=22.2805,
            longitude=114.1594,
            geocode_score=90.0,
            geocode_candidate_count=1,
            language="en",
            needs_large_type=False,
            is_domestic_helper=True,
        ),
    },
    {
        "id": "t8_0020",
        "signal": "TC8NE",
        "when": "2025-07-20T00:20:00+08:00",
        "diff_label": "独居老人 · 中文大字 · 屯门 · 八号深夜星期日",
        "filename": "wipha_t8_0020.png",
        "personal": PersonalContext(
            request_address="101 Wu Shan Road",
            district="屯門區",
            latitude=22.37693,
            longitude=113.96868,
            geocode_score=88.75,
            geocode_candidate_count=1,
            language="zh",
            needs_large_type=True,
        ),
    },
    {
        "id": "t10_0920",
        "signal": "TC10",
        "when": "2025-07-20T09:20:00+08:00",
        "diff_label": "Migrant domestic helper + 2 cats · English · Yuen Long · Signal 10",
        "filename": "wipha_t10_0920.png",
        "personal": PersonalContext(
            request_address="Long Ping Estate, Yuen Long",
            district="元朗區",
            latitude=22.4486,
            longitude=114.0253,
            geocode_score=92.0,
            geocode_candidate_count=1,
            is_domestic_helper=True,
            has_pets=True,
            language="en",
        ),
    },
    {
        "id": "t3_1940",
        "signal": "TC3",
        "when": "2025-07-20T19:40:00+08:00",
        "diff_label": "本地独居上班族 · 中文 · 湾仔 · 三号仍生效",
        "filename": "wipha_t3_1940.png",
        "personal": PersonalContext(
            request_address="258 Queen's Road East, Wan Chai",
            district="灣仔區",
            latitude=22.2765,
            longitude=114.1718,
            geocode_score=85.0,
            geocode_candidate_count=1,
            language="zh",
        ),
    },
)


def _weather(signal: str, when: str) -> WeatherState:
    ts = datetime.fromisoformat(when)
    return WeatherState(
        observed_at=ts,
        warnings={
            "WTCSGNL": ActiveWarning(
                warning_key="WTCSGNL",
                code="WTCSGNL",
                name="Tropical Cyclone Warning Signal",
                warning_type=signal,
                action_code="ISSUE",
                issue_time=ts,
                update_time=ts,
            )
        },
        source_updated_at={"warnsum:WTCSGNL": ts},
    )


def scene_response(scene: dict):
    return evaluate(scene["personal"], _weather(scene["signal"], scene["when"]))


def _weather_for(scene) -> WeatherState:
    when = scene["when"]
    issue = scene.get("issue_time", when)
    if scene["signal"] == "WHOT":
        w = Warning(warning_key="WHOT", code="WHOT", name="Very Hot Weather Warning",
                    warning_type=None, action_code="ISSUE", issue_time=issue, update_time=issue)
        return WeatherState(observed_at=when, warnings={"WHOT": w})
    # 原有 TC 分支
    w = Warning(warning_key="WTCSGNL", code="WTCSGNL", name="Tropical Cyclone Warning Signal",
                warning_type=scene["signal"], action_code="ISSUE", issue_time=issue, update_time=issue)
    return WeatherState(observed_at=when, warnings={"WTCSGNL": w})
