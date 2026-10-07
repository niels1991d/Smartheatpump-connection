"""Web-app (voor op je iPhone-beginscherm) + kleine API rond de warmtepomp."""

from __future__ import annotations

import os
import secrets
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .client import HeatPump, HeatPumpError
from .config import Config, load_config
from .demo import DemoHeatPump
from .history import History

WEB_DIR = Path(__file__).parent / "web"
STATUS_CACHE_SECONDS = 3


def create_app(
    config: Config | None = None,
    pump=None,
    history: History | None = None,
    sample_interval: int = 300,
) -> Flask:
    config = config or load_config()
    demo = os.environ.get("SHP_DEMO") == "1"
    history = history or History(os.environ.get("SHP_HISTORY_DB", "history.db"))
    if pump is None and demo:
        if not history.since(86400):
            _seed_demo_history(history)
        recent = history.since(86400)
        pump = DemoHeatPump(config, current=recent[-1]["current"] if recent else 24.6)
    pump = pump or HeatPump(config)

    app = Flask(__name__, static_folder=None)
    lock = threading.Lock()
    cache: dict = {"at": 0.0, "status": None}

    def read_status(fresh: bool = False):
        with lock:
            if fresh or time.monotonic() - cache["at"] > STATUS_CACHE_SECONDS:
                cache["status"] = pump.status()
                cache["at"] = time.monotonic()
            return cache["status"]

    def status_payload(fresh: bool = False):
        s = read_status(fresh)
        return {**s.as_dict(), "connection": pump.mode, "updated": int(time.time())}

    @app.before_request
    def check_password():
        if not request.path.startswith("/api/") or request.path == "/api/info":
            return None
        if config.app_password and not secrets.compare_digest(
            request.headers.get("X-App-Password", ""), config.app_password
        ):
            return jsonify(error="Onjuist wachtwoord"), 401
        return None

    @app.errorhandler(HeatPumpError)
    def on_pump_error(e):
        return jsonify(error=str(e)), 502

    @app.get("/api/info")
    def info():
        return jsonify(
            auth_required=bool(config.app_password),
            modes=config.modes,
            temp_min=config.temp_min,
            temp_max=config.temp_max,
            connection=pump.mode,
        )

    @app.get("/api/status")
    def status():
        return jsonify(status_payload())

    def body() -> dict:
        return request.get_json(silent=True) or {}

    @app.post("/api/power")
    def power():
        pump.set_power(bool(body().get("on")))
        return jsonify(status_payload(fresh=True))

    @app.post("/api/target")
    def target():
        try:
            celsius = float(body()["celsius"])
        except (KeyError, TypeError, ValueError):
            return jsonify(error="Geef 'celsius' op als getal"), 400
        pump.set_target_temp(celsius)
        return jsonify(status_payload(fresh=True))

    @app.post("/api/mode")
    def mode():
        value = body().get("mode")
        if value not in {m["value"] for m in config.modes}:
            return jsonify(error="Onbekende modus"), 400
        pump.set_mode(value)
        return jsonify(status_payload(fresh=True))

    @app.get("/api/history")
    def hist():
        hours = min(max(request.args.get("hours", 24, type=int), 1), 24 * 30)
        return jsonify(history.since(hours * 3600))

    @app.get("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.get("/<path:name>")
    def static_file(name):
        return send_from_directory(WEB_DIR, name)

    if sample_interval > 0:
        def sampler():
            while True:
                try:
                    history.add(read_status(fresh=True))
                except Exception as e:  # noqa: BLE001 - blijf doorgaan bij netwerkfouten
                    app.logger.warning("Status ophalen mislukt: %s", e)
                time.sleep(sample_interval)

        threading.Thread(target=sampler, daemon=True).start()

    return app


def _seed_demo_history(history: History) -> None:
    """Een dag aan nepmetingen zodat de grafiek in demo-modus iets laat zien."""
    from .client import Status

    now = int(time.time())
    temp = 23.0
    for i in range(288, 0, -1):
        ts = now - i * 300
        on = i < 100 or i > 220  # 's nachts even uit
        goal = 28.0 if on else 19.0
        temp += (goal - temp) * (0.02 if on else 0.006)
        history.add(Status(on, 28.0, round(temp, 1), None, 0, {}), ts=ts)

def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    create_app().run(host=host, port=port, threaded=True)
