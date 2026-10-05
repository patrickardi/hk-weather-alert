from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class CitationFootnote(BaseModel):
    source_url: HttpUrl=Field(...,description="Official HK government or meteorological source URL")
    ##requires web link from official gov
    retrieved_at: str=Field(...,description="Date fetched/recorded (YYYY-MM-DD)")
    verified_by: str=Field(...,description="Team member who verified this entry")


class EmergencyShelter(BaseModel):
    shelter_id: str
    name_en: str
    name_indo: Optional[str]=Field(None,description="Indonesian translation")
    address: str
    coordinates: dict=Field(...,example={  "lat":22.2819 , "lng": 114.1581  })
    citation: CitationFootnote


class ActionOutput(BaseModel):
    timestamp: str
    user_status: str
    do_actions:   List[str]
    dont_actions:   List[str]
    escalation_hotline:  Optional[str]=None
    citation_footnotes: List[CitationFootnote]
    ## do and dont actions , optional hotline number , citations


class Provenance(str, Enum):
    TEMPLATE = "template"
    QUOTE_ONLY = "quote_only"


class Severity(str, Enum):
    ADVISORY = "advisory"
    CAUTION = "caution"
    WARNING = "warning"
    DANGER = "danger"

    @property
    def rank(self) -> int:           # §5.4：别再让字符串比较决定顺序
        return _SEVERITY_RANK[self]

_SEVERITY_RANK = {Severity.ADVISORY: 0, Severity.CAUTION: 1,
                  Severity.WARNING: 2, Severity.DANGER: 3}


class Block(str, Enum):              # §5.1
    ACTIVE_WARNINGS = "active_warnings"
    LOCAL_OBSERVATION = "local_observation"
    SHELTER = "shelter"
    HOUSING_RISK = "housing_risk"
    WORK = "work"
    CONTACT = "contact"


class BlockOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    block: Block
    rendered: bool
    omitted_reason: str | None = None

    @model_validator(mode="after")
    def _reason_iff_omitted(self):
        if not self.rendered and not self.omitted_reason:
            raise ValueError(f"{self.block.value}: omitted block needs a reason")
        if self.rendered and self.omitted_reason is not None:
            raise ValueError(f"{self.block.value}: rendered block must not carry a reason")
        return self


class HotlineMode(str, Enum):        # §6.1
    ROUND_THE_CLOCK = "round_the_clock"   # T8+/山泥傾瀉/紅黑雨
    UNTIL_MIDNIGHT = "until_midnight"     # 僅酷熱
    NONE = "none"                         # → 1823


class ContactBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    emergency: str = "999"
    emergency_sms_fax: str = "992"
    general_enquiry: str = "1823"
    hotline_number: str | None
    hotline_mode: HotlineMode
    hotline_closes_at: datetime | None     # UNTIL_MIDNIGHT 时必填，印成时间不印"午夜"
    callback_caller_id_withheld: bool      # §6 的来电不显示号码提醒

    @model_validator(mode="after")
    def _midnight_needs_time(self):
        if self.hotline_mode is HotlineMode.UNTIL_MIDNIGHT and self.hotline_closes_at is None:
            raise ValueError("until_midnight needs hotline_closes_at")
        if self.hotline_mode is HotlineMode.NONE and self.hotline_number is not None:
            raise ValueError("mode=none must not carry a hotline number")
        return self


class AdviceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    block: Block                           # 新增：设计靠它决定放哪
    title: str
    body: str
    safety_critical: bool
    tier: Severity
    provenance: Provenance = Provenance.TEMPLATE
    source_url: str = ""
    source_label: str = ""
    quote: str | None = None
    retrieved_on: date | None = None       # 新增（README §3）

    @model_validator(mode="after")
    def _safety_critical_needs_source(self):
        if self.safety_critical:
            if not self.source_url:
                raise ValueError(f"{self.code}: safety_critical needs source_url")
            if self.retrieved_on is None:
                raise ValueError(f"{self.code}: safety_critical needs retrieved_on")
            if self.provenance is Provenance.QUOTE_ONLY and (not self.quote or "TODO" in self.quote):
                raise ValueError(f"{self.code}: quote_only needs a real quote")
        return self

FALLBACK_CODES = frozenset({"emergency_999", "emergency_sms_992", "where_to_ask"})


class RiskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    abstained: bool
    abstain_reason: str | None = None
    stale_as_of: datetime | None           # 必填：None 要显式写，卡上印「時間未知」
    blocks: list[BlockOutcome]             # 必填：六个块各出现一次
    contact: ContactBlock                  # 必填
    not_considered: list[str]              # 必填：[] 也要显式写（§5.2）
    fired_rules: list[str] = Field(default_factory=list)
    advice: list[AdviceItem] = Field(default_factory=list)

    @property
    def rendered_blocks(self) -> set[Block]:
        return {b.block for b in self.blocks if b.rendered}

    @model_validator(mode="after")
    def _contract(self):
        if self.abstained and not self.abstain_reason:
            raise ValueError("弃答必须有理由")
        if not self.abstained and self.abstain_reason is not None:
            raise ValueError("未弃答不应有 abstain_reason")
        seen = [b.block for b in self.blocks]
        if sorted(seen) != sorted(Block):
            raise ValueError("blocks must list every Block exactly once")
        rendered = self.rendered_blocks
        for item in self.advice:
            if item.block not in rendered:
                raise ValueError(f"{item.code}: advice placed in an omitted block")
        for blk in rendered:                        # rendered ≠ blank
            if not any(a.block is blk for a in self.advice):
                raise ValueError(f"{blk.value}: rendered but has no content")
        if self.abstained and not FALLBACK_CODES & {a.code for a in self.advice}:
            raise ValueError("abstain is never blank (§5.3)")      # §5.3
        return self