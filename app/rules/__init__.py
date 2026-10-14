from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import yaml

from app.schemas import ContactSpec, HotlineMode, Provenance, Rule, RuleSource, Severity

RULES_DIR = Path(__file__).parent


def _parse_retrieved_on(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _source(raw: dict) -> RuleSource:
    return RuleSource(
        quote=raw["quote"],
        url=raw.get("url", ""),
        label=str(raw.get("label") or ""),
        retrieved_on=_parse_retrieved_on(raw.get("retrieved_on")),
    )


def _parse_rules(payload: dict) -> list[Rule]:
    rules: list[Rule] = []
    for raw in payload.get("rules") or []:
        provenance = raw.get("provenance", raw.get("tier"))
        rules.append(
            Rule(
                id=raw["id"],
                safety_critical=raw["safety_critical"],
                provenance=Provenance(provenance),
                source=_source(raw["source"]),
                severity=Severity(raw["severity"]),
                title=raw["title"],
                body=raw["body"],
                title_en=raw.get("title_en") or "",
                body_en=raw.get("body_en") or "",
            )
        )
    return rules


def _parse_contacts(payload: dict) -> list[ContactSpec]:
    contacts: list[ContactSpec] = []
    for raw in payload.get("contacts") or []:
        contacts.append(
            ContactSpec(
                id=raw["id"],
                mode=HotlineMode(raw["mode"]),
                codes=tuple(raw.get("codes") or ()),
                types=tuple(raw.get("types") or ()),
                had_hotline=raw.get("had_hotline"),
                had_hours=raw.get("had_hours"),
                enquiry=raw.get("enquiry", "1823"),
                default=bool(raw.get("default", False)),
                source=_source(raw["source"]),
            )
        )
    return contacts


def _load_payloads() -> tuple[list[Rule], list[ContactSpec]]:
    rules: list[Rule] = []
    contacts: list[ContactSpec] = []
    for path in sorted(RULES_DIR.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        rules.extend(_parse_rules(payload))
        contacts.extend(_parse_contacts(payload))
    return rules, contacts


@lru_cache(maxsize=1)
def load_rules() -> list[Rule]:
    return _load_payloads()[0]


@lru_cache(maxsize=1)
def load_contacts() -> list[ContactSpec]:
    return _load_payloads()[1]


def get_rule(rule_id: str) -> Rule:
    for rule in load_rules():
        if rule.id == rule_id:
            return rule
    raise KeyError(rule_id)
