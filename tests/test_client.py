import json

import pytest

from smartheatpump import HeatPump, HeatPumpError, load_config
from smartheatpump.config import Config


class FakeDevice:
    def __init__(self, *a, **kw):
        self.dps = {"1": True, "2": 280, "3": 254, "4": "heat", "15": 0}
        self.sent = []

    def set_socketTimeout(self, t):
        pass

    def status(self):
        return {"dps": dict(self.dps)}

    def set_value(self, dp, value):
        self.sent.append((dp, value))
        return {"dps": {str(dp): value}}


@pytest.fixture
def pump(monkeypatch):
    monkeypatch.setattr("smartheatpump.client.tinytuya.Device", FakeDevice)
    cfg = Config(device_id="abc", ip="1.2.3.4", local_key="k", temp_scale=10)
    return HeatPump(cfg)


def test_status_scales_temperatures(pump):
    s = pump.status()
    assert pump.mode == "local"
    assert s.power is True
    assert s.target_temp == 28.0
    assert s.current_temp == 25.4
    assert s.mode == "heat"


def test_set_target_temp(pump):
    pump.set_target_temp(30.5)
    assert pump._dev.sent == [(2, 305)]


def test_set_target_temp_out_of_range(pump):
    with pytest.raises(HeatPumpError):
        pump.set_target_temp(90)


def test_power(pump):
    pump.set_power(False)
    assert pump._dev.sent == [(1, False)]


def test_no_connection_configured():
    with pytest.raises(HeatPumpError):
        HeatPump(Config())


def test_load_config_env_overrides(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"device_id": "x", "ip": "1.1.1.1", "dp_map": {"current_temp": 21}}))
    monkeypatch.setenv("SHP_LOCAL_KEY", "geheim")
    cfg = load_config(p)
    assert cfg.local_key == "geheim"
    assert cfg.dp_map["current_temp"] == "21"
    assert cfg.dp_map["power"] == "1"
    assert cfg.has_local
