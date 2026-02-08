#!/usr/bin/env python3
"""
TRMNL Astrology Current Chart Updater
Fetches current planetary positions for Philadelphia and sends to TRMNL
Saves PNG to docs/ folder for GitHub Pages hosting
"""

import os
import sys
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


def get_current_chart():
    """Fetch current planetary positions chart from Astrologer API"""
    print("Fetching current planetary positions for Philadelphia...")
    
    now = datetime.now()
    
    CHART_PAYLOAD["subject"]["year"] = now.year
    CHART_PAYLOAD["subject"]["month"] = now.month
    CHART_PAYLOAD["subject"]["day"] = now.day
    CHART_PAYLOAD["subject"]["hour"] = now.hour
    CHART_PAYLOAD["subject"]["minute"] = now.minute
    
    print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    response = requests.post(
        f"{ASTROLOGER_API_URL}/api/v5/chart/birth-chart",
        json=CHART_PAYLOAD,
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code} - {response.text}")
    
    data = response.json()
    
    if data.get("status") != "OK":
        raise Exception(f"Chart generation failed: {data}")
    
    return data["chart"]


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
    print(f"✅ PNG saved to {output_path} ({file_size} bytes)")
    
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
    
    print("✅ Successfully sent URL to TRMNL!")
    print(f"   Payload size: {len(str(payload))} bytes")
    print(f"   Image URL: {image_url}")
    return response.json()


def main():
    """Main execution"""
    if not all([ASTROLOGER_API_URL, TRMNL_API_KEY, PLUGIN_UUID, GITHUB_USERNAME, GITHUB_REPO]):
        print("❌ Error: Missing required environment variables:")
        print(f"   ASTROLOGER_API_URL: {'✓' if ASTROLOGER_API_URL else '✗'}")
        print(f"   TRMNL_API_KEY: {'✓' if TRMNL_API_KEY else '✗'}")
        print(f"   PLUGIN_UUID: {'✓' if PLUGIN_UUID else '✗'}")
        print(f"   GITHUB_USERNAME: {'✓' if GITHUB_USERNAME else '✗'}")
        print(f"   GITHUB_REPO: {'✓' if GITHUB_REPO else '✗'}")
        sys.exit(1)
    
    try:
        svg_chart = get_current_chart()
        png_path = svg_to_png_bw(svg_chart)
        result = send_to_trmnl()
        
        print(f"\n✅ SUCCESS! Chart updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   File saved to: {png_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
