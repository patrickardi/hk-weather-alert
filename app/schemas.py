from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

FALLBACK_CODES = frozenset({"emergency_999", "emergency_sms_992", "where_to_ask"})
TC8_PLUS_TYPES = frozenset({"TC8NE", "TC8SE", "TC8NW", "TC8SW", "TC9", "TC10"})
HAD_ROUND_THE_CLOCK_CODES = frozenset({"WRAINR", "WRAINB", "WL"})
BANNED_PHRASES = frozenset({"typhoon shelter", "Typhoon shelter", "避风塘"})


class Severity(str, Enum):
    ADVISORY = "advisory"
    CAUTION = "caution"
    WARNING = "warning"
    DANGER = "danger"

    @property
    def rank(self) -> int:
        return {
            Severity.ADVISORY: 1,
            Severity.CAUTION: 2,
            Severity.WARNING: 3,
            Severity.DANGER: 4,
        }[self]


class Provenance(str, Enum):
    QUOTE_ONLY = "quote_only"
    TEMPLATE = "template"


class Housing(str, Enum):
    STANDARD = "standard"
    ROOFTOP = "rooftop"
    SQUATTER = "squatter"
    TONG_LAU = "tong_lau"
    SUBDIVIDED = "subdivided_flat"


class Block(str, Enum):
    ACTIVE_WARNINGS = "active_warnings"
    LOCAL_OBSERVATION = "local_observation"
    SHELTER = "shelter"
    HOUSING_RISK = "housing_risk"
    WORK = "work"
    CONTACT = "contact"


class HotlineMode(str, Enum):
    HAD_ROUND_THE_CLOCK = "had_round_the_clock"
    HAD_UNTIL_MIDNIGHT = "had_until_midnight"
    GOV_1823 = "gov_1823"


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
    district: str = ""
    latitude: float | None = None
    longitude: float | None = None
    northing: float | None = None
    easting: float | None = None
    building_name_zh: str | None = None
    building_name_en: str | None = None
    geocode_score: float | None = None
    geocode_candidate_count: int | None = None
    geocode_alternatives: list[str] = Field(default_factory=list)
    is_domestic_helper: bool | None = None
    has_pets: bool | None = None
    housing: Housing | None = None
    has_bedridden: bool | None = None


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
    cancelled_codes: list[str] = Field(default_factory=list)

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


class BlockOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block: Block
    rendered: bool
    omitted_reason: str | None = None

    @model_validator(mode="after")
    def _omitted_reason_required(self):
        if not self.rendered and not self.omitted_reason:
            raise ValueError("omitted_reason required when rendered is False")
        if self.rendered and self.omitted_reason is not None:
            raise ValueError("rendered block must not have omitted_reason")
        return self


class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    hotline: str = "999"
    label: str = "如遇紧急情况，请致电"
    sms_hotline: str = "992"
    had_hotline: str | None = None
    had_hours: str | None = None
    enquiry: str = "1823"
    mode: HotlineMode = HotlineMode.GOV_1823


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
    retrieved_on: date | None = None

    @model_validator(mode="after")
    def _safety_critical_needs_source(self):
        if self.safety_critical:
            if not self.source_url:
                raise ValueError(f"{self.code}: safety_critical needs source_url")
            if self.retrieved_on is None:
                raise ValueError(f"{self.code}: safety_critical needs retrieved_on")
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
    block_outcomes: list[BlockOutcome] = Field(default_factory=list)
    contact: ContactInfo | None = None
    not_considered: list[str] = Field(default_factory=list)
    stale_as_of: str | None = None

    @model_validator(mode="after")
    def _abstain_contract(self):
        if self.abstained:
            if not self.abstain_reason:
                raise ValueError("弃答必须有理由")
            codes = {item.code for item in self.advice}
            if not codes.intersection(FALLBACK_CODES):
                raise ValueError("弃答必须含 fallback 热线")
        elif self.abstain_reason is not None:
            raise ValueError("未弃答不应有 abstain_reason")
        return self


class RuleSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    quote: str
    url: str = ""
    label: str = ""
    retrieved_on: date | None = None


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    safety_critical: bool
    provenance: Provenance
    source: RuleSource
    severity: Severity
    title: str
    body: str

    @model_validator(mode="after")
    def _safety_critical_source(self):
        if self.safety_critical:
            if not self.source.url:
                raise ValueError(f"{self.id}: safety_critical needs source.url")
            if self.source.retrieved_on is None:
                raise ValueError(f"{self.id}: safety_critical needs retrieved_on")
            if "TODO" in self.source.quote:
                raise ValueError(f"{self.id}: source.quote still contains TODO")
        return self
