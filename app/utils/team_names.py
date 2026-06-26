"""Deterministic team-name normalization.

The agent translates obvious team names to their official FIFA English form before
calling the API, but it is an LLM and occasionally sends a native-language or accented
spelling ("França", "Coreia do Sul", "Holanda"). The football-data.org match filter and
the api-sports team search both expect the English name, so a native spelling silently
yields no match.

`normalize_team_name` is the deterministic safety net for that boundary:
- lowercases + strips accents for a case/accent-insensitive lookup;
- idempotent for names already in English ("Brazil" -> "Brazil");
- returns the original (stripped) string on a miss, preserving the fuzzy-search fallback.

It can only fix a name or leave it unchanged — it never maps to a *different* team, so it
cannot introduce a wrong match.
"""

import unicodedata


def _fold(value: str) -> str:
    """Lowercase and strip accents/diacritics for lookup."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_marks.lower().strip()


# Canonical official English name -> native/abbreviated aliases (PT / ES / FR and common
# shorthands). Keys are matched accent- and case-insensitively, so accented forms such as
# "frança" / "méxico" are covered by their plain spelling here.
_ALIASES_BY_CANONICAL: dict[str, list[str]] = {
    "Brazil": ["brasil"],
    "France": ["franca", "francia"],
    "Germany": ["alemanha", "alemania", "allemagne"],
    "Spain": ["espanha", "espana", "espagne"],
    "England": ["inglaterra", "angleterre"],
    "Netherlands": ["holanda", "paises baixos", "pays-bas", "pays bas"],
    "Belgium": ["belgica", "belgique"],
    "Croatia": ["croacia", "croatie"],
    "Switzerland": ["suica", "suisse", "suiza"],
    "South Korea": [
        "coreia do sul",
        "corea del sur",
        "coree du sud",
        "coreia",
        "korea republic",
        "republic of korea",
    ],
    "Japan": ["japao", "japon"],
    "United States": [
        "estados unidos",
        "eua",
        "eeuu",
        "usa",
        "estados unidos da america",
    ],
    "Mexico": ["mexico", "mexique"],
    "Ivory Coast": ["costa do marfim", "cote d'ivoire", "cote divoire", "costa de marfil"],
    "Morocco": ["marrocos", "maroc", "marruecos"],
    "Saudi Arabia": ["arabia saudita"],
    "Poland": ["polonia", "pologne"],
    "Denmark": ["dinamarca", "danemark"],
    "Sweden": ["suecia", "suede"],
    "Norway": ["noruega", "norvege"],
    "Serbia": ["servia", "serbie"],
    "Wales": ["pais de gales", "galles", "gales"],
    "Uruguay": ["uruguai"],
    "Colombia": ["colombie"],
    "Ecuador": ["equador"],
    "Italy": ["italia", "italie"],
    "Turkey": ["turquia", "turquie", "turkiye"],
    "Cameroon": ["camaroes", "cameroun"],
    "Egypt": ["egito", "egypte"],
    "Ghana": ["gana"],
    "South Africa": ["africa do sul", "afrique du sud", "sudafrica"],
    "Iran": ["ira"],
    "Qatar": ["catar"],
    "Paraguay": ["paraguai"],
}


def _build_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in _ALIASES_BY_CANONICAL.items():
        lookup[_fold(canonical)] = canonical
        for alias in aliases:
            lookup[_fold(alias)] = canonical
    return lookup


_LOOKUP = _build_lookup()


def normalize_team_name(name: str) -> str:
    """Map a user-supplied team name to its official FIFA English name.

    Returns the original (stripped) name when no alias is known.
    """
    if not name or not name.strip():
        return name
    return _LOOKUP.get(_fold(name), name.strip())
