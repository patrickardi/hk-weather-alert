from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Severity(str, Enum):
    ADVISORY = "advisory"
    CAUTION = "caution"
    WARNING = "warning"
    DANGER = "danger"


class Provenance(str, Enum):
    QUOTE_ONLY = "quote_only"
    TEMPLATE = "template"


class ActiveWarning(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    warning_key: str
    code: str
    name: str
    warning_type: str | None = None
    action_code: str
    issue_time: datetime
    update_time: datetime


class RainfallAtPlace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    place: str
    max_mm: float | None = None
    is_main: bool | None = None


class TemperatureAtPlace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    place: str
    value_c: int


class HumidityObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    place: str
    value_percent: int
    record_time: datetime


class UvObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    place: str
    value: int
    desc: str
    record_desc: str


class PersonalContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_address: str
    district: str
    latitude: float
    longitude: float
    northing: float | None = None
    easting: float | None = None
    building_name_zh: str | None = None
    building_name_en: str | None = None
    geocode_score: float
    is_domestic_helper: bool = False
    has_pets: bool = False
    housing: str = "standard"
    has_bedridden: bool = False


class WeatherState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observed_at: datetime | None = None
    fetched_at: datetime | None = None
    source_updated_at: dict[str, datetime] = Field(default_factory=dict)
    icon_codes: list[int] = Field(default_factory=list)
    icon_update_time: datetime | None = None
    warning_messages: list[str] = Field(default_factory=list)
    rainfall_start_time: datetime | None = None
    rainfall_end_time: datetime | None = None
    rainfall: list[RainfallAtPlace] = Field(default_factory=list)
    temperatures: list[TemperatureAtPlace] = Field(default_factory=list)
    temperature_record_time: datetime | None = None
    humidity: HumidityObservation | None = None
    uv_index: UvObservation | None = None
    warnings: dict[str, ActiveWarning] = Field(default_factory=dict)

    @property
    def stale_as_of(self) -> datetime | None:
        if not self.source_updated_at:
            return None
        return min(self.source_updated_at.values())


class CardBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    title: str
    body: str
    code: str = ""


class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    hotline: str = "999"
    label: str = "如遇紧急情况，请致电 999"


class AdviceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    title: str
    body: str
    safety_critical: bool
    tier: Severity
    provenance: Provenance = Provenance.TEMPLATE
    source_url: str = ""
    source_label: str = ""
    quote: str | None = None

    @model_validator(mode="after")
    def _safety_critical_needs_source(self):
        if self.safety_critical:
            if not self.source_url:
                raise ValueError(f"{self.code}: safety_critical needs source_url")
            if self.provenance is Provenance.QUOTE_ONLY:
                if not self.quote or "TODO" in self.quote:
                    raise ValueError(f"{self.code}: quote_only needs a real quote")
        return self


class RiskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    abstained: bool
    abstain_reason: str | None = None
    fired_rules: list[str] = Field(default_factory=list)
    advice: list[AdviceItem] = Field(default_factory=list)
    blocks: list[CardBlock] = Field(default_factory=list)
    contact: ContactInfo | None = None
    not_considered: list[str] = Field(default_factory=list)
    stale_as_of: str | None = None

    @model_validator(mode="after")
    def _abstain_contract(self):
        if self.abstained:
            if not self.abstain_reason:
                raise ValueError("弃答必须有理由")
        elif self.abstain_reason is not None:
            raise ValueError("未弃答不应有 abstain_reason")
        return self


class RuleSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    quote: str
    url: str = ""
    label: str = ""


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    safety_critical: bool
    tier: Provenance
    source: RuleSource
    severity: Severity
    title: str
    body: str
