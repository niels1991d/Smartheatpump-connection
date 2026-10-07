"""Opdrachtregel: `python -m smartheatpump <commando>`."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import tinytuya

from .client import HeatPump, HeatPumpError
from .config import load_config


def _pump(args) -> HeatPump:
    return HeatPump(load_config(args.config), prefer=args.via)


def cmd_scan(args) -> None:
    print("Zoeken naar Tuya-apparaten op het lokale netwerk (±18 s)...")
    devices = tinytuya.deviceScan(verbose=False, maxretry=args.retries)
    if not devices:
        print("Niets gevonden. Zit je op hetzelfde netwerk als de warmtepomp?")
        return
    for ip, d in devices.items():
        print(f"{ip:15}  id={d.get('gwId')}  versie={d.get('version')}")


def cmd_dps(args) -> None:
    print(json.dumps(_pump(args).raw_dps(), indent=2, ensure_ascii=False))


def cmd_status(args) -> None:
    pump = _pump(args)
    s = pump.status()
    if args.json:
        print(json.dumps(s.as_dict(), ensure_ascii=False))
        return
    aan = {True: "aan", False: "uit", None: "?"}[s.power]
    print(f"Verbinding:       {pump.mode}")
    print(f"Status:           {aan}")
    print(f"Watertemperatuur: {s.current_temp} °C")
    print(f"Doeltemperatuur:  {s.target_temp} °C")
    print(f"Modus:            {s.mode}")
    if s.fault:
        print(f"Storing:          {s.fault}")


def cmd_on(args) -> None:
    _pump(args).set_power(True)
    print("Warmtepomp aangezet.")


def cmd_off(args) -> None:
    _pump(args).set_power(False)
    print("Warmtepomp uitgezet.")


def cmd_set_temp(args) -> None:
    _pump(args).set_target_temp(args.celsius)
    print(f"Doeltemperatuur ingesteld op {args.celsius} °C.")


def cmd_set_mode(args) -> None:
    _pump(args).set_mode(args.mode)
    print(f"Modus ingesteld op {args.mode}.")


def cmd_log(args) -> None:
    pump = _pump(args)
    out = Path(args.file)
    new = not out.exists()
    print(f"Loggen naar {out} elke {args.interval} s (Ctrl+C om te stoppen).")
    with out.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["tijd", "aan", "watertemp", "doeltemp", "modus", "storing"])
        while True:
            try:
                s = pump.status()
                w.writerow([datetime.now().isoformat(timespec="seconds"), s.power,
                            s.current_temp, s.target_temp, s.mode, s.fault])
                f.flush()
                print(f"{datetime.now():%H:%M:%S}  {s.current_temp} °C → {s.target_temp} °C")
            except HeatPumpError as e:
                print(f"Fout: {e}", file=sys.stderr)
            time.sleep(args.interval)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smartheatpump", description="Verbinding met je Tuya/Smart Heatpump-warmtepomp.")
    p.add_argument("-c", "--config", help="pad naar config.json (standaard ./config.json)")
    p.add_argument("--via", choices=["auto", "local", "cloud"], default="auto", help="verbindingstype")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="zoek warmtepompen op je netwerk")
    s.add_argument("--retries", type=int, default=15)
    s.set_defaults(func=cmd_scan)

    sub.add_parser("dps", help="toon alle ruwe datapoints").set_defaults(func=cmd_dps)

    s = sub.add_parser("status", help="toon de status")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    sub.add_parser("on", help="zet de warmtepomp aan").set_defaults(func=cmd_on)
    sub.add_parser("off", help="zet de warmtepomp uit").set_defaults(func=cmd_off)

    s = sub.add_parser("set-temp", help="stel de doeltemperatuur in")
    s.add_argument("celsius", type=float)
    s.set_defaults(func=cmd_set_temp)

    s = sub.add_parser("set-mode", help="stel de modus in (waarde verschilt per model)")
    s.add_argument("mode")
    s.set_defaults(func=cmd_set_mode)

    s = sub.add_parser("log", help="log de status periodiek naar CSV")
    s.add_argument("--interval", type=int, default=60)
    s.add_argument("--file", default="warmtepomp.csv")
    s.set_defaults(func=cmd_log)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except HeatPumpError as e:
        print(f"Fout: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    return 0
