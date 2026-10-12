from datetime import datetime

from pydantic import ValidationError

from app.engine import abstain_incomplete, abstain_sources_disagree, evaluate
from app.schemas import (
    ActiveWarning,
    Housing,
    HumidityObservation,
    PersonalContext,
    RainfallAtPlace,
    RiskResponse,
    TemperatureAtPlace,
    UvObservation,
    WeatherState,
)
from app.wire import (
    AlsDocument,
    RhrreadDocument,
    UpstreamNotJson,
    UvIndexObject,
    WarnsumDocument,
    parse_als,
    parse_json_object,
    parse_rhrread,
    parse_warnsum,
)


def _as_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _as_main(value: str) -> bool | None:
    if value == "TRUE":
        return True
    if value == "FALSE":
        return False
    return None


def sources_disagree(warnsum: WarnsumDocument, rhrread: RhrreadDocument) -> bool:
    warnsum_empty = len(warnsum.root) == 0
    raw = rhrread.warningMessage
    messages_empty = raw == "" or raw == []
    return warnsum_empty != messages_empty


def to_weather(warnsum: WarnsumDocument, rhrread: RhrreadDocument) -> WeatherState:
    warnings: dict[str, ActiveWarning] = {}
    cancelled: list[str] = []
    source_updated: dict[str, datetime] = {"rhrread": _as_dt(rhrread.updateTime)}
    for key, item in warnsum.root.items():
        if item.actionCode == "CANCEL":
            cancelled.append(item.code)
            continue
        warnings[key] = ActiveWarning(
            warning_key=key,
            code=item.code,
            name=item.name,
            warning_type=item.type,
            action_code=item.actionCode,
            issue_time=_as_dt(item.issueTime),
            update_time=_as_dt(item.updateTime),
        )
        source_updated[f"warnsum:{item.code}"] = _as_dt(item.updateTime)

    raw_messages = rhrread.warningMessage
    warning_messages = [] if raw_messages == "" else list(raw_messages)

    uv_index = None
    if isinstance(rhrread.uvindex, UvIndexObject) and rhrread.uvindex.data:
        first = rhrread.uvindex.data[0]
        uv_index = UvObservation(
            place=first.place,
            value=first.value,
            desc=first.desc,
            record_desc=rhrread.uvindex.recordDesc,
        )

    rainfall = []
    for row in rhrread.rainfall.data:
        rainfall.append(
            RainfallAtPlace(
                place=row.place,
                max_mm=float(row.max),
                is_main=_as_main(row.main),
            )
        )

    temperatures = [
        TemperatureAtPlace(place=row.place, value_c=row.value)
        for row in rhrread.temperature.data
    ]

    humidity = None
    if rhrread.humidity and rhrread.humidity.data:
        hum = rhrread.humidity.data[0]
        humidity = HumidityObservation(
            place=hum.place,
            value_percent=hum.value,
            record_time=_as_dt(rhrread.humidity.recordTime),
        )

    observed = _as_dt(rhrread.updateTime)
    icon_update = _as_dt(rhrread.iconUpdateTime) if rhrread.iconUpdateTime else None
    return WeatherState(
        observed_at=observed,
        fetched_at=observed,
        source_updated_at=source_updated,
        icon_codes=list(rhrread.icon),
        icon_update_time=icon_update,
        warning_messages=warning_messages,
        rainfall_start_time=_as_dt(rhrread.rainfall.startTime),
        rainfall_end_time=_as_dt(rhrread.rainfall.endTime),
        rainfall=rainfall,
        temperatures=temperatures,
        temperature_record_time=_as_dt(rhrread.temperature.recordTime),
        humidity=humidity,
        uv_index=uv_index,
        warnings=warnings,
        cancelled_codes=cancelled,
    )


def to_personal(als: AlsDocument, **flags) -> PersonalContext:
    line = als.RequestAddress.AddressLine[0] if als.RequestAddress.AddressLine else ""
    alternatives = []
    for item in als.SuggestedAddress:
        premises = item.Address.PremisesAddress
        chi = premises.ChiPremisesAddress
        eng = premises.EngPremisesAddress
        name = None
        if chi and chi.BuildingName:
            name = chi.BuildingName
        elif eng and eng.BuildingName:
            name = eng.BuildingName
        if name:
            alternatives.append(name)
    housing = flags.get("housing", None)
    if housing is not None and not isinstance(housing, Housing):
        housing = Housing(housing)
    if not als.SuggestedAddress:
        return PersonalContext(
            request_address=line,
            district="",
            geocode_candidate_count=0,
            geocode_alternatives=[],
            is_domestic_helper=flags.get("is_domestic_helper"),
            has_pets=flags.get("has_pets"),
            housing=housing,
            has_bedridden=flags.get("has_bedridden"),
        )
    top = als.SuggestedAddress[0]
    premises = top.Address.PremisesAddress
    chi = premises.ChiPremisesAddress
    eng = premises.EngPremisesAddress
    geo = premises.GeospatialInformation
    district = ""
    if chi and chi.ChiDistrict and chi.ChiDistrict.DcDistrict:
        district = chi.ChiDistrict.DcDistrict
    elif eng and eng.EngDistrict and eng.EngDistrict.DcDistrict:
        district = eng.EngDistrict.DcDistrict
    score = None
    if top.ValidationInformation and top.ValidationInformation.Score is not None:
        score = float(top.ValidationInformation.Score)
    return PersonalContext(
        request_address=line,
        district=district,
        latitude=float(geo.Latitude) if geo and geo.Latitude else None,
        longitude=float(geo.Longitude) if geo and geo.Longitude else None,
        northing=float(geo.Northing) if geo and geo.Northing else None,
        easting=float(geo.Easting) if geo and geo.Easting else None,
        building_name_zh=chi.BuildingName if chi else None,
        building_name_en=eng.BuildingName if eng else None,
        geocode_score=score,
        geocode_candidate_count=len(als.SuggestedAddress),
        geocode_alternatives=alternatives,
        is_domestic_helper=flags.get("is_domestic_helper"),
        has_pets=flags.get("has_pets"),
        housing=housing,
        has_bedridden=flags.get("has_bedridden"),
    )


def weather_from_hko(warnsum: dict, rhrread: dict) -> WeatherState:
    return to_weather(parse_warnsum(warnsum), parse_rhrread(rhrread))


def personal_from_als(payload: dict, **flags) -> PersonalContext:
    return to_personal(parse_als(payload), **flags)


def build_card(
    *,
    personal: PersonalContext | dict,
    warnsum_body: str,
    warnsum_ctype: str,
    rhrread_body: str,
    rhrread_ctype: str,
) -> RiskResponse:
    try:
        warnsum_payload = parse_json_object(warnsum_ctype, warnsum_body)
        rhrread_payload = parse_json_object(rhrread_ctype, rhrread_body)
        warnsum = parse_warnsum(warnsum_payload)
        rhrread = parse_rhrread(rhrread_payload)
        ctx = (
            personal
            if isinstance(personal, PersonalContext)
            else PersonalContext.model_validate(personal)
        )
        if sources_disagree(warnsum, rhrread):
            return abstain_sources_disagree()
        weather = to_weather(warnsum, rhrread)
    except (UpstreamNotJson, ValidationError, ValueError, TypeError):
        return abstain_incomplete()
    return evaluate(ctx, weather)
