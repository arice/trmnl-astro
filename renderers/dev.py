"""
Development chart renderer: Experimental layouts.

This is your sandbox for iterating on new chart designs.
Modify freely - production.py remains untouched.

The render() function receives the same inputs as production:
- positions: Dict of body positions from API
- config: Dict with 'location', 'bodies', 'display' keys

Output: SVG string (800x480)

Current design: big glyphs held at their true zodiac angle.

The governing idea is that a glyph's *angle* is the information. Two planets a
degree apart cannot both be drawn at full size on their own ray, so something has
to give, and there are only two directions to give in:

    sideways  - slide the glyph around the ring. Cheap on space, but it moves the
                glyph off its true angle, which is the one thing the wheel is for.
    outward   - push the glyph further out along the *same* ray. Costs radial
                depth, but the angle stays exactly right.

So placement searches outward first and only slides sideways when it runs out of
depth. Every glyph sits as near the rim as it can, and a leader line runs from a
tick at the planet's real position out to it - usually dead straight, because the
angle usually did not have to move at all.

The legend carries sign, arcminutes, retrograde and house, so the wheel does not
repeat any of it.
"""

import math
from datetime import datetime
from zoneinfo import ZoneInfo
import svgwrite

from .base import (
    ASTRO_BODY_GLYPHS as BODY_GLYPHS,
    ASTRO_SIGN_GLYPHS as SIGN_GLYPHS,
    ASTRO_RETROGRADE_GLYPH as RETROGRADE_GLYPH,
    MOON_PHASES, DARK_GRAY,
    get_moon_phase, get_house_number, ordinal
)

# GLYPH_FONT draws astrological symbols and nothing else; TEXT_FONT draws every
# letter, digit and degree mark. Keeping them apart matters because dedicated
# astrology faces (Astronomicon and kin) map their symbols onto ASCII letters --
# point one of those at a timestamp and the date turns into planets.
GLYPH_FONT = 'Astronomicon'
TEXT_FONT = 'DejaVu Sans, Arial, sans-serif'

# Panel the wheel and its labels live in; the legend owns everything to the right.
PANEL = (4, 4, 430, 476)        # left, top, right, bottom


def _box_exit(box, ux, uy):
    """Distance from a label's anchor to its own box edge along (ux, uy)."""
    l, r, u, d = box
    t = 1e9
    if ux > 1e-9:
        t = min(t, r / ux)
    elif ux < -1e-9:
        t = min(t, l / -ux)
    if uy > 1e-9:
        t = min(t, d / uy)
    elif uy < -1e-9:
        t = min(t, u / -uy)
    return t


# Sweep flags for the limb and terminator arcs of each phase. Derived by
# rendering all four flag combinations per phase and keeping the one whose lit
# area matches (1 - cos elongation) / 2 *and* whose centroid falls on the correct
# limb - area alone has a mirror-image solution that lights the wrong side.
_MOON_ARCS = {
    0: (0, 1),   # new             0.00 lit
    1: (1, 0),   # waxing crescent 0.15, right
    2: (1, 0),   # first quarter   0.50, right
    3: (1, 1),   # waxing gibbous  0.85, right
    4: (0, 0),   # full            1.00
    5: (0, 0),   # waning gibbous  0.85, left
    6: (0, 0),   # last quarter    0.50, left
    7: (0, 1),   # waning crescent 0.15, left
}


def _moon_path(cx, cy, r, idx):
    """Outline of the lit part of the Moon for one of the eight phases.

    The phase emoji (U+1F311 and friends) is missing from every font that carries
    the zodiac, so it renders as a tofu box. Two arcs draw it instead: the limb,
    and the terminator, whose horizontal radius is the cosine of the elongation.
    """
    limb, term = _MOON_ARCS[idx]
    rx = abs(math.cos(math.radians(idx * 45))) * r
    return (f"M {cx},{cy - r} A {r},{r} 0 0,{limb} {cx},{cy + r} "
            f"A {rx},{r} 0 0,{term} {cx},{cy - r} Z")


