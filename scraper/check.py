#!/usr/bin/env python3
"""
Watchfinder New Arrivals Tracker
Scrapes watchfinder.co.uk/new-arrivals and sends notifications for new watches
"""

import json
import os
import sys
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup


# Configuration
WATCHFINDER_URL = "https://www.watchfinder.co.uk/new-arrivals"
STATE_FILE = "data/known_watches.json"
DASHBOARD_FILE = "docs/index.html"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
RETENTION_DAYS = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def load_known_watches() -> Dict:
    """Load previously seen watches from state file"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_known_watches(watches: Dict) -> None:
    """Save known watches to state file"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(watches, f, indent=2)


def prune_old_watches(watches: Dict) -> Dict:
    """Remove watches older than RETENTION_DAYS"""
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    pruned = {}
    for url, data in watches.items():
        try:
            first_seen = datetime.fromisoformat(data.get('first_seen', ''))
            if first_seen > cutoff_date:
                pruned[url] = data
        except (ValueError, TypeError):
            # Keep watches with invalid timestamps
            pruned[url] = data
    return pruned


def fetch_new_arrivals() -> Optional[str]:
    """Fetch the new arrivals page HTML"""
    try:
        # Add random delay to be polite
        time.sleep(random.uniform(1, 3))
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(WATCHFINDER_URL, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        return None


def parse_watches(html: str) -> List[Dict]:
    """Parse watch listings from HTML"""
    watches = []
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Watchfinder uses various selectors - try multiple patterns
        # Common patterns: product cards, watch tiles, etc.
        # We'll look for typical product listing patterns
        
        # Try finding product cards/tiles
        product_selectors = [
            'div.product-card',
            'div.watch-card',
            'article.product',
            'div.product-item',
            'li.product',
            'div[data-product-id]',
            'a[href*="/watch/"]',
        ]
        
        products = []
        for selector in product_selectors:
            products = soup.select(selector)
            if products:
                print(f"Found {len(products)} products using selector: {selector}")
                break
        
        # If no products found with specific selectors, try finding all links to watch pages
        if not products:
            products = soup.find_all('a', href=lambda h: h and '/watch/' in h)
            print(f"Found {len(products)} watch links")
        
        for product in products:
            try:
                watch = parse_single_watch(product, soup)
                if watch and watch.get('url'):
                    watches.append(watch)
            except Exception as e:
                print(f"Error parsing watch: {e}", file=sys.stderr)
                continue
        
        print(f"Successfully parsed {len(watches)} watches")
        
    except Exception as e:
        print(f"Error parsing HTML: {e}", file=sys.stderr)
    
    return watches


def parse_single_watch(element, soup) -> Optional[Dict]:
    """Parse a single watch element"""
    try:
        # Get URL
        url = None
        if element.name == 'a':
            url = element.get('href')
        else:
            link = element.find('a')
            if link:
                url = link.get('href')
        
        if not url:
            return None
        
        # Make URL absolute
        if url.startswith('/'):
            url = f"https://www.watchfinder.co.uk{url}"
        elif not url.startswith('http'):
            url = f"https://www.watchfinder.co.uk/{url}"
        
        # Get title/description
        title = None
        title_selectors = [
            element.find('h2'),
            element.find('h3'),
            element.find(class_=lambda c: c and ('title' in c.lower() or 'name' in c.lower())),
            element.find('a', href=lambda h: h and '/watch/' in h),
        ]
        
        for title_elem in title_selectors:
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    break
        
        if not title:
            # Try to get title from link text
            if element.name == 'a':
                title = element.get_text(strip=True)
        
        # Get price
        price = None
        price_selectors = [
            element.find(class_=lambda c: c and 'price' in c.lower()),
            element.find('span', class_=lambda c: c and 'price' in c.lower()),
            element.find(text=lambda t: t and '£' in t),
        ]
        
        for price_elem in price_selectors:
            if price_elem:
                if isinstance(price_elem, str):
                    price = price_elem.strip()
                else:
                    price = price_elem.get_text(strip=True)
                if price:
                    break
        
        # Get image
        image = None
        img_elem = element.find('img')
        if img_elem:
            image = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
            if image and image.startswith('//'):
                image = f"https:{image}"
            elif image and image.startswith('/'):
                image = f"https://www.watchfinder.co.uk{image}"
        
        # Only return if we have at least URL and title
        if url and title:
            return {
                'url': url,
                'title': title,
                'price': price or 'Price not available',
                'image': image or '',
                'first_seen': datetime.now().isoformat()
            }
        
        return None
        
    except Exception as e:
        print(f"Error parsing single watch: {e}", file=sys.stderr)
        return None


def send_notification(watch: Dict) -> bool:
    """Send notification via ntfy.sh"""
    if not NTFY_TOPIC:
        print("Warning: NTFY_TOPIC not set, skipping notification")
        return False
    
    try:
        ntfy_url = f"https://ntfy.sh/{NTFY_TOPIC}"
        
        headers = {
            'Title': watch['title'],
            'Tags': 'watch,new',
            'Priority': 'default',
        }
        
        # Add click action to open watch URL
        if watch.get('url'):
            headers['Click'] = watch['url']
        
        # Add image attachment
        if watch.get('image'):
            headers['Attach'] = watch['image']
        
        # Message body is the price
        message = watch.get('price', 'Price not available')
        
        response = requests.post(ntfy_url, data=message.encode('utf-8'), headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"Notification sent for: {watch['title']}")
        return True
        
    except Exception as e:
        print(f"Error sending notification: {e}", file=sys.stderr)
        return False


def generate_dashboard(known_watches: Dict, last_check: str) -> None:
    """Generate HTML dashboard for GitHub Pages"""
    
    # Sort watches by first_seen (most recent first)
    sorted_watches = sorted(
        known_watches.items(),
        key=lambda x: x[1].get('first_seen', ''),
        reverse=True
    )
    
    # Take last 50
    recent_watches = sorted_watches[:50]
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Watchfinder Tracker</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #2d3748;
            margin-bottom: 15px;
            font-size: 2.5em;
        }}
        
        .stats {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        
        .stat {{
            background: #f7fafc;
            padding: 15px 25px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .stat-label {{
            color: #718096;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        
        .stat-value {{
            color: #2d3748;
            font-size: 1.5em;
            font-weight: bold;
        }}
        
        .watches-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .watch-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex;
            flex-direction: column;
        }}
        
        .watch-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.15);
        }}
        
        .watch-image {{
            width: 100%;
            height: 250px;
            object-fit: cover;
            background: #f7fafc;
        }}
        
        .watch-info {{
            padding: 20px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }}
        
        .watch-title {{
            color: #2d3748;
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 10px;
            line-height: 1.4;
        }}
        
        .watch-price {{
            color: #667eea;
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .watch-date {{
            color: #a0aec0;
            font-size: 0.85em;
            margin-bottom: 15px;
        }}
        
        .watch-link {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            text-align: center;
            margin-top: auto;
            transition: background 0.2s;
        }}
        
        .watch-link:hover {{
            background: #5568d3;
        }}
        
        .no-image {{
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 3em;
        }}
        
        @media (max-width: 768px) {{
            h1 {{
                font-size: 1.8em;
            }}
            
            .stats {{
                gap: 15px;
            }}
            
            .watches-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⌚ Watchfinder Tracker</h1>
            <p>Tracking new arrivals from <a href="https://www.watchfinder.co.uk/new-arrivals" target="_blank" style="color: #667eea;">Watchfinder.co.uk</a></p>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Last Checked</div>
                    <div class="stat-value">{last_check}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Total Watches Tracked</div>
                    <div class="stat-value">{len(known_watches)}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Recent Additions</div>
                    <div class="stat-value">{len(recent_watches)}</div>
                </div>
            </div>
        </div>
        
        <div class="watches-grid">
"""
    
    for url, watch in recent_watches:
        image_html = ''
        if watch.get('image'):
            image_html = f'<img src="{watch["image"]}" alt="{watch["title"]}" class="watch-image">'
        else:
            image_html = '<div class="watch-image no-image">⌚</div>'
        
        # Format date nicely
        try:
            first_seen = datetime.fromisoformat(watch.get('first_seen', ''))
            date_str = first_seen.strftime('%B %d, %Y at %H:%M')
        except:
            date_str = watch.get('first_seen', 'Unknown')
        
        html += f"""
            <div class="watch-card">
                {image_html}
                <div class="watch-info">
                    <div class="watch-title">{watch['title']}</div>
                    <div class="watch-price">{watch['price']}</div>
                    <div class="watch-date">Added: {date_str}</div>
                    <a href="{url}" target="_blank" class="watch-link">View on Watchfinder</a>
                </div>
            </div>
"""
    
    html += """
        </div>
    </div>
</body>
</html>
"""
    
    os.makedirs(os.path.dirname(DASHBOARD_FILE), exist_ok=True)
    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Dashboard updated: {DASHBOARD_FILE}")


def main():
    """Main execution flow"""
    print(f"Starting Watchfinder check at {datetime.now().isoformat()}")
    
    # Load known watches
    known_watches = load_known_watches()
    initial_count = len(known_watches)
    print(f"Loaded {initial_count} known watches")
    
    # Check if this is the first run
    is_first_run = initial_count == 0
    
    # Fetch new arrivals
    html = fetch_new_arrivals()
    if not html:
        print("Failed to fetch page, exiting")
        sys.exit(1)
    
    # Parse watches
    current_watches = parse_watches(html)
    if not current_watches:
        print("Warning: No watches found on page. Site structure may have changed.")
        # Still update dashboard with current state
        last_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        generate_dashboard(known_watches, last_check)
        return
    
    print(f"Found {len(current_watches)} watches on page")
    
    # Detect new watches
    new_watches = []
    for watch in current_watches:
        url = watch['url']
        if url not in known_watches:
            new_watches.append(watch)
            known_watches[url] = watch
    
    print(f"Detected {len(new_watches)} new watches")
    
    # Send notifications for new watches (skip on first run to avoid spam)
    if not is_first_run:
        for watch in new_watches:
            send_notification(watch)
    else:
        print("First run detected - skipping notifications to avoid spam")
    
    # Prune old watches
    known_watches = prune_old_watches(known_watches)
    print(f"After pruning: {len(known_watches)} watches")
    
    # Save state
    save_known_watches(known_watches)
    print(f"State saved to {STATE_FILE}")
    
    # Generate dashboard
    last_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    generate_dashboard(known_watches, last_check)
    
    print(f"Check complete. New watches: {len(new_watches)}")


if __name__ == '__main__':
    main()
