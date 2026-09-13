from typing import Dict, Any, List

EMERGENCY_CONTACTS = [
    {"name": "National Emergency Number", "number": "112", "desc": "Police, Fire, and Ambulance unified helpline"},
    {"name": "Fire Service Emergency", "number": "101", "desc": "Immediate local fire response"},
    {"name": "Disaster Management (NDMA)", "number": "1078", "desc": "National Disaster Management Authority Helpline"},
    {"name": "Ambulance / Health Emergency", "number": "108", "desc": "Emergency medical response and transport"}
]

def generate_preparedness_advisory(
    risk_level: str,
    fwi_score: float,
    aqi_val: int,
    aqi_category: str,
    nearby_fires_count: int,
    closest_fire_km: float = 999.0
) -> Dict[str, Any]:
    advisories: List[Dict[str, str]] = []
    actions: List[str] = []

    if aqi_val > 300:
        advisories.append({
            "type": "severe_air",
            "title": "Severe Air Hazard Warning",
            "message": "Atmospheric particulate matter is at hazardous concentrations. High risk of acute respiratory distress.",
            "urgency": "critical"
        })
        actions.append("Wear a certified N95 / FFP2 respirator outdoors.")
        actions.append("Keep indoor spaces sealed; operate HEPA air purifiers if available.")
        actions.append("Children, seniors, and cardiopulmonary patients must remain strictly indoors.")
    elif aqi_val > 150:
        advisories.append({
            "type": "unhealthy_air",
            "title": "Elevated Air Pollution Advisory",
            "message": "Air quality is degraded. Prolonged outdoor exertion may cause breathing discomfort.",
            "urgency": "warning"
        })
        actions.append("Reduce prolonged or strenuous outdoor physical activities.")
        actions.append("Sensitive groups should carry rescue inhalers and wear protective masks.")

    if risk_level in ("Very High", "Extreme") or nearby_fires_count > 0:
        advisories.append({
            "type": "wildfire_alert",
            "title": f"Wildfire Danger Level: {risk_level}",
            "message": f"{nearby_fires_count} active satellite fire hotspots detected within 50km perimeter (closest: {closest_fire_km:.1f} km).",
            "urgency": "danger" if risk_level == "Extreme" else "warning"
        })
        actions.append("Strict ban on any open biomass, agricultural residue, or camp burning.")
        actions.append("Establish a 10-meter defensible perimeter around residential dwellings by removing dry leaf litter.")
        actions.append("Prepare an emergency evacuation kit with identity documents, essential medicines, and water.")
        actions.append("Report any uncontrolled smoke column immediately to forest officials via 112 or 101.")
    elif risk_level == "High":
        actions.append("Exercise extreme caution with machinery and tools capable of throwing sparks in dry vegetation.")
        actions.append("Monitor local weather and forest department advisories closely.")
    else:
        if not actions:
            actions.append("Environmental baseline is stable. Maintain standard fire safety consciousness.")

    return {
        "status": "alert" if (aqi_val > 200 or risk_level in ("High", "Very High", "Extreme")) else "normal",
        "advisories": advisories,
        "recommended_actions": actions,
        "emergency_contacts": EMERGENCY_CONTACTS
    }