def _overlaps(a, b, pad):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or
                a[3] + pad <= b[1] or b[3] + pad <= a[1])


def render(positions, config):
    """Chart with large glyphs pinned to their true zodiac angle."""
    location = config['location']
    bodies = config.get('bodies', list(BODY_GLYPHS.keys()))
    display = config.get('display', {})
    show_retrograde = display.get('show_retrograde', True)
    show_moon_phase = display.get('show_moon_phase', True)
    show_house_numbers = display.get('show_house_numbers', True)

    dwg = svgwrite.Drawing(size=('800px', '480px'))
    dwg.add(dwg.rect(insert=(0, 0), size=('800px', '480px'), fill='white'))

    # === LEFT SIDE: Zodiac wheel ===
    wheel_cx, wheel_cy = 216, 240
    outer_r = 92
    inner_r = 62          # 30px band, sized for the 24px sign glyphs
    sign_glyph_r = (outer_r + inner_r) / 2
    tick_outer = outer_r + 8

    # Planet and sign glyphs are kept within ~1.7x of each other so the wheel
    # reads as one object rather than big symbols orbiting fine print. Dropping
    # the planets from 58 to 48 also costs far less than it sounds: it takes
    # glyphs sitting at their exactly-true angle from 72% to 85%, because a
    # smaller glyph needs to be bumped out to a further radius less often.
    GLYPH_SIZE = 40
    DEGREE_SIZE = GLYPH_SIZE // 2   # degrees ride under each glyph at half its size
    SIGN_GLYPH_SIZE = 24
    ANGLE_SIZE = 22                 # ASC / MC are reference axes, not planets

    # Every wheel label is a glyph stacked over its degree, so both the planets
    # and the two axes read the same way. Measured proportions, not guesses:
    # Astronomicon's widest planet is 0.775 of its size and 0.825 tall, and a
    # three-character degree in the text face runs about 1.75 of its own size.
    _GLYPH_W = 0.78 * GLYPH_SIZE
    _GLYPH_H = 0.83 * GLYPH_SIZE
    _DEG_W = 1.75 * DEGREE_SIZE
    _DEG_H = 0.75 * DEGREE_SIZE
    _NAME_W = 1.90 * ANGLE_SIZE     # "ASC" is the widest axis name
    _NAME_H = 0.75 * ANGLE_SIZE

    # 'below' stacks the degree under its glyph; 'right' sets it alongside.
    # Stacked labels are narrow and tall, side-by-side ones wide and short, and
    # the panel has far more room vertically than horizontally, so the choice
    # costs real accuracy - see the comparison in the dev log.
    DEGREE_PLACEMENT = 'right'
    _GAP = 6

    if DEGREE_PLACEMENT == 'right':
        # End the glyph and start the figure either side of the anchor, rather
        # than centring each in a slot cut for the widest possible one. Centring
        # made the gap depend on how narrow that particular glyph and degree
        # happened to be: 6px after the Sun and 20 degrees, 18px after Pluto
        # and 3. Anchoring the facing edges makes it exactly _GAP every time.
        GLYPH_BASELINE = _GLYPH_H / 2
        DEGREE_BASELINE = _DEG_H / 2
        NAME_BASELINE = _NAME_H / 2
        ANGLE_DEG_BASELINE = _DEG_H / 2
        GLYPH_ANCHOR, DEGREE_ANCHOR = 'end', 'start'
        GLYPH_DX = -_GAP / 2
        DEGREE_DX = _GAP / 2
        NAME_DX = -_GAP / 2
        ANGLE_DEG_DX = _GAP / 2
        GLYPH_BOX = (_GAP / 2 + _GLYPH_W + 2, _GAP / 2 + _DEG_W + 2,
                     _GLYPH_H / 2 + 2, _GLYPH_H / 2 + 2)
        ANGLE_BOX = (_GAP / 2 + _NAME_W + 2, _GAP / 2 + _DEG_W + 2,
                     _NAME_H / 2 + 2, _NAME_H / 2 + 2)
    else:
        GLYPH_BASELINE = -0.05 * GLYPH_SIZE
        DEGREE_BASELINE = GLYPH_BASELINE + 0.45 * GLYPH_SIZE
        NAME_BASELINE = -0.05 * GLYPH_SIZE
        ANGLE_DEG_BASELINE = NAME_BASELINE + 0.45 * GLYPH_SIZE
        GLYPH_ANCHOR = DEGREE_ANCHOR = 'middle'
        GLYPH_DX = DEGREE_DX = NAME_DX = ANGLE_DEG_DX = 0
        _GH = max(_GLYPH_W, _DEG_W) / 2 + 2
        GLYPH_BOX = (_GH, _GH, _GLYPH_H - GLYPH_BASELINE, DEGREE_BASELINE)
        _AH = max(_NAME_W, _DEG_W) / 2 + 2
        ANGLE_BOX = (_AH, _AH, _NAME_H - NAME_BASELINE, ANGLE_DEG_BASELINE)

    # Search preferences. Radial displacement keeps the angle honest, so it is
    # made cheap; angular displacement is what we are trying not to spend.
    ANGLE_STEP = 1.5         # degrees per sideways step
    ANGLE_LIMIT = 120        # furthest a glyph may ever be slid sideways
    RADIAL_STEP = 5          # px per outward step
    RADIAL_COST = 0.028      # cost of 1px outward, relative to 1 degree sideways
    LABEL_PAD = 5

    # A leader line only earns its place when the glyph is genuinely hard to
    # attribute: either sitting off its own ray, or far enough out that the eye
    # needs help bridging the gap. A glyph resting on the rim at its exact angle
    # needs no pointer, and drawing one anyway just adds clutter.
    LEADER_MIN_LATERAL = 6      # px off the true ray
    LEADER_MIN_GAP = 30         # px of clear space between rim and glyph

    asc_lon = positions.get('ascendant', {}).get('lon', 0)
    rotation_offset = 180 - asc_lon

    def to_screen_angle(zodiac_lon):
        return math.radians(zodiac_lon + rotation_offset)

    def box_at(cx, cy, box):
        l, r, u, d = box
        return (cx - l, cy - u, cx + r, cy + d)

    def radial_extent(theta, box):
        """How deep a label reaches along its own ray."""
        l, r, u, d = box
        return abs(math.cos(theta)) * max(l, r) + abs(math.sin(theta)) * max(u, d)

    def r_bounds(theta, box):
        """Nearest and furthest this label's centre can sit on this ray.

        The far bound solves the panel rectangle directly rather than inscribing
        an ellipse in it, so the corners stay usable.
        """
        l, r, u, d = box
        dx, dy = math.cos(theta), -math.sin(theta)      # screen y grows downward
        far = 1e5
        if dx > 1e-6:
            far = min(far, (PANEL[2] - r - wheel_cx) / dx)
        elif dx < -1e-6:
            far = min(far, (PANEL[0] + l - wheel_cx) / dx)
        if dy > 1e-6:
            far = min(far, (PANEL[3] - d - wheel_cy) / dy)
        elif dy < -1e-6:
            far = min(far, (PANEL[1] + u - wheel_cy) / dy)
        near = tick_outer + 6 + radial_extent(theta, box)
        return near, max(far, near)

    # --- wheel -------------------------------------------------------------
    dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=outer_r,
                       stroke='black', stroke_width=2, fill='none'))
    dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=inner_r,
                       stroke='black', stroke_width=2, fill='none'))
    for i in range(12):
        a = to_screen_angle(i * 30)
        dwg.add(dwg.line(start=(wheel_cx, wheel_cy),
                         end=(wheel_cx + outer_r * math.cos(a),
                              wheel_cy - outer_r * math.sin(a)),
                         stroke='black', stroke_width=1))
        mid = to_screen_angle(i * 30 + 15)
        dwg.add(dwg.text(SIGN_GLYPHS[i],
                         insert=(wheel_cx + sign_glyph_r * math.cos(mid),
                                 wheel_cy - sign_glyph_r * math.sin(mid) + 0.34 * SIGN_GLYPH_SIZE),
                         text_anchor='middle', font_size=f'{SIGN_GLYPH_SIZE}px',
                         font_family=GLYPH_FONT, fill='black'))

    # --- placement ---------------------------------------------------------
    # Two hard rules, in this order of importance:
    #
    #   1. Order is never violated. Whatever else happens, the glyphs must read
    #      around the wheel in the same sequence as the planets do around the
    #      zodiac. Drawing Venus before Neptune when it is actually after is a
    #      worse lie than drawing it a few degrees off.
    #   2. Angle is preserved where possible. Collisions are resolved by pushing
    #      outward along the same ray, which costs only depth; sliding sideways
    #      is the last resort because it is what spends angle.
    #
    # Rule 1 is enforced by cutting the cycle at its widest gap, unwrapping to a
    # line, and requiring the placed angles to stay non-decreasing along it.
    entries = [(b, to_screen_angle(positions[b]['lon']))
               for b in bodies if b in positions]
    n = len(entries)
    entries.sort(key=lambda e: e[1] % (2 * math.pi))
    gaps = [((entries[(i + 1) % n][1] - entries[i][1]) % (2 * math.pi)) for i in range(n)]
    cut = max(range(n), key=lambda i: gaps[i])
    entries = entries[cut + 1:] + entries[:cut + 1]

    base = entries[0][1]
    trues = [base + ((th - base) % (2 * math.pi)) for _, th in entries]

    def is_axis(body):
        return body in ('ascendant', 'medium_coeli')

    # Candidates for each label, cheapest first. Angle is weighted far above
    # radius, and the axes are weighted higher still so they effectively never
    # move -- they are the marks everything else is read against.
    all_candidates = []
    for i, (body, _) in enumerate(entries):
        box = ANGLE_BOX if is_axis(body) else GLYPH_BOX
        weight = 8.0 if is_axis(body) else 1.0
        near0 = r_bounds(trues[i], box)[0]
        cands = []
        for si in range(int(ANGLE_LIMIT / ANGLE_STEP) + 1):
            for sgn in ((0,) if si == 0 else (1, -1)):
                d_deg = sgn * si * ANGLE_STEP
                theta = trues[i] + math.radians(d_deg)
                lo, hi = r_bounds(theta, box)
                r = lo
                while r <= hi + 0.5:
                    cands.append((weight * abs(d_deg) + RADIAL_COST * (r - near0), theta, r))
                    r += RADIAL_STEP
        cands.sort(key=lambda c: c[0])
        all_candidates.append(cands)

    def best_spot(i, lower, upper, others, pad):
        """Cheapest collision-free spot for label i with its angle in bounds."""
        box = ANGLE_BOX if is_axis(entries[i][0]) else GLYPH_BOX
        for cost, theta, r in all_candidates[i]:
            if theta < lower - 1e-9 or theta > upper + 1e-9:
                continue
            cx = wheel_cx + r * math.cos(theta)
            cy = wheel_cy - r * math.sin(theta)
            rect = box_at(cx, cy, box)
            if not any(_overlaps(rect, o, pad) for o in others):
                return (cost, theta, r, cx, cy, rect)
        return None

    TWO_PI = 2 * math.pi
    slots = [None] * n
    for pad in (LABEL_PAD, 0):
        placed_rects = []
        ok = True
        lower = -1e9
        for i in range(n):
            upper = trues[0] + TWO_PI - 1e-6 if i == n - 1 else 1e9
            spot = best_spot(i, lower, upper, placed_rects, pad)
            if spot is None:
                ok = False
                break
            slots[i] = spot
            placed_rects.append(spot[5])
            lower = spot[1]              # keeps the sequence non-decreasing
        if ok:
            break
    else:
        # Nothing fits even touching: fall back to true angles at max radius.
        for i, (body, _) in enumerate(entries):
            box = ANGLE_BOX if is_axis(body) else GLYPH_BOX
            r = r_bounds(trues[i], box)[1]
            cx = wheel_cx + r * math.cos(trues[i])
            cy = wheel_cy - r * math.sin(trues[i])
            slots[i] = (0, trues[i], r, cx, cy, box_at(cx, cy, box))

    # The forward pass can only push a crowded run one way. Sweep back and forth
    # letting each label return toward its true angle as far as its neighbours
    # allow; the monotonic bounds keep the order intact throughout.
    for _ in range(3):
        for order in (range(n - 1, -1, -1), range(n)):
            for i in order:
                lower = slots[i - 1][1] if i > 0 else trues[0] - TWO_PI + 1e-6
                upper = slots[i + 1][1] if i < n - 1 else trues[0] + TWO_PI - 1e-6
                others = [s[5] for j, s in enumerate(slots) if j != i]
                spot = best_spot(i, lower, upper, others, LABEL_PAD)
                if spot is not None and spot[0] < slots[i][0] - 1e-9:
                    slots[i] = spot

    placed = {entries[i][0]: (slots[i][1], slots[i][2], slots[i][3], slots[i][4])
              for i in range(n)}

    # --- ticks, leaders, glyphs -------------------------------------------
    for body, true_angle in entries:
        theta, r, lx, ly = placed[body]
        is_angle = body in ('ascendant', 'medium_coeli')
        box = ANGLE_BOX if is_angle else GLYPH_BOX

        tx1 = wheel_cx + outer_r * math.cos(true_angle)
        ty1 = wheel_cy - outer_r * math.sin(true_angle)
        tx2 = wheel_cx + tick_outer * math.cos(true_angle)
        ty2 = wheel_cy - tick_outer * math.sin(true_angle)
        dwg.add(dwg.line(start=(tx1, ty1), end=(tx2, ty2),
                         stroke='black', stroke_width=2))

        # Aim the leader at the glyph itself rather than at a radius along its
        # ray. Those differ whenever a glyph is displaced sideways at a small
        # radius, and the ray version then degenerates into a stub skimming the
        # rim, pointing tens of degrees away from what it is supposed to label.
        vx, vy = lx - tx2, ly - ty2
        span = math.hypot(vx, vy)
        lateral = abs(r * math.sin(theta - true_angle))
        if span > 1e-6:
            ux, uy = -vx / span, -vy / span
            inset = _box_exit(box, ux, uy) + 3
            clear = span - inset
            if lateral > LEADER_MIN_LATERAL or clear > LEADER_MIN_GAP:
                if clear > 2:
                    dwg.add(dwg.line(start=(tx2, ty2),
                                     end=(lx + ux * inset, ly + uy * inset),
                                     stroke=DARK_GRAY, stroke_width=1))

        deg_text = f"{positions[body]['deg']}\u00B0"
        if is_angle:
            name = 'ASC' if body == 'ascendant' else 'MC'
            dwg.add(dwg.text(name, insert=(lx + NAME_DX, ly + NAME_BASELINE),
                             text_anchor=GLYPH_ANCHOR,
                             font_size=f'{ANGLE_SIZE}px', font_family=TEXT_FONT,
                             fill='black', font_weight='bold'))
            dwg.add(dwg.text(deg_text, insert=(lx + ANGLE_DEG_DX, ly + ANGLE_DEG_BASELINE),
                             text_anchor=DEGREE_ANCHOR, font_size=f'{DEGREE_SIZE}px',
                             font_family=TEXT_FONT, fill='black'))
        else:
            dwg.add(dwg.text(BODY_GLYPHS[body], insert=(lx + GLYPH_DX, ly + GLYPH_BASELINE),
                             text_anchor=GLYPH_ANCHOR, font_size=f'{GLYPH_SIZE}px',
                             font_family=GLYPH_FONT, fill='black'))
            dwg.add(dwg.text(deg_text, insert=(lx + DEGREE_DX, ly + DEGREE_BASELINE),
                             text_anchor=DEGREE_ANCHOR, font_size=f'{DEGREE_SIZE}px',
                             font_family=TEXT_FONT, fill='black'))

    # === RIGHT SIDE: Legend panel (unchanged) ===
    legend_x = 435
    legend_y_start = 32       # baseline; 15 put the cap-height above the canvas
    line_height = 30
    # Astronomicon sets smaller than a text face at the same nominal size, so the
    # legend glyphs step up and the figures step down to bring them into balance.
    LEGEND_GLYPH_SIZE = 30
    LEGEND_TEXT_SIZE = 20
    asc_sign = positions.get('ascendant', {}).get('sign', 0)

    # Anchor the header from the left rather than centring it. The title is bold,
    # and the bold face is ~15% wider than the regular one, so a centred title
    # grows out to both sides -- enough to run into the moon on a machine that
    # has the bold face when the machine it was tuned on did not. Anchored left,
    # the gap is fixed whatever the font does.
    moon_idx = get_moon_phase(positions) if show_moon_phase else None
    title_x = legend_x + (34 if moon_idx is not None else 2)
    dwg.add(dwg.text('Planetary Positions', insert=(title_x, legend_y_start),
                     text_anchor='start', font_size='22px',
                     font_family=TEXT_FONT, fill='black', font_weight='bold'))
    if moon_idx is not None:
        mcx, mcy, mr = legend_x + 13, legend_y_start - 7, 9
        dwg.add(dwg.circle(center=(mcx, mcy), r=mr, fill='white',
                           stroke='black', stroke_width=1.5))
        if moon_idx != 0:
            dwg.add(dwg.path(d=_moon_path(mcx, mcy, mr, moon_idx),
                             fill='black', stroke='none'))
    dwg.add(dwg.line(start=(legend_x, legend_y_start + 12),
                     end=(legend_x + 340, legend_y_start + 12),
                     stroke='black', stroke_width=1))

    y = legend_y_start + 40
    for body in bodies:
        if body in positions:
            pos = positions[body]
            is_axis_row = body in ('ascendant', 'medium_coeli')
            dwg.add(dwg.text(BODY_GLYPHS[body], insert=(legend_x + 10, y),
                             font_size=f'{24 if is_axis_row else LEGEND_GLYPH_SIZE}px',
                             font_family=TEXT_FONT if is_axis_row else GLYPH_FONT,
                             fill='black', font_weight='bold'))
            dwg.add(dwg.text(SIGN_GLYPHS[pos['sign']], insert=(legend_x + 72, y),
                             font_size=f'{LEGEND_GLYPH_SIZE}px',
                             font_family=GLYPH_FONT, fill='black'))
            dwg.add(dwg.text(f"{pos['deg']:02d}°{pos['min']:02d}'", insert=(legend_x + 118, y),
                             font_size=f'{LEGEND_TEXT_SIZE}px', font_family=TEXT_FONT,
                             fill='black'))
            if show_retrograde and pos.get('retrograde', False):
                dwg.add(dwg.text(RETROGRADE_GLYPH, insert=(legend_x + 196, y),
                                 font_size='20px', font_family=GLYPH_FONT, fill='black'))
            if show_house_numbers and body not in ['ascendant', 'medium_coeli']:
                dwg.add(dwg.text(ordinal(get_house_number(pos['sign'], asc_sign)),
                                 insert=(legend_x + 238, y),
                                 font_size=f'{LEGEND_TEXT_SIZE}px',
                                 font_family=TEXT_FONT, fill='black'))
            y += line_height

    now_local = datetime.now(ZoneInfo(location['timezone']))
    stamp = f"{now_local.strftime('%B %d %Y')} {now_local.strftime('%-I:%M %p').lower()}"
    dwg.add(dwg.text(f"[DEV] {location['name']} | {stamp}", insert=(legend_x + 170, 468),
                     text_anchor='middle', font_size='14px',
                     font_family=TEXT_FONT, fill=DARK_GRAY))

    return dwg.tostring()
