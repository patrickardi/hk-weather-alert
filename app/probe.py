from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"

HKO_WARNSUM = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=en"
HKO_RHRREAD = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"
HKO_ID = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=id"
ALS = "https://www.als.gov.hk/lookup?q=101%20Wu%20Shan%20Road&n=5"


def _get(url: str, headers: dict[str, str] | None = None) -> tuple[int, str, str]:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=30) as resp:
        body = resp.read()
        ctype = resp.headers.get("Content-Type", "")
        text = body.decode("utf-8", errors="replace")
        return resp.status, ctype, text


def run() -> dict:
    FIXTURES.mkdir(exist_ok=True)
    report: dict = {}

    status, ctype, text = _get(HKO_WARNSUM)
    (FIXTURES / "warnsum_en_live.json").write_text(text, encoding="utf-8")
    report["warnsum"] = {"status": status, "content_type": ctype, "top": text[:80]}

    status, ctype, text = _get(HKO_RHRREAD)
    (FIXTURES / "rhrread_tc_live.json").write_text(text, encoding="utf-8")
    report["rhrread"] = {"status": status, "content_type": ctype}

    status, ctype, text = _get(HKO_ID)
    (FIXTURES / "upstream_200_html.txt").write_text(text, encoding="utf-8")
    report["warnsum_lang_id"] = {
        "status": status,
        "content_type": ctype,
        "json": ctype.startswith("application/json"),
    }

    status, ctype, text = _get(ALS, headers={"Accept": "application/json"})
    (FIXTURES / "als_101_wu_shan_road.json").write_text(text, encoding="utf-8")
    report["als"] = {"status": status, "content_type": ctype}
    return report


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False, indent=2))
    except URLError as exc:
        raise SystemExit(f"probe failed: {exc}") from exc
