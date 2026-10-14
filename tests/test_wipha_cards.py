from app.render import render_html
from app.schemas import Block, HotlineMode
from app.wipha import SCENES, scene_response


def _by_id(scene_id: str) -> dict:
    return next(scene for scene in SCENES if scene["id"] == scene_id)


def _outcome(result, block: Block):
    return next(item for item in result.block_outcomes if item.block is block)


def test_three_scenes_are_different_people_places_languages():
    addresses = {scene["personal"].request_address for scene in SCENES}
    districts = {scene["personal"].district for scene in SCENES}
    languages = {scene["personal"].language for scene in SCENES}
    assert len(addresses) == 3
    assert len(districts) == 3
    assert languages == {"zh", "en"}


def test_elderly_card_is_large_type_chinese():
    scene = _by_id("t8_0020")
    result = scene_response(scene)
    html = render_html(result, diff_label=scene["diff_label"])
    assert result.needs_large_type is True
    assert result.language == "zh"
    assert "class=\"peak-warning large\"" in html or " large" in html
    assert "屯門" in html
    assert result.contact.had_hotline == "2572 8427"
    assert "星期日" in html
    assert "深夜" in html


def test_helper_english_card_mentions_pets_and_stay_in():
    scene = _by_id("t10_0920")
    result = scene_response(scene)
    html = render_html(result, diff_label=scene["diff_label"])
    assert result.language == "en"
    assert "helper_tc8plus" in result.fired_rules
    assert "pets_tc8plus" in result.fired_rules
    assert "Keep pets indoors" in html
    assert "stay indoors" in html.lower() or "Stay indoors" in html
    assert "In an emergency, call 999" in html
    assert "元朗" in html
    assert "danger" in html
    assert "Hurricane Signal No. 10" in html


def test_local_t3_not_all_clear():
    scene = _by_id("t3_1940")
    result = scene_response(scene)
    html = render_html(result, diff_label=scene["diff_label"])
    assert result.language == "zh"
    assert result.contact.mode is HotlineMode.GOV_1823
    assert "灣仔" in html
    assert "仍" in html
    assert "目前没有生效的天气警告" not in html
    assert _outcome(result, Block.SHELTER).rendered is False


def test_wipha_three_cards_html_differ():
    htmls = [render_html(scene_response(scene), diff_label=scene["diff_label"]) for scene in SCENES]
    assert htmls[0] != htmls[1] != htmls[2]
    assert htmls[0] != htmls[2]
