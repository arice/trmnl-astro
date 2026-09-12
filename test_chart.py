#!/usr/bin/env python3
"""
Local test script for chart rendering.
Run: pip install svgwrite cairosvg pillow pyyaml && python test_chart.py

Generates both production and dev charts.

Position data, in order of preference:
  1. docs/last_positions.json, when it is fresh (CI rewrites it every 5 minutes)
  2. the same file from GitHub Pages, when the local copy has gone stale
  3. _FALLBACK_POSITIONS, a hand-picked collision test case (--fallback forces this)
"""

import io
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import cairosvg
import yaml
from PIL import Image

from renderers import render_production, render_dev

# Load config
with open('config.yaml', 'r') as f:
    CONFIG = yaml.safe_load(f)

# Positions from 2026-03-09 12:03pm — reproduces Saturn/Venus/Neptune collision near top
_FALLBACK_POSITIONS = {
    'sun':     {'lon': 349.08, 'sign': 11, 'deg': 19, 'min':  5, 'retrograde': False},
    'moon':    {'lon': 240.22, 'sign':  8, 'deg':  0, 'min': 13, 'retrograde': False},
    'mercury': {'lon': 344.65, 'sign': 11, 'deg': 14, 'min': 39, 'retrograde': True},
    'venus':   {'lon':   4.00, 'sign':  0, 'deg':  4, 'min':  0, 'retrograde': False},
    'mars':    {'lon': 335.57, 'sign': 11, 'deg':  5, 'min': 34, 'retrograde': False},
    'jupiter': {'lon': 105.08, 'sign':  3, 'deg': 15, 'min':  5, 'retrograde': True},
    'saturn':  {'lon':   2.77, 'sign':  0, 'deg':  2, 'min': 46, 'retrograde': False},
    'uranus':  {'lon':  57.93, 'sign':  1, 'deg': 27, 'min': 56, 'retrograde': False},
    'neptune': {'lon':   1.35, 'sign':  0, 'deg':  1, 'min': 21, 'retrograde': False},
    'pluto':   {'lon': 304.75, 'sign': 10, 'deg':  4, 'min': 45, 'retrograde': False},
    'ascendant':   {'lon':  84.60, 'sign': 2, 'deg': 24, 'min': 36, 'retrograde': False},
    'medium_coeli': {'lon': 330.88, 'sign': 11, 'deg':  0, 'min': 53, 'retrograde': False},
}

_POSITIONS_FILE = 'docs/last_positions.json'
_PAGES_URL = 'https://arice.github.io/trmnl-astro/last_positions.json'

# CI rewrites last_positions.json every 5 minutes, so an old mtime just means this
# repo has not been pulled lately — past this age, trust the network instead.
_STALE_AFTER = timedelta(hours=2)


def _file_age(path):
    return timedelta(seconds=time.time() - os.path.getmtime(path))


def _fmt_age(age):
    hours = age.total_seconds() / 3600
    if hours < 1:
        return f"{age.total_seconds() / 60:.0f} min old"
    if hours < 48:
        return f"{hours:.1f} hours old"
    return f"{hours / 24:.0f} days old"


def _read_local():
    with open(_POSITIONS_FILE) as f:
        return json.load(f)


def _sun_lon_now():
    """Approximate ecliptic longitude of the Sun right now, to within ~0.02°.

    Low-precision solar formula from the Astronomical Almanac. Plenty accurate
    for telling which day a set of positions is from — the Sun moves ~1°/day.
    """
    epoch = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    n = (datetime.now(timezone.utc) - epoch).total_seconds() / 86400
    mean_lon = 280.460 + 0.9856474 * n
    mean_anom = math.radians(357.528 + 0.9856003 * n)
    return (mean_lon + 1.915 * math.sin(mean_anom) + 0.020 * math.sin(2 * mean_anom)) % 360


def _warn_if_wrong_day(positions):
    """Cross-check the data against the real sky.

    Charts are stamped with datetime.now() rather than the data's own time, so
    stale positions still render as though current. This is what catches that.
    """
    sun = positions.get('sun')
    if not sun:
        return
    off = abs((sun['lon'] - _sun_lon_now() + 180) % 360 - 180)
    if off > 1.5:
        print(f"\n  WARNING: the Sun is {off:.1f}° from where it actually is right now")
        print(f"           (~{off / 0.9856:.0f} days off) — this is not today's sky.")
        print("           Run: git pull --rebase\n")


def load_positions():
    """Pick the freshest positions source available."""
    if '--fallback' in sys.argv:
        print("Using fallback positions (collision test case)")
        return _FALLBACK_POSITIONS

    local_age = _file_age(_POSITIONS_FILE) if os.path.exists(_POSITIONS_FILE) else None

    if local_age is not None and local_age < _STALE_AFTER:
        print(f"Using live positions from {_POSITIONS_FILE} ({_fmt_age(local_age)})")
        return _read_local()

    if local_age is not None:
        print(f"{_POSITIONS_FILE} is {_fmt_age(local_age)} — fetching from GitHub Pages instead")

    try:
        with urllib.request.urlopen(_PAGES_URL, timeout=5) as r:
            positions = json.load(r)
        print(f"Using live positions from {_PAGES_URL}")
        return positions
    except Exception as e:
        print(f"Could not reach {_PAGES_URL}: {e}")

    if local_age is not None:
        print(f"Falling back to stale {_POSITIONS_FILE} ({_fmt_age(local_age)})")
        return _read_local()

    print("Using mock positions (no other source available)")
    return _FALLBACK_POSITIONS


POSITIONS = load_positions()
if '--fallback' not in sys.argv:
    _warn_if_wrong_day(POSITIONS)


def svg_to_png(svg_content, output_path):
    """Convert SVG to 4-level grayscale PNG"""
    png_data = cairosvg.svg2png(
        bytestring=svg_content.encode('utf-8'),
        output_width=800,
        output_height=480
    )
    img = Image.open(io.BytesIO(png_data))
    img = img.convert('L')
    img = img.point(lambda x: [0, 85, 170, 255][min(x // 64, 3)], 'L')
    img.save(output_path, format='PNG', optimize=True)
    print(f"  Saved: {output_path}")


if __name__ == "__main__":
    print("Rendering test charts...\n")

    print("Production renderer:")
    svg_prod = render_production(POSITIONS, CONFIG)
    svg_to_png(svg_prod, "./test_chart_prod.png")

    print("\nDev renderer:")
    svg_dev = render_dev(POSITIONS, CONFIG)
    svg_to_png(svg_dev, "./test_chart_dev.png")

    print("\nDone! Open test_chart_prod.png and test_chart_dev.png to compare.")
