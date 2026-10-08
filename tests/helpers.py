from pydantic import ValidationError

from app.engine import abstain_incomplete, evaluate
from app.schemas import PersonalContext, RiskResponse, WeatherState


def run_evaluate(personal, weather) -> RiskResponse:
    try:
        ctx = (
            personal
            if isinstance(personal, PersonalContext)
            else PersonalContext.model_validate(personal)
        )
        state = (
            weather
            if isinstance(weather, WeatherState)
            else WeatherState.model_validate(weather)
        )
    except ValidationError:
        return abstain_incomplete()
    return evaluate(ctx, state)
