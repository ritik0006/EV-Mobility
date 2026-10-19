from math import asin, cos, radians, sin, sqrt

ROAD_FACTOR = 1.3                   # straight-line km -> approximate road km
DEMO_SPEED_KMH = 180                # simulated speed so a demo ride finishes in about 3 minutes
RATES = {"2w": (20, 8), "4w": (50, 16)}               # base fare (Rs), Rs per km
CO2_KG_PER_KM = {"2w": 0.026, "4w": 0.062}            # estimated saving versus a petrol vehicle


def km(a_lat, a_lng, b_lat, b_lng):
    """Great-circle distance in km (haversine)."""
    p1, p2 = radians(a_lat), radians(b_lat)
    h = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(b_lng - a_lng) / 2) ** 2
    return 12742 * asin(sqrt(h))


def lerp(a, b, f):
    return a + (b - a) * f
