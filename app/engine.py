from app.mapping import to_hko_place
from app.rules import get_rule
from app.schemas import (
    AdviceItem,
    Block,
    BlockOutcome,
    CardBlock,
    ContactInfo,
    HAD_ROUND_THE_CLOCK_CODES,
    HotlineMode,
    Housing,
    PersonalContext,
    RiskResponse,
    Rule,
    Severity,
    TC8_PLUS_TYPES,
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
        provenance=rule.provenance,
        source_url=rule.source.url,
        source_label=rule.source.label,
        quote=rule.source.quote if rule.safety_critical else None,
        retrieved_on=rule.source.retrieved_on,
    )


def _block_kind(item: AdviceItem) -> str:
    if item.code == "no_active_warning_status":
        return "status"
    if item.code in DONT_CODES or item.tier in {Severity.DANGER, Severity.WARNING}:
        return "dont"
    return "do"


def compute_contact(weather: WeatherState | None) -> ContactInfo:
    if weather is None:
        return ContactInfo()
    codes = {item.code for item in weather.warnings.values()}
    types = {item.warning_type for item in weather.warnings.values() if item.warning_type}
    if codes.intersection(HAD_ROUND_THE_CLOCK_CODES) or types.intersection(TC8_PLUS_TYPES):
        return ContactInfo(
            had_hotline="2572 8427",
            had_hours="24小时",
            mode=HotlineMode.HAD_ROUND_THE_CLOCK,
        )
    if "WHOT" in codes:
        return ContactInfo(
            had_hotline="2572 8427",
            had_hours="午夜前",
            mode=HotlineMode.HAD_UNTIL_MIDNIGHT,
        )
    return ContactInfo(mode=HotlineMode.GOV_1823)


def _address_unconfirmed(personal: PersonalContext | None) -> bool:
    if personal is None:
        return True
    return personal.geocode_candidate_count is not None


def _block_outcomes(
    *,
    abstained: bool,
    abstain_reason: str | None,
    personal: PersonalContext | None,
    weather: WeatherState | None,
) -> list[BlockOutcome]:
    if abstained:
        reason = abstain_reason or "整卡弃答"
        return [
            BlockOutcome(block=Block.ACTIVE_WARNINGS, rendered=False, omitted_reason=reason),
            BlockOutcome(block=Block.LOCAL_OBSERVATION, rendered=False, omitted_reason=reason),
            BlockOutcome(block=Block.SHELTER, rendered=False, omitted_reason=reason),
            BlockOutcome(block=Block.HOUSING_RISK, rendered=False, omitted_reason=reason),
            BlockOutcome(
                block=Block.WORK,
                rendered=False,
                omitted_reason="劳工处工作热压力警告不在 warnsum，本卡不覆盖休息安排",
            ),
            BlockOutcome(block=Block.CONTACT, rendered=True),
        ]
    unconfirmed = _address_unconfirmed(personal)
    place = to_hko_place(personal.district) if personal and personal.district else None
    local_ok = place is not None
    housing_ok = bool(personal and personal.housing is not None and not unconfirmed)
    if unconfirmed:
        housing_reason = "未能确认地址，不显示住屋风险"
    else:
        housing_reason = "未询问住所类型，未纳入住屋风险"
    return [
        BlockOutcome(block=Block.ACTIVE_WARNINGS, rendered=True),
        BlockOutcome(
            block=Block.LOCAL_OBSERVATION,
            rendered=local_ok,
            omitted_reason=None if local_ok else "未能对应本区观测",
        ),
        BlockOutcome(
            block=Block.SHELTER,
            rendered=False,
            omitted_reason="未能确认地址，不显示庇护所，以免导向错误地点",
        ),
        BlockOutcome(
            block=Block.HOUSING_RISK,
            rendered=housing_ok,
            omitted_reason=None if housing_ok else housing_reason,
        ),
        BlockOutcome(
            block=Block.WORK,
            rendered=False,
            omitted_reason="劳工处工作热压力警告不在 warnsum，本卡不覆盖休息安排",
        ),
        BlockOutcome(block=Block.CONTACT, rendered=True),
    ]


