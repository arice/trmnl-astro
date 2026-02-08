#!/usr/bin/env python3
"""
Local test script for chart rendering.
Run: pip install svgwrite cairosvg pillow pyyaml && python test_chart.py

Generates both production and dev charts using mock data.
"""

import yaml
import cairosvg
from PIL import Image
import io

from renderers import render_production, render_dev

# Load config
with open('config.yaml', 'r') as f:
    CONFIG = yaml.safe_load(f)

# Mock position data (similar to real positions)
MOCK_POSITIONS = {
    'sun': {'lon': 319.5, 'sign': 10, 'deg': 19, 'min': 31, 'retrograde': False},
    'moon': {'lon': 216.1, 'sign': 7, 'deg': 6, 'min': 4, 'retrograde': False},
    'mercury': {'lon': 332.4, 'sign': 10, 'deg': 2, 'min': 21, 'retrograde': True},
    'venus': {'lon': 327.3, 'sign': 10, 'deg': 27, 'min': 20, 'retrograde': False},
    'mars': {'lon': 312.5, 'sign': 10, 'deg': 12, 'min': 27, 'retrograde': False},
    'jupiter': {'lon': 136.6, 'sign': 4, 'deg': 16, 'min': 36, 'retrograde': True},
    'saturn': {'lon': 359.4, 'sign': 11, 'deg': 29, 'min': 23, 'retrograde': False},
    'uranus': {'lon': 57.5, 'sign': 1, 'deg': 27, 'min': 28, 'retrograde': True},
    'neptune': {'lon': 0.35, 'sign': 11, 'deg': 0, 'min': 21, 'retrograde': False},
    'pluto': {'lon': 303.9, 'sign': 10, 'deg': 3, 'min': 55, 'retrograde': False},
    'mean_north_lunar_node': {'lon': 355.1, 'sign': 11, 'deg': 25, 'min': 6, 'retrograde': False},
    'ascendant': {'lon': 245.0, 'sign': 8, 'deg': 5, 'min': 2, 'retrograde': False},
    'medium_coeli': {'lon': 171.3, 'sign': 5, 'deg': 21, 'min': 17, 'retrograde': False},
}


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
    print("Rendering test charts with mock data...\n")

    print("Production renderer:")
    svg_prod = render_production(MOCK_POSITIONS, CONFIG)
    svg_to_png(svg_prod, "./test_chart_prod.png")

    print("\nDev renderer:")
    svg_dev = render_dev(MOCK_POSITIONS, CONFIG)
    svg_to_png(svg_dev, "./test_chart_dev.png")

    print("\nDone! Open test_chart_prod.png and test_chart_dev.png to compare.")
