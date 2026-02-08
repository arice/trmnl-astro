#!/usr/bin/env python3
"""
TRMNL Astrology Current Chart Updater
Fetches current planetary positions and renders a custom wheel + legend chart
optimized for e-ink display.
"""

import os
import sys
import math
import requests
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo

# Load configuration from config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

# Configuration from environment variables
ASTROLOGER_API_URL = os.environ.get('ASTROLOGER_API_URL')
TRMNL_API_KEY = os.environ.get('TRMNL_API_KEY')
PLUGIN_UUID = os.environ.get('PLUGIN_UUID')
GITHUB_USERNAME = os.environ.get('GH_USERNAME')
GITHUB_REPO = os.environ.get('GH_REPO')

# TRMNL webhook endpoint
TRMNL_WEBHOOK_URL = f"https://usetrmnl.com/api/custom_plugins/{PLUGIN_UUID}"

# Output path for PNG
OUTPUT_PATH = "docs/chart.png"

# Location from config
LOCATION = CONFIG['location']

# Build chart payload from config
CHART_PAYLOAD = {
    "subject": {
        "name": f"{LOCATION['name']} Now",
        "year": None,
        "month": None,
        "day": None,
        "hour": None,
        "minute": None,
        "city": LOCATION['city'],
        "nation": LOCATION['nation'],
        "longitude": LOCATION['longitude'],
        "latitude": LOCATION['latitude'],
        "timezone": LOCATION['timezone']
    }
}

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

# Retrograde symbol (using simple R for compatibility)
RETROGRADE_GLYPH = 'R'

# Dark gray for secondary elements (2-bit grayscale support)
DARK_GRAY = '#555555'

# Bodies to display (from config)
BODIES = CONFIG.get('bodies', [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter',
    'saturn', 'uranus', 'neptune', 'pluto', 'mean_north_lunar_node',
    'mean_south_lunar_node', 'ascendant', 'medium_coeli'
])

# Display options from config
DISPLAY = CONFIG.get('display', {})
SHOW_RETROGRADE = DISPLAY.get('show_retrograde', True)
SHOW_MOON_PHASE = DISPLAY.get('show_moon_phase', True)
SHOW_HOUSE_NUMBERS = DISPLAY.get('show_house_numbers', True)


