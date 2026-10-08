ALLOWED_SAFETY_CRITICAL_TIERS = {"quote_only", "template"}


def _attr(obj, name):
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def _rules():
    from app.rules import load_rules

    rules = load_rules()
    assert rules, "rules catalog must not be empty"
    return rules


def test_rule_ids_are_unique():
    ids = [_attr(rule, "id") for rule in _rules()]
    duplicates = sorted({rule_id for rule_id in ids if ids.count(rule_id) > 1})
    assert duplicates == [], f"duplicate rule ids: {duplicates}"


def test_safety_critical_rules_use_quote_only_or_template_tier():
    bad = []
    for rule in _rules():
        if not _attr(rule, "safety_critical"):
            continue
        tier = _attr(rule, "tier")
        value = tier.value if hasattr(tier, "value") else tier
        if value not in ALLOWED_SAFETY_CRITICAL_TIERS:
            bad.append((_attr(rule, "id"), value))
    assert bad == [], f"safety_critical rules must use quote_only or template: {bad}"


def test_safety_critical_rules_must_have_source():
    missing = []
    for rule in _rules():
        if not _attr(rule, "safety_critical"):
            continue
        source = _attr(rule, "source")
        if not source:
            missing.append(_attr(rule, "id"))
    assert missing == [], f"safety_critical rules missing source: {missing}"


def test_safety_critical_source_quote_has_no_todo():
    tainted = []
    for rule in _rules():
        if not _attr(rule, "safety_critical"):
            continue
        source = _attr(rule, "source")
        quote = _attr(source, "quote")
        if "TODO" in quote:
            tainted.append(_attr(rule, "id"))
    assert tainted == [], f"source.quote still contains TODO: {tainted}"
