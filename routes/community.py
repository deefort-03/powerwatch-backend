# routes/community.py
from flask import Blueprint, request, jsonify
from extensions import db
from models import VALID_LOCATIONS
from datetime import datetime

community_bp = Blueprint("community", __name__)

class CommunityReport(db.Model):
    __tablename__ = "community_reports"
    id          = db.Column(db.Integer, primary_key=True)
    location    = db.Column(db.String(50), nullable=False, index=True)
    accurate    = db.Column(db.Boolean,  nullable=False)  # True = confirmed, False = disputed
    reported_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id":          self.id,
            "location":    self.location,
            "accurate":    self.accurate,
            "reported_at": self.reported_at.isoformat(),
        }


@community_bp.route("/report", methods=["POST"])
def report():
    """
    POST /api/community/report
    Students confirm or dispute the current sensor reading.

    Body: { "location": "agbowo", "accurate": true }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    location = str(data.get("location", "")).lower().strip()
    accurate = data.get("accurate")

    if location not in VALID_LOCATIONS:
        return jsonify({"error": "Invalid location"}), 422
    if accurate is None or not isinstance(accurate, bool):
        return jsonify({"error": "accurate must be true or false"}), 422

    report = CommunityReport(location=location, accurate=accurate)
    db.session.add(report)
    db.session.commit()

    return jsonify({"message": "Report recorded", "id": report.id}), 201


@community_bp.route("/summary/<location>", methods=["GET"])
def summary(location):
    """
    GET /api/community/summary/<location>
    Returns the last 20 community reports for a location
    with a trust score (% who said accurate).
    """
    location = location.lower()
    if location not in VALID_LOCATIONS:
        return jsonify({"error": "Invalid location"}), 404

    reports = (CommunityReport.query
        .filter_by(location=location)
        .order_by(CommunityReport.reported_at.desc())
        .limit(20).all())

    total = len(reports)
    confirmed = sum(1 for r in reports if r.accurate)
    trust_score = round((confirmed / total * 100) if total else 0)

    return jsonify({
        "location":    location,
        "total":       total,
        "confirmed":   confirmed,
        "disputed":    total - confirmed,
        "trust_score": trust_score,
        "reports":     [r.to_dict() for r in reports],
    })


@community_bp.route("/summary/all", methods=["GET"])
def summary_all():
    """GET /api/community/summary/all — trust scores for all locations"""
    result = {}
    for loc in VALID_LOCATIONS:
        reports = (CommunityReport.query
            .filter_by(location=loc)
            .order_by(CommunityReport.reported_at.desc())
            .limit(20).all())
        total = len(reports)
        confirmed = sum(1 for r in reports if r.accurate)
        result[loc] = {
            "total":       total,
            "confirmed":   confirmed,
            "disputed":    total - confirmed,
            "trust_score": round((confirmed / total * 100) if total else 0),
        }
    return jsonify(result)
