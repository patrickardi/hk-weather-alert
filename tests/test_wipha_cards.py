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


def test_fdh_heat_card_english_outdoor_before_midnight():
    scene = _by_id("vhww_fdh_1400")
    result = scene_response(scene)
    html = render_html(result, diff_label=scene["diff_label"])

    # 身份与 UI：英文、标准字号、不弃答
    assert result.abstained is False
    assert result.language == "en"
    assert result.needs_large_type is False
    assert 'class="peak-warning large"' not in html

    # 核心：同一号码，时段切换为 before midnight，卡上不得出现 24 小时
    assert result.contact.had_hotline == "2572 8427"
    assert result.contact.mode == "had_before_midnight"
    assert "before midnight" in html
    assert "round-the-clock" not in html and "24小时" not in html and "24-hour" not in html.split("2157 9537")[0]

    # 规则：酷热规则触发，台风规则不触发
    for code in ("vhww_in_force", "heat_outdoor_precautions", "heat_shelter_open", "fdh_support_line"):
        assert code in result.fired_rules
    assert "tc8_in_force" not in result.fired_rules
    assert "shelter_may_open" not in result.fired_rules

    assert "BEWARE OF HEAT STROKE" in html
    assert "MORNING OR LATE AFTERNOON" in html
    assert "Sai Ying Pun Community Complex Community Hall" in html
    assert "2 High Street" in html
    assert "2157 9537" in html                      # 外佣专线
    assert "999" in html

    assert "6:45" in html
    assert "Sunday" in html
    
    assert "P2026092700144" in html
    assert "P2026093000535" in html
    assert "domestic_helper" not in result.not_considered

    assert "{{" not in html and "TODO" not in html and "SAMPLE" not in html
