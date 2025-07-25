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


def get_voice(speaker: str = None) -> str:
    """
    Returns voice profile names mapped to each character/speaker.
    """
    voice_profiles: dict[str, str] = {
        "maya": "Laomedeia",  # Upbeat
        "jake": "Zubenelgenubi",  # Casual
        "sofia": "Leda",  # Youthful
        "alex": "Pulcherrima",  # Forward
    }
    return voice_profiles[speaker] if speaker in voice_profiles else "Zephyr"  # Clear as default
