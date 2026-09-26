"""
Upcoming sky events: lunations, ingresses, stations and exact aspects.

Computed locally with the Swiss Ephemeris (pyswisseph, Moshier mode - no
ephemeris files needed). The Astrologer API gives the current moment only;
nothing it exposes will say when Venus next changes sign or when the Moon
next squares Saturn, so this module looks ahead itself.

Every finder works the same way: sample the sky on a fixed grid, notice where
a monitored quantity changes sign between two samples, then bisect that
interval down to the minute. Hourly sampling is fine even for the Moon (13
degrees a day) because nothing here moves fast enough to cross a boundary
twice in an hour.

Each event is a dict:
    when   datetime, UTC
    kind   'lunation' | 'ingress' | 'station' | 'aspect'
    body   the moving body (or the faster one, for aspects)
    plus kind-specific fields documented on each finder.
"""

from datetime import datetime, timedelta, timezone

import swisseph as swe

_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

_PLANETS = {
    'sun': swe.SUN, 'moon': swe.MOON, 'mercury': swe.MERCURY, 'venus': swe.VENUS,
    'mars': swe.MARS, 'jupiter': swe.JUPITER, 'saturn': swe.SATURN,
    'uranus': swe.URANUS, 'neptune': swe.NEPTUNE, 'pluto': swe.PLUTO,
}
_ORDER = list(_PLANETS)

# Only the Ptolemaic aspects; an e-ink panel has no room for minor ones.
ASPECTS = {0: 'conjunction', 60: 'sextile', 90: 'square', 120: 'trine', 180: 'opposition'}


def _jd(dt):
    dt = dt.astimezone(timezone.utc)
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute / 60 + dt.second / 3600)


def _dt(jd):
    y, m, d, h = swe.revjul(jd)
    return (datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)).replace(microsecond=0)


def _lon_speed(jd, body):
    r = swe.calc_ut(jd, _PLANETS[body], _FLAGS)[0]
    return r[0], r[3]


def _bisect(f, lo, hi, tol=1 / 1440):
    """Root of f between lo and hi (Julian days), where f changes sign."""
    flo = f(lo)
    while hi - lo > tol:
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm < 0) == (flo < 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def _wrap(x):
    """Angle folded into [-180, 180)."""
    return (x + 180) % 360 - 180


def upcoming_events(start=None, days=45):
    """All events in the window, sorted by time. `start` defaults to now (UTC)."""
    start = start or datetime.now(timezone.utc)
    jd0 = _jd(start)
    step = 1 / 24
    n = int(days / step) + 1
    grid = [jd0 + i * step for i in range(n)]

    # One pass over the ephemeris; every finder reads from these.
    lon = {b: [] for b in _PLANETS}
    spd = {b: [] for b in _PLANETS}
    for jd in grid:
        for b in _PLANETS:
            l, s = _lon_speed(jd, b)
            lon[b].append(l)
            spd[b].append(s)

    events = []
    events += _lunations(grid, lon)
    events += _ingresses(grid, lon)
    events += _stations(grid, spd)
    events += _aspects(grid, lon)
    events.sort(key=lambda e: e['when'])
    return events


def _lunations(grid, lon):
    """New and full Moons. Fields: phase ('new'|'full'), lon (Moon's longitude)."""
    out = []
    for target, phase in ((0, 'new'), (180, 'full')):
        def f(jd, t=target):
            return _wrap(_lon_speed(jd, 'moon')[0] - _lon_speed(jd, 'sun')[0] - t)
        prev = _wrap(lon['moon'][0] - lon['sun'][0] - target)
        for i in range(1, len(grid)):
            cur = _wrap(lon['moon'][i] - lon['sun'][i] - target)
            # A sign change that is a genuine crossing, not the +-180 wrap.
            if (prev < 0) != (cur < 0) and abs(cur - prev) < 180:
                jd = _bisect(f, grid[i - 1], grid[i])
                out.append({'when': _dt(jd), 'kind': 'lunation', 'body': 'moon',
                            'phase': phase, 'lon': _lon_speed(jd, 'moon')[0]})
            prev = cur
    return out


def _ingresses(grid, lon):
    """Sign changes. Fields: sign (entered, 0-11), retrograde (entering backwards)."""
    out = []
    for b in _PLANETS:
        for i in range(1, len(grid)):
            s0, s1 = int(lon[b][i - 1] // 30), int(lon[b][i] // 30)
            if s0 == s1:
                continue
            # Boundary crossed: the cusp of s1 going forward, or of s0 going back.
            forward = _wrap(lon[b][i] - lon[b][i - 1]) > 0
            cusp = (s1 if forward else s0) * 30
            jd = _bisect(lambda jd, c=cusp: _wrap(_lon_speed(jd, b)[0] - c),
                         grid[i - 1], grid[i])
            out.append({'when': _dt(jd), 'kind': 'ingress', 'body': b,
                        'sign': s1, 'retrograde': not forward})
    return out


def _stations(grid, spd):
    """Retrograde and direct stations. Fields: direction ('retrograde'|'direct'), lon."""
    out = []
    for b in _ORDER[2:]:               # Sun and Moon never station
        for i in range(1, len(grid)):
            if (spd[b][i - 1] < 0) == (spd[b][i] < 0):
                continue
            jd = _bisect(lambda jd: _lon_speed(jd, b)[1], grid[i - 1], grid[i])
            out.append({'when': _dt(jd), 'kind': 'station', 'body': b,
                        'direction': 'retrograde' if spd[b][i] < 0 else 'direct',
                        'lon': _lon_speed(jd, b)[0]})
    return out


def _aspects(grid, lon):
    """Exact Ptolemaic aspects. Fields: other, angle, lon (of `body`)."""
    out = []
    for ia, a in enumerate(_ORDER):
        for b in _ORDER[ia + 1:]:
            for angle in ASPECTS:
                # Separation minus the aspect angle, folded so exactness is a
                # zero crossing. For 0 and 180 the fold itself crosses at the
                # antipode, which the 180-jump filter below discards.
                diff = [_wrap(lon[a][i] - lon[b][i]) for i in range(len(grid))]
                for sign in ((1,) if angle in (0, 180) else (1, -1)):
                    prev = _wrap(diff[0] - sign * angle)
                    for i in range(1, len(grid)):
                        cur = _wrap(diff[i] - sign * angle)
                        if (prev < 0) != (cur < 0) and abs(cur - prev) < 180:
                            jd = _bisect(
                                lambda jd, t=sign * angle: _wrap(
                                    _lon_speed(jd, a)[0] - _lon_speed(jd, b)[0] - t),
                                grid[i - 1], grid[i])
                            out.append({'when': _dt(jd), 'kind': 'aspect', 'body': a,
                                        'other': b, 'angle': angle,
                                        'lon': _lon_speed(jd, a)[0]})
                        prev = cur
    return out


if __name__ == '__main__':
    import time
    t0 = time.time()
    for e in upcoming_events(days=45):
        print(e['when'].strftime('%b %d %H:%M'), e['kind'].ljust(8), e['body'].ljust(8),
              {k: (round(v, 2) if isinstance(v, float) else v)
               for k, v in e.items() if k not in ('when', 'kind', 'body')})
    print(f"{time.time() - t0:.1f}s")
