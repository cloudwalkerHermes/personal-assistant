#!/usr/bin/env python3
"""
tasks/rory_checkin.py
----------------------
Fires 7a/11a/3p/7p — has Voicebox speak a check-in message through the
Rory Cochrane voice clone, played on the Windows desktop's speakers.

Run from personal-assistant/:
    .venv/bin/python3 tasks/rory_checkin.py
"""

import requests

VOICEBOX_URL  = "http://192.168.1.3:17493"
PROFILE_ID    = "35b05941-2681-441f-97d4-905cd7a2d5e4"  # Rory Cochrane
ENGINE        = "qwen"
MESSAGE       = "Hey man, just checking in... want to do another gummy B?"


def main():
    r = requests.post(
        f"{VOICEBOX_URL}/speak",
        json={"text": MESSAGE, "profile": PROFILE_ID, "engine": ENGINE},
        timeout=30,
    )
    print(r.status_code, r.text[:200])


if __name__ == "__main__":
    main()