def get_positions():
    """Fetch position data from Astrologer API /api/v5/chart-data/birth-chart endpoint"""
    print(f"Fetching current planetary positions for {LOCATION['name']}...")

    # Get current time in configured timezone
    local_tz = ZoneInfo(LOCATION['timezone'])
    now = datetime.now(local_tz)

    CHART_PAYLOAD["subject"]["year"] = now.year
    CHART_PAYLOAD["subject"]["month"] = now.month
    CHART_PAYLOAD["subject"]["day"] = now.day
    CHART_PAYLOAD["subject"]["hour"] = now.hour
    CHART_PAYLOAD["subject"]["minute"] = now.minute

    print(f"Time ({LOCATION['name']}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    response = requests.post(
        f"{ASTROLOGER_API_URL}/api/v5/chart-data/birth-chart",
        json=CHART_PAYLOAD,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code} - {response.text}")

    data = response.json()

    if data.get("status") != "OK":
        raise Exception(f"Position fetch failed: {data}")

    # Extract position data from chart_data.subject
    positions = {}
    subject = data["chart_data"]["subject"]

    for body in BODIES:
        if body in subject and subject[body] is not None:
            pos = subject[body]
            abs_pos = pos.get('abs_pos', 0)
            sign_num = pos.get('sign_num', int(abs_pos // 30))
            position_in_sign = pos.get('position', abs_pos % 30)

            positions[body] = {
                'lon': abs_pos,
                'sign': sign_num,
                'deg': int(position_in_sign),
                'min': int((position_in_sign % 1) * 60),
                'retrograde': pos.get('retrograde', False)
            }

    print(f"Retrieved positions for {len(positions)} bodies")
    return positions


def get_moon_phase(positions):
    """Calculate moon phase from Sun-Moon angle (0-7 index)"""
    if 'sun' not in positions or 'moon' not in positions:
        return None
    sun_lon = positions['sun']['lon']
    moon_lon = positions['moon']['lon']
    # Moon's elongation from Sun (0-360°)
    elongation = (moon_lon - sun_lon) % 360
    # Divide into 8 phases (45° each)
    phase_index = int((elongation + 12) / 45) % 8 # add 12 to shift visual phase a little bit early to better reflect human perception
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


def render_chart_svg(positions):
    """Generate 800x480 wheel + legend SVG optimized for e-ink"""
    import svgwrite

    dwg = svgwrite.Drawing(size=('800px', '480px'))

    # White background
    dwg.add(dwg.rect(insert=(0, 0), size=('800px', '480px'), fill='white'))

    # === LEFT SIDE: Zodiac Wheel ===
    wheel_cx, wheel_cy = 220, 240  # Shifted left to make room for labels on right
    outer_r = 175          # Outer edge of sign ring
    inner_r = 150          # Inner edge of sign ring (main wheel boundary)
    sign_glyph_r = 163     # Sign glyphs centered in the ring
    planet_r = 125         # Planet glyphs inside the wheel (closer to ticks)
    degree_r = 195         # Degree labels OUTSIDE the wheel
    degree_r_min = 180     # Minimum radius for degree labels (pushed inward)
    degree_r_max = 210     # Maximum radius (avoid clipping at edges)
    tick_outer = inner_r   # Ticks attach to inner ring
    tick_inner = inner_r - 9  # Ticks extend inward toward planet glyphs (9px)

    # Calculate rotation so Ascendant is at 9 o'clock (180° screen angle)
    asc_lon = positions.get('ascendant', {}).get('lon', 0)
    rotation_offset = 180 - asc_lon  # Rotate wheel so ASC is at left

    def to_screen_angle(zodiac_lon):
        """Convert zodiac longitude to screen angle with ASC at 9 o'clock"""
        return math.radians(zodiac_lon + rotation_offset)

    # Outer circle (outer edge of sign ring)
    dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=outer_r,
                       stroke='black', stroke_width=2, fill='none'))

    # Inner circle (inner edge of sign ring / main wheel boundary)
    dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=inner_r,
                       stroke='black', stroke_width=2, fill='none'))

    # Draw 12 sign divisions and glyphs
    for i in range(12):
        # Line from center to outer circle at sign boundaries
        angle_rad = to_screen_angle(i * 30)

        x1 = wheel_cx
        y1 = wheel_cy
        x2 = wheel_cx + outer_r * math.cos(angle_rad)
        y2 = wheel_cy - outer_r * math.sin(angle_rad)

        dwg.add(dwg.line(start=(x1, y1), end=(x2, y2),
                        stroke='black', stroke_width=1))

        # Sign glyph centered in the narrow ring
        mid_angle_rad = to_screen_angle(i * 30 + 15)
        gx = wheel_cx + sign_glyph_r * math.cos(mid_angle_rad)
        gy = wheel_cy - sign_glyph_r * math.sin(mid_angle_rad)

        dwg.add(dwg.text(SIGN_GLYPHS[i], insert=(gx, gy + 6),
                        text_anchor='middle', font_size='18px',
                        font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black'))

    # Draw tick marks first
    for body in BODIES:
        if body in positions and body not in ['ascendant', 'medium_coeli']:
            pos = positions[body]
            lon = pos['lon']
            angle = to_screen_angle(lon)

            # Tick mark on inner ring
            t1x = wheel_cx + tick_inner * math.cos(angle)
            t1y = wheel_cy - tick_inner * math.sin(angle)
            t2x = wheel_cx + tick_outer * math.cos(angle)
            t2y = wheel_cy - tick_outer * math.sin(angle)
            dwg.add(dwg.line(start=(t1x, t1y), end=(t2x, t2y),
                            stroke=DARK_GRAY, stroke_width=2))

    # Draw degree labels with collision avoidance
    degree_labels = []
    for body in BODIES:
        if body in positions and body not in ['ascendant', 'medium_coeli']:
            pos = positions[body]
            lon = pos['lon']
            degree_labels.append((lon, pos['deg']))

    # Sort by longitude for collision detection
    degree_labels.sort(key=lambda x: x[0])
    placed_degrees = []  # (angle, radius) of placed labels

    for lon, deg in degree_labels:
        angle = to_screen_angle(lon)
        current_r = degree_r

        # Check for collisions - if too close angularly, adjust radius
        for placed_angle, placed_r in placed_degrees:
            angle_diff = abs(angle - placed_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            # If within ~8 degrees and same radius band, need to offset
            if angle_diff < 0.14 and abs(current_r - placed_r) < 12:
                # Check if pushing outward would clip at image edge
                test_x = wheel_cx + (current_r + 14) * math.cos(angle)
                test_y = wheel_cy - (current_r + 14) * math.sin(angle)
                if test_x < 15 or test_x > 785 or test_y < 15 or test_y > 465:
                    # Would clip - push inward instead
                    current_r = max(degree_r_min, current_r - 14)
                else:
                    # Safe to push outward
                    current_r = min(degree_r_max, current_r + 14)

        deg_x = wheel_cx + current_r * math.cos(angle)
        deg_y = wheel_cy - current_r * math.sin(angle)
        deg_label = f"{deg}°"
        dwg.add(dwg.text(deg_label, insert=(deg_x, deg_y + 4),
                        text_anchor='middle', font_size='12px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

        placed_degrees.append((angle, current_r))

    # Place planet glyphs on wheel at their longitudes
    planet_positions = []
    for body in BODIES:
        if body in positions and body not in ['ascendant', 'medium_coeli']:
            lon = positions[body]['lon']
            planet_positions.append((body, lon))

    # Collision avoidance: stack planets radially (adjust radius, not angle)
    # This keeps planets in their correct zodiacal position
    planet_positions.sort(key=lambda x: x[1])
    placed = []  # (angle, radius) of placed planets

    for body, lon in planet_positions:
        screen_angle = to_screen_angle(lon)
        current_r = planet_r

        # Check for collisions - if too close angularly, move inward
        for placed_angle, placed_r in placed:
            angle_diff = abs(screen_angle - placed_angle)
            # Also check wrap-around (e.g., 359° vs 1°)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            # If within ~10 degrees and same radius band, move inward
            if angle_diff < 0.18 and abs(current_r - placed_r) < 20:
                current_r -= 22  # Move inward by 22px

        px = wheel_cx + current_r * math.cos(screen_angle)
        py = wheel_cy - current_r * math.sin(screen_angle)

        placed.append((screen_angle, current_r))

        dwg.add(dwg.text(BODY_GLYPHS[body], insert=(px, py + 6),
                        text_anchor='middle', font_size='20px',
                        font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black',
                        font_weight='bold'))

    # Draw ASC tick on outer ring (always at 9 o'clock / 180°)
    if 'ascendant' in positions:
        asc_rad = math.radians(180)  # ASC is always at 9 o'clock
        # Tick mark on outer ring (175 → 185)
        tick_start_x = wheel_cx + outer_r * math.cos(asc_rad)
        tick_start_y = wheel_cy - outer_r * math.sin(asc_rad)
        tick_end_x = wheel_cx + (outer_r + 10) * math.cos(asc_rad)
        tick_end_y = wheel_cy - (outer_r + 10) * math.sin(asc_rad)
        dwg.add(dwg.line(start=(tick_start_x, tick_start_y), end=(tick_end_x, tick_end_y),
                        stroke='black', stroke_width=2))
        # ASC label outside the wheel
        label_x = wheel_cx + (degree_r + 8) * math.cos(asc_rad)
        label_y = wheel_cy - (degree_r + 8) * math.sin(asc_rad)
        dwg.add(dwg.text('ASC', insert=(label_x, label_y + 4),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black',
                        font_weight='bold'))
        # ASC degree label below
        asc_deg = positions['ascendant']['deg']
        dwg.add(dwg.text(f"{asc_deg}°", insert=(label_x, label_y + 16),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

    # Draw MC tick on outer ring (rotated with the wheel)
    if 'medium_coeli' in positions:
        mc_rad = to_screen_angle(positions['medium_coeli']['lon'])
        # Tick mark on outer ring (175 → 185)
        tick_start_x = wheel_cx + outer_r * math.cos(mc_rad)
        tick_start_y = wheel_cy - outer_r * math.sin(mc_rad)
        tick_end_x = wheel_cx + (outer_r + 10) * math.cos(mc_rad)
        tick_end_y = wheel_cy - (outer_r + 10) * math.sin(mc_rad)
        dwg.add(dwg.line(start=(tick_start_x, tick_start_y), end=(tick_end_x, tick_end_y),
                        stroke='black', stroke_width=2))
        label_x = wheel_cx + (degree_r + 8) * math.cos(mc_rad)
        label_y = wheel_cy - (degree_r + 8) * math.sin(mc_rad)
        dwg.add(dwg.text('MC', insert=(label_x, label_y + 4),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black',
                        font_weight='bold'))
        # MC degree label below
        mc_deg = positions['medium_coeli']['deg']
        dwg.add(dwg.text(f"{mc_deg}°", insert=(label_x, label_y + 16),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

    # === RIGHT SIDE: Legend Panel ===
    legend_x = 470
    legend_y_start = 25
    line_height = 30  # Reduced to fit 14 items above timestamp

    # Get ASC sign for house calculations
    asc_sign = positions.get('ascendant', {}).get('sign', 0)

    # Header with moon phase
    header_text = 'Planetary Positions'
    if SHOW_MOON_PHASE:
        moon_phase_idx = get_moon_phase(positions)
        if moon_phase_idx is not None:
            header_text = f'{MOON_PHASES[moon_phase_idx]} {header_text}'

    dwg.add(dwg.text(header_text, insert=(legend_x + 130, legend_y_start),
                    text_anchor='middle', font_size='18px',
                    font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black',
                    font_weight='bold'))

    # Divider line
    dwg.add(dwg.line(start=(legend_x, legend_y_start + 10),
                    end=(legend_x + 260, legend_y_start + 10),
                    stroke='black', stroke_width=1))

    # List each body with position
    y = legend_y_start + 40
    for body in BODIES:
        if body in positions:
            pos = positions[body]
            glyph = BODY_GLYPHS[body]
            sign_glyph = SIGN_GLYPHS[pos['sign']]
            deg_str = f"{pos['deg']:02d}\u00B0{pos['min']:02d}'"

            # Body glyph
            dwg.add(dwg.text(glyph, insert=(legend_x + 10, y),
                            font_size='20px', font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black', font_weight='bold'))

            # Sign glyph
            dwg.add(dwg.text(sign_glyph, insert=(legend_x + 60, y),
                            font_size='20px', font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black'))

            # Degrees
            dwg.add(dwg.text(deg_str, insert=(legend_x + 100, y),
                            font_size='18px', font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black'))

            # Retrograde indicator (right after degrees)
            if SHOW_RETROGRADE and pos.get('retrograde', False):
                dwg.add(dwg.text(RETROGRADE_GLYPH, insert=(legend_x + 168, y),
                                font_size='14px', font_family='DejaVu Sans, Arial, sans-serif',
                                fill='black', font_weight='bold'))

            # House number (not for ASC/MC - they define the houses)
            if SHOW_HOUSE_NUMBERS and body not in ['ascendant', 'medium_coeli']:
                house_num = get_house_number(pos['sign'], asc_sign)
                dwg.add(dwg.text(ordinal(house_num), insert=(legend_x + 195, y),
                                font_size='16px', font_family='DejaVu Sans, Arial, sans-serif',
                                fill='black'))

            y += line_height

    # Timestamp at bottom (using configured timezone)
    local_tz = ZoneInfo(LOCATION['timezone'])
    now_local = datetime.now(local_tz)
    date_str = now_local.strftime('%B %d %Y')
    time_str = now_local.strftime('%-I:%M %p').lower()
    timestamp = f"{date_str} {time_str}"
    dwg.add(dwg.text(f"{LOCATION['name']} | {timestamp}", insert=(legend_x + 130, 460),
                    text_anchor='middle', font_size='14px',
                    font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill=DARK_GRAY))

    return dwg.tostring()


def svg_to_png_grayscale(svg_content, output_path=OUTPUT_PATH):
    """Convert SVG to 4-level grayscale PNG for TRMNL 2-bit e-ink display"""
    print("Converting SVG to 4-level grayscale PNG for e-ink...")

    try:
        import cairosvg
        from PIL import Image
        import io
    except ImportError:
        print("Installing required packages...")
        os.system(f"{sys.executable} -m pip install cairosvg pillow")
        import cairosvg
        from PIL import Image
        import io

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    png_data = cairosvg.svg2png(
        bytestring=svg_content.encode('utf-8'),
        output_width=800,
        output_height=480
    )

    img = Image.open(io.BytesIO(png_data))
    img = img.convert('L')
    # 4-level quantization for 2-bit grayscale: 0, 85, 170, 255
    img = img.point(lambda x: [0, 85, 170, 255][min(x // 64, 3)], 'L')

    img.save(output_path, format='PNG', optimize=True)

    file_size = os.path.getsize(output_path)
    print(f"PNG saved to {output_path} ({file_size} bytes)")

    return output_path


def send_to_trmnl():
    """Send image URL to TRMNL via webhook"""
    print("Sending URL to TRMNL...")

    timestamp = int(datetime.now().timestamp())
    image_url = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/chart.png?t={timestamp}"

    payload = {
        "merge_variables": {
            "chart_url": image_url,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M EST")
        }
    }

    headers = {
        "Authorization": f"Bearer {TRMNL_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        TRMNL_WEBHOOK_URL,
        json=payload,
        headers=headers,
        timeout=30
    )

    if response.status_code not in [200, 201]:
        raise Exception(f"TRMNL webhook error: {response.status_code} - {response.text}")

    print("Successfully sent URL to TRMNL!")
    print(f"   Payload size: {len(str(payload))} bytes")
    print(f"   Image URL: {image_url}")
    return response.json()


def main():
    """Main execution"""
    if not all([ASTROLOGER_API_URL, TRMNL_API_KEY, PLUGIN_UUID, GITHUB_USERNAME, GITHUB_REPO]):
        print("Error: Missing required environment variables:")
        print(f"   ASTROLOGER_API_URL: {'set' if ASTROLOGER_API_URL else 'missing'}")
        print(f"   TRMNL_API_KEY: {'set' if TRMNL_API_KEY else 'missing'}")
        print(f"   PLUGIN_UUID: {'set' if PLUGIN_UUID else 'missing'}")
        print(f"   GITHUB_USERNAME: {'set' if GITHUB_USERNAME else 'missing'}")
        print(f"   GITHUB_REPO: {'set' if GITHUB_REPO else 'missing'}")
        sys.exit(1)

    try:
        # Fetch planetary positions
        positions = get_positions()

        # Render custom wheel + legend SVG
        svg_chart = render_chart_svg(positions)

        # Convert to e-ink optimized PNG (4-level grayscale)
        png_path = svg_to_png_grayscale(svg_chart)

        # Send to TRMNL
        result = send_to_trmnl()

        print(f"\nSUCCESS! Chart updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   File saved to: {png_path}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