def pack_response(
    *,
    abstained: bool,
    abstain_reason: str | None,
    fired_rules: list[str],
    advice: list[AdviceItem],
    weather: WeatherState | None = None,
    personal: PersonalContext | None = None,
) -> RiskResponse:
    blocks = [
        CardBlock(kind=_block_kind(item), title=item.title, body=item.body, code=item.code)
        for item in advice
        if item.code not in {"emergency_999", "emergency_sms_992", "where_to_ask"}
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
        for code in weather.cancelled_codes:
            not_considered.append(f"actionCode:CANCEL:{code}")
        if weather.stale_as_of is not None:
            stale = weather.stale_as_of.isoformat()
    if personal is not None:
        if personal.is_domestic_helper is None:
            not_considered.append("is_domestic_helper")
        if personal.has_pets is None:
            not_considered.append("has_pets")
        if personal.has_bedridden is None:
            not_considered.append("has_bedridden")
        if personal.housing is None:
            not_considered.append("housing")
    return RiskResponse(
        abstained=abstained,
        abstain_reason=abstain_reason,
        fired_rules=fired_rules,
        advice=advice,
        blocks=blocks,
        block_outcomes=_block_outcomes(
            abstained=abstained,
            abstain_reason=abstain_reason,
            personal=personal,
            weather=weather,
        ),
        contact=compute_contact(weather),
        not_considered=not_considered,
        stale_as_of=stale,
    )


def _with_emergency(advice: list[AdviceItem], fired: list[str]) -> tuple[list[AdviceItem], list[str]]:
    emergency = get_rule("emergency_999")
    sms = get_rule("emergency_sms_992")
    ask = get_rule("where_to_ask")
    extra = [_advice_from_rule(emergency), _advice_from_rule(sms), _advice_from_rule(ask)]
    extra_ids = [emergency.id, sms.id, ask.id]
    return [*advice, *extra], [*fired, *extra_ids]


def abstain_incomplete() -> RiskResponse:
    rule = get_rule("abstain_incomplete_data")
    advice, fired = _with_emergency([], [rule.id])
    return pack_response(
        abstained=True,
        abstain_reason="数据不完整，不足以判断你所在位置的情况",
        fired_rules=fired,
        advice=advice,
    )


def abstain_sources_disagree() -> RiskResponse:
    rule = get_rule("abstain_source_disagreement")
    advice, fired = _with_emergency([], [rule.id])
    return pack_response(
        abstained=True,
        abstain_reason="warnsum 与实时天气报告不一致",
        fired_rules=fired,
        advice=advice,
    )


def _warning_codes(state: WeatherState) -> set[str]:
    return {item.code for item in state.warnings.values()}


def evaluate(personal: PersonalContext, weather: WeatherState) -> RiskResponse:
    if not isinstance(personal, PersonalContext) or not isinstance(weather, WeatherState):
        raise TypeError("evaluate accepts PersonalContext and WeatherState only")

    place = to_hko_place(personal.district) if personal.district else None
    if personal.district and place is None:
        rule = get_rule("abstain_out_of_scope")
        advice, fired = _with_emergency([], [rule.id])
        return pack_response(
            abstained=True,
            abstain_reason="地址不在本卡覆盖的香港十八区范围内",
            fired_rules=fired,
            advice=advice,
            weather=weather,
            personal=personal,
        )

    codes = _warning_codes(weather)
    fired: list[str] = []
    advice: list[AdviceItem] = []
    unconfirmed = _address_unconfirmed(personal)

    if not codes:
        status = get_rule("no_active_warning_status")
        fired.append(status.id)
        advice.append(_advice_from_rule(status))
        advice, fired = _with_emergency(advice, fired)
        return pack_response(
            abstained=False,
            abstain_reason=None,
            fired_rules=fired,
            advice=advice,
            weather=weather,
            personal=personal,
        )

    rain_present = RAIN_CODES.intersection(codes)
    if rain_present:
        top = max(rain_present, key=RAIN_ORDER.index)
        rain_rule = get_rule("rainstorm_level")
        fired.append(rain_rule.id)
        advice.append(_advice_from_rule(rain_rule, severity=RAIN_SEVERITY[top]))

    if not unconfirmed and "WRAINB" in codes and personal.is_domestic_helper is True:
        rule = get_rule("helper_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if not unconfirmed and "WRAINB" in codes and personal.has_pets is True:
        rule = get_rule("pets_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if not unconfirmed and "WRAINB" in codes and personal.has_bedridden is True:
        rule = get_rule("bedridden_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if (
        not unconfirmed
        and "WL" in codes
        and personal.housing is Housing.ROOFTOP
    ):
        rule = get_rule("rooftop_landslip")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    advice, fired = _with_emergency(advice, fired)
    return pack_response(
        abstained=False,
        abstain_reason=None,
        fired_rules=fired,
        advice=advice,
        weather=weather,
        personal=personal,
    )
