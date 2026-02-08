"""
Development chart renderer: Experimental layouts.

This is your sandbox for iterating on new chart designs.
Modify freely - production.py remains untouched.

The render() function receives the same inputs as production:
- positions: Dict of body positions from API
- config: Dict with 'location', 'bodies', 'display' keys

Output: SVG string (800x480)
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
    Experimental chart renderer.

    Currently: Copy of production layout.
    Modify this to try new designs!

    Ideas to try:
    - Different wheel/legend proportions
    - Aspect lines between planets
    - Alternative color schemes (for grayscale)
    - Different glyph sizes or fonts
    - House cusp indicators
    - Element/modality groupings
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
    outer_r = 155      # Smaller wheel to make room for outside labels
    inner_r = 130
    sign_glyph_r = 143
    planet_r = 185     # Labels outside wheel (beyond outer_r)
    max_planet_r = 230 # Maximum outward radius for labels
    tick_inner = outer_r
    tick_outer = outer_r + 10  # Ticks point outward toward labels

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
                        font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black'))

    # Draw tick marks on outer ring (pointing outward toward labels)
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

    # Place combined planet glyph + degree labels with collision avoidance
    planet_positions = []
    for body in bodies:
        if body in positions and body not in ['ascendant', 'medium_coeli']:
            pos = positions[body]
            planet_positions.append((body, pos['lon'], pos['deg']))

    planet_positions.sort(key=lambda x: x[1])
    placed = []

    def has_collision(angle, radius, placed_list):
        """Check if a label at (angle, radius) would overlap any placed label."""
        for placed_angle, placed_r in placed_list:
            angle_diff = abs(angle - placed_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff

            # On left/right sides (horizontal zones), labels spread horizontally
            # so we can allow closer angular spacing at the same radius
            is_horizontal = abs(math.sin(angle)) < 0.5  # within ~30° of horizontal
            placed_is_horizontal = abs(math.sin(placed_angle)) < 0.5

            if is_horizontal and placed_is_horizontal:
                # Both on sides - only collide if very close (< 3°)
                threshold = 0.05
            else:
                # Top/bottom or mixed - need more spacing
                threshold = 0.08

            if angle_diff < threshold and abs(radius - placed_r) < 16:
                return True
        return False

    for body, lon, deg in planet_positions:
        screen_angle = to_screen_angle(lon)
        current_r = planet_r

        # Keep moving outward until we find a clear spot
        while has_collision(screen_angle, current_r, placed) and current_r < max_planet_r:
            current_r += 22

        px = wheel_cx + current_r * math.cos(screen_angle)
        py = wheel_cy - current_r * math.sin(screen_angle)

        placed.append((screen_angle, current_r))

        # Adaptive layout: stack at top/bottom (where horizontal space is tight),
        # side-by-side on left/right (where there's more horizontal room)
        # sin(angle) > 0.7 means roughly within 45° of vertical (top or bottom)
        is_vertical_zone = abs(math.sin(screen_angle)) > 0.7

        glyph = BODY_GLYPHS[body]
        deg_text = f"{deg}°"
        font = 'Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif'

        if is_vertical_zone:
            # Stack: glyph on top, degree below
            dwg.add(dwg.text(glyph, insert=(px, py),
                            text_anchor='middle', font_size='15px',
                            font_family=font, fill='black'))
            dwg.add(dwg.text(deg_text, insert=(px, py + 12),
                            text_anchor='middle', font_size='12px',
                            font_family=font, fill='black'))
        else:
            # Side-by-side: glyph then degree (separate elements for consistent sizing)
            dwg.add(dwg.text(glyph, insert=(px - 6, py + 5),
                            text_anchor='middle', font_size='15px',
                            font_family=font, fill='black'))
            dwg.add(dwg.text(deg_text, insert=(px + 8, py + 5),
                            text_anchor='middle', font_size='12px',
                            font_family=font, fill='black'))

    # Draw ASC tick and label at left edge (9 o'clock position)
    if 'ascendant' in positions:
        asc_rad = math.radians(180)
        # Tick mark extending outward
        dwg.add(dwg.line(start=(wheel_cx - outer_r, wheel_cy),
                        end=(wheel_cx - outer_r - 12, wheel_cy),
                        stroke='black', stroke_width=2))
        asc_deg = positions['ascendant']['deg']
        # Label to the left of tick
        label_x = wheel_cx - outer_r - 35
        label_y = wheel_cy
        dwg.add(dwg.text('ASC', insert=(label_x, label_y - 2),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black',
                        font_weight='bold'))
        dwg.add(dwg.text(f"{asc_deg}°", insert=(label_x, label_y + 10),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

    # Draw MC tick and label outside wheel
    if 'medium_coeli' in positions:
        mc_rad = to_screen_angle(positions['medium_coeli']['lon'])
        mc_deg = positions['medium_coeli']['deg']
        # Tick mark extending outward
        tick_start_x = wheel_cx + outer_r * math.cos(mc_rad)
        tick_start_y = wheel_cy - outer_r * math.sin(mc_rad)
        tick_end_x = wheel_cx + (outer_r + 12) * math.cos(mc_rad)
        tick_end_y = wheel_cy - (outer_r + 12) * math.sin(mc_rad)
        dwg.add(dwg.line(start=(tick_start_x, tick_start_y), end=(tick_end_x, tick_end_y),
                        stroke='black', stroke_width=2))
        # Label beyond tick
        mc_label_r = outer_r + 30
        label_x = wheel_cx + mc_label_r * math.cos(mc_rad)
        label_y = wheel_cy - mc_label_r * math.sin(mc_rad)
        dwg.add(dwg.text('MC', insert=(label_x, label_y - 2),
                        text_anchor='middle', font_size='11px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black',
                        font_weight='bold'))
        dwg.add(dwg.text(f"{mc_deg}°", insert=(label_x, label_y + 10),
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
                    font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black',
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
                            font_size='20px', font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black', font_weight='bold'))

            dwg.add(dwg.text(sign_glyph, insert=(legend_x + 60, y),
                            font_size='20px', font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black'))

            dwg.add(dwg.text(deg_str, insert=(legend_x + 100, y),
                            font_size='18px', font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black'))

            if show_retrograde and pos.get('retrograde', False):
                dwg.add(dwg.text(RETROGRADE_GLYPH, insert=(legend_x + 168, y),
                                font_size='14px', font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                                fill='black'))

            if show_house_numbers and body not in ['ascendant', 'medium_coeli']:
                house_num = get_house_number(pos['sign'], asc_sign)
                dwg.add(dwg.text(ordinal(house_num), insert=(legend_x + 195, y),
                                font_size='16px', font_family='DejaVu Sans, Arial, sans-serif',
                                fill='black'))

            y += line_height

    # Timestamp with DEV indicator
    local_tz = ZoneInfo(location['timezone'])
    now_local = datetime.now(local_tz)
    date_str = now_local.strftime('%B %d %Y')
    time_str = now_local.strftime('%-I:%M %p').lower()
    timestamp = f"{date_str} {time_str}"
    dwg.add(dwg.text(f"[DEV] {location['name']} | {timestamp}", insert=(legend_x + 130, 460),
                    text_anchor='middle', font_size='14px',
                    font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill=DARK_GRAY))

    return dwg.tostring()
