"""HKO / ALS wire models: exact JSON mirror. No domain, no coercion."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

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
    max: int | float | str
    main: str


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
    icon: list[int] = Field(default_factory=list)
    iconUpdateTime: str | None = None
    uvindex: UvIndexObject | Literal[""] = ""
    updateTime: str
    temperature: TemperatureBlock
    tcmessage: str | None = None
    mintempFrom00To09: str | None = None
    rainfallFrom00To12: str | None = None
    rainfallLastMonth: str | None = None
    rainfallJanuaryToLastMonth: str | None = None
    humidity: HumidityBlock | None = None


class RequestAddress(WireModel):
    AddressLine: list[str] = Field(default_factory=list)


class EngStreet(WireModel):
    LocationName: str | None = None
    StreetName: str | None = None
    BuildingNoFrom: str | None = None


class EngDistrict(WireModel):
    DcDistrict: str | None = None


_EngStreetAlias = EngStreet
_EngDistrictAlias = EngDistrict


class EngPremisesAddress(WireModel):
    BuildingName: str | None = None
    EngStreet: _EngStreetAlias | None = None
    EngDistrict: _EngDistrictAlias | None = None
    Region: str | None = None


class ChiStreet(WireModel):
    LocationName: str | None = None
    StreetName: str | None = None
    BuildingNoFrom: str | None = None


class ChiDistrict(WireModel):
    DcDistrict: str | None = None


_ChiStreetAlias = ChiStreet
_ChiDistrictAlias = ChiDistrict


class ChiPremisesAddress(WireModel):
    Region: str | None = None
    ChiDistrict: _ChiDistrictAlias | None = None
    ChiStreet: _ChiStreetAlias | None = None
    BuildingName: str | None = None


class GeospatialInformation(WireModel):
    Northing: str | None = None
    Easting: str | None = None
    Latitude: str | None = None
    Longitude: str | None = None


_EngPremisesAddressAlias = EngPremisesAddress
_ChiPremisesAddressAlias = ChiPremisesAddress
_GeospatialInformationAlias = GeospatialInformation


class PremisesAddress(WireModel):
    EngPremisesAddress: _EngPremisesAddressAlias | None = None
    ChiPremisesAddress: _ChiPremisesAddressAlias | None = None
    GeoAddress: str | None = None
    GeospatialInformation: _GeospatialInformationAlias | None = None


class AlsAddress(WireModel):
    PremisesAddress: PremisesAddress


class ValidationInformation(WireModel):
    Score: float | None = None


_ValidationInformationAlias = ValidationInformation


class SuggestedAddress(WireModel):
    Address: AlsAddress
    ValidationInformation: _ValidationInformationAlias | None = None


_RequestAddressAlias = RequestAddress
_SuggestedAddressAlias = SuggestedAddress


class AlsDocument(WireModel):
    RequestAddress: _RequestAddressAlias
    SuggestedAddress: list[_SuggestedAddressAlias] = Field(default_factory=list)


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
