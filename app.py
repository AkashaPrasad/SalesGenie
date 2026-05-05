"""SalesGenie Flask application entry point."""

import logging
import os

from flask import Flask
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config

cache = Cache()
limiter = Limiter(
    key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(test_config: dict | None = None) -> Flask:
    """Flask application factory.

    Args:
        test_config: Optional dict to override config in tests.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    _configure_app(app, test_config)
    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_security_headers(app)

    return app


def _configure_app(app: Flask, test_config: dict | None) -> None:
    """Apply Flask configuration from config class or test overrides."""
    if test_config:
        for k, v in test_config.items():
            os.environ.setdefault(k, str(v))

    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-only-insecure-key"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not (
            test_config is not None
            or os.environ.get("FLASK_DEBUG", "false").lower() == "true"
        ),
        TESTING=test_config is not None,
        CACHE_TYPE="SimpleCache",
        CACHE_DEFAULT_TIMEOUT=60,
    )

    if test_config:
        app.config.update(test_config)


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    cache.init_app(app)
    limiter.init_app(app)


def _register_blueprints(app: Flask) -> None:
    """Register all Blueprint route modules."""
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.leads import leads_bp
    from routes.outreach import outreach_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(outreach_bp)


def _register_error_handlers(app: Flask) -> None:
    """Register custom HTTP error handlers."""
    from flask import jsonify, render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("index.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({"error": "Rate limit exceeded. Please slow down."}), 429

    @app.errorhandler(500)
    def server_error(e):
        logger.error("Internal server error: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500


def _register_security_headers(app: Flask) -> None:
    """Add OWASP-recommended security headers to every response."""

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        return response


if __name__ == "__main__":
    application = create_app()
    application.run(debug=Config.DEBUG, port=5000)
