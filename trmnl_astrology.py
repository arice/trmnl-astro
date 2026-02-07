#!/usr/bin/env python3
"""
TRMNL Astrology Transit Chart Updater
Fetches hourly transit charts from self-hosted Astrologer API and sends to TRMNL
"""

import os
import sys
import base64
import requests
from datetime import datetime
from io import BytesIO

# Configuration from environment variables
ASTROLOGER_API_URL = os.environ.get('ASTROLOGER_API_URL')  # e.g., http://your-droplet-ip:8000
TRMNL_API_KEY = os.environ.get('TRMNL_API_KEY')
PLUGIN_UUID = os.environ.get('PLUGIN_UUID')

# TRMNL webhook endpoint
TRMNL_WEBHOOK_URL = f"https://usetrmnl.com/api/custom_plugins/{PLUGIN_UUID}"

# Transit chart request payload
TRANSIT_PAYLOAD = {
    "subject": {
        "name": "Current Transits",
        "year": None,  # Will be set dynamically
        "month": None,
        "day": None,
        "hour": None,
        "minute": None,
        "city": "London",
        "nation": "GB",
        "longitude": -0.1278,
        "latitude": 51.5074,
        "timezone": "Europe/London"
    }
}


def get_current_transit_chart():
    """Fetch current transit chart from Astrologer API"""
    print("Fetching current transit chart...")
    
    # Get current time
    now = datetime.now()
    
    # Update payload with current time
    TRANSIT_PAYLOAD["subject"]["year"] = now.year
    TRANSIT_PAYLOAD["subject"]["month"] = now.month
    TRANSIT_PAYLOAD["subject"]["day"] = now.day
    TRANSIT_PAYLOAD["subject"]["hour"] = now.hour
    TRANSIT_PAYLOAD["subject"]["minute"] = now.minute
    
    # Call Astrologer API
    response = requests.post(
        f"{ASTROLOGER_API_URL}/api/v5/chart/transit",
        json=TRANSIT_PAYLOAD,
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code} - {response.text}")
    
    data = response.json()
    
    if data.get("status") != "OK":
        raise Exception(f"Chart generation failed: {data}")
    
    return data["chart"]


def svg_to_png_base64(svg_content):
    """Convert SVG to PNG and encode as base64"""
    print("Converting SVG to PNG...")
    
    try:
        import cairosvg
    except ImportError:
        print("Installing cairosvg...")
        os.system(f"{sys.executable} -m pip install cairosvg")
        import cairosvg
    
    # Convert SVG to PNG (800x480 for TRMNL e-ink display)
    png_data = cairosvg.svg2png(
        bytestring=svg_content.encode('utf-8'),
        output_width=800,
        output_height=480
    )
    
    # Encode as base64
    base64_png = base64.b64encode(png_data).decode('utf-8')
    
    return base64_png


def send_to_trmnl(image_base64):
    """Send image to TRMNL via webhook"""
    print("Sending to TRMNL...")
    
    payload = {
        "merge_variables": {
            "transit_chart": image_base64,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M UTC")
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
    
    print("✅ Successfully sent to TRMNL!")
    return response.json()


def main():
    """Main execution"""
    # Validate environment variables
    if not all([ASTROLOGER_API_URL, TRMNL_API_KEY, PLUGIN_UUID]):
        print("❌ Error: Missing required environment variables:")
        print(f"   ASTROLOGER_API_URL: {'✓' if ASTROLOGER_API_URL else '✗'}")
        print(f"   TRMNL_API_KEY: {'✓' if TRMNL_API_KEY else '✗'}")
        print(f"   PLUGIN_UUID: {'✓' if PLUGIN_UUID else '✗'}")
        sys.exit(1)
    
    try:
        # Step 1: Get transit chart SVG
        svg_chart = get_current_transit_chart()
        
        # Step 2: Convert to PNG and encode
        png_base64 = svg_to_png_base64(svg_chart)
        
        # Step 3: Send to TRMNL
        result = send_to_trmnl(png_base64)
        
        print(f"✅ Success! Chart updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
