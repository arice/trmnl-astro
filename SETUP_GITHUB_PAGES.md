# TRMNL Astrology Setup - GitHub Pages Solution

---

## Setup Steps

### 1. Enable GitHub Pages

1. Go to your repo: `https://github.com/YOUR-USERNAME/trmnl-astro`
2. **Settings** → **Pages**
3. **Source**: Deploy from a branch
4. **Branch**: `main` (or `master`)
5. **Folder**: `/docs`
6. Click **Save**

Your site will be at: `https://YOUR-USERNAME.github.io/trmnl-astro/`

---

### 2. Add GitHub Secrets

Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add these **5 secrets**:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `ASTROLOGER_API_URL` | Your API endpoint | `http://123.456.78.90:8000` |
| `TRMNL_API_KEY` | Your TRMNL API key | `trmnl_xxxxxxxxxxxxx` |
| `PLUGIN_UUID` | Your TRMNL plugin UUID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `GITHUB_USERNAME` | Your GitHub username | `arice` |
| `GITHUB_REPO` | Your repo name | `trmnl-astro` |

---

### 3. Update TRMNL Plugin Markup

Go to TRMNL → Your Private Plugin → **Edit Markup**

Paste this:

```html
<div class="w-full h-full flex items-center justify-center bg-white">
  <img src="{{ chart_url }}" alt="Astrology Chart" class="w-full h-full object-contain" />
</div>
```

**Variable name**: `chart_url` (not `transit_chart`)

---

### 4. Update Your Repo

Replace these files in your GitHub repo:

1. **`trmnl_astrology.py`** - Main script
2. **`.github/workflows/hourly_update.yml`** - Workflow

Create a `docs/` folder:
```bash
mkdir docs
touch docs/.gitkeep
git add docs/.gitkeep
git commit -m "Add docs folder for GitHub Pages"
git push
```

---

### 5. Test It!

1. Go to **Actions** tab in your GitHub repo
2. Click **Update TRMNL Transit Chart**
3. Click **Run workflow** → **Run workflow**
4. Wait ~1 minute
5. Check the logs

After the first run, your chart will be at:
```
https://YOUR-USERNAME.github.io/trmnl-astro/chart.png
```

---

## How It Works

```
Every 15 minutes:
├─ GitHub Actions runs
├─ Python script:
│  ├─ Fetches chart from your Astrologer API
│  ├─ Converts to B&W PNG (~10KB)
│  └─ Saves to docs/chart.png
├─ Git commits the PNG
├─ Git pushes to GitHub
├─ Sends tiny webhook to TRMNL (~100 bytes):
│  └─ { "chart_url": "https://..." }
└─ TRMNL fetches image from GitHub Pages
```

**Webhook payload**: ~100 bytes ✓  
**2KB limit**: No problem! ✓

---

## Troubleshooting

### "Chart not updating on TRMNL"
- Check GitHub Actions logs for errors
- Verify GitHub Pages is enabled
- Try `https://YOUR-USERNAME.github.io/trmnl-astro/chart.png` in browser

### "Image shows old chart"
- GitHub Pages can cache for a few minutes
- The `?t=timestamp` in the URL forces refresh
- TRMNL should show new image within ~5 minutes

### "Workflow fails at commit step"
- Make sure Actions has write permissions:
  - Settings → Actions → General → Workflow permissions
  - Select "Read and write permissions"
  - Save

### "API timeout"
- Check your Astrologer API is running: `docker ps`
- Test it manually: `curl http://YOUR-IP:8000`

---

## Files Needed

Upload to your repo:

1. **`trmnl_astrology.py`** - Main script
2. **`.github/workflows/hourly_update.yml`** - Workflow file
3. **`docs/.gitkeep`** - Empty file to create docs/ folder

---

## Why This Works

- ✅ **Free** (GitHub Pages, GitHub Actions)
- ✅ **Secure** (no SSH keys, no upload endpoints)
- ✅ **Simple** (just Git)
- ✅ **Under 2KB** (sends URL, not image)
- ✅ **Reliable** (GitHub's infrastructure)

Who cares about commit history? You get a working astrology display! 🌟

---

Good luck!
