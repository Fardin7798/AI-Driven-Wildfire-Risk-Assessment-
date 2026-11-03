"""Where a station-trained model is extrapolating.

A district forecast is labelled `extrapolated` when the district centroid is more than
EXTRAPOLATION_KM from the nearest training station, OR lies outside the convex hull of the
training stations. Training stations are the CPCB stations whose days the model was fitted on.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from shapely.geometry import MultiPoint, Point

EXTRAPOLATION_KM = 200.0
EARTH_RADIUS_KM = 6371.0


def nearest_km(
    lat: Sequence[float], lon: Sequence[float], ref_lat: Sequence[float], ref_lon: Sequence[float]
) -> np.ndarray:
    """Great-circle distance (km) from each point to its nearest reference point."""
    la1 = np.radians(np.asarray(lat, float))[:, None]
    la2 = np.radians(np.asarray(ref_lat, float))[None]
    dlo = np.radians(np.asarray(lon, float))[:, None] - np.radians(np.asarray(ref_lon, float))[None]
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin(dlo / 2) ** 2
    return (2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))).min(1)


def inside_hull(
    lat: Sequence[float], lon: Sequence[float], ref_lat: Sequence[float], ref_lon: Sequence[float]
) -> list[bool]:
    """True where the point lies inside (or on) the convex hull of the reference points."""
    hull = MultiPoint(list(zip(ref_lon, ref_lat, strict=True))).convex_hull
    return [bool(hull.covers(Point(x, y))) for x, y in zip(lon, lat, strict=True)]


def extrapolated(nearest_station_km: float, inside_station_hull: bool) -> bool:
    return bool(nearest_station_km > EXTRAPOLATION_KM or not inside_station_hull)
