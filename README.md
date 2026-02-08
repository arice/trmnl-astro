# TRMNL Astrology Chart

Displays current planetary positions on your TRMNL e-ink display. Fetches position data from a self-hosted Astrologer API, renders a custom wheel + legend chart, and serves it via GitHub Pages.

## Features

- **15-Minute Updates**: Automatically updates planetary positions via GitHub Actions
- **Custom Chart Rendering**: Clean wheel + legend layout optimized for e-ink
- **Self-Hosted API**: Uses your own Astrologer API (Kerykeion-based)
- **GitHub Pages**: Chart hosted publicly, no base64 encoding needed
- **Whole Sign Houses**: Traditional house system with ASC at 9 o'clock

## Prerequisites

1. **Self-hosted Astrologer API** running on your server
   - This project uses [Astrologer-API](https://github.com/g-battaglia/Astrologer-API), a REST API built on [Kerykeion](https://github.com/g-battaglia/kerykeion)
   - Should be accessible at `http://your-server:PORT`
   - Needs the `/api/v5/chart-data/birth-chart` endpoint
   - See [Astrologer-API setup instructions](https://github.com/g-battaglia/Astrologer-API#docker-deployment)

2. **TRMNL Account** with a custom plugin
   - Sign up at [usetrmnl.com](https://usetrmnl.com)
   - Create a custom plugin to get your `PLUGIN_UUID`
   - Get your API key from settings

3. **GitHub Account** with Pages enabled

## Setup Instructions

### 1. Fork/Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/trmnl-astro.git
cd trmnl-astro
```

### 2. Enable GitHub Pages

1. Go to repository **Settings** → **Pages**
2. Set **Source** to "Deploy from a branch"
3. Set **Branch** to `main` and folder to `/docs`
4. Save

Your chart will be served at: `https://YOUR_USERNAME.github.io/trmnl-astro/chart.png`

### 3. Set Up GitHub Secrets

Go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ASTROLOGER_API_URL` | Your Astrologer API endpoint | `http://123.456.78.90:27391` |
| `TRMNL_API_KEY` | Your TRMNL API key | `trmnl_xxxxxxxxxxxxx` |
| `PLUGIN_UUID` | Your TRMNL plugin UUID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `GH_USERNAME` | Your GitHub username | `arice` |
| `GH_REPO` | This repository name | `trmnl-astro` |

### 4. Create TRMNL Custom Plugin

1. Log into [TRMNL](https://usetrmnl.com)
2. Go to **Plugins** → **Create Custom Plugin**
3. Configure:
   - **Name**: Planetary Positions
   - **Strategy**: Webhook
   - **Markup**:

```html
<img src="{{chart_url}}" style="width:100%; height:100%;" />
```

4. Save and copy your **Plugin UUID**

### 5. Test

1. Go to **Actions** tab in your GitHub repository
2. Click **Update TRMNL Transit Chart** workflow
3. Click **Run workflow** → **Run workflow**
4. Check `docs/chart.png` and your TRMNL device

## Configuration

### Change Location

Edit `trmnl_astrology.py` and update `CHART_PAYLOAD`:

```python
CHART_PAYLOAD = {
    "subject": {
        "name": "Your City Now",
        "city": "New York",
        "nation": "US",
        "longitude": -74.0060,
        "latitude": 40.7128,
        "timezone": "America/New_York"
        # ... year/month/day/hour/minute are set automatically
    }
}
```

### Change Update Frequency

Edit `.github/workflows/hourly_update.yml`:

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes (current)
    # - cron: '0 * * * *'   # Every hour
    # - cron: '*/30 * * * *' # Every 30 minutes
```

## Project Structure

```
.
├── trmnl_astrology.py      # Main script: fetch, render, webhook
├── test_chart.py           # Local testing with mock data
├── CLAUDE.md               # AI assistant context
├── docs/
│   └── chart.png           # Output image (GitHub Pages)
└── .github/workflows/
    └── hourly_update.yml   # GitHub Actions workflow
```

## How It Works

1. **GitHub Actions** triggers every 15 minutes
2. **Python script** fetches position data from Astrologer API
3. **Custom renderer** creates SVG wheel + legend (800x480)
4. **CairoSVG** converts to B&W PNG for e-ink
5. **Git** commits and pushes to `docs/chart.png`
6. **GitHub Pages** serves the image publicly
7. **Webhook** notifies TRMNL with the image URL
8. **TRMNL** displays the chart on your e-ink screen

## Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests cairosvg pillow svgwrite

# Test with mock data (no API needed)
python test_chart.py
open test_chart.png
```

Note: Astrological glyphs may show as squares locally unless you install the Noto Sans Symbols 2 font.

## Troubleshooting

### Workflow failing?

Check the Actions tab for error logs:
- **API error 404**: Verify your API URL and that `/api/v5/chart-data/birth-chart` exists
- **TRMNL webhook error**: Verify API key and Plugin UUID
- **Font issues**: The workflow installs Noto Sans Symbols 2 automatically

### Chart not updating on TRMNL?

1. Check that GitHub Pages is enabled and serving `docs/chart.png`
2. Verify webhook strategy is set (not polling)
3. Pin the plugin to force immediate display
4. Check GitHub Actions logs for webhook response

### Glyphs showing as squares?

This is expected locally. In production (GitHub Actions), the workflow installs the required Noto Sans Symbols 2 font.

## Resources

- [Astrologer API](https://github.com/g-battaglia/Astrologer-API) by g-battaglia
- [Kerykeion](https://github.com/g-battaglia/kerykeion) - Python astrology library
- [TRMNL Documentation](https://docs.usetrmnl.com)

## License

MIT License
