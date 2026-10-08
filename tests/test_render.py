from app.render import render_html
from app.samples import SAMPLES


def test_sample_card_has_status_contact_and_blocks():
    html = render_html(SAMPLES["wushan_red_rain_partial"])
    assert "STATUS" in html
    assert "999" in html
    assert "DONT" in html
    assert "uv_index" in html
