"""
Development chart renderer: Experimental layouts.

This is your sandbox for iterating on new chart designs.
Modify freely - production.py remains untouched.

The render() function receives the same inputs as production:
- positions: Dict of body positions from API
- config: Dict with 'location', 'bodies', 'display' keys

Output: SVG string (800x480)

Current design: radial columns, after the classic desktop chart layout.

Each body is a column of upright pieces running inward from the sign ring along
its own ray: glyph, whole degree, sign, arcminute, retrograde mark. The wheel
fills the full panel height, so a column has ~130px of depth to work with.

Only the angle can give when columns collide, so placement is one-dimensional:
bodies keep their zodiac order, each adjacent pair gets the smallest angular gap
at which their pieces clear, and crowded runs spread symmetrically about their
true angles. A short leader joins a tick at the true position to any column
that had to move.
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
    get_moon_phase, get_house_number
)

# GLYPH_FONT draws astrological symbols and nothing else; TEXT_FONT draws every
# letter, digit and degree mark. Keeping them apart matters because dedicated
# astrology faces (Astronomicon and kin) map their symbols onto ASCII letters --
# point one of those at a timestamp and the date turns into planets.
GLYPH_FONT = 'Astronomicon'
TEXT_FONT = 'DejaVu Sans, Arial, sans-serif'

LIGHT_GRAY = '#aaaaaa'

# Ink widths as a fraction of font size, measured with PIL from the vendored
# Astronomicon and DejaVu Sans. Vertical: DejaVu ink sits 0.75 above the
# baseline to 0.01 below; Astronomicon 0.70 above to 0.10 below.
_ASTRO_W = {'Q': .77, 'R': .52, 'S': .46, 'T': .47, 'U': .77, 'V': .62, 'W': .48,
            'X': .56, 'Y': .55, 'Z': .51, 'g': .6, 'i': .6,
            'A': .60, 'B': .56, 'C': .56, 'D': .81, 'E': .65, 'F': .68, 'G': .90,
            'H': .85, 'I': .72, 'J': .68, 'K': .89, 'L': .56, 'M': .31,
            '!': .55, '"': .55, '#': .55, '$': .60, '%': .60}
_TEXT_W = {'\u00B0': .50, "'": .28, ' ': .32, '\u2192': .84}      # digits are .636
_BOLD_W = {'A': .80, 'C': .71, 'M': .96, 'D': .83, 'I': .40}


def _text_w(s, size, bold=False):
    table = _BOLD_W if bold else _TEXT_W
    return size * sum(table.get(ch, .636) for ch in s)


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
    """Chart with each body's details stacked along its own ray."""
    location = config['location']
    bodies = list(config.get('bodies', list(BODY_GLYPHS.keys())))
    # Nodes and the DC/IC axes ride along whenever the fetch supplied them,
    # without touching config.yaml, so production's legend keeps its 12 rows
    # until this design is promoted.
    for extra in ('mean_north_lunar_node', 'mean_south_lunar_node', 'descendant', 'imum_coeli'):
        if extra in positions and extra not in bodies:
            bodies.append(extra)
    display = config.get('display', {})
    show_retrograde = display.get('show_retrograde', True)
    show_moon_phase = display.get('show_moon_phase', True)
    show_house_numbers = display.get('show_house_numbers', True)

    dwg = svgwrite.Drawing(size=('800px', '480px'))
    dwg.add(dwg.rect(insert=(0, 0), size=('800px', '480px'), fill='white'))

    # === LEFT SIDE: Zodiac wheel ===
    wheel_cx, wheel_cy = 238, 240
    outer_r = 234
    inner_r = 202          # 32px band for the sign glyphs
    sign_glyph_r = (outer_r + inner_r) / 2
    hub_r = 52
    TICK = 7

    SIGN_GLYPH_SIZE = 26
    GLYPH_SIZE = 32        # planet glyph heads each column
    AXIS_SIZE = 20         # AC / MC, bold text
    DEGREE_SIZE = 20
    SIGN_SIZE = 20
    MINUTE_SIZE = 14
    RX_SIZE = 24
    PIECE_GAP = 3          # between pieces within a column
    COLUMN_PAD = 3         # between pieces of neighbouring columns

    AXES = {'ascendant': 'AC', 'medium_coeli': 'MC',
            'descendant': 'DC', 'imum_coeli': 'IC'}

    asc_lon = positions.get('ascendant', {}).get('lon', 0)
    rotation_offset = 180 - asc_lon

    def to_screen_angle(zodiac_lon):
        return math.radians(zodiac_lon + rotation_offset)

    def pieces_for(body):
        """(text, font, size, bold, w, h, baseline_offset) outermost first."""
        pos = positions[body]
        out = []
        if body in AXES:
            name = AXES[body]
            out.append((name, TEXT_FONT, AXIS_SIZE, True,
                        _text_w(name, AXIS_SIZE, True), .76 * AXIS_SIZE, .37 * AXIS_SIZE))
        else:
            g = BODY_GLYPHS[body]
            out.append((g, GLYPH_FONT, GLYPH_SIZE, False,
                        _ASTRO_W.get(g, .7) * GLYPH_SIZE, .8 * GLYPH_SIZE, .30 * GLYPH_SIZE))
        deg = f"{pos['deg']}\u00B0"
        out.append((deg, TEXT_FONT, DEGREE_SIZE, False,
                    _text_w(deg, DEGREE_SIZE), .76 * DEGREE_SIZE, .37 * DEGREE_SIZE))
        s = SIGN_GLYPHS[pos['sign']]
        out.append((s, GLYPH_FONT, SIGN_SIZE, False,
                    _ASTRO_W[s] * SIGN_SIZE, .7 * SIGN_SIZE, .30 * SIGN_SIZE))
        mins = f"{pos['min']:02d}'"
        out.append((mins, TEXT_FONT, MINUTE_SIZE, False,
                    _text_w(mins, MINUTE_SIZE), .76 * MINUTE_SIZE, .37 * MINUTE_SIZE))
        if show_retrograde and pos.get('retrograde', False):
            out.append((RETROGRADE_GLYPH, GLYPH_FONT, RX_SIZE, False,
                        _ASTRO_W['M'] * RX_SIZE, .45 * RX_SIZE, .30 * RX_SIZE))
        return out

    def layout_column(pieces, theta, displaced):
        """Centre point and box of every piece, walking inward along theta."""
        c, s = math.cos(theta), math.sin(theta)
        edge = inner_r - TICK - (8 if displaced else 3)
        placed = []
        for p in pieces:
            w, h = p[4], p[5]
            ext = abs(c) * w / 2 + abs(s) * h / 2
            r = edge - ext
            cx, cy = wheel_cx + r * c, wheel_cy - r * s
            placed.append((p, cx, cy, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)))
            edge = r - ext - PIECE_GAP
        return placed

    def columns_clash(pa, ta, pb, tb):
        ra = [q[3] for q in layout_column(pa, ta, True)]
        rb = [q[3] for q in layout_column(pb, tb, True)]
        return any(_overlaps(a, b, COLUMN_PAD) for a in ra for b in rb)

    def required_gap(pa, pb, mid):
        """Smallest angular gap (radians) at which two columns centred on mid clear."""
        d = 0.0
        step = math.radians(0.5)
        while d < math.radians(60):
            if not columns_clash(pa, mid - d / 2, pb, mid + d / 2):
                return d
            d += step
        return d

    # --- order and unwrap ----------------------------------------------------
    entries = [(b, to_screen_angle(positions[b]['lon']))
               for b in bodies if b in positions]
    n = len(entries)
    TWO_PI = 2 * math.pi
    entries.sort(key=lambda e: e[1] % TWO_PI)
    gaps = [((entries[(i + 1) % n][1] - entries[i][1]) % TWO_PI) for i in range(n)]
    cut = max(range(n), key=lambda i: gaps[i])
    entries = entries[cut + 1:] + entries[:cut + 1]
    base = entries[0][1]
    trues = [base + ((th - base) % TWO_PI) for _, th in entries]
    pieces = [pieces_for(b) for b, _ in entries]

    # --- spread --------------------------------------------------------------
    # Classic 1-D label spreading: overlapping runs merge into clusters, and each
    # cluster sits where its members' mean displacement is zero. The gap a pair
    # needs depends on where on the wheel it sits (a column is wide across a
    # vertical ray and narrow across a horizontal one), so gaps are re-measured
    # at the placed angles until they stop changing.
    def spread(req):
        clusters = []            # [start, end, pos_of_start]
        for i in range(n):
            clusters.append([i, i, trues[i]])
            while len(clusters) > 1:
                a, b = clusters[-2], clusters[-1]
                a_end = a[2] + sum(req[a[0]:a[1]])
                if a_end + req[a[1]] <= b[2]:
                    break
                start, end = a[0], b[1]
                offs, acc = [], 0.0
                for k in range(start, end + 1):
                    offs.append(acc)
                    if k < end:
                        acc += req[k]
                p = sum(trues[k] - offs[k - start] for k in range(start, end + 1)) / len(offs)
                clusters[-2:] = [[start, end, p]]
        out = []
        for st, en, p in clusters:
            acc = 0.0
            for k in range(st, en + 1):
                out.append(p + acc)
                if k < en:
                    acc += req[k]
        return out

    placed = list(trues)
    req = [0.0] * n
    for _ in range(6):
        new_req = [required_gap(pieces[i], pieces[i + 1], (placed[i] + placed[i + 1]) / 2)
                   for i in range(n - 1)] + [0.0]
        req = [max(a, b) for a, b in zip(req, new_req)]
        placed = spread(req)
        if all(not columns_clash(pieces[i], placed[i], pieces[i + 1], placed[i + 1])
               for i in range(n - 1)):
            break

    # --- wheel -----------------------------------------------------------------
    for r, sw in ((outer_r, 2), (inner_r, 2), (hub_r, 1)):
        dwg.add(dwg.circle(center=(wheel_cx, wheel_cy), r=r,
                           stroke='black', stroke_width=sw, fill='none'))
    asc_sign = positions.get('ascendant', {}).get('sign', 0)
    for i in range(12):
        a = to_screen_angle(i * 30)
        ca, sa = math.cos(a), -math.sin(a)
        dwg.add(dwg.line(start=(wheel_cx + inner_r * ca, wheel_cy + inner_r * sa),
                         end=(wheel_cx + outer_r * ca, wheel_cy + outer_r * sa),
                         stroke='black', stroke_width=1.5))
        # House cusps (whole sign) run faintly through the label field.
        dwg.add(dwg.line(start=(wheel_cx + hub_r * ca, wheel_cy + hub_r * sa),
                         end=(wheel_cx + inner_r * ca, wheel_cy + inner_r * sa),
                         stroke=LIGHT_GRAY, stroke_width=1))
        mid = to_screen_angle(i * 30 + 15)
        dwg.add(dwg.text(SIGN_GLYPHS[i],
                         insert=(wheel_cx + sign_glyph_r * math.cos(mid),
                                 wheel_cy - sign_glyph_r * math.sin(mid) + 0.30 * SIGN_GLYPH_SIZE),
                         text_anchor='middle', font_size=f'{SIGN_GLYPH_SIZE}px',
                         font_family=GLYPH_FONT, fill='black'))
        if show_house_numbers:
            hr = hub_r - 12
            house = get_house_number(i, asc_sign)
            dwg.add(dwg.text(str(house),
                             insert=(wheel_cx + hr * math.cos(mid),
                                     wheel_cy - hr * math.sin(mid) + 0.37 * 12),
                             text_anchor='middle', font_size='12px',
                             font_family=TEXT_FONT, fill=DARK_GRAY))

    # --- columns ---------------------------------------------------------------
    for i, (body, true_angle) in enumerate(entries):
        theta = placed[i]
        displaced = abs(theta - true_angle) > math.radians(0.75)
        c1, s1 = math.cos(true_angle), -math.sin(true_angle)
        tx2 = wheel_cx + (inner_r - TICK) * c1
        ty2 = wheel_cy + (inner_r - TICK) * s1
        dwg.add(dwg.line(start=(wheel_cx + inner_r * c1, wheel_cy + inner_r * s1),
                         end=(tx2, ty2), stroke='black', stroke_width=2))
        column = layout_column(pieces[i], theta, True)
        if displaced:
            ex = wheel_cx + (inner_r - TICK - 6) * math.cos(theta)
            ey = wheel_cy - (inner_r - TICK - 6) * math.sin(theta)
            dwg.add(dwg.line(start=(tx2, ty2), end=(ex, ey),
                             stroke=DARK_GRAY, stroke_width=1))
        for p, cx, cy, _ in column:
            text, font, size, bold, w, h, base_off = p
            kw = {'font_weight': 'bold'} if bold else {}
            dwg.add(dwg.text(text, insert=(cx, cy + base_off), text_anchor='middle',
                             font_size=f'{size}px', font_family=font, fill='black', **kw))

    # === RIGHT SIDE: Upcoming events ===
    # The wheel now carries every current position, so the panel looks ahead
    # instead of repeating it. Events come from events.py via config['events'];
    # without them the panel just shows the Moon.
    panel_x = 488
    panel_right = 796
    header_y = 32
    ROW = 26
    ROW_SIZE = 18
    ROW_GLYPH = 24          # Astronomicon sets small; step it up to match the text
    DATE_W = 90             # date column
    tz = ZoneInfo(location['timezone'])
    events = config.get('events') or []

    def aspect_glyph(angle):
        from .base import ASTRO_ASPECT_GLYPHS
        return ASTRO_ASPECT_GLYPHS[angle]

    def deg_sign(lon):
        """Pieces for a longitude as '17°' + sign glyph."""
        return [(f"{int(lon % 30)}\u00B0", TEXT_FONT, ROW_SIZE),
                (SIGN_GLYPHS[int(lon // 30)], GLYPH_FONT, ROW_GLYPH)]

    def describe(e):
        """Row pieces for one event: list of (text, font, size)."""
        G, T = GLYPH_FONT, TEXT_FONT
        b = BODY_GLYPHS[e['body']]
        if e['kind'] == 'lunation':
            return [(('New' if e['phase'] == 'new' else 'Full') + ' Moon ', T, ROW_SIZE)] + deg_sign(e['lon'])
        if e['kind'] == 'ingress':
            rx = [(RETROGRADE_GLYPH, G, ROW_GLYPH)] if e['retrograde'] else []
            return [(b, G, ROW_GLYPH)] + rx + [(' \u2192 ', T, ROW_SIZE),
                                               (SIGN_GLYPHS[e['sign']], G, ROW_GLYPH)]
        if e['kind'] == 'station':
            if e['direction'] == 'retrograde':
                return [(b, G, ROW_GLYPH), (' stations ', T, ROW_SIZE), (RETROGRADE_GLYPH, G, ROW_GLYPH)]
            return [(b, G, ROW_GLYPH), (' stations direct', T, ROW_SIZE)]
        if e['kind'] == 'aspect':
            return [(b, G, ROW_GLYPH), (' ', T, ROW_SIZE), (aspect_glyph(e['angle']), G, ROW_GLYPH),
                    (' ', T, ROW_SIZE), (BODY_GLYPHS[e['other']], G, ROW_GLYPH),
                    ('  ', T, ROW_SIZE)] + deg_sign(e['lon'])
        return []

    def draw_pieces(x, y, pieces, fill='black'):
        """One <text> with a <tspan> per piece, so the renderer measures the
        widths itself and mixed faces butt up correctly. Spaces become NBSP
        because a tspan's leading or trailing space is collapsed."""
        t = dwg.text('', insert=(x, y), fill=fill)
        for text, font, size in pieces:
            t.add(dwg.tspan(text.replace(' ', '\u00A0'),
                            font_size=f'{size}px', font_family=font))
        dwg.add(t)

    def when_text(e):
        return e['when'].astimezone(tz).strftime('%b %-d')

    # -- header: Moon phase and illumination, the one "now" fact worth a line --
    moon_idx = get_moon_phase(positions) if show_moon_phase else None
    if moon_idx is not None:
        mcx, mcy, mr = panel_x + 14, header_y - 8, 12
        dwg.add(dwg.circle(center=(mcx, mcy), r=mr, fill='white',
                           stroke='black', stroke_width=1.5))
        # Ink is the shadow: the lit part of the disc stays paper-white, so a
        # full Moon is an empty circle and a new Moon a solid one. The dark
        # region of any phase is exactly the lit region of the opposite phase.
        if moon_idx != 4:
            dwg.add(dwg.path(d=_moon_path(mcx, mcy, mr, (moon_idx + 4) % 8),
                             fill='black', stroke='none'))
        elong = (positions['moon']['lon'] - positions['sun']['lon']) % 360
        lit = (1 - math.cos(math.radians(elong))) / 2
        names = ['New Moon', 'Waxing Crescent', 'First Quarter', 'Waxing Gibbous',
                 'Full Moon', 'Waning Gibbous', 'Last Quarter', 'Waning Crescent']
        title = f"{names[moon_idx]}  {round(lit * 100)}%"
    else:
        title = 'Upcoming'
    dwg.add(dwg.text(title, insert=(panel_x + 36, header_y), font_size='22px',
                     font_family=TEXT_FONT, fill='black', font_weight='bold'))
    dwg.add(dwg.line(start=(panel_x, header_y + 12), end=(panel_right, header_y + 12),
                     stroke='black', stroke_width=1))

    # -- rows: one chronological list. Lunations and planetary events appear
    #    as they come; of the Moon's own aspects only the next one is kept, and
    #    Moon ingresses and Sun-Moon aspects are dropped as noise - the lunations
    #    already cover the conjunction and opposition.
    def is_noise(e):
        if e['kind'] == 'aspect' and {e['body'], e['other']} == {'sun', 'moon'}:
            return True
        return e['kind'] in ('ingress', 'aspect') and e['body'] == 'moon'

    next_moon = next((e for e in events if e['kind'] == 'aspect' and e['body'] == 'moon'
                      and e['other'] != 'sun'), None)
    rows = [e for e in events if e is next_moon or not is_noise(e)]

    y = header_y + 40
    bottom = 450
    for e in rows:
        if y > bottom:
            break
        dwg.add(dwg.text(when_text(e), insert=(panel_x + 2, y),
                         font_size='14px', font_family=TEXT_FONT, fill=DARK_GRAY))
        draw_pieces(panel_x + DATE_W, y, describe(e))
        y += ROW

    now_local = datetime.now(ZoneInfo(location['timezone']))
    stamp = f"{now_local.strftime('%B %d %Y')} {now_local.strftime('%-I:%M %p').lower()}"
    dwg.add(dwg.text(f"[DEV] {location['name']} | {stamp}", insert=(796, 468),
                     text_anchor='end', font_size='14px',
                     font_family=TEXT_FONT, fill=DARK_GRAY))

    return dwg.tostring()
