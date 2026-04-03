# models.py
from extensions import db
from datetime import datetime

VALID_LOCATIONS = ["agbowo", "orogun", "barika"]

class SensorReading(db.Model):
    __tablename__ = "sensor_readings"
    id          = db.Column(db.Integer, primary_key=True)
    location    = db.Column(db.String(50), nullable=False, index=True)
    status      = db.Column(db.String(3),  nullable=False)  # "ON" only from NodeMCU
    recorded_at = db.Column(db.DateTime,   nullable=False, default=datetime.utcnow, index=True)
    source      = db.Column(db.String(20), nullable=False, default="sensor")

    def to_dict(self):
        return {
            "id":          self.id,
            "location":    self.location,
            "status":      self.status,
            "recorded_at": self.recorded_at.isoformat(),
            "source":      self.source,
        }


class DailySummary(db.Model):
    __tablename__ = "daily_summaries"
    id            = db.Column(db.Integer, primary_key=True)
    location      = db.Column(db.String(50), nullable=False, index=True)
    date          = db.Column(db.Date,       nullable=False, index=True)
    hours_on      = db.Column(db.Float,      nullable=False, default=0.0)
    hours_off     = db.Column(db.Float,      nullable=False, default=0.0)
    reading_count = db.Column(db.Integer,    nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("location", "date", name="uq_location_date"),
    )

    def to_dict(self):
        total = self.hours_on + self.hours_off
        return {
            "location":      self.location,
            "date":          self.date.isoformat(),
            "hours_on":      round(self.hours_on, 2),
            "hours_off":     round(self.hours_off, 2),
            "uptime_pct":    round((self.hours_on / total * 100) if total else 0, 1),
            "reading_count": self.reading_count,
        }
