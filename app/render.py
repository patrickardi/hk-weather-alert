from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas import RiskResponse

TEMPLATE_DIR = Path(__file__).parent / "templates"


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
        contact=response.contact,
        not_considered=response.not_considered,
        stale_as_of=response.stale_as_of,
    )


if __name__ == "__main__":
    import sys

    from app.samples import SAMPLES

    print(render_html(SAMPLES[sys.argv[1] if len(sys.argv) > 1 else "wushan_red_rain_partial"]))
