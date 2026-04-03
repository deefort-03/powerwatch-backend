# routes/reports.py
from flask import Blueprint, request, jsonify
from extensions import db
from models import DailySummary, VALID_LOCATIONS
from datetime import date, timedelta
from sqlalchemy import extract

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/daily/<location>", methods=["GET"])
def daily(location):
    location = location.lower()
    if location not in VALID_LOCATIONS:
        return jsonify({"error": "Invalid location"}), 404
    days = min(int(request.args.get("days", 7)), 365)
    start_date = date.today() - timedelta(days=days - 1)
    summaries = (DailySummary.query
        .filter(DailySummary.location == location, DailySummary.date >= start_date)
        .order_by(DailySummary.date.asc()).all())
    summary_map = {s.date: s for s in summaries}
    result = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        if day in summary_map:
            result.append(summary_map[day].to_dict())
        else:
            result.append({"location": location, "date": day.isoformat(),
                           "hours_on": 0.0, "hours_off": 0.0, "uptime_pct": 0.0, "reading_count": 0})
    return jsonify(result)


@reports_bp.route("/daily/all", methods=["GET"])
def daily_all():
    days = min(int(request.args.get("days", 7)), 365)
    start_date = date.today() - timedelta(days=days - 1)
    summaries = (DailySummary.query
        .filter(DailySummary.date >= start_date)
        .order_by(DailySummary.date.asc()).all())
    grid = {}
    for s in summaries:
        if s.date not in grid:
            grid[s.date] = {}
        grid[s.date][s.location] = round(s.hours_on, 2)
    result = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        entry = {"date": day.isoformat()}
        for loc in VALID_LOCATIONS:
            entry[loc] = grid.get(day, {}).get(loc, 0.0)
        result.append(entry)
    return jsonify(result)


@reports_bp.route("/monthly/<location>", methods=["GET"])
def monthly(location):
    location = location.lower()
    if location not in VALID_LOCATIONS:
        return jsonify({"error": "Invalid location"}), 404
    year = int(request.args.get("year", date.today().year))
    summaries = (DailySummary.query
        .filter(DailySummary.location == location, extract("year", DailySummary.date) == year)
        .all())
    monthly_totals = {}
    for s in summaries:
        m = s.date.month
        if m not in monthly_totals:
            monthly_totals[m] = {"hours_on": 0.0, "hours_off": 0.0}
        monthly_totals[m]["hours_on"]  += s.hours_on
        monthly_totals[m]["hours_off"] += s.hours_off
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    result = []
    for m in range(1, 13):
        data = monthly_totals.get(m, {"hours_on": 0.0, "hours_off": 0.0})
        total = data["hours_on"] + data["hours_off"]
        result.append({"month": m, "month_name": month_names[m-1],
                       "hours_on": round(data["hours_on"], 2),
                       "hours_off": round(data["hours_off"], 2),
                       "uptime_pct": round((data["hours_on"]/total*100) if total else 0, 1)})
    return jsonify(result)


@reports_bp.route("/monthly/all", methods=["GET"])
def monthly_all():
    year = int(request.args.get("year", date.today().year))
    summaries = (DailySummary.query
        .filter(extract("year", DailySummary.date) == year).all())
    grid = {}
    for s in summaries:
        m = s.date.month
        if m not in grid:
            grid[m] = {}
        grid[m][s.location] = grid[m].get(s.location, 0.0) + s.hours_on
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    result = []
    for m in range(1, 13):
        entry = {"month": m, "month_name": month_names[m-1]}
        for loc in VALID_LOCATIONS:
            entry[loc] = round(grid.get(m, {}).get(loc, 0.0), 2)
        result.append(entry)
    return jsonify(result)
