#!/usr/bin/env python3
"""
TRMNL Astrology Current Chart Updater
Fetches current planetary positions for Philadelphia and renders a custom
wheel + legend chart optimized for e-ink display.
"""

import os
import sys
import math
import requests
from datetime import datetime

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

# Current chart request payload (Philadelphia)
CHART_PAYLOAD = {
    "subject": {
        "name": "Philadelphia Now",
        "year": None,
        "month": None,
        "day": None,
        "hour": None,
        "minute": None,
        "city": "Philadelphia",
        "nation": "US",
        "longitude": -75.1652,
        "latitude": 39.9526,
        "timezone": "America/New_York"
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

# Bodies to display (in order for legend)
# API field names -> display names
BODIES = [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter',
    'saturn', 'uranus', 'neptune', 'pluto', 'mean_north_lunar_node',
    'mean_south_lunar_node', 'ascendant', 'medium_coeli'
]


def get_positions():
    """Fetch position data from Astrologer API /api/v5/chart-data/birth-chart endpoint"""
    print("Fetching current planetary positions for Philadelphia...")

    now = datetime.now()

    CHART_PAYLOAD["subject"]["year"] = now.year
    CHART_PAYLOAD["subject"]["month"] = now.month
    CHART_PAYLOAD["subject"]["day"] = now.day
    CHART_PAYLOAD["subject"]["hour"] = now.hour
    CHART_PAYLOAD["subject"]["minute"] = now.minute

    print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

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


def render_chart_svg(positions):
    """Generate 800x480 wheel + legend SVG optimized for e-ink"""
    import svgwrite

    dwg = svgwrite.Drawing(size=('800px', '480px'))

    # White background
    dwg.add(dwg.rect(insert=(0, 0), size=('800px', '480px'), fill='white'))

    # === LEFT SIDE: Zodiac Wheel ===
    wheel_cx, wheel_cy = 240, 240
    outer_r = 200
    inner_r = 140
    glyph_r = 170  # Radius for sign glyphs
    planet_r = 100  # Radius for planet glyphs

    # Outer circle
    dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=outer_r,
                       stroke='black', stroke_width=3, fill='none'))

    # Inner circle
    dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=inner_r,
                       stroke='black', stroke_width=2, fill='none'))

    # Draw 12 sign divisions and glyphs
    for i in range(12):
        # Line from inner to outer circle at sign boundaries
        # Aries starts at 0 degrees (right side, 3 o'clock position)
        # Zodiac goes counter-clockwise
        angle_deg = i * 30
        angle_rad = math.radians(angle_deg)

        # Calculate line endpoints (rotate so 0 deg Aries is at right)
        x1 = wheel_cx + inner_r * math.cos(angle_rad)
        y1 = wheel_cy - inner_r * math.sin(angle_rad)
        x2 = wheel_cx + outer_r * math.cos(angle_rad)
        y2 = wheel_cy - outer_r * math.sin(angle_rad)

        dwg.add(dwg.line(start=(x1, y1), end=(x2, y2),
                        stroke='black', stroke_width=1))

        # Sign glyph in middle of each sign sector
        mid_angle_deg = i * 30 + 15
        mid_angle_rad = math.radians(mid_angle_deg)
        gx = wheel_cx + glyph_r * math.cos(mid_angle_rad)
        gy = wheel_cy - glyph_r * math.sin(mid_angle_rad)

        dwg.add(dwg.text(SIGN_GLYPHS[i], insert=(gx, gy + 8),
                        text_anchor='middle', font_size='24px',
                        font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif', fill='black'))

    # Place planet glyphs on wheel at their longitudes
    # Collect positions to handle collisions
    planet_positions = []
    for body in BODIES:
        if body in positions and body not in ['ascendant', 'medium_coeli']:
            lon = positions[body]['lon']
            planet_positions.append((body, lon))

    # Simple collision avoidance: offset planets that are too close
    planet_positions.sort(key=lambda x: x[1])
    placed = []

    for body, lon in planet_positions:
        # Convert longitude to angle (0 deg Aries = right side, counter-clockwise)
        angle_rad = math.radians(lon)

        # Check for collisions with already placed planets
        adjusted_angle = angle_rad
        for _, placed_angle in placed:
            angle_diff = abs(adjusted_angle - placed_angle)
            if angle_diff < 0.2:  # Too close (~11 degrees)
                adjusted_angle += 0.15

        px = wheel_cx + planet_r * math.cos(adjusted_angle)
        py = wheel_cy - planet_r * math.sin(adjusted_angle)

        placed.append((body, adjusted_angle))

        dwg.add(dwg.text(BODY_GLYPHS[body], insert=(px, py + 6),
                        text_anchor='middle', font_size='20px',
                        font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif', fill='black',
                        font_weight='bold'))

    # Draw ASC line (thicker, extends from center)
    if 'ascendant' in positions:
        asc_lon = positions['ascendant']['lon']
        asc_rad = math.radians(asc_lon)
        ax = wheel_cx + outer_r * math.cos(asc_rad)
        ay = wheel_cy - outer_r * math.sin(asc_rad)
        dwg.add(dwg.line(start=(wheel_cx, wheel_cy), end=(ax, ay),
                        stroke='black', stroke_width=3))
        # ASC label outside
        label_x = wheel_cx + (outer_r + 15) * math.cos(asc_rad)
        label_y = wheel_cy - (outer_r + 15) * math.sin(asc_rad)
        dwg.add(dwg.text('ASC', insert=(label_x, label_y + 4),
                        text_anchor='middle', font_size='12px',
                        font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif', fill='black',
                        font_weight='bold'))

    # Draw MC line
    if 'medium_coeli' in positions:
        mc_lon = positions['medium_coeli']['lon']
        mc_rad = math.radians(mc_lon)
        mx = wheel_cx + outer_r * math.cos(mc_rad)
        my = wheel_cy - outer_r * math.sin(mc_rad)
        dwg.add(dwg.line(start=(wheel_cx, wheel_cy), end=(mx, my),
                        stroke='black', stroke_width=2, stroke_dasharray='5,3'))
        label_x = wheel_cx + (outer_r + 15) * math.cos(mc_rad)
        label_y = wheel_cy - (outer_r + 15) * math.sin(mc_rad)
        dwg.add(dwg.text('MC', insert=(label_x, label_y + 4),
                        text_anchor='middle', font_size='12px',
                        font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif', fill='black',
                        font_weight='bold'))

    # === RIGHT SIDE: Legend Panel ===
    legend_x = 500
    legend_y_start = 30
    line_height = 30

    # Header
    dwg.add(dwg.text('Current Transits', insert=(legend_x + 100, legend_y_start),
                    text_anchor='middle', font_size='18px',
                    font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif', fill='black',
                    font_weight='bold'))

    # Divider line
    dwg.add(dwg.line(start=(legend_x, legend_y_start + 10),
                    end=(legend_x + 200, legend_y_start + 10),
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
                            font_size='22px', font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif',
                            fill='black', font_weight='bold'))

            # Sign glyph
            dwg.add(dwg.text(sign_glyph, insert=(legend_x + 60, y),
                            font_size='22px', font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif',
                            fill='black'))

            # Degrees
            dwg.add(dwg.text(deg_str, insert=(legend_x + 100, y),
                            font_size='20px', font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif',
                            fill='black'))

            y += line_height

    # Timestamp at bottom
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    dwg.add(dwg.text(f'Philadelphia | {timestamp}', insert=(legend_x + 100, 460),
                    text_anchor='middle', font_size='12px',
                    font_family='Symbola, Noto Sans Symbols2, Noto Sans Symbols, Arial, sans-serif', fill='black'))

    return dwg.tostring()


def svg_to_png_bw(svg_content, output_path=OUTPUT_PATH):
    """Convert SVG to black & white PNG for e-ink display"""
    print("Converting SVG to B&W PNG for e-ink...")

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
    img = img.point(lambda x: 0 if x < 128 else 255, '1')

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

        # Convert to e-ink optimized PNG
        png_path = svg_to_png_bw(svg_chart)

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
