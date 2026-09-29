
from schemas import EmergencyShelter, ActionOutput, CitationFootnote
from datetime import datetime
import zoneinfo

def verify_shelter(data:dict) -> EmergencyShelter:
    """validate raw shelter data w/ pydantic schema in schema.py before processing (llm)"""
    return EmergencyShelter(**data)

def generate_card(status:str , actions:dict, citations:list) -> ActionOutput:
    """format output for pipeline  (image generation)"""

    hk=zoneinfo.ZoneInfo("Asia/Hong_Kong")
    hkt=datetime.now(hk)

    current_time=hkt.strftime("%Y-%m-%d %H:%M HKT")


    return ActionOutput(
        timestamp=current_time,
        user_status=status,
        do_actions=actions.get("do",[]),
        dont_actions=actions.get("dont",[]),
        citation_footnotes=citations
    )