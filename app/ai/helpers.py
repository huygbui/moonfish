import random


def get_random_category() -> str:
    """
    Returns a random podcast category based on 2025 trends and popularity weights.
    """
    categories_weights = [
        ("True crime", 0.13),
        ("Mental health & self-improvement", 0.13),
        ("Society & culture", 0.12),
        ("Unexplained phenomena", 0.12),
        ("Business & technology", 0.12),
        ("Science & innovation", 0.11),
        ("Health & wellness", 0.09),
        ("News & current events", 0.09),
        ("History", 0.09),
    ]

    subcategories = {
        "News & current events": [
            "power struggles and hidden agendas",
            "grassroots movements and social change",
            "government vs corporate interests",
            "privacy and surveillance issues",
            "big tech controversies",
            "whistleblowers and leaked secrets",
        ],
        "True crime": [
            "cold case breakthroughs",
            "forensic science advances",
            "wrongful convictions and justice",
            "victim advocacy and family stories",
            "criminal rehabilitation and second chances",
            "crime prevention and community safety",
        ],
        "Society & culture": [
            "technology's impact on human behavior",
            "viral culture and internet phenomena",
            "changing work and lifestyle patterns",
            "generational conflicts and differences",
            "digital addiction and online culture",
            "influence and manipulation tactics",
        ],
        "Business & technology": [
            "startup failures and success stories",
            "corporate ethics and scandals",
            "market disruptions and economic shifts",
            "business responsibility and impact",
            "investment trends and financial bubbles",
            "innovation and breakthrough technologies",
        ],
        "Health & wellness": [
            "medical breakthroughs and treatments",
            "alternative and experimental therapies",
            "healthcare privacy and data security",
            "patient rights and advocacy",
            "wellness industry trends and dangers",
            "mental health awareness and stigma",
        ],
        "Mental health & self-improvement": [
            "therapeutic approaches and breakthroughs",
            "addiction and recovery journeys",
            "workplace mental health issues",
            "self-help industry and guru culture",
            "digital wellness and app culture",
            "productivity culture and burnout",
        ],
        "Science & innovation": [
            "groundbreaking research and discoveries",
            "technology solutions to global problems",
            "environmental innovation and sustainability",
            "scientific misconduct and ethics",
            "energy revolution and new technologies",
            "academic publishing and research integrity",
        ],
        "History": [
            "unsolved historical mysteries",
            "cultural preservation and heritage",
            "archaeological discoveries and revelations",
            "untold stories and forgotten figures",
            "historical artifacts and their secrets",
            "historical justice and reconciliation",
        ],
        "Unexplained phenomena": [
            "scientific explanations for mysteries",
            "investigation methods and breakthrough cases",
            "anomalous discoveries and evidence",
            "pattern recognition and hidden connections",
            "collaborative research and investigations",
            "paradigm-shifting evidence and theories",
        ],
    }

    categories, weights = zip(*categories_weights)
    category = random.choices(categories, weights=weights)[0]

    if category in subcategories:
        subcategory = random.choice(subcategories[category])
        return f"{category} (specifically {subcategory})"

    return category


if __name__ == "__main__":
    print(get_random_category())
