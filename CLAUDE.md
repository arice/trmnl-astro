# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a TRMNL e-ink display integration that shows astrological charts. It fetches planetary position data from a self-hosted Astrologer API, renders a custom wheel + legend chart optimized for e-ink, and hosts it via GitHub Pages for TRMNL to display.

## Architecture

```
GitHub Actions (every 5 min)
    ↓
trmnl_astrology.py
    ├── Calls Astrologer API /api/v5/chart-data/birth-chart → Gets JSON position data
    ├── renderers/production.py → Production chart SVG (800x480)
    ├── renderers/dev.py → Development chart SVG (for iteration)
    ├── svg_to_png_grayscale() → Converts to 4-level grayscale PNG for e-ink
    ├── Saves to docs/chart.png (production) + docs/dev-chart.png (dev)
    └── Sends webhook to TRMNL with production chart URL
    ↓
Git commits & pushes both charts
    ↓
GitHub Pages serves both charts
    ↓
TRMNL fetches and displays production chart
```

## Key Files

- `trmnl_astrology.py` - Main script: fetches positions, renders both charts, sends webhook
- `renderers/` - Chart rendering modules
  - `base.py` - Shared glyphs, colors, and utilities
  - `production.py` - Stable production renderer (used by TRMNL)
  - `dev.py` - Development sandbox for iterating on new designs
- `.github/workflows/hourly_update.yml` - GitHub Actions workflow (runs every 5 minutes)
- `docs/chart.png` - Production image served via GitHub Pages
- `docs/dev-chart.png` - Development image for iteration (also on GitHub Pages)
- `test_chart.py` - Local testing with mock data (run in venv)

## Chart Rendering Details

The renderers create custom astrological wheel charts:

**Layout (800x480):**
- Left side: Zodiac wheel (center at 220, 240)
- Right side: Legend panel with all 13 bodies + degrees

**Wheel structure:**
- `outer_r` (175): Outer edge of sign ring
- `inner_r` (150): Inner edge of sign ring
- `sign_glyph_r` (163): Sign glyphs centered in ring
- `planet_r` (125): Combined planet glyph + degree labels (e.g., "☉19°") inside wheel
- `degree_r` (195): Used only for ASC/MC label positioning outside wheel
- Tick marks on inner ring pointing inward

**Key features:**
- Ascendant always at 9 o'clock (wheel rotates)
- Combined labels: glyph + degree in single label (e.g., "☉19°") with thin space (U+2009)
- Improved collision avoidance: `has_collision()` with while loop finds truly clear spots
- Radial stacking: labels move inward to avoid overlaps
- Whole sign houses (12 equal divisions)
- Font stack: Apple Symbols (macOS), Noto Sans Symbols 2 (CI), DejaVu Sans (fallback)
- Retrograde indicator uses ℞ glyph (U+211E)

## Running Locally

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests cairosvg pillow svgwrite pyyaml

# Run test with mock data (no API needed)
python test_chart.py
open test_chart_prod.png test_chart_dev.png

# Note: On macOS, glyphs render via Apple Symbols font
# On Linux/CI, Noto Sans Symbols 2 is installed by workflow
```

## Development Workflow

To iterate on chart designs without affecting production:

1. Edit `renderers/dev.py` - this is your sandbox
2. Run `python test_chart.py` to generate both charts locally
3. Compare `test_chart_prod.png` (production) with `test_chart_dev.png` (your changes)
4. When happy, copy your changes from `dev.py` to `production.py`

The dev chart is also published to GitHub Pages at:
`https://<username>.github.io/<repo>/dev-chart.png`

## Required GitHub Secrets

- `ASTROLOGER_API_URL` - Astrologer API endpoint (e.g., http://your-droplet:27391)
- `TRMNL_API_KEY` - TRMNL API key
- `PLUGIN_UUID` - TRMNL plugin UUID
- `GH_USERNAME` - GitHub username (for Pages URL)
- `GH_REPO` - Repository name (for Pages URL)

## Configuration

**Location:** Set in `trmnl_astrology.py` in `CHART_PAYLOAD` (currently Philadelphia). Update `city`, `nation`, `longitude`, `latitude`, and `timezone` to change location.

**Schedule:** Set in `.github/workflows/hourly_update.yml` cron expression (currently every 15 minutes).

**TRMNL Plugin:** Uses webhook strategy. Markup should be:
```html
<img src="{{chart_url}}" style="width:100%; height:100%;" />
```

## API Reference

The Astrologer API endpoint `/api/v5/chart-data/birth-chart` returns:
```json
{
  "status": "OK",
  "chart_data": {
    "subject": {
      "sun": {"abs_pos": 319.5, "sign_num": 10, "position": 19.5, ...},
      "moon": {"abs_pos": 216.1, "sign_num": 7, "position": 6.1, ...},
      ...
      "ascendant": {"abs_pos": 245.0, ...},
      "medium_coeli": {"abs_pos": 171.3, ...}
    }
  }
}
```

Key fields per body:
- `abs_pos`: Absolute longitude (0-360)
- `sign_num`: Sign index (0-11)
- `position`: Degrees within sign (0-30)
