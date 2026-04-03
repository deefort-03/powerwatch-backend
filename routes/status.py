# routes/status.py
from flask import Blueprint, jsonify, request
from models import SensorReading, VALID_LOCATIONS
from datetime import datetime

status_bp = Blueprint("status", __name__)

# ── KEY CHANGE ──────────────────────────────────────────────────────────────
# With no voltage sensor, the NodeMCU only pings when it has power (status=ON).
# If we haven't heard from it in 10 minutes → the power is OFF.
# So stale = OFF (not UNKNOWN like before).
STALE_MINUTES = 10
# ────────────────────────────────────────────────────────────────────────────

def get_location_status(location):
    latest = (SensorReading.query
        .filter_by(location=location)
        .order_by(SensorReading.recorded_at.desc())
        .first())

    if not latest:
        return {
            "location":     location,
            "status":       "OFF",
            "last_updated": None,
            "stale":        True,
            "source":       None,
            "age_minutes":  None,
            "note":         "No data yet — sensor not installed or never pinged",
        }

    age_minutes = (datetime.utcnow() - latest.recorded_at).total_seconds() / 60
    # If NodeMCU hasn't pinged in STALE_MINUTES → power is off
    power_off = age_minutes > STALE_MINUTES

    return {
        "location":     location,
        "status":       "OFF" if power_off else "ON",
        "last_updated": latest.recorded_at.isoformat(),
        "stale":        power_off,
        "source":       latest.source,
        "age_minutes":  round(age_minutes, 1),
    }


@status_bp.route("/all", methods=["GET"])
def all_status():
    """GET /api/status/all — returns ON/OFF for all 3 locations"""
    result = {loc: get_location_status(loc) for loc in VALID_LOCATIONS}
    result["fetched_at"] = datetime.utcnow().isoformat()
    return jsonify(result)


@status_bp.route("/<location>", methods=["GET"])
def single_status(location):
    """GET /api/status/<location>"""
    location = location.lower()
    if location not in VALID_LOCATIONS:
        return jsonify({"error": "Invalid location"}), 404
    return jsonify(get_location_status(location))
