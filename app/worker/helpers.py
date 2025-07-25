# Helpers
def get_character(speaker: str = None) -> str:
    """
    Returns formatted speaker descriptions for the prompt.
    """
    speakers: dict[str, str] = {
        "maya": "Enthusiastic and upbeat, always finds the silver lining in everything",
        "jake": "Quick with jokes, questions everything, playfully sarcastic",
        "sofia": "Thoughtful and narrative-driven, asks deep questions",
        "alex": "No-nonsense and authentic, tells it like it is",
    }

    return speakers[speaker] if speaker in speakers else "Natural and conversational"
