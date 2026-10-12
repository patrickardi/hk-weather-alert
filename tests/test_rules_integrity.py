def _rules():
    from app.rules import load_rules

    rules = load_rules()
    assert rules, "rules catalog must not be empty"
    return rules


def test_rule_ids_are_unique():
    ids = [rule.id for rule in _rules()]
    duplicates = sorted({rule_id for rule_id in ids if ids.count(rule_id) > 1})
    assert duplicates == [], f"duplicate rule ids: {duplicates}"


def test_safety_critical_rules_must_have_url_and_retrieved_on():
    missing = []
    for rule in _rules():
        if not rule.safety_critical:
            continue
        if not rule.source.url or rule.source.retrieved_on is None:
            missing.append(rule.id)
    assert missing == [], f"safety_critical rules missing url/retrieved_on: {missing}"


def test_safety_critical_source_quote_has_no_todo():
    tainted = []
    for rule in _rules():
        if not rule.safety_critical:
            continue
        if "TODO" in rule.source.quote:
            tainted.append(rule.id)
    assert tainted == [], f"source.quote still contains TODO: {tainted}"


def test_rule_uses_provenance_not_tier():
    for rule in _rules():
        assert hasattr(rule, "provenance")
        assert not hasattr(rule, "tier")
