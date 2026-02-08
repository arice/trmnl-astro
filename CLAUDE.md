# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a TRMNL e-ink display integration that shows astrological transit charts. It fetches charts from a self-hosted Astrologer API, converts them to e-ink optimized PNG images, and hosts them via GitHub Pages for TRMNL to display.

## Architecture

```
GitHub Actions (every 15 min)
    ↓
trmnl_astrology.py
    ├── Calls Astrologer API → Gets SVG chart
    ├── Converts SVG → B&W PNG (800x480)
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

- `trmnl_astrology.py` - Main script that fetches chart, converts to PNG, sends webhook
- `.github/workflows/hourly_update.yml` - GitHub Actions workflow (runs every 15 minutes)
- `docs/chart.png` - Output image served via GitHub Pages

## Running Locally

```bash
# Install dependencies
pip install requests cairosvg pillow

# Set required environment variables
export ASTROLOGER_API_URL="http://your-droplet-ip:8000"
export TRMNL_API_KEY="your-key"
export PLUGIN_UUID="your-uuid"
export GH_USERNAME="your-github-username"
export GH_REPO="trmnl-astro"

# Run
python trmnl_astrology.py
```

## Required GitHub Secrets

- `ASTROLOGER_API_URL` - Astrologer API endpoint
- `TRMNL_API_KEY` - TRMNL API key
- `PLUGIN_UUID` - TRMNL plugin UUID
- `GH_USERNAME` - GitHub username (for Pages URL)
- `GH_REPO` - Repository name (for Pages URL)

## Configuration

Location is set in `trmnl_astrology.py` in `CHART_PAYLOAD` (currently Philadelphia). Update `city`, `nation`, `longitude`, `latitude`, and `timezone` to change location.

Schedule is set in `.github/workflows/hourly_update.yml` cron expression (currently every 15 minutes).
