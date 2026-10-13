from app.mapping import to_hko_place
from app.rules import get_rule, load_contacts
from app.schemas import (
    AdviceItem,
    Block,
    BlockOutcome,
    CardBlock,
    ContactInfo,
    ContactSpec,
    Housing,
    PersonalContext,
    RiskResponse,
    Rule,
    SHELTER_OMIT_REASON,
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


def _contact_from_spec(spec: ContactSpec) -> ContactInfo:
    return ContactInfo(
        had_hotline=spec.had_hotline,
        had_hours=spec.had_hours,
        enquiry=spec.enquiry,
        mode=spec.mode,
        source_url=spec.source.url,
        source_label=spec.source.label,
        retrieved_on=spec.source.retrieved_on,
    )


def compute_contact(weather: WeatherState | None) -> ContactInfo:
    specs = load_contacts()
    default = next((item for item in specs if item.default), None)
    if weather is None:
        return _contact_from_spec(default) if default else ContactInfo()
    codes = {item.code for item in weather.warnings.values()}
    types = {item.warning_type for item in weather.warnings.values() if item.warning_type}
    for spec in specs:
        if spec.default:
            continue
        if codes.intersection(spec.codes) or types.intersection(spec.types):
            return _contact_from_spec(spec)
    return _contact_from_spec(default) if default else ContactInfo()


def _address_unconfirmed(personal: PersonalContext | None) -> bool:
    if personal is None:
        return True
    count = personal.geocode_candidate_count
    if count is None:
        return False
    return count != 1


def _human_not_considered(key: str) -> str:
    labels = {
        "weather_snapshot": "没有天气快照",
        "uv_index": "紫外线指数未知",
        "is_domestic_helper": "未询问是否外佣",
        "has_pets": "未询问是否有宠物",
        "has_bedridden": "未询问家中是否有卧床者",
        "housing": "未询问住所类型",
    }
    if key in labels:
        return labels[key]
    if key.startswith("rainfall.main:"):
        place = key.split(":", 1)[1]
        return f"{place}的雨量主站标记未知"
    if key.startswith("actionCode:CANCEL:"):
        code = key.split(":")[-1]
        return f"{code}警告已取消，不计入生效警告"
    return key


def _block_outcomes(
    *,
    abstained: bool,
    abstain_reason: str | None,
    personal: PersonalContext | None,
    weather: WeatherState | None,
) -> list[BlockOutcome]:
    if abstained:
        reason = abstain_reason or "资料不足，无法给出针对你处境的行动建议"
        return [
            BlockOutcome(block=Block.ACTIVE_WARNINGS, rendered=False, omitted_reason=reason),
            BlockOutcome(block=Block.LOCAL_OBSERVATION, rendered=False, omitted_reason=reason),
            BlockOutcome(block=Block.SHELTER, rendered=False, omitted_reason=SHELTER_OMIT_REASON),
            BlockOutcome(block=Block.HOUSING_RISK, rendered=False, omitted_reason=reason),
            BlockOutcome(
                block=Block.WORK,
                rendered=False,
                omitted_reason="劳工处工作热压力警告不在天文台警告摘要内，本卡不覆盖休息安排",
            ),
            BlockOutcome(block=Block.CONTACT, rendered=True),
        ]
    unconfirmed = _address_unconfirmed(personal)
    place = to_hko_place(personal.district) if personal and personal.district else None
    local_ok = place is not None
    housing_ok = bool(personal and personal.housing is not None and not unconfirmed)
    if personal is None or personal.housing is None:
        housing_reason = "未询问住所类型，未纳入住屋风险"
    elif unconfirmed:
        housing_reason = "地址未能唯一对应，不显示住屋风险"
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
            omitted_reason=SHELTER_OMIT_REASON,
        ),
        BlockOutcome(
            block=Block.HOUSING_RISK,
            rendered=housing_ok,
            omitted_reason=None if housing_ok else housing_reason,
        ),
        BlockOutcome(
            block=Block.WORK,
            rendered=False,
            omitted_reason="劳工处工作热压力警告不在天文台警告摘要内，本卡不覆盖休息安排",
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
        not_considered=[_human_not_considered(item) for item in not_considered],
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
        abstain_reason="天文台警告摘要与分区天气报告不一致，无法判断当前警告",
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

    if "WRAINB" in codes and personal.is_domestic_helper is True:
        rule = get_rule("helper_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if "WRAINB" in codes and personal.has_pets is True:
        rule = get_rule("pets_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if "WRAINB" in codes and personal.has_bedridden is True:
        rule = get_rule("bedridden_black_rain")
        fired.append(rule.id)
        advice.append(_advice_from_rule(rule))

    if "WL" in codes and personal.housing is Housing.ROOFTOP:
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
