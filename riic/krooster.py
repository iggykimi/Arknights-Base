"""Download a public Krooster roster.

The network lookup page (krooster.com/network/lookup/USER) is rendered server-side
with the roster in its ``__NEXT_DATA__`` JSON, keyed by game char id. Only what the
planner reads is kept: elite, level and potential.
"""

import json
import re
import urllib.request
from pathlib import Path

URL = "https://www.krooster.com/network/lookup/{}"
_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL)


def fetch(user: str) -> dict[str, dict]:
    req = urllib.request.Request(URL.format(user), headers={"User-Agent": "riic"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8")
    m = _DATA.search(html)
    if not m:
        raise RuntimeError(f"No roster data in {URL.format(user)}")
    data = json.loads(m[1])["props"]["pageProps"].get("data")
    if not data or not data.get("roster"):
        raise RuntimeError(f"Krooster user {user!r} not found or private")
    return {
        cid: {k: o[k] for k in ("elite", "level", "potential")}
        for cid, o in sorted(data["roster"].items())
    }


def save(user: str, path: Path) -> int:
    """Write ``user``'s roster to ``path``; returns the operator count."""
    roster = fetch(user)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(roster, indent=1) + "\n", encoding="utf-8", newline="\n")
    return len(roster)
