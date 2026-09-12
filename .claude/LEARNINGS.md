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
