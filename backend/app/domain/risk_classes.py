from dataclasses import dataclass


@dataclass(frozen=True)
class RiskClassInfo:
    name: str
    code: str
    color_hex: str
    badge_label: str
    advisory: str


RISK_CLASSES: dict[str, RiskClassInfo] = {
    "Low": RiskClassInfo(
        name="Low",
        code="LOW",
        color_hex="#10B981",
        badge_label="Low Fire Danger",
        advisory="Low probability of ignition and fire spread. Standard agricultural precautions apply.",
    ),
    "Moderate": RiskClassInfo(
        name="Moderate",
        code="MODERATE",
        color_hex="#F59E0B",
        badge_label="Moderate Fire Danger",
        advisory="Vegetation fuels are moderately dry. Surface fires may ignite from open sparks; caution advised during afternoon hours.",
    ),
    "High": RiskClassInfo(
        name="High",
        code="HIGH",
        color_hex="#F97316",
        badge_label="High Fire Danger",
        advisory="Critical fuel dryness and active wind spread potential. Controlled open burning prohibited; monitoring advised.",
    ),
    "Extreme": RiskClassInfo(
        name="Extreme",
        code="EXTREME",
        color_hex="#EF4444",
        badge_label="Extreme Wildfire Threat",
        advisory="Severe wildfire spread conditions. Explosive ignition risk; immediate alert to district civil defense and rapid response teams.",
    ),
}

DEFAULT_PROBABILITY_THRESHOLDS: dict[str, float] = {
    "moderate": 0.25,
    "high": 0.55,
    "extreme": 0.80,
}


def classify_probability(prob: float, thresholds: dict[str, float] | None = None) -> str:
    """Classify model probability into Low / Moderate / High / Extreme using calibrated thresholds."""
    th = thresholds or DEFAULT_PROBABILITY_THRESHOLDS
    mod_th = th.get("moderate", 0.25)
    high_th = th.get("high", 0.55)
    ext_th = th.get("extreme", 0.80)

    if prob >= ext_th:
        return "Extreme"
    elif prob >= high_th:
        return "High"
    elif prob >= mod_th:
        return "Moderate"
    else:
        return "Low"


def classify_fwi(fwi: float) -> str:
    """Rule-based baseline classification based on Canadian FWI scale calibrated for South Asia."""
    if fwi >= 30.0:
        return "Extreme"
    elif fwi >= 15.0:
        return "High"
    elif fwi >= 5.0:
        return "Moderate"
    else:
        return "Low"
