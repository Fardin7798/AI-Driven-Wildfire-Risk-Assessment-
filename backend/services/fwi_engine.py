import math
from typing import Dict, Any

def compute_ffmc(temp: float, rh: float, wind: float, rain: float, prev_ffmc: float = 85.0) -> float:
    mo = 147.2 * (101.0 - prev_ffmc) / (59.5 + prev_ffmc)
    if rain > 0.5:
        rf = rain - 0.5
        if mo <= 150.0:
            mr = mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))
        else:
            mr = mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf)) + 0.0015 * ((mo - 150.0) ** 2) * math.sqrt(rf)
        mo = min(mr, 250.0)

    ed = 0.942 * (rh ** 0.679) + 11.0 * math.exp((rh - 100.0) / 10.0) + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
    if mo > ed:
        ko = 0.424 * (1.0 - (rh / 100.0) ** 1.7) + 0.0694 * math.sqrt(wind) * (1.0 - (rh / 100.0) ** 8)
        kd = ko * 0.581 * math.exp(0.0365 * temp)
        m = ed + (mo - ed) * (10.0 ** (-kd))
    else:
        ew = 0.618 * (rh ** 0.753) + 10.0 * math.exp((rh - 100.0) / 10.0) + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
        if mo < ew:
            k1 = 0.424 * (1.0 - ((100.0 - rh) / 100.0) ** 1.7) + 0.0694 * math.sqrt(wind) * (1.0 - ((100.0 - rh) / 100.0) ** 8)
            kw = k1 * 0.581 * math.exp(0.0365 * temp)
            m = ew - (ew - mo) * (10.0 ** (-kw))
        else:
            m = mo

    ffmc = 59.5 * (250.0 - m) / (147.2 + m)
    return max(0.0, min(101.0, ffmc))

def compute_isi(wind: float, ffmc: float) -> float:
    fm = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
    fw = math.exp(0.05039 * wind)
    ff = 91.9 * math.exp(-0.1386 * fm) * (1.0 + (fm ** 5.31) / (4.93e07))
    return 0.208 * fw * ff

def compute_fwi(isi: float, bui: float = 30.0) -> float:
    if bui <= 80.0:
        fd = 0.626 * (bui ** 0.809) + 2.0
    else:
        fd = 1000.0 / (25.0 + 108.64 * math.exp(-0.023 * bui))
    b = 0.1 * isi * fd
    if b > 1.0:
        fwi = math.exp(2.72 * ((0.434 * math.log(b)) ** 0.647))
    else:
        fwi = b
    return max(0.0, fwi)

def get_risk_level(fwi: float) -> Dict[str, str]:
    if fwi < 5.2:
        return {"level": "Low", "color": "#22c55e", "badge": "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"}
    elif fwi < 11.2:
        return {"level": "Moderate", "color": "#eab308", "badge": "bg-amber-500/10 text-amber-400 border-amber-500/20"}
    elif fwi < 21.3:
        return {"level": "High", "color": "#f97316", "badge": "bg-orange-500/10 text-orange-400 border-orange-500/20"}
    elif fwi < 38.0:
        return {"level": "Very High", "color": "#ef4444", "badge": "bg-red-500/10 text-red-400 border-red-500/20"}
    else:
        return {"level": "Extreme", "color": "#991b1b", "badge": "bg-purple-500/10 text-purple-400 border-purple-500/20"}

def calculate_fire_risk(temp: float, rh: float, wind: float, rain: float) -> Dict[str, Any]:
    ffmc = compute_ffmc(temp=temp, rh=rh, wind=wind, rain=rain)
    isi = compute_isi(wind=wind, ffmc=ffmc)
    fwi = compute_fwi(isi=isi)
    risk_info = get_risk_level(fwi)

    factors = []
    if temp > 35.0:
        factors.append(f"Elevated surface temperature ({temp:.1f}°C)")
    if rh < 30.0:
        factors.append(f"Critical low relative humidity ({rh:.1f}%) drying fine fuels")
    if wind > 20.0:
        factors.append(f"Gusty surface winds ({wind:.1f} km/h) accelerating potential spread")
    if rain < 1.0:
        factors.append("Extended absence of recent precipitation (<1mm)")
    if not factors:
        factors.append("Stable meteorological conditions with adequate moisture content")

    return {
        "fwi_score": round(fwi, 1),
        "risk_level": risk_info["level"],
        "color": risk_info["color"],
        "badge": risk_info["badge"],
        "ffmc": round(ffmc, 1),
        "isi": round(isi, 1),
        "key_drivers": factors
    }
