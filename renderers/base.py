"""
Shared constants and utilities for chart renderers.
"""

import math

# Astrological glyphs
BODY_GLYPHS = {
    'sun': '\u2609',        # ☉
    'moon': '\u263D',       # ☽
    'mercury': '\u263F',    # ☿
    'venus': '\u2640',      # ♀
    'mars': '\u2642',       # ♂
    'jupiter': '\u2643',    # ♃
    'saturn': '\u2644',     # ♄
    'uranus': '\u2645',     # ♅
    'neptune': '\u2646',    # ♆
    'pluto': '\u2647',      # ♇
    'mean_north_lunar_node': '\u260A',  # ☊ (North Node)
    'mean_south_lunar_node': '\u260B',  # ☋ (South Node)
    'ascendant': 'ASC',
    'medium_coeli': 'MC'
}

SIGN_GLYPHS = [
    '\u2648',  # ♈ Aries
    '\u2649',  # ♉ Taurus
    '\u264A',  # ♊ Gemini
    '\u264B',  # ♋ Cancer
    '\u264C',  # ♌ Leo
    '\u264D',  # ♍ Virgo
    '\u264E',  # ♎ Libra
    '\u264F',  # ♏ Scorpio
    '\u2650',  # ♐ Sagittarius
    '\u2651',  # ♑ Capricorn
    '\u2652',  # ♒ Aquarius
    '\u2653',  # ♓ Pisces
]

# Moon phase symbols (8 phases)
MOON_PHASES = [
    '\U0001F311',  # 🌑 New Moon (0-45°)
    '\U0001F312',  # 🌒 Waxing Crescent (45-90°)
    '\U0001F313',  # 🌓 First Quarter (90-135°)
    '\U0001F314',  # 🌔 Waxing Gibbous (135-180°)
    '\U0001F315',  # 🌕 Full Moon (180-225°)
    '\U0001F316',  # 🌖 Waning Gibbous (225-270°)
    '\U0001F317',  # 🌗 Last Quarter (270-315°)
    '\U0001F318',  # 🌘 Waning Crescent (315-360°)
]

# Retrograde symbol
RETROGRADE_GLYPH = 'R'

# Colors for 2-bit grayscale e-ink display
DARK_GRAY = '#555555'


def get_moon_phase(positions):
    """Calculate moon phase from Sun-Moon angle (0-7 index)"""
    if 'sun' not in positions or 'moon' not in positions:
        return None
    sun_lon = positions['sun']['lon']
    moon_lon = positions['moon']['lon']
    # Moon's elongation from Sun (0-360°)
    elongation = (moon_lon - sun_lon) % 360
    # Divide into 8 phases (45° each)
    phase_index = int((elongation + 12) / 45) % 8
    return phase_index


def get_house_number(body_sign, asc_sign):
    """Calculate whole sign house number (1-12) from planet and ASC signs"""
    return ((body_sign - asc_sign) % 12) + 1


def ordinal(n):
    """Return ordinal string for a number (1st, 2nd, 3rd, etc.)"""
    if 11 <= n <= 13:
        return f"{n}th"
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"
