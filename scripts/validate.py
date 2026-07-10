#!/usr/bin/env python3
"""Validate contest-catalog.json — run on every push and before any
auto-commit so a broken file can never reach the app."""
import json
import sys
from pathlib import Path

# The exchange shapes CallScribe builds know. An entry pointing anywhere
# else is dropped by the app, so it's a mistake here.
KNOWN_PROFILES = {
    "rst-serial", "rst-cq-zone", "rst-itu-zone", "rst-state",
    "class-section", "name-state", "sweepstakes", "grid", "qso-party",
}


def fail(msg):
    print(f"INVALID: {msg}")
    sys.exit(1)


def main():
    path = Path(__file__).resolve().parent.parent / "contest-catalog.json"
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        fail(f"not valid JSON: {e}")

    if data.get("version") != 1:
        fail(f"version must be 1, got {data.get('version')!r}")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        fail("entries must be a non-empty list")

    keys = set()
    for e in entries:
        key = e.get("key")
        if not key or not isinstance(key, str):
            fail(f"entry missing key: {e}")
        if key in keys:
            fail(f"duplicate key {key}")
        keys.add(key)
        if not e.get("name"):
            fail(f"{key}: missing name")
        if e.get("profileID") not in KNOWN_PROFILES:
            fail(f"{key}: unknown profileID {e.get('profileID')!r}")
        if e.get("submitVia") not in (None, "cabrillo", "adif"):
            fail(f"{key}: bad submitVia {e.get('submitVia')!r}")
        for rule in e.get("schedule", []):
            month, ordinal = rule.get("month"), rule.get("ordinal")
            if month not in range(1, 13):
                fail(f"{key}: bad schedule month {month!r}")
            if ordinal not in (-1, 1, 2, 3, 4):
                fail(f"{key}: bad schedule ordinal {ordinal!r}")

    print(f"OK: {len(entries)} entries")


if __name__ == "__main__":
    main()
