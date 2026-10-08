from app.mapping import to_hko_place
from app.rules import get_rule
from app.schemas import (
    AdviceItem,
    CardBlock,
    ContactInfo,
    PersonalContext,
    RiskResponse,
    Rule,
    Severity,
    WeatherState,
)

DONT_CODES = {
    "helper_black_rain",
    "pets_black_rain",
    "bedridden_black_rain",
    "rooftop_landslip",
    "rainstorm_level",
}

RAIN_SEVERITY = {
    "WRAINA": Severity.CAUTION,
    "WRAINR": Severity.WARNING,
    "WRAINB": Severity.DANGER,
}
RAIN_CODES = frozenset(RAIN_SEVERITY)
RAIN_ORDER = ("WRAINA", "WRAINR", "WRAINB")


def _advice_from_rule(rule: Rule, *, severity: Severity | None = None) -> AdviceItem:
    chosen = severity or rule.severity
    return AdviceItem(
        code=rule.id,
        title=rule.title,
        body=rule.body,
        safety_critical=rule.safety_critical,
        tier=chosen,
        provenance=rule.tier,
        source_url=rule.source.url,
        source_label=rule.source.label,
        quote=rule.source.quote if rule.safety_critical else None,
    )


def _block_kind(item: AdviceItem) -> str:
    if item.code == "no_active_warning_status":
        return "status"
    if item.code in DONT_CODES or item.tier in {Severity.DANGER, Severity.WARNING}:
        return "dont"
    return "do"


def pack_response(
    *,
    abstained: bool,
    abstain_reason: str | None,
    fired_rules: list[str],
    advice: list[AdviceItem],
    weather: WeatherState | None = None,
) -> RiskResponse:
    blocks = [
        CardBlock(kind=_block_kind(item), title=item.title, body=item.body, code=item.code)
        for item in advice
        if item.code != "emergency_999"
    ]
    not_considered: list[str] = []
    stale = None
    if weather is None:
        not_considered.append("weather_snapshot")
    else:
        if weather.uv_index is None:
            not_considered.append("uv_index")
        for row in weather.rainfall:
            if row.is_main is None:
                not_considered.append(f"rainfall.main:{row.place}")
        if weather.stale_as_of is not None:
            stale = weather.stale_as_of.isoformat()
    return RiskResponse(
        abstained=abstained,
        abstain_reason=abstain_reason,
        fired_rules=fired_rules,
        advice=advice,
        blocks=blocks,
        contact=ContactInfo(),
        not_considered=not_considered,
        stale_as_of=stale,
    )


def abstain_incomplete() -> RiskResponse:
    rule = get_rule("abstain_incomplete_data")
    emergency = get_rule("emergency_999")
    return pack_response(
        abstained=True,
        abstain_reason="数据不完整，不足以判断你所在位置的情况",
        fired_rules=[rule.id, emergency.id],
        advice=[_advice_from_rule(emergency)],
    )


def _warning_codes(state: WeatherState) -> set[str]:
    return {item.code for item in state.warnings.values()}


def evaluate(personal: PersonalContext, weather: WeatherState) -> RiskResponse:
    place = to_hko_place(personal.district)
    if place is None:
        rule = get_rule("abstain_out_of_scope")
        emergency = get_rule("emergency_999")
        return pack_response(
            abstained=True,
            abstain_reason="地址不在本卡覆盖的香港十八区范围内",
            fired_rules=[rule.id, emergency.id],
            advice=[_advice_from_rule(emergency)],
            weather=weather,
        )

    codes = _warning_codes(weather)
    fired: list[str] = []
    advice: list[AdviceItem] = []

    if not codes:
        status = get_rule("no_active_warning_status")
        fired.append(status.id)
        advice.append(_advice_from_rule(status))
        emergency = get_rule("emergency_999")
        fired.append(emergency.id)
        advice.append(_advice_from_rule(emergency))
        return pack_response(
            abstained=False,
            abstain_reason=None,
            fired_rules=fired,
            advice=advice,
            weather=weather,
        )

    rain_present = RAIN_CODES.intersection(codes)
    if rain_present:
        top = max(rain_present, key=RAIN_ORDER.index)
        rain_rule = get_rule("rainstorm_level")
        fired.append(rain_rule.id)
        advice.append(_advice_from_rule(rain_rule, severity=RAIN_SEVERITY[top]))

    if "WRAINB" in codes and personal.is_domestic_helper:
        rule = get_rule("helper_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if "WRAINB" in codes and personal.has_pets:
        rule = get_rule("pets_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if "WRAINB" in codes and personal.has_bedridden:
        rule = get_rule("bedridden_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if "WL" in codes and personal.housing == "rooftop":
        rule = get_rule("rooftop_landslip")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    emergency = get_rule("emergency_999")
    fired.append(emergency.id)
    advice.append(_advice_from_rule(emergency))
    return pack_response(
        abstained=False,
        abstain_reason=None,
        fired_rules=fired,
        advice=advice,
        weather=weather,
    )
