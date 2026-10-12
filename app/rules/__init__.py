from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import yaml

from app.schemas import Provenance, Rule, RuleSource, Severity

RULES_DIR = Path(__file__).parent


def _parse_retrieved_on(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _parse_file(path: Path) -> list[Rule]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules: list[Rule] = []
    for raw in payload.get("rules") or []:
        source = raw["source"]
        provenance = raw.get("provenance", raw.get("tier"))
        rules.append(
            Rule(
                id=raw["id"],
                safety_critical=raw["safety_critical"],
                provenance=Provenance(provenance),
                source=RuleSource(
                    quote=source["quote"],
                    url=source.get("url", ""),
                    label=source.get("label", ""),
                    retrieved_on=_parse_retrieved_on(source.get("retrieved_on")),
                ),
                severity=Severity(raw["severity"]),
                title=raw["title"],
                body=raw["body"],
            )
        )
    return rules


@lru_cache(maxsize=1)
def load_rules() -> list[Rule]:
    rules: list[Rule] = []
    for path in sorted(RULES_DIR.glob("*.yaml")):
        rules.extend(_parse_file(path))
    return rules


def get_rule(rule_id: str) -> Rule:
    for rule in load_rules():
        if rule.id == rule_id:
            return rule
    raise KeyError(rule_id)
