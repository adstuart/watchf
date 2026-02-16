# ⌚ Watchfinder Tracker

A simple, automated tool that tracks new arrivals on [Watchfinder.co.uk](https://www.watchfinder.co.uk/new-arrivals) and sends instant push notifications to your phone for every new watch listed.

## 🎯 What It Does

- **Monitors** Watchfinder's new arrivals page every 5 minutes
- **Detects** newly listed watches automatically
- **Sends** rich push notifications with thumbnail, description, and price
- **Displays** a beautiful dashboard of recent watches via GitHub Pages
- **Runs** entirely on GitHub (no servers needed!)

## 🏗️ Architecture

```
┌─────────────────────┐
│  GitHub Actions     │  ← Runs every 5 minutes (cron schedule)
│  (Compute Engine)   │     Executes Python scraper
└──────────┬──────────┘
           │
           ├──→ Scrapes Watchfinder.co.uk
           ├──→ Compares with known watches (stored in repo)
           ├──→ Sends notifications via Ntfy.sh (push to phone)
           ├──→ Updates dashboard HTML
           └──→ Commits changes back to repo
                      │
                      ├──→ data/known_watches.json (state)
                      └──→ docs/index.html (dashboard)
                                    │
                                    ↓
                          ┌──────────────────┐
                          │  GitHub Pages    │
                          │  (Dashboard)     │
                          └──────────────────┘
```

## 🚀 Setup Instructions

### 1. Fork/Clone This Repository

```bash
git clone https://github.com/YOUR-USERNAME/watchf.git
cd watchf
```

### 2. Create a Free Ntfy.sh Topic

Ntfy.sh provides free, no-account push notifications.

1. Choose a unique topic name (e.g., `watchfinder-yourname-2026`)
2. **On your phone**, install the [Ntfy app](https://ntfy.sh):
   - iOS: [App Store](https://apps.apple.com/app/ntfy/id1625396347)
   - Android: [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy) or [F-Droid](https://f-droid.org/packages/io.heckel.ntfy/)
3. Open the app and subscribe to your topic (e.g., `watchfinder-yourname-2026`)
4. That's it! You'll now receive push notifications on this topic.

### 3. Add GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add a secret:
   - Name: `NTFY_TOPIC`
   - Value: Your chosen topic name (e.g., `watchfinder-yourname-2026`)

### 4. Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. Click **"I understand my workflows, go ahead and enable them"**
3. The workflow will now run automatically every 5 minutes

### 5. Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Under **Source**, select:
   - **Deploy from a branch**
   - Branch: `main`
   - Folder: `/docs`
3. Click **Save**
4. Your dashboard will be available at: `https://YOUR-USERNAME.github.io/watchf/`

### 6. Test Manually (Optional)

You can trigger the workflow manually to test:

1. Go to **Actions** tab
2. Select **"Check Watchfinder New Arrivals"** workflow
3. Click **Run workflow** → **Run workflow**
4. Watch the workflow execute in real-time

## 📱 Using the Tracker

### Receiving Notifications

Once set up, you'll automatically receive push notifications on your phone when:
- A new watch is listed on Watchfinder
- The notification includes:
  - **Title**: Watch brand and model
  - **Message**: Price
  - **Image**: Watch thumbnail
  - **Click action**: Tap to open the watch page on Watchfinder

### Viewing the Dashboard

Visit your GitHub Pages URL to see:
- Last check timestamp
- Total number of watches tracked
- Grid of the 50 most recent arrivals with images, prices, and links

Example: `https://YOUR-USERNAME.github.io/watchf/`

## 🛠️ How It Works

### Scraper (`scraper/check.py`)

The Python scraper:
1. Fetches the Watchfinder new arrivals page with proper headers
2. Parses HTML with BeautifulSoup to extract watch data (title, price, image, URL)
3. Compares against `data/known_watches.json` to detect new watches
4. Sends notifications via Ntfy.sh for new watches (skips on first run)
5. Updates the state file and regenerates the dashboard HTML
6. Prunes watches older than 30 days to keep the state file manageable

### State Management

- `data/known_watches.json` stores all seen watches as:
  ```json
  {
    "https://watchfinder.co.uk/watch-url": {
      "title": "Rolex Submariner",
      "price": "£8,950",
      "image": "https://...",
      "first_seen": "2026-02-16T12:34:56"
    }
  }
  ```
- Automatically prunes entries older than 30 days
- On first run, treats all watches as "already seen" to avoid notification spam

### Dashboard (`docs/index.html`)

- Auto-generated on each run
- Clean, responsive design with inline CSS
- Shows the 50 most recent watches in a card grid
- No external dependencies or frameworks

## 🔧 Customization

### Change Check Frequency

Edit `.github/workflows/check.yml`:
```yaml
schedule:
  - cron: '*/5 * * * *'  # Every 5 minutes
  # - cron: '*/10 * * * *'  # Every 10 minutes
  # - cron: '0 * * * *'     # Every hour
```

### Change Retention Period

Edit `scraper/check.py`:
```python
RETENTION_DAYS = 30  # Change to any number of days
```

### Multiple Topics

You can subscribe to multiple Ntfy topics on your phone if you want to:
- Separate notifications for different users
- Have both a main topic and a test topic

## 🐛 Troubleshooting

### No Notifications Received

1. Check that `NTFY_TOPIC` secret is set correctly
2. Verify you're subscribed to the same topic in the Ntfy app
3. Check the Actions workflow logs for errors
4. Test by sending a manual notification:
   ```bash
   curl -d "Test" https://ntfy.sh/YOUR-TOPIC
   ```

### No Watches Found

- The scraper logs "Warning: No watches found" if the page structure changed
- Check the Actions workflow logs for details
- The site may be temporarily down or blocking requests

### Dashboard Not Updating

1. Verify GitHub Pages is enabled and set to `/docs` folder
2. Check that `docs/index.html` was committed to the repo
3. GitHub Pages can take a few minutes to update after a commit

### Workflow Not Running

1. Ensure Actions are enabled in your repository settings
2. Check that the workflow file is in `.github/workflows/check.yml`
3. GitHub has a limit on scheduled workflow frequency; it may have slight delays

## 📦 Dependencies

- `requests` - HTTP library for fetching web pages
- `beautifulsoup4` - HTML parsing and extraction
- `lxml` - Fast XML/HTML parser for BeautifulSoup

## 🤝 Contributing

This is a simple personal project, but feel free to:
- Report issues if Watchfinder changes their page structure
- Suggest improvements
- Fork and adapt for other watch retailers

## 📄 License

This project is provided as-is for educational and personal use. Be respectful of Watchfinder's website and follow their terms of service.

## ⚠️ Disclaimer

This tool is not affiliated with or endorsed by Watchfinder. Use responsibly and don't overwhelm their servers. The scraper includes random delays and proper headers to be polite.