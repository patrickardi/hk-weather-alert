"""HKO / ALS wire models: exact JSON mirror. No domain, no coercion."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, RootModel

WIRE_CONFIG = ConfigDict(extra="allow", frozen=True)


class WireModel(BaseModel):
    model_config = WIRE_CONFIG


class WarnsumWarningItem(WireModel):
    name: str
    code: str
    type: str | None = None
    actionCode: str
    issueTime: str
    updateTime: str


class WarnsumDocument(RootModel[dict[str, WarnsumWarningItem]]):
    model_config = ConfigDict(frozen=True)


class RainfallRow(WireModel):
    unit: str
    place: str
    max: int
    main: Literal["FALSE", ""]


class RainfallBlock(WireModel):
    data: list[RainfallRow]
    startTime: str
    endTime: str


class TemperatureRow(WireModel):
    place: str
    value: int
    unit: str


class TemperatureBlock(WireModel):
    data: list[TemperatureRow]
    recordTime: str


class HumidityRow(WireModel):
    unit: str
    value: int
    place: str


class HumidityBlock(WireModel):
    recordTime: str
    data: list[HumidityRow]


class UvRow(WireModel):
    place: str
    value: int
    desc: str


class UvIndexObject(WireModel):
    data: list[UvRow]
    recordDesc: str


class RhrreadDocument(WireModel):
    rainfall: RainfallBlock
    warningMessage: list[str] | Literal[""]
    icon: list[int]
    iconUpdateTime: str
    uvindex: UvIndexObject | Literal[""]
    updateTime: str
    temperature: TemperatureBlock
    tcmessage: str
    mintempFrom00To09: str
    rainfallFrom00To12: str
    rainfallLastMonth: str
    rainfallJanuaryToLastMonth: str
    humidity: HumidityBlock


class RequestAddress(WireModel):
    AddressLine: list[str]


class EngStreet(WireModel):
    LocationName: str
    StreetName: str
    BuildingNoFrom: str


class EngDistrict(WireModel):
    DcDistrict: str


class EngPremisesAddress(WireModel):
    BuildingName: str
    EngStreet: EngStreet
    EngDistrict: EngDistrict
    Region: str


class ChiStreet(WireModel):
    LocationName: str
    StreetName: str
    BuildingNoFrom: str


class ChiDistrict(WireModel):
    DcDistrict: str


class ChiPremisesAddress(WireModel):
    Region: str
    ChiDistrict: ChiDistrict
    ChiStreet: ChiStreet
    BuildingName: str


class GeospatialInformation(WireModel):
    Northing: str
    Easting: str
    Latitude: str
    Longitude: str


class PremisesAddress(WireModel):
    EngPremisesAddress: EngPremisesAddress
    ChiPremisesAddress: ChiPremisesAddress
    GeoAddress: str
    GeospatialInformation: GeospatialInformation


class AlsAddress(WireModel):
    PremisesAddress: PremisesAddress


class ValidationInformation(WireModel):
    Score: float


class SuggestedAddress(WireModel):
    Address: AlsAddress
    ValidationInformation: ValidationInformation


class AlsDocument(WireModel):
    RequestAddress: RequestAddress
    SuggestedAddress: list[SuggestedAddress]


class UpstreamNotJson(ValueError):
    pass


def looks_like_json(content_type: str, body: str) -> bool:
    if "html" in (content_type or "").lower():
        return False
    stripped = (body or "").lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def parse_json_object(content_type: str, body: str) -> dict:
    if not looks_like_json(content_type, body):
        raise UpstreamNotJson("upstream body is not a JSON object")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise UpstreamNotJson("upstream body is not JSON") from exc
    if not isinstance(payload, dict):
        raise UpstreamNotJson("upstream JSON is not an object")
    return payload


def parse_warnsum(payload: dict) -> WarnsumDocument:
    return WarnsumDocument.model_validate(payload)


def parse_rhrread(payload: dict) -> RhrreadDocument:
    return RhrreadDocument.model_validate(payload)


def parse_als(payload: dict) -> AlsDocument:
    return AlsDocument.model_validate(payload)
