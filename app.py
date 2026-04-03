import os
from flask import Flask
from flask_cors import CORS
from extensions import db
from routes.sensor import sensor_bp
from routes.status import status_bp
from routes.reports import reports_bp
from routes.override import override_bp


def create_app():
    app = Flask(__name__)
    CORS(app)

    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/powerwatch")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

    db.init_app(app)

    app.register_blueprint(sensor_bp,   url_prefix="/api/sensor")
    app.register_blueprint(status_bp,   url_prefix="/api/status")
    app.register_blueprint(reports_bp,  url_prefix="/api/reports")
    app.register_blueprint(override_bp, url_prefix="/api/override")

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
