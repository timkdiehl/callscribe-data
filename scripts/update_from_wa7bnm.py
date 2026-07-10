#!/usr/bin/env python3
"""Weekly drift check against the WA7BNM contest calendar RSS feed.

The feed is a rolling ~8-day window, so every contest passes through it
the week before it runs — checking weekly verifies each catalog entry's
weekend rule right when a wrong date would mislead the app's picker.

For each feed item that names a catalog contest:
- parse its start day, snap to the weekend's Saturday (UTC),
- compare with the Saturday our weekend rule predicts,
- on drift, derive the corrected rule from the observed date and update
  contest-catalog.json (only that entry's rule for that month),
- anything ambiguous (weekday start, no full-weekend fit) is reported
  for a human instead of guessed at.

Signals for the workflow: a dirty contest-catalog.json means "commit
me"; a problems.txt means "open an issue". Exit is 0 unless the feed or
file is unreadable.
Usage: update_from_wa7bnm.py [--dry-run] [--rss FILE]
"""
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

RSS_URL = "https://www.contestcalendar.com/calendar.rss"

# Catalog key → exact WA7BNM feed title.
TITLES = {
    "arrl-fd": "ARRL Field Day",
    "1010-winter-ssb": "10-10 Int. Winter Contest, SSB",
    "1010-summer-ssb": "10-10 Int. Summer Contest, SSB",
    "winter-fd": "Winter Field Day",
    "cq-wpx-ssb": "CQ WW WPX Contest, SSB",
    "cq-wpx-cw": "CQ WW WPX Contest, CW",
    "cq-ww-ssb": "CQ Worldwide DX Contest, SSB",
    "cq-ww-cw": "CQ Worldwide DX Contest, CW",
    "iaru-hf": "IARU HF World Championship",
    "arrl-ss-ph": "ARRL Sweepstakes Contest, SSB",
    "arrl-ss-cw": "ARRL Sweepstakes Contest, CW",
    "naqp-ssb": "North American QSO Party, SSB",
    "naqp-cw": "North American QSO Party, CW",
    "arrl-dx-ph": "ARRL International DX Contest, SSB",
    "arrl-10m": "ARRL 10-Meter Contest",
    "cq-160-ssb": "CQ 160-Meter Contest, SSB",
    "arrl-vhf-jan": "ARRL January VHF Contest",
    "arrl-vhf-jun": "ARRL June VHF Contest",
    "arrl-vhf-sep": "ARRL September VHF Contest",
    "cq-ww-vhf": "CQ Worldwide VHF Contest",
}
MONTHS = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def full_weekend_saturdays(year, month):
    """Saturdays whose Sunday stays in the month — mirrors WeekendRule."""
    out = []
    day = dt.date(year, month, 1)
    while day.month == month:
        if day.weekday() == 5:  # Saturday
            sunday = day + dt.timedelta(days=1)
            if sunday.month == month:
                out.append(day)
        day += dt.timedelta(days=1)
    return out


def rule_saturday(rule, year):
    sats = full_weekend_saturdays(year, rule["month"])
    if not sats:
        return None
    if rule["ordinal"] == -1:
        return sats[-1]
    index = rule["ordinal"] - 1
    return sats[index] if index < len(sats) else None


def parse_feed_items(rss_text):
    for m in re.finditer(
        r"<item>.*?<title>(.*?)</title>.*?<description>(.*?)</description>.*?</item>",
        rss_text, re.S,
    ):
        yield m.group(1).strip(), m.group(2).strip()


def first_date(description, today):
    """'1200Z, Jul 11 to 1200Z, Jul 12' → the start date; the feed only
    shows the next ~8 days, so the year is today's (or next, at the
    December→January seam)."""
    m = re.search(r"([A-Z][a-z]{2}) (\d{1,2})", description)
    if not m:
        return None
    month, day = MONTHS.get(m.group(1)), int(m.group(2))
    if not month:
        return None
    year = today.year + (1 if month < today.month - 6 else 0)
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def weekend_saturday(date):
    """Snap a contest start day to its weekend's Saturday; None for
    weekday starts (not a full-weekend contest — needs a human)."""
    if date.weekday() == 5:
        return date
    if date.weekday() == 6:
        return date - dt.timedelta(days=1)
    return None


def main():
    dry_run = "--dry-run" in sys.argv
    rss_file = None
    if "--rss" in sys.argv:
        rss_file = sys.argv[sys.argv.index("--rss") + 1]

    catalog_path = Path(__file__).resolve().parent.parent / "contest-catalog.json"
    catalog = json.loads(catalog_path.read_text())
    entries = {e["key"]: e for e in catalog["entries"]}
    today = dt.date.today()

    if rss_file:
        rss = Path(rss_file).read_text()
    else:
        req = urllib.request.Request(RSS_URL, headers={"User-Agent": "callscribe-data catalog check"})
        rss = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

    by_title = {t: k for k, t in TITLES.items()}
    changed, problems = [], []

    for title, description in parse_feed_items(rss):
        key = by_title.get(title)
        if not key or key not in entries:
            continue
        entry = entries[key]
        start = first_date(description, today)
        if start is None:
            problems.append(f"{key}: could not parse date from {description!r}")
            continue
        actual_sat = weekend_saturday(start)
        if actual_sat is None:
            problems.append(
                f"{key}: starts on a weekday ({start}) — not a full-weekend "
                f"pattern, review the schedule rule by hand"
            )
            continue

        month_rules = [r for r in entry.get("schedule", []) if r["month"] == actual_sat.month]
        predicted = [rule_saturday(r, actual_sat.year) for r in month_rules]
        if actual_sat in predicted:
            print(f"ok: {key} — rule predicts {actual_sat}, feed agrees")
            continue

        sats = full_weekend_saturdays(actual_sat.year, actual_sat.month)
        if actual_sat not in sats:
            problems.append(
                f"{key}: feed says {actual_sat}, which is not a full weekend "
                f"of its month — review by hand"
            )
            continue
        new_rule = {"month": actual_sat.month, "ordinal": sats.index(actual_sat) + 1}
        old = month_rules[0] if month_rules else None
        entry.setdefault("schedule", [])
        entry["schedule"] = [r for r in entry["schedule"] if r["month"] != actual_sat.month]
        entry["schedule"].append(new_rule)
        entry["schedule"].sort(key=lambda r: r["month"])
        changed.append(
            f"{key}: {old} → {new_rule} (feed start {start}, predicted {predicted})"
        )

    for line in changed:
        print("drift fixed:", line)
    for line in problems:
        print("needs review:", line)

    if changed and not dry_run:
        catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n")

    if problems and not dry_run:
        Path("problems.txt").write_text("\n".join(problems) + "\n")


if __name__ == "__main__":
    main()
