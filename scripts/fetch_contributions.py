#!/usr/bin/env python3
import os
import sys
import json
import re
from datetime import datetime
from collections import defaultdict
import requests
from bs4 import BeautifulSoup

def fetch_contributions(username="Rupam797"):
    """
    Fetch public contribution calendar from GitHub user's contributions page.
    """
    url = f"https://github.com/users/{username}/contributions"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"Fetching contribution calendar for '{username}' from {url}...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch contributions page. HTTP Status: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    td_days = soup.find_all("td", class_="ContributionCalendar-day")
    tooltips = {t.get("for"): t.text.strip() for t in soup.find_all("tool-tip")}

    days = []
    for td in td_days:
        td_id = td.get("id")
        date_str = td.get("data-date")
        if not date_str:
            continue

        level = int(td.get("data-level", "0"))
        tt_text = tooltips.get(td_id, "")

        count = 0
        if tt_text:
            if "No contributions" in tt_text or "No contribution" in tt_text:
                count = 0
            else:
                m = re.search(r"^([\d,]+)\s+contribution", tt_text)
                if m:
                    count = int(m.group(1).replace(",", ""))

        days.append({
            "date": date_str,
            "count": count,
            "level": level
        })

    # Sort days chronologically
    days.sort(key=lambda d: d["date"])

    # Calculate statistics
    total_contributions = sum(d["count"] for d in days)

    # Longest streak
    longest_streak = 0
    cur_streak = 0
    for d in days:
        if d["count"] > 0:
            cur_streak += 1
            if cur_streak > longest_streak:
                longest_streak = cur_streak
        else:
            cur_streak = 0

    # Current streak (working backward from today or yesterday)
    current_streak = 0
    if days:
        if days[-1]["count"] > 0:
            idx = len(days) - 1
            while idx >= 0 and days[idx]["count"] > 0:
                current_streak += 1
                idx -= 1
        elif len(days) > 1 and days[-2]["count"] > 0:
            idx = len(days) - 2
            while idx >= 0 and days[idx]["count"] > 0:
                current_streak += 1
                idx -= 1

    # Best day
    best_day = max(days, key=lambda d: d["count"]) if days else None

    # Monthly totals
    monthly_totals = defaultdict(int)
    for d in days:
        monthly_totals[d["date"][:7]] += d["count"]

    payload = {
        "username": username,
        "total_contributions": total_contributions,
        "stats": {
            "total": total_contributions,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "best_day": best_day,
            "monthly_totals": dict(monthly_totals)
        },
        "days": days,
        "fetched_at": datetime.now().isoformat()
    }

    # Save to data/contributions.json
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, "contributions.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Successfully saved contribution data to {json_path}")
    print(f"Total Contributions: {total_contributions:,}")
    print(f"Current Streak: {current_streak} days")
    print(f"Longest Streak: {longest_streak} days")
    if best_day:
        print(f"Best Day: {best_day['date']} ({best_day['count']} contributions)")

    return payload

if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else os.getenv("GITHUB_USERNAME", "Rupam797")
    fetch_contributions(username)
