# TRMNL Astrology Transit Chart

Automatically updates your TRMNL e-ink display with hourly astrological transit charts from a self-hosted Astrologer API.

## 🌟 Features

- **Hourly Updates**: Automatically fetches and displays current planetary transits every hour
- **Self-Hosted**: Uses your own Astrologer API running on Digital Ocean
- **E-ink Optimized**: Converts SVG charts to 800x480 PNG perfect for TRMNL displays
- **GitHub Actions**: Fully automated via GitHub Actions (free, no server needed)

## 📋 Prerequisites

1. **Self-hosted Astrologer API** running on your Digital Ocean droplet
   - Should be accessible at `http://your-droplet-ip:8000`
   - Port 8000 should be open in your firewall
   
2. **TRMNL Account** with a custom plugin created
   - Sign up at [usetrmnl.com](https://usetrmnl.com)
   - Create a custom plugin to get your `PLUGIN_UUID`
   - Get your API key from settings

3. **GitHub Account** (free)

## 🚀 Setup Instructions

### 1. Fork/Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/trmnl-astrology.git
cd trmnl-astrology
```

Or click "Fork" in GitHub to create your own copy.

### 2. Set Up GitHub Secrets

Go to your repository settings → Secrets and variables → Actions → New repository secret

Add these three secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `ASTROLOGER_API_URL` | Your Astrologer API endpoint | `http://123.456.78.90:8000` |
| `TRMNL_API_KEY` | Your TRMNL API key | `trmnl_xxxxxxxxxxxxx` |
| `PLUGIN_UUID` | Your TRMNL plugin UUID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |

### 3. Create TRMNL Custom Plugin

1. Log into [TRMNL](https://usetrmnl.com)
2. Go to **Plugins** → **Create Custom Plugin**
3. Set up your plugin:
   - **Name**: Astrology Transits
   - **Strategy**: Webhook
   - **Markup**: Use this template:

```html
<div class="w-full h-full flex items-center justify-center bg-white">
  <img src="{{ transit_chart }}" alt="Transit Chart" class="w-full h-full object-contain" />
</div>
```

4. **Merge Variables**: Add `transit_chart` (type: image/base64)
5. Copy your **Plugin UUID** and **API Key**

### 4. Push to GitHub

```bash
git add .
git commit -m "Initial setup"
git push origin main
```

The workflow will automatically run every hour! 🎉

### 5. Test Manually

You can test immediately without waiting for the hourly cron:

1. Go to **Actions** tab in your GitHub repository
2. Click **Update TRMNL Transit Chart** workflow
3. Click **Run workflow** → **Run workflow**
4. Watch the logs to verify it works

## 🔧 Configuration

### Change Location

Edit `trmnl_astrology.py` and update the location:

```python
TRANSIT_PAYLOAD = {
    "subject": {
        # ... other fields ...
        "city": "New York",
        "nation": "US",
        "longitude": -74.0060,  # Your longitude
        "latitude": 40.7128,    # Your latitude
        "timezone": "America/New_York"
    }
}
```

### Change Update Frequency

Edit `.github/workflows/hourly_update.yml`:

```yaml
on:
  schedule:
    - cron: '0 * * * *'  # Every hour
    # - cron: '*/30 * * * *'  # Every 30 minutes
    # - cron: '0 0 * * *'  # Daily at midnight
```

## 📁 Project Structure

```
.
├── trmnl_astrology.py          # Main Python script
├── .github/
│   └── workflows/
│       └── hourly_update.yml   # GitHub Actions workflow
└── README.md                   # This file
```

## 🔍 How It Works

1. **GitHub Actions** triggers the workflow hourly (via cron schedule)
2. **Python script** calls your self-hosted Astrologer API with current timestamp
3. **API returns** SVG chart of current planetary transits
4. **Script converts** SVG → PNG (800x480) and base64 encodes it
5. **Webhook sends** image to TRMNL plugin
6. **TRMNL displays** updated chart on your e-ink screen

## 🐛 Troubleshooting

### Workflow failing?

Check the Actions tab for error logs:
- **API not reachable**: Verify droplet IP, port 8000 is open (`sudo ufw status`)
- **TRMNL webhook error**: Verify API key and Plugin UUID
- **Conversion error**: Usually a cairosvg dependency issue (auto-installed)

### API not responding?

SSH into your droplet and check:

```bash
# Is Docker running?
docker ps

# Check API logs
docker logs astrologer-api

# Test API locally
curl http://localhost:8000/api/v5/chart/birth-chart \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"subject": {"name": "Test", "year": 1990, "month": 1, "day": 1, "hour": 12, "minute": 0, "city": "London", "nation": "GB", "longitude": -0.1278, "latitude": 51.5074, "timezone": "Europe/London"}}'
```

### TRMNL not updating?

1. Check your plugin settings in TRMNL dashboard
2. Verify the webhook URL is correct
3. Look at GitHub Actions logs for webhook response
4. Try manually triggering the workflow

## 📊 API Costs

- **GitHub Actions**: Free (2,000 minutes/month on free tier, this uses ~1 min/day)
- **Digital Ocean Droplet**: Your existing droplet (no additional cost)
- **Astrologer API**: Self-hosted (free, open source)
- **TRMNL**: Your existing plan

**Total additional cost: $0** ✨

## 🎨 Customization Ideas

- Display birth chart instead of transits
- Show multiple charts (natal + transits)
- Add text overlay with key transits
- Custom color schemes for e-ink optimization
- Daily aspect notifications

## 📚 Resources

- [Astrologer API Documentation](https://github.com/g-battaglia/Astrologer-API)
- [TRMNL Documentation](https://docs.usetrmnl.com)
- [GitHub Actions Cron Syntax](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)

## 📄 License

MIT License - feel free to use and modify!

## 🙏 Credits

- [Astrologer API](https://github.com/g-battaglia/Astrologer-API) by g-battaglia
- [Kerykeion](https://github.com/g-battaglia/kerykeion) - Python astrology library
- [TRMNL](https://usetrmnl.com) - E-ink display platform

---

Made with ✨ and ♐️ by [Your Name]
