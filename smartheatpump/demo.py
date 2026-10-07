"""Nep-warmtepomp om de app te bekijken zonder echte verbinding (SHP_DEMO=1)."""

from __future__ import annotations

import threading
import time

from .client import HeatPumpError, Status
from .config import Config


class DemoHeatPump:
    mode = "demo"

    def __init__(self, config: Config, current: float = 24.6):
        self.config = config
        self._lock = threading.Lock()
        self._power = True
        self._target = 28.0
        self._current = current
        self._mode = config.modes[0]["value"] if config.modes else "heat"
        self._last = time.monotonic()

    def _tick(self) -> None:
        # Watertemperatuur beweegt langzaam richting doel als de pomp aan staat.
        now = time.monotonic()
        dt, self._last = now - self._last, now
        goal = self._target if self._power else 18.0
        rate = 0.02 if self._power else 0.005  # °C per seconde
        step = min(abs(goal - self._current), rate * dt)
        self._current += step if goal > self._current else -step

    def status(self) -> Status:
        with self._lock:
            self._tick()
            return Status(
                power=self._power,
                target_temp=self._target,
                current_temp=round(self._current, 1),
                mode=self._mode,
                fault=0,
                raw={},
            )

    def set_power(self, on: bool) -> None:
        with self._lock:
            self._tick()
            self._power = bool(on)

    def set_target_temp(self, celsius: float) -> None:
        lo, hi = self.config.temp_min, self.config.temp_max
        if not lo <= celsius <= hi:
            raise HeatPumpError(f"Doeltemperatuur moet tussen {lo:g} en {hi:g} °C liggen.")
        with self._lock:
            self._tick()
            self._target = float(celsius)

    def set_mode(self, mode: str) -> None:
        with self._lock:
            self._mode = mode
