"""Configuratie laden uit een JSON-bestand en omgevingsvariabelen."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# Veelgebruikte datapoints (DP's) bij Tuya-warmtepompen (o.a. zwembadwarmtepompen).
# Dit verschilt per model: controleer met `smartheatpump dps` en pas zo nodig aan
# in config.json onder "dp_map".
DEFAULT_DP_MAP: dict[str, str] = {
    "power": "1",
    "target_temp": "2",
    "current_temp": "3",
    "mode": "4",
    "fault": "15",
}

# Modi zoals de warmtepomp ze kent (waarde) en hoe de app ze toont (label).
DEFAULT_MODES: list[dict[str, str]] = [
    {"value": "heat", "label": "Verwarmen"},
    {"value": "cool", "label": "Koelen"},
    {"value": "auto", "label": "Auto"},
]


@dataclass
class Config:
    device_id: str = ""
    # Lokale verbinding
    ip: str = ""
    local_key: str = ""
    version: float = 3.3
    # Cloud-verbinding (Tuya IoT Platform)
    api_region: str = "eu"
    api_key: str = ""
    api_secret: str = ""
    # Welke DP welke betekenis heeft
    dp_map: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_DP_MAP))
    # Sommige modellen geven temperaturen ×10 terug (bijv. 285 = 28,5 °C)
    temp_scale: float = 1.0
    temp_min: float = 5.0
    temp_max: float = 40.0
    modes: list[dict[str, str]] = field(default_factory=lambda: [dict(m) for m in DEFAULT_MODES])
    # Wachtwoord voor de web-app (leeg = geen wachtwoord, alleen veilig in je eigen netwerk)
    app_password: str = ""

    @property
    def has_local(self) -> bool:
        return bool(self.device_id and self.ip and self.local_key)

    @property
    def has_cloud(self) -> bool:
        return bool(self.device_id and self.api_key and self.api_secret)


_ENV = {
    "device_id": "SHP_DEVICE_ID",
    "ip": "SHP_IP",
    "local_key": "SHP_LOCAL_KEY",
    "version": "SHP_VERSION",
    "api_region": "SHP_API_REGION",
    "api_key": "SHP_API_KEY",
    "api_secret": "SHP_API_SECRET",
    "temp_scale": "SHP_TEMP_SCALE",
    "temp_min": "SHP_TEMP_MIN",
    "temp_max": "SHP_TEMP_MAX",
    "app_password": "SHP_APP_PASSWORD",
}


def load_config(path: str | os.PathLike | None = None) -> Config:
    """Laad config uit `path` (standaard ./config.json); env-variabelen gaan voor."""
    data: dict = {}
    p = Path(path or os.environ.get("SHP_CONFIG", "config.json"))
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))

    for key, env in _ENV.items():
        if os.environ.get(env):
            data[key] = os.environ[env]

    dp_map = dict(DEFAULT_DP_MAP)
    dp_map.update({k: str(v) for k, v in data.pop("dp_map", {}).items()})

    cfg = Config(dp_map=dp_map, **{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    cfg.version = float(cfg.version)
    cfg.temp_scale = float(cfg.temp_scale)
    cfg.temp_min = float(cfg.temp_min)
    cfg.temp_max = float(cfg.temp_max)
    return cfg
