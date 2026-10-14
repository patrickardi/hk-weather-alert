import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas import RiskResponse, Severity

TEMPLATE_DIR = Path(__file__).parent / "templates"
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
OUTPUT = ROOT / "output"


def render_html(response: RiskResponse, diff_label: str = "") -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("card.html.j2")
    situational = [
        item
        for item in response.advice
        if item.code not in {"emergency_999", "emergency_sms_992", "where_to_ask"}
    ]
    peak = max((item.tier for item in situational), default=Severity.ADVISORY)
    outcomes = response.block_outcomes
    considered = response.not_considered
    blocks = response.blocks
    if response.needs_large_type:
        outcomes = [item for item in outcomes if item.rendered]
        considered = []
        blocks = [item for item in blocks if item.kind in {"dont", "status", "caution"}]
    return template.render(
        abstained=response.abstained,
        abstain_reason=response.abstain_reason or "",
        advice=response.advice,
        blocks=blocks,
        block_outcomes=outcomes,
        contact=response.contact,
        not_considered=considered,
        stale_as_of=response.stale_as_of,
        location_line=response.location_line or "",
        diff_label=diff_label,
        peak_name=peak.value,
        lang=response.language,
        large=response.needs_large_type,
    )


def render_from_fixtures() -> str:
    from app.adapters import build_card, personal_from_als

    personal = personal_from_als(
        json.loads((FIXTURES / "als_101_wu_shan_road.json").read_text(encoding="utf-8"))
    )
    return render_html(
        build_card(
            personal=personal,
            warnsum_body=(FIXTURES / "warnsum_en_live.json").read_text(encoding="utf-8"),
            warnsum_ctype="application/json",
            rhrread_body=(FIXTURES / "rhrread_tc_live.json").read_text(encoding="utf-8"),
            rhrread_ctype="application/json",
        )
    )


def render_png(html: str, path: Path) -> Path:
    from playwright.sync_api import sync_playwright

    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 480, "height": 1400})
        page.set_content(html, wait_until="load")
        page.screenshot(path=str(path), full_page=True)
        browser.close()
    return path


def render_wipha_pngs() -> list[Path]:
    from app.wipha import SCENES, scene_response

    written = []
    for scene in SCENES:
        html = render_html(scene_response(scene), diff_label=scene["diff_label"])
        written.append(render_png(html, OUTPUT / scene["filename"]))
    return written


if __name__ == "__main__":
    if "--fixtures" in sys.argv:
        print(render_from_fixtures())
    elif "--html" in sys.argv:
        from app.samples import SAMPLES

        print(render_html(SAMPLES["wushan_red_rain_partial"]))
    else:
        paths = render_wipha_pngs()
        for path in paths:
            print(path)
