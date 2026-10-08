from app.schemas import (
    AdviceItem,
    CardBlock,
    ContactInfo,
    Provenance,
    RiskResponse,
    Severity,
)

_RAIN = AdviceItem(
    code="rainstorm_level",
    title="暴雨警告",
    body="请留意最新暴雨警告，减少非必要外出。",
    safety_critical=True,
    tier=Severity.WARNING,
    provenance=Provenance.QUOTE_ONLY,
    source_url="https://www.hko.gov.hk/tc/wservice/warning/rainstor.htm",
    source_label="香港天文台",
    quote="市民应留意最新的暴雨警告，采取适当防御措施。",
)

_EMERGENCY = AdviceItem(
    code="emergency_999",
    title="紧急求助",
    body="如遇紧急情况，请致电 999。",
    safety_critical=True,
    tier=Severity.DANGER,
    provenance=Provenance.QUOTE_ONLY,
    source_url="https://www.police.gov.hk/ppp_tc/contact_us.html",
    source_label="香港警务处",
    quote="如遇紧急情况，请致电 999。",
)

SAMPLES = {
    "wushan_red_rain_partial": RiskResponse(
        abstained=False,
        fired_rules=["rainstorm_level", "emergency_999"],
        advice=[_RAIN, _EMERGENCY],
        blocks=[
            CardBlock(
                kind="dont",
                title=_RAIN.title,
                body=_RAIN.body,
                code=_RAIN.code,
            )
        ],
        contact=ContactInfo(),
        not_considered=["uv_index", "rainfall.main:屯門"],
        stale_as_of="2026-09-25T14:00:00+08:00",
    )
}
