"""Check listing.md fields against App Store Connect character limits.

    python3 ios/AppStore/check_listing.py
"""
import os
import re
import sys

LIMITS = {
    "Name": 30,
    "Subtitle": 30,
    "Promotional text": 170,
    "Description": 4000,
    "Keywords": 100,
}

text = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "listing.md")).read()
failed = False
for heading, limit in LIMITS.items():
    match = re.search(rf"^## {re.escape(heading)}\b.*?\n```\n(.*?)\n```", text, re.S | re.M)
    if not match:
        print(f"{heading:17} MISSING")
        failed = True
        continue
    value = match.group(1)
    ok = len(value) <= limit
    failed |= not ok
    print(f"{heading:17} {len(value):5} / {limit:<5} {'ok' if ok else 'TOO LONG'}")
    if heading == "Keywords" and ", " in value:
        print("                  keywords contain ', ' (spaces waste characters)")
        failed = True
sys.exit(1 if failed else 0)
