import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas import RiskResponse

TEMPLATE_DIR = Path(__file__).parent / "templates"
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def render_html(response: RiskResponse) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("card.html.j2")
    return template.render(
        abstained=response.abstained,
        abstain_reason=response.abstain_reason or "",
        advice=response.advice,
        blocks=response.blocks,
        block_outcomes=response.block_outcomes,
        contact=response.contact,
        not_considered=response.not_considered,
        stale_as_of=response.stale_as_of,
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


if __name__ == "__main__":
    if "--fixtures" in sys.argv:
        print(render_from_fixtures())
    else:
        from app.samples import SAMPLES

        key = "wushan_red_rain_partial"
        for arg in sys.argv[1:]:
            if not arg.startswith("--"):
                key = arg
        print(render_html(SAMPLES[key]))
