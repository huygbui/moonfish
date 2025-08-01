import random


def get_random_category() -> str:
    """
    Returns a random podcast category based on 2025 trends and popularity weights.
    """
    categories_weights = [
        ("true crime", 14),
        ("society & culture", 15),
        ("business", 9),
        ("health & wellness", 12),
        ("art & design", 12),
        ("science & innovation", 9),
        ("history", 8),
        ("unexplained phenomena", 10),
        ("nature", 9),
    ]

    subcategories = {
        "true crime": [
            "unsolved cases",
            "criminal behavior",
            "white-collar crime and financial fraud",
        ],
        "society & culture": [
            "everyday social rituals and unspoken rules",
            "how spaces shape human behavior",
            "cultural traditions adapting to modern life",
            "viral moments and their unexpected consequences",
            "communities formed around shared obsessions",
        ],
        "business": [
            "corporate scandals and spectacular failures",
            "the psychology of money and wealth",
            "underground economies and black markets",
            "family business dynasties and feuds",
            "marketing manipulation and consumer psychology",
            "business cults and toxic company cultures",
        ],
        "health & wellness": [
            "body mysteries and medical anomalies",
            "traditional healing wisdom meets modern science",
            "the neuroscience of habits and behavior change",
            "sleep, dreams, and circadian mysteries",
            "the placebo effect and mind-body connection",
            "the secret lives of our emotions",
            "nutrition myths and food culture",
            "resilience and post-traumatic growth",
            "creativity, flow states, and peak performance",
            "the psychology of decision-making",
        ],
        "art & design": [
            "the psychology of color, shape, and visual perception",
            "design decisions that changed how we live",
            "the hidden stories behind famous artworks",
            "street art, rebellion, and public space battles",
            "craft traditions surviving in the digital age",
            "when art becomes valuable and why",
        ],
        "science & innovation": [
            "citizen science and amateur discoveries",
            "when different fields collide and create breakthroughs",
            "technology's unintended consequences",
            "climate solutions and environmental restoration",
            "space exploration and cosmic perspective",
            "the frontiers of human enhancement",
        ],
        "history": [
            "daily life in different historical periods",
            "forgotten inventions and lost knowledge",
            "historical figures' personal relationships",
            "cultural exchanges and cross-pollination",
            "historical coincidences and turning points",
            "alternative histories and what-if scenarios",
        ],
        "unexplained phenomena": [
            "unusual human abilities and edge cases",
            "natural phenomena that seem impossible",
            "coincidences, synchronicities, and patterns",
            "the boundaries between known and unknown",
            "anomalous archaeological findings",
            "consciousness and perception mysteries",
        ],
        "nature": [
            "animal intelligence and consciousness",
            "urban wildlife adaptation",
            "extreme weather and climate events",
            "ecosystem collapse and recovery",
            "human-nature relationships",
            "natural phenomena and mysteries",
            "conservation success and failure stories",
            "invasive species disruption",
            "biomimicry and nature-inspired design",
            "wilderness survival and exploration",
            "ocean mysteries and deep sea life",
            "plant intelligence and communication",
        ],
    }

    categories, weights = zip(*categories_weights)
    category = random.choices(categories, weights=weights)[0]

    if category in subcategories:
        subcategory = random.choice(subcategories[category])
        return f"{category} (specifically {subcategory})"

    return category


def get_random_angle():
    """Universal angles that work with ANY category"""
    angles = [
        # Core angles (consolidated)
        "The untold story",  # Covers: hidden, nobody tells you, secrets
        "The real truth",  # Covers: surprising truth, what's really happening
        "The dark side",  # Covers: human cost, negative aspects
        "The psychology",  # Mental/behavioral aspects
        "The unintended consequences",  # Ripple effects
        # Fresh angles
        "The future of",  # Forward-looking
        "The weird economics",  # Money/incentive structures
        "The cultural divide",  # Different perspectives globally
        "The origin story",  # How it all began
        "The turning point",  # Key moment that changed everything
        "The unlikely solution",  # Innovative fixes
        "The generational gap",  # How different ages see it
        "The global vs local",  # Scale differences
        "The ethical dilemma",  # Moral complexities
        "The pattern behind",  # Hidden systems/connections
    ]
    return random.choice(angles)


if __name__ == "__main__":
    print(get_random_category())
