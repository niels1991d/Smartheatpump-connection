import pytest

from smartheatpump.config import Config
from smartheatpump.demo import DemoHeatPump
from smartheatpump.history import History
from smartheatpump.server import create_app


def make_client(tmp_path, **cfg):
    config = Config(**cfg)
    app = create_app(config, pump=DemoHeatPump(config), history=History(str(tmp_path / "h.db")), sample_interval=0)
    return app.test_client()


@pytest.fixture
def client(tmp_path):
    return make_client(tmp_path)


def test_index_and_info(client):
    assert b"Warmtepomp" in client.get("/").data
    info = client.get("/api/info").get_json()
    assert info["auth_required"] is False
    assert info["modes"][0]["value"] == "heat"


def test_status_and_controls(client):
    assert client.get("/api/status").get_json()["power"] is True
    assert client.post("/api/power", json={"on": False}).get_json()["power"] is False
    assert client.post("/api/target", json={"celsius": 30}).get_json()["target_temp"] == 30
    assert client.post("/api/mode", json={"mode": "cool"}).get_json()["mode"] == "cool"


def test_invalid_input(client):
    assert client.post("/api/target", json={}).status_code == 400
    assert client.post("/api/target", json={"celsius": 99}).status_code == 502
    assert client.post("/api/mode", json={"mode": "turbo"}).status_code == 400


def test_password_required(tmp_path):
    c = make_client(tmp_path, app_password="geheim")
    assert c.get("/api/info").get_json()["auth_required"] is True
    assert c.get("/api/status").status_code == 401
    assert c.get("/api/status", headers={"X-App-Password": "fout"}).status_code == 401
    assert c.get("/api/status", headers={"X-App-Password": "geheim"}).status_code == 200


def test_history(tmp_path):
    config = Config()
    pump = DemoHeatPump(config)
    history = History(str(tmp_path / "h.db"))
    history.add(pump.status())
    c = create_app(config, pump=pump, history=history, sample_interval=0).test_client()
    rows = c.get("/api/history?hours=1").get_json()
    assert len(rows) == 1 and rows[0]["target"] == 28.0
