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

    # === LEFT SIDE: Zodiac Wheel (moderately compact) ===
    wheel_cx, wheel_cy = 195, 240  # Slightly left of center
    outer_r = 130                   # ~16% smaller wheel
    inner_r = 108
    sign_glyph_r = 120              # Centered in ring
    planet_r = 155                  # Labels start outside wheel
    max_planet_r = 215              # Maximum outward radius for labels
    tick_inner = outer_r
    tick_outer = outer_r + 10       # Ticks point outward toward labels

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

        dwg.add(dwg.text(SIGN_GLYPHS[i], insert=(gx, gy + 5),
                        text_anchor='middle', font_size='16px',
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

    # Kerykeion-inspired collision avoidance
    GROUP_THRESHOLD = 3.5    # degrees - planets within this form a group
    SPREAD_AMOUNT = 1.75     # degrees - how much to spread grouped planets

    # Two radii for alternating placement (creates natural vertical separation)
    inner_planet_r = planet_r
    outer_planet_r = planet_r + 20

    def angular_distance(lon1, lon2):
        """Shortest angular distance between two longitudes (signed)"""
        diff = (lon2 - lon1) % 360
        if diff > 180:
            diff -= 360
        return diff

    def abs_angular_distance(lon1, lon2):
        """Absolute angular distance between two longitudes"""
        return abs(angular_distance(lon1, lon2))

    def is_near_asc(screen_angle):
        """Check if angle is in the ASC zone (left side, within ~15° of horizontal)"""
        angle_from_pi = abs(screen_angle - math.pi)
        if angle_from_pi > math.pi:
            angle_from_pi = 2 * math.pi - angle_from_pi
        return angle_from_pi < 0.26  # ~15 degrees

    # Get MC longitude for collision avoidance
    mc_lon = positions.get('medium_coeli', {}).get('lon', None)

    def is_near_mc(screen_angle):
        """Check if angle is near MC (within ~15° of MC's screen angle)"""
        if mc_lon is None:
            return False
        mc_screen = to_screen_angle(mc_lon)
        angle_diff = abs(screen_angle - mc_screen)
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff
        return angle_diff < 0.26

    # === GROUPING ALGORITHM ===
    # Find groups of planets within GROUP_THRESHOLD of each other

    def find_groups(positions_list):
        """Identify groups of close planets and calculate adjusted positions"""
        if not positions_list:
            return {}

        adjustments = {}  # body -> adjusted_lon

        # Initialize with natural positions
        for body, lon, deg in positions_list:
            adjustments[body] = lon

        n = len(positions_list)
        if n < 2:
            return adjustments

        # Find groups by scanning sorted positions
        i = 0
        while i < n:
            group_start = i
            group = [positions_list[i]]

            # Extend group while next planet is within threshold
            while i + 1 < n:
                current_lon = positions_list[i][1]
                next_lon = positions_list[i + 1][1]
                if abs_angular_distance(current_lon, next_lon) < GROUP_THRESHOLD:
                    group.append(positions_list[i + 1])
                    i += 1
                else:
                    break

            # Apply symmetric spreading to group
            if len(group) == 2:
                # Two planets: spread symmetrically from midpoint
                body1, lon1, _ = group[0]
                body2, lon2, _ = group[1]
                midpoint = (lon1 + lon2) / 2
                adjustments[body1] = midpoint - SPREAD_AMOUNT
                adjustments[body2] = midpoint + SPREAD_AMOUNT

            elif len(group) >= 3:
                # 3+ planets: distribute evenly across the span + padding
                lons = [g[1] for g in group]
                span_start = min(lons) - SPREAD_AMOUNT
                span_end = max(lons) + SPREAD_AMOUNT
                total_span = span_end - span_start
                step = total_span / (len(group) - 1) if len(group) > 1 else 0

                for j, (body, lon, deg) in enumerate(group):
                    adjustments[body] = span_start + (j * step)

            i += 1

        return adjustments

    # Calculate adjusted positions for all planets
    adjusted_lons = find_groups(planet_positions)

    # === PLACEMENT LOOP ===
    # Track which radius tier each planet uses (alternating)
    planet_index = 0

    for body, lon, deg in planet_positions:
        adjusted_lon = adjusted_lons.get(body, lon)
        screen_angle = to_screen_angle(lon)
        display_angle = to_screen_angle(adjusted_lon)

        # Alternate between inner and outer radius for natural separation
        if planet_index % 2 == 0:
            current_r = inner_planet_r
        else:
            current_r = outer_planet_r

        y_offset = 0

        # Special handling for ASC zone - use vertical displacement instead
        if is_near_asc(display_angle):
            current_r = planet_r  # Reset to base radius
            # Shift based on zodiacal position relative to ASC
            if lon < asc_lon:
                y_offset = -22  # Above ASC
            else:
                y_offset = 22   # Below ASC

        # Special handling for MC zone - use vertical displacement
        elif is_near_mc(display_angle):
            current_r = planet_r - 15  # Slightly inward
            if mc_lon and lon < mc_lon:
                y_offset = -22  # Above MC
            else:
                y_offset = 22   # Below MC

        # Calculate final position
        px = wheel_cx + current_r * math.cos(display_angle)
        py = wheel_cy - current_r * math.sin(display_angle) + y_offset

        # Safety check: avoid collision with ASC label (always at left edge: x≈27, y=240)
        asc_label_x = wheel_cx - outer_r - 38
        asc_label_y = wheel_cy
        if abs(px - asc_label_x) < 40 and abs(py - asc_label_y) < 20:
            nudge = 22
            py += nudge if screen_angle > math.pi else -nudge

        planet_index += 1

        # Adaptive layout: stack at top/bottom (where horizontal space is tight),
        # side-by-side on left/right (where there's more horizontal room)
        # sin(angle) > 0.7 means roughly within 45° of vertical (top or bottom)
        # Use display_angle for consistency with actual placement
        is_vertical_zone = abs(math.sin(display_angle)) > 0.7

        glyph = BODY_GLYPHS[body]
        deg_text = f"{deg}°"
        font = 'Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif'

        if is_vertical_zone:
            # Stack: glyph on top, degree below
            dwg.add(dwg.text(glyph, insert=(px, py),
                            text_anchor='middle', font_size='20px',
                            font_family=font, fill='black'))
            dwg.add(dwg.text(deg_text, insert=(px, py + 14),
                            text_anchor='middle', font_size='16px',
                            font_family=font, fill='black'))
        else:
            # Side-by-side: glyph then degree (separate elements for consistent sizing)
            dwg.add(dwg.text(glyph, insert=(px - 9, py + 6),
                            text_anchor='middle', font_size='20px',
                            font_family=font, fill='black'))
            dwg.add(dwg.text(deg_text, insert=(px + 13, py + 6),
                            text_anchor='middle', font_size='16px',
                            font_family=font, fill='black'))

    # Draw ASC tick and label at left edge (9 o'clock position)
    # ASC is always horizontal (left side of wheel) - use side-by-side layout
    if 'ascendant' in positions:
        asc_rad = math.radians(180)
        # Tick mark extending outward
        dwg.add(dwg.line(start=(wheel_cx - outer_r, wheel_cy),
                        end=(wheel_cx - outer_r - 12, wheel_cy),
                        stroke='black', stroke_width=2))
        asc_deg = positions['ascendant']['deg']
        # Label to the left of tick - side-by-side layout
        label_x = wheel_cx - outer_r - 38
        label_y = wheel_cy + 5
        dwg.add(dwg.text('ASC', insert=(label_x - 12, label_y),
                        text_anchor='middle', font_size='14px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black',
                        font_weight='bold'))
        dwg.add(dwg.text(f"{asc_deg}°", insert=(label_x + 14, label_y),
                        text_anchor='middle', font_size='14px',
                        font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

    # Draw MC tick and label outside wheel
    # MC uses same vertical/horizontal zone logic as planets
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
        # Label beyond tick - use same zone logic as planets
        mc_label_r = outer_r + 30
        label_x = wheel_cx + mc_label_r * math.cos(mc_rad)
        label_y = wheel_cy - mc_label_r * math.sin(mc_rad)
        mc_is_vertical = abs(math.sin(mc_rad)) > 0.7

        if mc_is_vertical:
            # Stack: MC on top, degree below
            dwg.add(dwg.text('MC', insert=(label_x, label_y),
                            text_anchor='middle', font_size='14px',
                            font_family='DejaVu Sans, Arial, sans-serif', fill='black',
                            font_weight='bold'))
            dwg.add(dwg.text(f"{mc_deg}°", insert=(label_x, label_y + 14),
                            text_anchor='middle', font_size='14px',
                            font_family='DejaVu Sans, Arial, sans-serif', fill='black'))
        else:
            # Side-by-side: MC then degree
            dwg.add(dwg.text('MC', insert=(label_x - 10, label_y + 5),
                            text_anchor='middle', font_size='14px',
                            font_family='DejaVu Sans, Arial, sans-serif', fill='black',
                            font_weight='bold'))
            dwg.add(dwg.text(f"{mc_deg}°", insert=(label_x + 14, label_y + 5),
                            text_anchor='middle', font_size='14px',
                            font_family='DejaVu Sans, Arial, sans-serif', fill='black'))

    # === RIGHT SIDE: Legend Panel (larger fonts) ===
    legend_x = 435
    legend_y_start = 15
    line_height = 30

    asc_sign = positions.get('ascendant', {}).get('sign', 0)

    header_text = 'Planetary Positions'
    if show_moon_phase:
        moon_phase_idx = get_moon_phase(positions)
        if moon_phase_idx is not None:
            header_text = f'{MOON_PHASES[moon_phase_idx]} {header_text}'

    dwg.add(dwg.text(header_text, insert=(legend_x + 170, legend_y_start),
                    text_anchor='middle', font_size='22px',
                    font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill='black',
                    font_weight='bold'))

    dwg.add(dwg.line(start=(legend_x, legend_y_start + 12),
                    end=(legend_x + 340, legend_y_start + 12),
                    stroke='black', stroke_width=1))

    y = legend_y_start + 38
    for body in bodies:
        if body in positions:
            pos = positions[body]
            glyph = BODY_GLYPHS[body]
            sign_glyph = SIGN_GLYPHS[pos['sign']]
            deg_str = f"{pos['deg']:02d}\u00B0{pos['min']:02d}'"

            dwg.add(dwg.text(glyph, insert=(legend_x + 10, y),
                            font_size='26px', font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black', font_weight='bold'))

            dwg.add(dwg.text(sign_glyph, insert=(legend_x + 70, y),
                            font_size='26px', font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black'))

            dwg.add(dwg.text(deg_str, insert=(legend_x + 120, y),
                            font_size='24px', font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                            fill='black'))

            if show_retrograde and pos.get('retrograde', False):
                dwg.add(dwg.text(RETROGRADE_GLYPH, insert=(legend_x + 210, y),
                                font_size='18px', font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif',
                                fill='black'))

            if show_house_numbers and body not in ['ascendant', 'medium_coeli']:
                house_num = get_house_number(pos['sign'], asc_sign)
                dwg.add(dwg.text(ordinal(house_num), insert=(legend_x + 245, y),
                                font_size='20px', font_family='DejaVu Sans, Arial, sans-serif',
                                fill='black'))

            y += line_height

    # Timestamp with DEV indicator
    local_tz = ZoneInfo(location['timezone'])
    now_local = datetime.now(local_tz)
    date_str = now_local.strftime('%B %d %Y')
    time_str = now_local.strftime('%-I:%M %p').lower()
    timestamp = f"{date_str} {time_str}"
    dwg.add(dwg.text(f"[DEV] {location['name']} | {timestamp}", insert=(legend_x + 170, 468),
                    text_anchor='middle', font_size='14px',
                    font_family='Apple Symbols, Noto Sans Symbols 2, DejaVu Sans, sans-serif', fill=DARK_GRAY))

    return dwg.tostring()
