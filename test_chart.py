#!/usr/bin/env python3
"""
Local test script for chart rendering.
Run: pip install svgwrite cairosvg pillow && python test_chart.py
"""

# Import the main module functions
from trmnl_astrology import render_chart_svg, svg_to_png_bw

# Mock position data (similar to real positions)
MOCK_POSITIONS = {
    'sun': {'lon': 319.5, 'sign': 10, 'deg': 19, 'min': 31},
    'moon': {'lon': 216.1, 'sign': 7, 'deg': 6, 'min': 4},
    'mercury': {'lon': 332.4, 'sign': 10, 'deg': 2, 'min': 21},
    'venus': {'lon': 327.3, 'sign': 10, 'deg': 27, 'min': 20},
    'mars': {'lon': 312.5, 'sign': 10, 'deg': 12, 'min': 27},
    'jupiter': {'lon': 136.6, 'sign': 4, 'deg': 16, 'min': 36},
    'saturn': {'lon': 359.4, 'sign': 11, 'deg': 29, 'min': 23},
    'uranus': {'lon': 57.5, 'sign': 1, 'deg': 27, 'min': 28},
    'neptune': {'lon': 0.35, 'sign': 11, 'deg': 0, 'min': 21},
    'pluto': {'lon': 303.9, 'sign': 10, 'deg': 3, 'min': 55},
    'mean_north_lunar_node': {'lon': 355.1, 'sign': 11, 'deg': 25, 'min': 6},
    'mean_south_lunar_node': {'lon': 175.1, 'sign': 5, 'deg': 25, 'min': 6},
    'ascendant': {'lon': 245.0, 'sign': 8, 'deg': 5, 'min': 2},
    'medium_coeli': {'lon': 171.3, 'sign': 5, 'deg': 21, 'min': 17},
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
    img = img.point(lambda x: 0 if x < 128 else 255, '1')
    img.save(output_path, format='PNG', optimize=True)

    print(f"\nDone! Open {output_path} to see the result.")
