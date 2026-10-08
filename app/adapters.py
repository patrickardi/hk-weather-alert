from datetime import datetime

from pydantic import ValidationError

from app.engine import abstain_incomplete, evaluate
from app.schemas import (
    ActiveWarning,
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


def to_weather(warnsum: WarnsumDocument, rhrread: RhrreadDocument) -> WeatherState:
    warnings: dict[str, ActiveWarning] = {}
    source_updated: dict[str, datetime] = {"rhrread": _as_dt(rhrread.updateTime)}
    for key, item in warnsum.root.items():
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
        is_main = None if row.main == "" else False
        rainfall.append(
            RainfallAtPlace(
                place=row.place,
                max_mm=float(row.max),
                is_main=is_main,
            )
        )

    temperatures = [
        TemperatureAtPlace(place=row.place, value_c=row.value)
        for row in rhrread.temperature.data
    ]

    humidity = None
    if rhrread.humidity.data:
        hum = rhrread.humidity.data[0]
        humidity = HumidityObservation(
            place=hum.place,
            value_percent=hum.value,
            record_time=_as_dt(rhrread.humidity.recordTime),
        )

    observed = _as_dt(rhrread.updateTime)
    return WeatherState(
        observed_at=observed,
        fetched_at=observed,
        source_updated_at=source_updated,
        icon_codes=list(rhrread.icon),
        icon_update_time=_as_dt(rhrread.iconUpdateTime),
        warning_messages=warning_messages,
        rainfall_start_time=_as_dt(rhrread.rainfall.startTime),
        rainfall_end_time=_as_dt(rhrread.rainfall.endTime),
        rainfall=rainfall,
        temperatures=temperatures,
        temperature_record_time=_as_dt(rhrread.temperature.recordTime),
        humidity=humidity,
        uv_index=uv_index,
        warnings=warnings,
    )


def to_personal(als: AlsDocument, **flags) -> PersonalContext:
    if not als.SuggestedAddress:
        raise ValueError("ALS returned no candidates")
    top = als.SuggestedAddress[0]
    premises = top.Address.PremisesAddress
    chi = premises.ChiPremisesAddress
    eng = premises.EngPremisesAddress
    geo = premises.GeospatialInformation
    line = als.RequestAddress.AddressLine[0] if als.RequestAddress.AddressLine else ""
    return PersonalContext(
        request_address=line,
        district=chi.ChiDistrict.DcDistrict,
        latitude=float(geo.Latitude),
        longitude=float(geo.Longitude),
        northing=float(geo.Northing),
        easting=float(geo.Easting),
        building_name_zh=chi.BuildingName or None,
        building_name_en=eng.BuildingName or None,
        geocode_score=float(top.ValidationInformation.Score),
        is_domestic_helper=bool(flags.get("is_domestic_helper", False)),
        has_pets=bool(flags.get("has_pets", False)),
        housing=str(flags.get("housing", "standard")),
        has_bedridden=bool(flags.get("has_bedridden", False)),
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
        ctx = (
            personal
            if isinstance(personal, PersonalContext)
            else PersonalContext.model_validate(personal)
        )
        weather = weather_from_hko(warnsum_payload, rhrread_payload)
    except (UpstreamNotJson, ValidationError, ValueError, TypeError):
        return abstain_incomplete()
    return evaluate(ctx, weather)
