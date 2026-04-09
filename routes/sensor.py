# routes/sensor.py
from flask import Blueprint, request, jsonify
from extensions import db
from models import SensorReading, DailySummary, VALID_LOCATIONS
from datetime import datetime
import os

sensor_bp = Blueprint("sensor", __name__)
API_KEY = os.getenv("SENSOR_API_KEY", "powerwatch-iot-key")

def require_api_key():
    key = request.headers.get("X-API-Key") or request.args.get("api_key")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    return None

def update_daily_summary(location, status, recorded_at):
    day = recorded_at.date()
    summary = DailySummary.query.filter_by(location=location, date=day).first()

    if not summary:
        summary = DailySummary(location=location, date=day, hours_on=0.0, hours_off=0.0, reading_count=0)
        db.session.add(summary)

    hours = 5 / 60
    if status == "ON":
        summary.hours_on = (summary.hours_on or 0.0) + hours
    else:
        summary.hours_off = (summary.hours_off or 0.0) + hours

    summary.reading_count = (summary.reading_count or 0) + 1
    db.session.commit()

@sensor_bp.route("/ingest", methods=["POST"])
def ingest():
    """
    Called by NodeMCU every 5 minutes.
    NodeMCU only sends "ON" — if power is off the device is dead and silent.
    """
    auth_error = require_api_key()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    location = str(data.get("location", "")).lower().strip()
    status   = str(data.get("status", "ON")).upper().strip()

    if location not in VALID_LOCATIONS:
        return jsonify({"error": f"Invalid location. Use: {VALID_LOCATIONS}"}), 422

    now = datetime.utcnow()
    reading = SensorReading(location=location, status=status, recorded_at=now, source="sensor")
    db.session.add(reading)
    db.session.commit()
    update_daily_summary(location, status, now)

    return jsonify({"message": "Ping recorded", "id": reading.id}), 201


@sensor_bp.route("/history/<location>", methods=["GET"])
def history(location):
    location = location.lower()
    if location not in VALID_LOCATIONS:
        return jsonify({"error": "Invalid location"}), 404
    limit = min(int(request.args.get("limit", 50)), 500)
    readings = (SensorReading.query
        .filter_by(location=location)
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit).all())
    return jsonify([r.to_dict() for r in readings])
