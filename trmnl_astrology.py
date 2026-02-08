#!/usr/bin/env python3
"""
TRMNL Astrology Current Chart Updater
Fetches current planetary positions and renders chart variants
optimized for e-ink display.

Generates two charts:
- docs/chart.png: Production (sent to TRMNL)
- docs/dev-chart.png: Development (for iterating on new designs)
"""

import os
import sys
import requests
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo

from renderers import render_production, render_dev

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

# Output paths
OUTPUT_PATH_PROD = "docs/chart.png"
OUTPUT_PATH_DEV = "docs/dev-chart.png"

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

# Bodies to display (from config)
BODIES = CONFIG.get('bodies', [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter',
    'saturn', 'uranus', 'neptune', 'pluto', 'mean_north_lunar_node',
    'mean_south_lunar_node', 'ascendant', 'medium_coeli'
])


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


def svg_to_png_grayscale(svg_content, output_path):
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

        # Render both chart variants
        print("\n--- Production Chart ---")
        svg_prod = render_production(positions, CONFIG)
        svg_to_png_grayscale(svg_prod, OUTPUT_PATH_PROD)

        print("\n--- Development Chart ---")
        svg_dev = render_dev(positions, CONFIG)
        svg_to_png_grayscale(svg_dev, OUTPUT_PATH_DEV)

        # Send production chart to TRMNL
        result = send_to_trmnl()

        print(f"\nSUCCESS! Charts updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Production: {OUTPUT_PATH_PROD}")
        print(f"   Development: {OUTPUT_PATH_DEV}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
