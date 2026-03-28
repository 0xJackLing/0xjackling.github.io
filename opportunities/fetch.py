#!/usr/bin/env python3
"""
Fetch Web3 & AI opportunities from multiple platforms.
Outputs opportunities.json for the dashboard.
"""

import json
import re
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from html.parser import HTMLParser

DATA_FILE = os.path.join(os.path.dirname(__file__), 'opportunities.json')


def fetch_url(url, timeout=30):
    """Fetch URL content as string."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; OpportunityBot/1.0)',
        'Accept': 'application/json, text/html, */*',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def fetch_json(url, timeout=30):
    """Fetch and parse JSON from URL."""
    text = fetch_url(url, timeout)
    if text:
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  [WARN] Invalid JSON from {url}: {e}", file=sys.stderr)
    return None


# ─── ETHGlobal ───────────────────────────────────────────────
def fetch_ethglobal():
    """Fetch events from ETHGlobal API."""
    print("Fetching ETHGlobal events...")
    items = []
    # ETHGlobal has an API endpoint for events
    data = fetch_json('https://ethglobal.com/api/events')
    if not data:
        # Fallback: try web scraping approach
        html = fetch_url('https://ethglobal.com/events')
        if html:
            # Extract JSON data embedded in page
            m = re.search(r'__NEXT_DATA__.*?<script[^>]*>(.*?)</script>', html, re.DOTALL)
            if m:
                try:
                    next_data = json.loads(m.group(1))
                    events = next_data.get('props', {}).get('pageProps', {}).get('events', [])
                    data = events
                except:
                    pass
    if not data:
        print("  Could not fetch ETHGlobal events, using fallback")
        return items

    events = data if isinstance(data, list) else data.get('data', data.get('events', []))
    for ev in events:
        if isinstance(ev, dict):
            start = ev.get('startDate', ev.get('start', ''))
            end = ev.get('endDate', ev.get('end', ''))
            # Skip past events
            if end:
                try:
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')) if 'T' in end else datetime.strptime(end[:10], '%Y-%m-%d')
                    if end_dt.date() < datetime.now().date() - timedelta(days=7):
                        continue
                except:
                    pass

            location = ev.get('city', ev.get('location', ''))
            if ev.get('isOnline') or ev.get('online'):
                location = 'Online'

            items.append({
                'title': ev.get('name', ev.get('title', '')),
                'category': 'hackathon',
                'platform': 'ETHGlobal',
                'url': f"https://ethglobal.com/events/{ev.get('slug', '')}",
                'prize': ev.get('prizePool', ''),
                'deadline': end[:10] if end else start[:10] if start else '',
                'start_date': start[:10] if start else '',
                'location': location,
                'description': ev.get('description', ev.get('tagline', '')),
                'tags': ['Ethereum'],
            })
    print(f"  Found {len(items)} ETHGlobal events")
    return items


# ─── DoraHacks ───────────────────────────────────────────────
def fetch_dorahacks():
    """Fetch hackathons from DoraHacks API."""
    print("Fetching DoraHacks hackathons...")
    items = []
    # DoraHacks public API
    data = fetch_json('https://dorahacks.io/api/hackathon/list?status=active&page=1&limit=50')
    if not data:
        # Try alternative endpoint
        data = fetch_json('https://api.dorahacks.io/v1/hackathon?status=active&limit=50')
    if not data:
        print("  Could not fetch DoraHacks API, trying web scrape")
        html = fetch_url('https://dorahacks.io/hackathon')
        if html:
            # Try to extract __NEXT_DATA__ or similar
            m = re.search(r'__NEXT_DATA__[^>]*>(.*?)</script>', html, re.DOTALL)
            if m:
                try:
                    nd = json.loads(m.group(1))
                    hacks = nd.get('props', {}).get('pageProps', {}).get('hackathons', [])
                    data = {'data': hacks}
                except:
                    pass
    if not data:
        print("  Could not fetch DoraHacks events")
        return items

    hacks = data if isinstance(data, list) else data.get('data', data.get('hackathons', data.get('results', [])))
    if isinstance(hacks, dict):
        hacks = hacks.get('list', hacks.get('items', []))

    for h in (hacks or []):
        if not isinstance(h, dict):
            continue
        end = h.get('endTime', h.get('end_time', h.get('deadline', '')))
        start = h.get('startTime', h.get('start_time', ''))

        # Normalize dates
        for field_name, field_val in [('end', end), ('start', start)]:
            if isinstance(field_val, (int, float)) and field_val > 1e9:
                dt = datetime.fromtimestamp(field_val / 1000 if field_val > 1e12 else field_val)
                if field_name == 'end':
                    end = dt.strftime('%Y-%m-%d')
                else:
                    start = dt.strftime('%Y-%m-%d')

        prize_val = h.get('totalPrize', h.get('prize', h.get('prizePool', '')))
        if isinstance(prize_val, (int, float)):
            prize_val = f"${prize_val:,.0f}"

        slug = h.get('slug', h.get('hackathonId', h.get('id', '')))
        items.append({
            'title': h.get('name', h.get('title', '')),
            'category': 'hackathon',
            'platform': 'DoraHacks',
            'url': f"https://dorahacks.io/hackathon/{slug}" if slug else '',
            'prize': str(prize_val) if prize_val else '',
            'deadline': str(end)[:10] if end else '',
            'start_date': str(start)[:10] if start else '',
            'location': 'Online' if h.get('isOnline', True) else h.get('location', ''),
            'description': (h.get('description', h.get('brief', '')) or '')[:300],
            'tags': h.get('tags', []),
        })

    print(f"  Found {len(items)} DoraHacks hackathons")
    return items


# ─── Devpost ─────────────────────────────────────────────────
class DevpostParser(HTMLParser):
    """Parse Devpost hackathon listings from HTML."""
    def __init__(self):
        super().__init__()
        self.items = []
        self._in_card = False
        self._current = {}
        self._capture = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')
        if 'hackathon-tile' in cls or 'challenge-listing' in cls:
            self._in_card = True
            self._current = {}
        if self._in_card:
            if tag == 'a' and 'challenge-listing-link' in cls:
                self._current['url'] = attrs_dict.get('href', '')
            if 'title' in cls:
                self._capture = 'title'
            if 'prize' in cls or 'value' in cls:
                self._capture = 'prize'
            if 'submission-period' in cls or 'date' in cls:
                self._capture = 'date'

    def handle_data(self, data):
        if self._capture and self._in_card:
            self._current[self._capture] = data.strip()
            self._capture = None

    def handle_endtag(self, tag):
        if tag in ('div', 'li', 'article') and self._in_card and self._current.get('title'):
            self.items.append(self._current)
            self._current = {}
            self._in_card = False


def fetch_devpost():
    """Fetch Web3/blockchain hackathons from Devpost."""
    print("Fetching Devpost hackathons...")
    items = []
    for query in ['blockchain', 'web3', 'crypto', 'defi']:
        url = f'https://devpost.com/api/hackathons?search={query}&status[]=upcoming&status[]=open&per_page=20'
        data = fetch_json(url)
        if data and isinstance(data, dict):
            hacks = data.get('hackathons', [])
            for h in hacks:
                title = h.get('title', '')
                # Deduplicate
                if any(i['title'] == title for i in items):
                    continue
                items.append({
                    'title': title,
                    'category': 'hackathon',
                    'platform': 'Devpost',
                    'url': h.get('url', ''),
                    'prize': h.get('prize_amount', ''),
                    'deadline': h.get('submission_period_dates', h.get('end_date', ''))[:10] if h.get('submission_period_dates') or h.get('end_date') else '',
                    'start_date': (h.get('start_date', '') or '')[:10],
                    'location': 'Online' if h.get('online_only') else h.get('location', 'Online'),
                    'description': (h.get('tagline', '') or '')[:300],
                    'tags': [t.get('name', t) if isinstance(t, dict) else t for t in h.get('themes', [])[:5]],
                })
    print(f"  Found {len(items)} Devpost hackathons")
    return items


# ─── Lablab.ai ───────────────────────────────────────────────
def fetch_lablab():
    """Fetch AI hackathons from lablab.ai."""
    print("Fetching Lablab.ai hackathons...")
    items = []
    data = fetch_json('https://lablab.ai/api/event')
    if not data:
        # Try scraping
        html = fetch_url('https://lablab.ai/event')
        if html:
            m = re.search(r'__NEXT_DATA__[^>]*>(.*?)</script>', html, re.DOTALL)
            if m:
                try:
                    nd = json.loads(m.group(1))
                    data = nd.get('props', {}).get('pageProps', {}).get('events', [])
                except:
                    pass
    if not data:
        print("  Could not fetch lablab.ai events")
        return items

    events = data if isinstance(data, list) else data.get('events', data.get('data', []))
    now = datetime.now()
    for ev in (events or []):
        if not isinstance(ev, dict):
            continue
        end = ev.get('endDate', ev.get('end_date', ''))
        if end:
            try:
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')) if 'T' in str(end) else datetime.strptime(str(end)[:10], '%Y-%m-%d')
                if end_dt.date() < now.date() - timedelta(days=7):
                    continue
            except:
                pass
        items.append({
            'title': ev.get('name', ev.get('title', '')),
            'category': 'ai',
            'platform': 'Lablab.ai',
            'url': f"https://lablab.ai/event/{ev.get('slug', '')}" if ev.get('slug') else '',
            'prize': ev.get('prize', ev.get('prizePool', '')),
            'deadline': str(end)[:10] if end else '',
            'start_date': str(ev.get('startDate', ev.get('start_date', '')))[:10],
            'location': 'Online',
            'description': (ev.get('description', ev.get('tagline', '')) or '')[:300],
            'tags': ['AI'] + (ev.get('technologies', [])[:3] if ev.get('technologies') else []),
        })
    print(f"  Found {len(items)} lablab.ai events")
    return items


# ─── Superteam Earn (Solana) ─────────────────────────────────
def fetch_superteam():
    """Fetch bounties/grants from Superteam Earn."""
    print("Fetching Superteam Earn bounties...")
    items = []
    data = fetch_json('https://earn.superteam.fun/api/listings?take=30&type=bounty&isOpen=true')
    if not data:
        data = fetch_json('https://earn.superteam.fun/api/listings/?take=30')
    if data:
        listings = data if isinstance(data, list) else data.get('listings', data.get('data', []))
        for b in (listings or []):
            if not isinstance(b, dict):
                continue
            reward = b.get('rewardAmount', b.get('reward', ''))
            token = b.get('token', 'USDC')
            prize_str = f"{reward} {token}" if reward else ''
            items.append({
                'title': b.get('title', ''),
                'category': 'quest',
                'platform': 'Superteam Earn',
                'url': f"https://earn.superteam.fun/listings/{b.get('type','bounties')}/{b.get('slug','')}" if b.get('slug') else '',
                'prize': prize_str,
                'deadline': (b.get('deadline', '') or '')[:10],
                'start_date': '',
                'location': 'Online',
                'description': (b.get('description', b.get('pocDescription', '')) or '')[:200],
                'tags': ['Solana'] + (b.get('skills', [])[:3] if isinstance(b.get('skills'), list) else []),
            })
    print(f"  Found {len(items)} Superteam listings")
    return items


# ─── Merge & Deduplicate ─────────────────────────────────────
def normalize_title(t):
    return re.sub(r'[^a-z0-9]', '', t.lower())


def merge_opportunities(old_items, new_items):
    """Merge new items into existing, avoiding duplicates."""
    seen = {normalize_title(i['title']) for i in old_items}
    merged = list(old_items)
    added = 0
    for item in new_items:
        key = normalize_title(item['title'])
        if key and key not in seen:
            seen.add(key)
            item['id'] = f"opp_{datetime.now().strftime('%Y%m%d')}_{len(merged)}"
            item['fetched'] = datetime.now().strftime('%Y-%m-%d')
            merged.append(item)
            added += 1
    print(f"  Merged: {added} new, {len(merged)} total")
    return merged


def prune_old(items, days=90):
    """Remove items whose deadline passed more than N days ago."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    kept = []
    for item in items:
        dl = item.get('deadline', '')
        if dl and dl < cutoff:
            continue
        kept.append(item)
    pruned = len(items) - len(kept)
    if pruned:
        print(f"  Pruned {pruned} expired items")
    return kept


def main():
    print(f"=== Opportunity Fetch ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")

    # Load existing data
    old_items = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            old_items = json.load(f)
        print(f"Loaded {len(old_items)} existing items")

    # Fetch from all sources
    new_items = []
    for fetcher in [fetch_ethglobal, fetch_dorahacks, fetch_devpost, fetch_lablab, fetch_superteam]:
        try:
            new_items.extend(fetcher())
        except Exception as e:
            print(f"  [ERROR] {fetcher.__name__}: {e}", file=sys.stderr)

    print(f"\nTotal fetched: {len(new_items)} items")

    # Merge and deduplicate
    merged = merge_opportunities(old_items, new_items)

    # Prune very old items
    merged = prune_old(merged)

    # Sort by deadline (soonest first, no-deadline last)
    merged.sort(key=lambda x: x.get('deadline') or '9999-99-99')

    # Save
    with open(DATA_FILE, 'w') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(merged)} items to {DATA_FILE}")


if __name__ == '__main__':
    main()
