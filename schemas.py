from typing import Optional,List
from pydantic import BaseModel,Field,HttpUrl


class CitationFootnote(BaseModel):
    source_url: HttpUrl=Field(...,description="Official HK government or meteorological source URL")
    ##requires web link from official gov
    retrieved_at: str=Field(...,description="Date fetched/recorded (YYYY-MM-DD)")
    verified_by: str=Field(...,description="Team member who verified this entry")

class EmergencyShelter(BaseModel):
    shelter_id: str
    name_en: str
    name_indo: Optional[str]=Field(None,description="Indonesian translation")
    address: str
    coordinates: dict=Field(...,example={  "lat":22.2819 , "lng": 114.1581  })
    citation: CitationFootnote

class ActionOutput(BaseModel):
    timestamp: str
    user_status: str
    do_actions:   List[str]
    dont_actions:   List[str]
    escalation_hotline:  Optional[str]=None
    citation_footnotes: List[CitationFootnote]
    ## do and dont actions , optional hotline number , citations