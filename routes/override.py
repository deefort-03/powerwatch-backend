# routes/override.py
from flask import Blueprint, request, jsonify
from extensions import db
from models import SensorReading, DailySummary, VALID_LOCATIONS
from datetime import datetime
import os

override_bp = Blueprint("override", __name__)
OVERRIDE_KEY = os.getenv("OVERRIDE_API_KEY", "powerwatch-override-key")

def require_override_key():
    key = request.headers.get("X-API-Key") or request.args.get("api_key")
    if key != OVERRIDE_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    return None

@override_bp.route("/report", methods=["POST"])
def manual_report():
    """Manual status report when NodeMCU is offline or needs correction."""
    auth_error = require_override_key()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    location = str(data.get("location", "")).lower().strip()
    status   = str(data.get("status", "")).upper().strip()
    if location not in VALID_LOCATIONS:
        return jsonify({"error": f"Invalid location"}), 422
    if status not in ("ON", "OFF"):
        return jsonify({"error": "Status must be ON or OFF"}), 422
    now = datetime.utcnow()
    reading = SensorReading(location=location, status=status, recorded_at=now, source="manual")
    db.session.add(reading)
    db.session.commit()
    day = now.date()
    summary = DailySummary.query.filter_by(location=location, date=day).first()
    if not summary:
        summary = DailySummary(location=location, date=day)
        db.session.add(summary)
    hours = 5 / 60
    if status == "ON":
        summary.hours_on += hours
    else:
        summary.hours_off += hours
    summary.reading_count += 1
    db.session.commit()
    return jsonify({"message": "Manual reading recorded", "id": reading.id,
                    "location": location, "status": status}), 201

@override_bp.route("/history", methods=["GET"])
def override_history():
    auth_error = require_override_key()
    if auth_error:
        return auth_error
    location = request.args.get("location", "").lower()
    limit = min(int(request.args.get("limit", 20)), 200)
    query = SensorReading.query.filter_by(source="manual")
    if location in VALID_LOCATIONS:
        query = query.filter_by(location=location)
    readings = query.order_by(SensorReading.recorded_at.desc()).limit(limit).all()
    return jsonify([r.to_dict() for r in readings])
