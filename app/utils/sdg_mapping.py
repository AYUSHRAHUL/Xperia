SDG_MAPPING = {
    "Water Leakage": {"sdgTags": [6], "impactType": "water"},
    "Garbage Dump": {"sdgTags": [11, 13], "impactType": "waste"},
    "Broken Streetlight": {"sdgTags": [5, 11], "impactType": "safety"},
    "Pothole": {"sdgTags": [11], "impactType": "emission"},
    "Traffic Signal Failure": {"sdgTags": [13], "impactType": "fuel"},
}


def map_category_to_sdg(category: str):
    return SDG_MAPPING.get(category, {"sdgTags": [], "impactType": None})


