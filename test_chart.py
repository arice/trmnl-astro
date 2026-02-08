#!/usr/bin/env python3
"""
Local test script for chart rendering.
Run: pip install svgwrite cairosvg pillow pyyaml && python test_chart.py
"""

# Import the main module functions
from trmnl_astrology import render_chart_svg, svg_to_png_grayscale

# Mock position data (similar to real positions)
# Includes retrograde flags for testing (Jupiter, Saturn, Uranus, Neptune, Pluto can be retrograde)
MOCK_POSITIONS = {
    'sun': {'lon': 319.5, 'sign': 10, 'deg': 19, 'min': 31, 'retrograde': False},
    'moon': {'lon': 216.1, 'sign': 7, 'deg': 6, 'min': 4, 'retrograde': False},
    'mercury': {'lon': 332.4, 'sign': 10, 'deg': 2, 'min': 21, 'retrograde': True},  # Rx for testing
    'venus': {'lon': 327.3, 'sign': 10, 'deg': 27, 'min': 20, 'retrograde': False},
    'mars': {'lon': 312.5, 'sign': 10, 'deg': 12, 'min': 27, 'retrograde': False},
    'jupiter': {'lon': 136.6, 'sign': 4, 'deg': 16, 'min': 36, 'retrograde': True},  # Rx for testing
    'saturn': {'lon': 359.4, 'sign': 11, 'deg': 29, 'min': 23, 'retrograde': False},
    'uranus': {'lon': 57.5, 'sign': 1, 'deg': 27, 'min': 28, 'retrograde': True},   # Rx for testing
    'neptune': {'lon': 0.35, 'sign': 11, 'deg': 0, 'min': 21, 'retrograde': False},
    'pluto': {'lon': 303.9, 'sign': 10, 'deg': 3, 'min': 55, 'retrograde': False},
    'mean_north_lunar_node': {'lon': 355.1, 'sign': 11, 'deg': 25, 'min': 6, 'retrograde': False},
    'ascendant': {'lon': 245.0, 'sign': 8, 'deg': 5, 'min': 2, 'retrograde': False},
    'medium_coeli': {'lon': 171.3, 'sign': 5, 'deg': 21, 'min': 17, 'retrograde': False},
}

if __name__ == "__main__":
    print("Rendering test chart...")
    svg = render_chart_svg(MOCK_POSITIONS)

    print("Converting to PNG...")
    output_path = "./test_chart.png"

    # Save SVG directly to PNG (bypass the makedirs issue)
    import cairosvg
    from PIL import Image
    import io

    png_data = cairosvg.svg2png(
        bytestring=svg.encode('utf-8'),
        output_width=800,
        output_height=480
    )
    img = Image.open(io.BytesIO(png_data))
    img = img.convert('L')
    # 4-level quantization for 2-bit grayscale: 0, 85, 170, 255
    img = img.point(lambda x: [0, 85, 170, 255][min(x // 64, 3)], 'L')
    img.save(output_path, format='PNG', optimize=True)

    print(f"\nDone! Open {output_path} to see the result.")
