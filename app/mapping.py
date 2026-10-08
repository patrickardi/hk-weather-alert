HKO_RAINFALL_PLACES = (
    "中西區",
    "東區",
    "葵青",
    "離島區",
    "北區",
    "西貢",
    "沙田",
    "南區",
    "大埔",
    "荃灣",
    "屯門",
    "灣仔",
    "元朗",
    "油尖旺",
    "深水埗",
    "九龍城",
    "黃大仙",
    "觀塘",
)

DC_DISTRICT_TO_HKO_PLACE: dict[str, str] = {
    "中西區": "中西區",
    "東區": "東區",
    "南區": "南區",
    "灣仔區": "灣仔",
    "九龍城區": "九龍城",
    "觀塘區": "觀塘",
    "深水埗區": "深水埗",
    "黃大仙區": "黃大仙",
    "油尖旺區": "油尖旺",
    "離島區": "離島區",
    "葵青區": "葵青",
    "北區": "北區",
    "西貢區": "西貢",
    "沙田區": "沙田",
    "大埔區": "大埔",
    "荃灣區": "荃灣",
    "屯門區": "屯門",
    "元朗區": "元朗",
    "CENTRAL AND WESTERN DISTRICT": "中西區",
    "EASTERN DISTRICT": "東區",
    "SOUTHERN DISTRICT": "南區",
    "WAN CHAI DISTRICT": "灣仔",
    "KOWLOON CITY DISTRICT": "九龍城",
    "KWUN TONG DISTRICT": "觀塘",
    "SHAM SHUI PO DISTRICT": "深水埗",
    "WONG TAI SIN DISTRICT": "黃大仙",
    "YAU TSIM MONG DISTRICT": "油尖旺",
    "ISLANDS DISTRICT": "離島區",
    "KWAI TSING DISTRICT": "葵青",
    "NORTH DISTRICT": "北區",
    "SAI KUNG DISTRICT": "西貢",
    "SHA TIN DISTRICT": "沙田",
    "TAI PO DISTRICT": "大埔",
    "TSUEN WAN DISTRICT": "荃灣",
    "TUEN MUN DISTRICT": "屯門",
    "YUEN LONG DISTRICT": "元朗",
}


def to_hko_place(district: str | None) -> str | None:
    if not district:
        return None
    if district in HKO_RAINFALL_PLACES:
        return district
    return DC_DISTRICT_TO_HKO_PLACE.get(district)
