# LEARNINGS

Gotchas only. Non-obvious constraints and mistakes worth not repeating.

## Testing chart designs

- **`docs/last_positions.json` used to shadow the live fetch.** Fixed 2026-09-12, but know
  the shape of it: `test_chart.py` only fell back to the Pages URL when that file was
  *missing* — and CI commits it, so it always existed locally and always won. The local copy
  was 186 days old; the Sun rendered in Pisces while the live sky had it in Virgo, a clean
  180° error with no warning. General lesson: when a fallback exists to keep data fresh,
  check whether the primary branch ever actually yields. Reading the code will not show it.

- **File mtime is not proof of fresh data.** `touch`, a fresh clone, and checking out an old
  commit all give a recent mtime over old content. `test_chart.py` therefore keeps a second,
  data-derived guard (`_sun_lon_now()`): it computes the Sun's true longitude and warns when
  the loaded positions disagree. Trust that warning over the mtime line above it.

- **The timestamp is `datetime.now()`, not the data's time.** A chart rendered from stale
  positions is still stamped with the current date/time, so a wrong-data render looks correct.
  Never sanity-check a test render by its footer.

- **Judge the design on the GitHub Pages PNG, not the local one.** Fonts differ: macOS resolves
  glyphs via Apple Symbols, CI via Noto Sans Symbols 2. Glyph widths and weights change, which
  moves label collisions around. The moon-phase emoji (U+1F311) renders as tofu (□) locally but
  as a real glyph in CI — an artifact of the font stack, not a bug to chase.

