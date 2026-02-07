#!/usr/bin/env python3
"""
TRMNL Astrology Current Chart Updater
Fetches current planetary positions for Philadelphia and sends to TRMNL
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

# Current chart request payload (Philadelphia)
CHART_PAYLOAD = {
    "subject": {
        "name": "Philadelphia Now",
        "year": None,  # Will be set dynamically
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
    
    # Get current time
    now = datetime.now()
    
    # Update payload with current time
    CHART_PAYLOAD["subject"]["year"] = now.year
    CHART_PAYLOAD["subject"]["month"] = now.month
    CHART_PAYLOAD["subject"]["day"] = now.day
    CHART_PAYLOAD["subject"]["hour"] = now.hour
    CHART_PAYLOAD["subject"]["minute"] = now.minute
    
    print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Call Astrologer API (using birth-chart endpoint for current positions)
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


def svg_to_png_base64(svg_content):
    """Convert SVG to PNG and encode as base64"""
    print("Converting SVG to PNG for e-ink display...")
    
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
    
    # Convert SVG to PNG at full size first
    png_data = cairosvg.svg2png(
        bytestring=svg_content.encode('utf-8'),
        output_width=800,
        output_height=480
    )
    
    # Open with PIL
    img = Image.open(io.BytesIO(png_data))
    
    # Convert to pure black and white (1-bit) for e-ink display
    img = img.convert('L')  # Convert to grayscale first
    img = img.point(lambda x: 0 if x < 128 else 255, '1')  # Convert to 1-bit B&W
    
    # Save with maximum compression
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    compressed_png = output.getvalue()
    
    # Encode as base64
    base64_png = base64.b64encode(compressed_png).decode('utf-8')
    
    print(f"PNG size: {len(compressed_png)} bytes, Base64 size: {len(base64_png)} bytes")
    
    return base64_png


def send_to_trmnl(image_base64):
    """Send image to TRMNL via webhook"""
    print("Sending to TRMNL...")
    
    payload = {
        "merge_variables": {
            "transit_chart": image_base64,
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
        # Step 1: Get current chart SVG
        svg_chart = get_current_chart()
        
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
