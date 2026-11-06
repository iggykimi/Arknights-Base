"""python -m riic.krooster USER: save a public Krooster roster as rosters/USER.json.

The network lookup page (krooster.com/network/lookup/USER) is rendered server-side
with the roster in its ``__NEXT_DATA__`` JSON, keyed by game char id. Only what the
planner reads is kept: elite, level and potential.
"""

import argparse
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("user")
    ap.add_argument("--out", type=Path, help="default: rosters/USER.json")
    args = ap.parse_args()
    out = args.out or ROOT / "rosters" / f"{args.user}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    roster = fetch(args.user)
    out.write_text(json.dumps(roster, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(out, f"({len(roster)} operadores)")


if __name__ == "__main__":
    main()