- **Collision behavior is data-dependent.** A layout that is clean on today's sky can overlap
  tomorrow. Test at least: live positions, `--fallback` (Saturn/Venus/Neptune stellium), and a
  case with a planet near the ASC (9 o'clock) and near the MC — both have special-cased
  displacement logic in the renderers.

## Design requests

- **"Make the glyphs 3x" is ambiguous - ask which glyphs.** This chart has three
  independent glyph classes: sign glyphs in the ring, planet labels on the wheel, and
  legend glyphs. 2026-09-12 I assumed "all of them", derived a hard geometric conflict
  (3x sign glyphs need a *bigger* wheel, since each gets one 12th of the ring arc), and
  presented it as a blocking constraint. Only the planet glyphs were meant; the sign ring
  at 16px needs 21px of arc and gets 31-42px even at half size, so there was no conflict
  at all. Signpost: when a scaling request names a term the codebase uses for several
  distinct things, ask before analysing. An unasked assumption that widens scope also
  invents constraints, and those constraints steer the user's decisions.

- **Aim a leader at the label, not at a radius along the label's ray.** Those coincide only
  when the label sits on its own ray. Compute the endpoint as "radius r along theta, pulled
  back a bit" and a sideways-displaced glyph at small radius makes `r - depth` fall below the
  rim, the clamp fires, and the line degenerates into a stub skimming the tick ring pointing
  tens of degrees away from the thing it labels (measured: 43 degrees off, ending 37px short).
  Draw from the tick toward the glyph's centre and stop at its box edge; the aim is then
  correct by construction, for free.

- **A leader line drawn unconditionally is mostly clutter.** Once placement got good, most
  glyphs sat on their exact ray touching the rim, and their "leader" was a stub joining a
  tick to a glyph already against it - over half the lines on a typical chart. Draw one only
  when the glyph is genuinely hard to attribute: off its ray by more than a few px, or far
  enough out that the eye needs help bridging. Dropped from 100% of labels to 46%.

- **The overlap audit must skip glyphs inside the ring.** They sit at fixed 30-degree
  spacing, so their clearance is an arc calculation, not a box one, and axis-aligned boxes
  clip corners on a circle without the ink ever touching. Raising sign glyphs to 32px made
  the audit report 138 phantom overlaps (real clearance: 6px). The filter used to key off
  font size, which silently stopped working the moment sign glyphs grew.

- **Glyph size buys placement quality superlinearly.** Dropping planet glyphs 58 -> 48px
  (a 17% trim, barely noticeable) took glyphs sitting at their exactly-true angle from 72%
  to 85% and mean drift from 3.3 to 1.1 degrees. A smaller label clears its neighbours at a
  nearer radius, so it is bumped outward less often, and each bump is what costs angle.
  Trim the label before reaching for a cleverer solver.

- **Order is a harder constraint than accuracy, and it is easy to lose.** A glyph drawn a
  few degrees off is a small error; a glyph drawn *before* one it actually comes after is a
  different chart. A greedy per-label search that lets each label roam +/-120 degrees will
  happily swap neighbours, and nothing in a drift metric detects it. Cut the cycle at its
  widest gap, unwrap to a line, and require placed angles to stay non-decreasing. Assert it
  in tests: sort by true angle and by drawn angle and check one is a cyclic rotation of the
  other. It cost 2.4 -> 3.1 degrees of mean drift and is worth far more than that.

- **Two placement ideas that measured as dead weight, both removed.** Shifting whole blocked
  runs to re-centre them: 3.20 vs 3.30 degrees, and a *worse* exact-angle rate, for ~50
  lines. Re-solving the angles with isotonic regression on top of the radial placement: the
  required-gap model assumes both labels share a radius, which is exactly what radial
  stacking exists to avoid, so it produced a cost-704 layout against the cost-121 one it was
  trying to improve and was rejected every single time. Measure before keeping cleverness.

- **Resolve label collisions radially, not tangentially.** Sliding a glyph sideways around
  the wheel destroys the one thing the wheel encodes: its angle. Pushing it outward along
  the *same ray* costs only depth and keeps the angle exact. Searching outward first and
  sliding sideways only as a last resort took glyphs at their exactly-correct angle from
  0% to 79%, and mean drift from 12.2 degrees to 2.4. `production.py` already did radial
  stacking; 2026-09-12 I replaced it with a tangential solver and had to be told the result
  looked wrong. Check what the existing code does before assuming a rewrite improves on it.

- **Optimising a metric is not the same as optimising the thing.** I minimised *angular*
  drift while letting labels drift outward to r=224 against an 87px rim. Angle improved and
  the chart got worse: at that radius 15 degrees is a 58px linear gap with a 136px leader
  line pointing across it. If a number says "better" and the picture says "worse", the
  metric is wrong - here it ignored radius entirely. Measure perceived error (linear
  offset, leader length), not just the component that is easy to compute.

- **In greedy placement, order is priority.** Whoever is placed first gets its exact spot.
  ASC/MC were being placed last and ended up 18 degrees off - unacceptable for the chart's
  reference axes. Place the must-be-exact items first, then the most constrained.

- **Always give a placement search a no-overlap fallback ladder.** The give-up branch that
  dumped a label at its true angle regardless of collisions was the entire source of a 1.2%
  overlap rate. Retrying the whole search with zero padding before giving up took it to 0%.

- **Two radial tiers do not fit this panel, at any wheel size.** Measured 2026-09-12: the
  wheel occupies r<95 and the panel edge sits at 158-176 on the left and right, so there is
  13px of radial depth where two side-by-side labels need ~98px. Shrinking the wheel does
  not rescue it - two such labels stacked radially need ~216px and the panel offers 212px
  from centre to edge, wheel or no wheel. Tiers only become feasible below ~39px glyphs,
  where drift is already low enough not to need them.

- **Inscribing an ellipse in a rectangular panel throws away four corners.** Worth knowing
  in general: check whether the placement *region* is leaving free space before reaching
  for a cleverer algorithm. (Superseded here - the ring-and-arc-length approach was
  replaced wholesale by the 2D radial-first search below.)

- **Watch for redundancy between wheel and legend.** The wheel repeated each planet's
  whole degree, which the legend already gives to the arcminute. Dropping it shrank the
  label footprint by more than half and bought ~9px of glyph at equal accuracy.

- **Uniform label gaps are wrong on a ring when labels are not square.** A side-by-side
  label is 106x48; a stacked one is 56x80. How much ring a label consumes depends on the
  direction the ring runs beneath it, so the gap has to be per-label:
  `|tangent.x| * half_width + |tangent.y| * half_height`. A uniform gap tuned for the
  axes fails on the diagonals, which is where every collision showed up.

- **Reserve space for the layout you actually draw.** The worst collision source was an
  off-by-one-iteration bug: orientation was chosen from the placement *before* the final
  solve, so a label could be drawn side-by-side (106px) in a gap reserved for its stacked
  form (56px). Iterate orientation and placement to agreement, and if they will not
  settle, re-solve using the layout that will be drawn.

- **Fitting demand to the room beats overflowing then compressing.** Linearly squeezing an
  over-capacity ring silently violates the gaps just solved for. Give back padding first,
  scale the labels only if zero padding still will not fit. This also removed a bizarre
  non-monotonic relationship where more padding produced *more* overlaps.

- **Validate layout against thousands of synthetic skies, not two.** `scratchpad/audit.py`
  parses the SVG's text elements, measures real glyph boxes with PIL, and checks bounds
  and pairwise overlap over N random skies with forced stelliums. It found 247 overlaps
  that eyeballing two charts had missed. Watch the audit's own bugs though: initialising a
  running `min` at 0 reports a reassuring "leftmost = 0.0" no matter what the data says.

## Fonts

- **The workflow's font download 404'd for the life of the project, silently.** `curl -L -o
  x.ttf <url>` writes the 9-byte "Not Found" body to the .ttf on failure, `fc-cache` skips the
  unreadable file, and rendering falls through to whatever is left in the stack. Nothing errors.
  Every chart CI ever published was drawn in DejaVu Sans, not the font the workflow named. Any
  build-time asset fetch needs a verification step - the workflow now greps `fc-list` and exits
  non-zero. Better still: the font is vendored in `fonts/`, so there is no fetch to fail.

- **Noto Sans Symbols 2 does not contain the zodiac or the planets.** Those live in
  Miscellaneous Symbols (U+2600-26FF), covered by *Noto Sans Symbols* - a different font. So
  the workflow was fetching the wrong font from a dead URL. Faces that do cover the set:
  DejaVu Sans, Apple Symbols, Arial Unicode, STIX Two Math, Astronomicon.

- **Astronomicon maps symbols onto ASCII letters, not Unicode.** `A`-`L` signs, `Q`-`Z`
  Sun-Pluto, `M` retrograde, `c`/`d` for AC/MC. So it can never appear in a font stack that
  also draws text - point it at the timestamp and the date becomes planets. This is why
  `GLYPH_FONT` and `TEXT_FONT` are separate in `dev.py`; before that split, degree strings and
  the footer were drawn in the symbol font, which was harmless with Unicode faces and would
  have been nonsense here.

- **Installing a font's regular face is not installing the font.** `font-weight="bold"` on a
  machine with only `DejaVuSans.ttf` silently renders regular; CI has the whole family and
  renders real bold, which is ~15% wider. That difference alone pushed the centred legend
  header into the moon glyph on the live chart while the local copy looked fine. Install every
  weight the renderer asks for, and prefer layouts that cannot break on a width change - the
  header is now anchored from the left rather than centred, so the gap is fixed whatever the
  face does.

- **Read a symbol font's character map, do not guess it.** Render the printable ASCII range in
  a labelled grid and look at it. The vendor page's own description had the planets in a
  different order than the font does.

- **Check glyph coverage by comparing against a known-absent codepoint.** A missing glyph
  renders as `.notdef` with a nonzero width, so `getbbox(ch)[2] > 0` reports every character
  as present. Render `chr(0xE000)` and compare bitmaps instead. Two of my coverage checks gave
  confidently wrong answers before this.

- **The layout audit must measure each element with the face the SVG names.** Measuring an
  Astronomicon `Q` with a text font gives the width of the letter Q, not of the Sun glyph - a
  wrong audit that reports clean.

## Data

- **The API returns 12 bodies, not 14.** `config.yaml` lists `mean_north_lunar_node` and
  `mean_south_lunar_node`, but the Astrologer response omits them, so renderers silently skip
  them. (CLAUDE.md's "all 13 bodies" is also wrong.) Don't debug missing nodes in the renderer.

## Workflow

- Test PNGs (`test_chart_*.png`) are gitignored — they will never show in `git status`.
- CI commits chart PNGs every 5 minutes, so the remote is almost always ahead. Always
  `git pull --rebase` before pushing.
- `gh workflow run "Update TRMNL Transit Chart"` forces an immediate CI render instead of
  waiting for the next cron tick. Note it also pushes a webhook to the live TRMNL device.
- **`docs/` is the GitHub Pages publish root.** Anything dropped there — dev logs included —
  is served publicly at `arice.github.io/trmnl-astro/`. It is not a private docs folder.
