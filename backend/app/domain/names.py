"""Readable names for GADM 4.1 admin units.

GADM 4.1 stores Indian NAME_1 / NAME_2 without spaces ("AndamanandNicobar",
"NorthandMiddleAndaman", "DakshinaKannada"). The rule below restores the spaces
deterministically; KNOWN_OVERRIDES fixes the few names the rule cannot (reviewed list,
see tests/unit/test_names.py which runs the rule over every GADM name).
"""

import re

KNOWN_OVERRIDES: dict[str, str] = {"NCTofDelhi": "NCT of Delhi"}

_AND = re.compile(r"(?<=[a-z])and(?=[A-Z])")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def humanize_gadm_name(name: str | None) -> str | None:
    if not name:
        return name
    if name in KNOWN_OVERRIDES:
        return KNOWN_OVERRIDES[name]
    if " " in name:  # already readable
        return name
    out = _AND.sub(" and ", name)
    out = _CAMEL.sub(" ", out)
    return re.sub(r"\s+", " ", out).strip()


def normalize_name_key(name: str) -> str:
    """Comparison key so 'Tamil Nadu', 'tamil nadu' and GADM's 'TamilNadu' all match."""
    return re.sub(r"[^a-z0-9]", "", name.lower())
