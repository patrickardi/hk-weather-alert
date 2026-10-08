"""Personal weather-risk card. Wire mirrors upstream; adapters map; engine reads domain."""

from app.adapters import build_card
from app.engine import evaluate
from app.wire import parse_als, parse_rhrread, parse_warnsum

__version__ = "0.1.0"
__all__ = ["evaluate", "build_card", "parse_als", "parse_rhrread", "parse_warnsum"]
