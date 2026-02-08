"""
Production chart renderer: Wheel + Legend layout.
This is the stable version used for TRMNL display.
"""

import math
from datetime import datetime
from zoneinfo import ZoneInfo
import svgwrite

from .base import (
    BODY_GLYPHS, SIGN_GLYPHS, MOON_PHASES, RETROGRADE_GLYPH, DARK_GRAY,
    get_moon_phase, get_house_number, ordinal
)


def render(positions, config):
    """
    Generate 800x480 wheel + legend SVG optimized for e-ink.

    Args:
        positions: Dict of body positions from API
        config: Dict with 'location', 'bodies', 'display' keys

    Returns:
        SVG string
    """
    location = config['location']
    bodies = config.get('bodies', list(BODY_GLYPHS.keys()))
    display = config.get('display', {})
    show_retrograde = display.get('show_retrograde', True)
    show_moon_phase = display.get('show_moon_phase', True)
    show_house_numbers = display.get('show_house_numbers', True)

    dwg = svgwrite.Drawing(size=('800px', '480px'))

    # White background
    dwg.add(dwg.rect(insert=(0, 0), size=('800px', '480px'), fill='white'))

    # === LEFT SIDE: Zodiac Wheel ===
    wheel_cx, wheel_cy = 220, 240
    outer_r = 175
    inner_r = 150
    sign_glyph_r = 163
    planet_r = 125
    degree_r = 195
    degree_r_min = 180
    degree_r_max = 210
    tick_outer = inner_r
    tick_inner = inner_r - 9

    # Calculate rotation so Ascendant is at 9 o'clock
    asc_lon = positions.get('ascendant', {}).get('lon', 0)
    rotation_offset = 180 - asc_lon

    def to_screen_angle(zodiac_lon):
        return math.radians(zodiac_lon + rotation_offset)

    # Outer circle
    dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=outer_r,
                       stroke='black', stroke_width=2, fill='none'))

    # Inner circle
    dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=inner_r,
                       stroke='black', stroke_width=2, fill='none'))

    # Draw 12 sign divisions and glyphs
    for i in range(12):
        angle_rad = to_screen_angle(i * 30)
        x1 = wheel_cx
        y1 = wheel_cy
        x2 = wheel_cx + outer_r * math.cos(angle_rad)
        y2 = wheel_cy - outer_r * math.sin(angle_rad)

        dwg.add(dwg.line(start=(x1, y1), end=(x2, y2),
                        stroke='black', stroke_width=1))

        mid_angle_rad = to_screen_angle(i * 30 + 15)
        gx = wheel_cx + sign_glyph_r * math.cos(mid_angle_rad)
        gy = wheel_cy - sign_glyph_r * math.sin(mid_angle_rad)

        dwg.add(dwg.text(SIGN_GLYPHS[i], insert=(gx, gy + 6),
                        text_anchor='middle', font_size='18px',
                        font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black'))

    # Draw tick marks
    for body in bodies:
        if body in positions and body not in ['ascendant', 'medium_coeli']:
            pos = positions[body]
            lon = pos['lon']
            angle = to_screen_angle(lon)

            t1x = wheel_cx + tick_inner * math.cos(angle)
            t1y = wheel_cy - tick_inner * math.sin(angle)
            t2x = wheel_cx + tick_outer * math.cos(angle)
            t2y = wheel_cy - tick_outer * math.sin(angle)
            dwg.add(dwg.line(start=(t1x, t1y), end=(t2x, t2y),
                            stroke=DARK_GRAY, stroke_width=2))

    # Draw degree labels with collision avoidance
    degree_labels = []
    for body in bodies:
        if body in positions and body not in ['ascendant', 'medium_coeli']:
            pos = positions[body]
            degree_labels.append((pos['lon'], pos['deg']))

    degree_labels.sort(key=lambda x: x[0])
    placed_degrees = []

    for lon, deg in degree_labels:
        angle = to_screen_angle(lon)
        current_r = degree_r

        for placed_angle, placed_r in placed_degrees:
            angle_diff = abs(angle - placed_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            if angle_diff < 0.14 and abs(current_r - placed_r) < 12:
                test_x = wheel_cx + (current_r + 14) * math.cos(angle)
                test_y = wheel_cy - (current_r + 14) * math.sin(angle)
                if test_x < 15 or test_x > 785 or test_y < 15 or test_y > 465:
                    current_r = max(degree_r_min, current_r - 14)
                else:
                    current_r = min(degree_r_max, current_r + 14)

        deg_x = wheel_cx + current_r * math.cos(angle)
        deg_y = wheel_cy - current_r * math.sin(angle)
        dwg.add(dwg.text(f"{deg}°", insert=(deg_x, deg_y + 4),
                        text_anchor='middle', font_size='12px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

        placed_degrees.append((angle, current_r))

    # Place planet glyphs with collision avoidance
    planet_positions = []
    for body in bodies:
        if body in positions and body not in ['ascendant', 'medium_coeli']:
            planet_positions.append((body, positions[body]['lon']))

    planet_positions.sort(key=lambda x: x[1])
    placed = []

    for body, lon in planet_positions:
        screen_angle = to_screen_angle(lon)
        current_r = planet_r

        for placed_angle, placed_r in placed:
            angle_diff = abs(screen_angle - placed_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            if angle_diff < 0.18 and abs(current_r - placed_r) < 20:
                current_r -= 22

        px = wheel_cx + current_r * math.cos(screen_angle)
        py = wheel_cy - current_r * math.sin(screen_angle)

        placed.append((screen_angle, current_r))

        dwg.add(dwg.text(BODY_GLYPHS[body], insert=(px, py + 6),
                        text_anchor='middle', font_size='20px',
                        font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black',
                        font_weight='bold'))

    # Draw ASC tick on outer ring
    if 'ascendant' in positions:
        asc_rad = math.radians(180)
        tick_start_x = wheel_cx + outer_r * math.cos(asc_rad)
        tick_start_y = wheel_cy - outer_r * math.sin(asc_rad)
        tick_end_x = wheel_cx + (outer_r + 10) * math.cos(asc_rad)
        tick_end_y = wheel_cy - (outer_r + 10) * math.sin(asc_rad)
        dwg.add(dwg.line(start=(tick_start_x, tick_start_y), end=(tick_end_x, tick_end_y),
                        stroke='black', stroke_width=2))
        label_x = wheel_cx + (degree_r + 8) * math.cos(asc_rad)
        label_y = wheel_cy - (degree_r + 8) * math.sin(asc_rad)
        dwg.add(dwg.text('ASC', insert=(label_x, label_y + 4),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black',
                        font_weight='bold'))
        asc_deg = positions['ascendant']['deg']
        dwg.add(dwg.text(f"{asc_deg}°", insert=(label_x, label_y + 16),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

    # Draw MC tick on outer ring
    if 'medium_coeli' in positions:
        mc_rad = to_screen_angle(positions['medium_coeli']['lon'])
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
        mc_deg = positions['medium_coeli']['deg']
        dwg.add(dwg.text(f"{mc_deg}°", insert=(label_x, label_y + 16),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

    # === RIGHT SIDE: Legend Panel ===
    legend_x = 470
    legend_y_start = 25
    line_height = 30

    asc_sign = positions.get('ascendant', {}).get('sign', 0)

    header_text = 'Planetary Positions'
    if show_moon_phase:
        moon_phase_idx = get_moon_phase(positions)
        if moon_phase_idx is not None:
            header_text = f'{MOON_PHASES[moon_phase_idx]} {header_text}'

    dwg.add(dwg.text(header_text, insert=(legend_x + 130, legend_y_start),
                    text_anchor='middle', font_size='18px',
                    font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black',
                    font_weight='bold'))

    dwg.add(dwg.line(start=(legend_x, legend_y_start + 10),
                    end=(legend_x + 260, legend_y_start + 10),
                    stroke='black', stroke_width=1))

    y = legend_y_start + 40
    for body in bodies:
        if body in positions:
            pos = positions[body]
            glyph = BODY_GLYPHS[body]
            sign_glyph = SIGN_GLYPHS[pos['sign']]
            deg_str = f"{pos['deg']:02d}\u00B0{pos['min']:02d}'"

            dwg.add(dwg.text(glyph, insert=(legend_x + 10, y),
                            font_size='20px', font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black', font_weight='bold'))

            dwg.add(dwg.text(sign_glyph, insert=(legend_x + 60, y),
                            font_size='20px', font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black'))

            dwg.add(dwg.text(deg_str, insert=(legend_x + 100, y),
                            font_size='18px', font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black'))

            if show_retrograde and pos.get('retrograde', False):
                dwg.add(dwg.text(RETROGRADE_GLYPH, insert=(legend_x + 168, y),
                                font_size='14px', font_family='DejaVu Sans, Arial, sans-serif',
                                fill='black', font_weight='bold'))

            if show_house_numbers and body not in ['ascendant', 'medium_coeli']:
                house_num = get_house_number(pos['sign'], asc_sign)
                dwg.add(dwg.text(ordinal(house_num), insert=(legend_x + 195, y),
                                font_size='16px', font_family='DejaVu Sans, Arial, sans-serif',
                                fill='black'))

            y += line_height

    # Timestamp
    local_tz = ZoneInfo(location['timezone'])
    now_local = datetime.now(local_tz)
    date_str = now_local.strftime('%B %d %Y')
    time_str = now_local.strftime('%-I:%M %p').lower()
    timestamp = f"{date_str} {time_str}"
    dwg.add(dwg.text(f"{location['name']} | {timestamp}", insert=(legend_x + 130, 460),
                    text_anchor='middle', font_size='14px',
                    font_family='Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill=DARK_GRAY))

    return dwg.tostring()
