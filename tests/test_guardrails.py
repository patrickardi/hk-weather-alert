from app.render import render_html
from app.rules import load_rules
from app.samples import SAMPLES
from app.schemas import BANNED_PHRASES


def test_never_print_typhoon_shelter():
    blobs = [render_html(SAMPLES["wushan_red_rain_partial"])]
    for rule in load_rules():
        blobs.append(rule.body)
        blobs.append(rule.title)
        blobs.append(rule.source.quote)
    joined = "\n".join(blobs)
    for phrase in BANNED_PHRASES:
        assert phrase not in joined, f"banned phrase found: {phrase}"


def test_never_assert_shelter_open():
    for rule in load_rules():
        lowered = f"{rule.body}{rule.title}{rule.source.quote}"
        assert "已经开放" not in lowered
        assert "現已開放" not in lowered
        assert "is now open" not in lowered.lower()
