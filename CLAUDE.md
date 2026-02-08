# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a TRMNL e-ink display integration that shows astrological charts. It fetches planetary position data from a self-hosted Astrologer API, renders a custom wheel + legend chart optimized for e-ink, and hosts it via GitHub Pages for TRMNL to display.

## Architecture

```
GitHub Actions (every 15 min)
    ↓
trmnl_astrology.py
    ├── Calls Astrologer API /api/v5/chart-data/birth-chart → Gets JSON position data
    ├── render_chart_svg() → Custom wheel + legend SVG (800x480)
    ├── svg_to_png_bw() → Converts to B&W PNG for e-ink
    ├── Saves to docs/chart.png
    └── Sends webhook to TRMNL with GitHub Pages URL
    ↓
Git commits & pushes docs/chart.png
    ↓
GitHub Pages serves chart.png
    ↓
TRMNL fetches and displays image
```

## Key Files

- `trmnl_astrology.py` - Main script: fetches positions, renders chart, sends webhook
- `.github/workflows/hourly_update.yml` - GitHub Actions workflow (runs every 15 minutes)
- `docs/chart.png` - Output image served via GitHub Pages
- `test_chart.py` - Local testing with mock data (run in venv)

## Chart Rendering Details

The `render_chart_svg()` function creates a custom astrological wheel:

**Layout (800x480):**
- Left side: Zodiac wheel (center at 220, 240)
- Right side: Legend panel with all 14 bodies + degrees

**Wheel structure:**
- `outer_r` (175): Outer edge of sign ring
- `inner_r` (150): Inner edge of sign ring
- `sign_glyph_r` (163): Sign glyphs centered in ring
- `planet_r` (115): Planet glyphs inside wheel
- `degree_r` (195): Degree labels outside wheel
- Tick marks on inner ring pointing inward

**Key features:**
- Ascendant always at 9 o'clock (wheel rotates)
- Radial collision avoidance (planets stack inward, not angularly)
- Whole sign houses (12 equal divisions)
- Uses Noto Sans Symbols 2 font for glyphs (installed in workflow)

## Running Locally

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests cairosvg pillow svgwrite

# Run test with mock data (no API needed)
python test_chart.py
open test_chart.png

# Note: Astrological glyphs may show as squares locally
# unless you install Noto Sans Symbols 2 font
```

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
