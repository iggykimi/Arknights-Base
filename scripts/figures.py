"""Rebuild the README chart: the optimised plan against a greedy assignment.

    python scripts/figures.py           # rebuild both plans per player (~5 min each)
    python scripts/figures.py --render  # redraw the SVGs from docs/figures/results.json

The greedy baseline keeps everything the optimised plan chose outside production
(CC, PP, RR, HR, trainer, workshop, dorms) and refills only the Factories and
Trading Posts, shift A first, by taking the best remaining team each time. A Gold
Factory counts as its bars at 500 LMD each, an EXP Factory as its EXP and a
Trading Post as the LMD it can sell. That is how one fills a base by hand from a
ranked list of teams. Both plans are scored by the same model.

Needs the guide workbook (see README) unless run with --render.
"""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from riic.__main__ import PLAYERS, player_settings
from riic.excel import WORKBOOK, require_workbook
from riic.gamedata import all_skills
from riic.model import LMD_PER_GOLD, Roster
from riic.optimize import _teams, all_assigned, build_plan, plan_value
from riic.roster import load_roster

OUT = ROOT / "docs" / "figures"
RESULTS = OUT / "results.json"

# Shared style of the owner's README graphics: transparent background, one file per
# GitHub theme. LMD (and gold, which becomes LMD) is accent 1, EXP accent 2.
THEMES = {
    "light": {"text": "#1f2328", "muted": "#59636e", "line": "#d1d9e0",
              "lmd": "#1f8a70", "exp": "#5b5bd6", "neutral": "#8c959f"},
    "dark": {"text": "#e6edf3", "muted": "#9198a1", "line": "#3d444d",
             "lmd": "#22d3a7", "exp": "#8b8bf0", "neutral": "#6e7681"},
}  # fmt: skip
FONT = "system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
PLAN = PLAYERS / "iggykimi" / "base_plan.md"
SHIFT = "A"


def greedy(plan, r: Roster):
    """Shifts A and B with Factories and Trading Posts refilled greedily."""
    s = plan.settings
    production = {o for sh in (plan.a, plan.b) for t in [*(t for t, _ in sh.facs), *sh.tps]
                  for o in t}  # fmt: skip
    free = set(r.owned) - (set(all_assigned(plan)) - production)
    shifts = []
    for shift in (plan.a, plan.b):
        teams = _teams(r, plan.context(shift, r), free)
        worth = {"Gold": LMD_PER_GOLD, "EXP": s.exp_weight, "TP": 1.0}
        facs, tps = [], []
        for kind, team, value, _ in sorted(teams, key=lambda t: -t[2] * worth[t[0]]):
            if not free >= set(team):
                continue
            if kind == "TP" and len(tps) < s.tp_count:
                tps.append(team)
            elif kind != "TP" and len(facs) < s.fac_count:
                facs.append((team, kind))
            else:
                continue
            free -= set(team)
        shifts.append(replace(shift, facs=facs, tps=tps))
    return shifts


def daily(plan, r: Roster, shifts) -> dict:
    """LMD and EXP per day over the 12 h A/B rotation."""
    a, b = (plan_value(plan, r, sh) for sh in shifts)
    return {"lmd": round((a.lmd + b.lmd) / 2), "exp": round((a.exp + b.exp) / 2)}


def compute() -> list[dict]:
    skills, names = all_skills(require_workbook(WORKBOOK), ROOT / ".cache" / "gamedata")
    rows = []
    for folder in sorted(p for p in PLAYERS.iterdir() if p.is_dir()):
        r = Roster(load_roster(folder / "roster.json", names), skills)
        plan = build_plan(r, player_settings(folder))
        rows.append({
            "player": folder.name,
            "operators": len(r.owned),
            "greedy": daily(plan, r, greedy(plan, r)),
            "milp": daily(plan, r, (plan.a, plan.b)),
        })  # fmt: skip
        print(rows[-1])
    return rows


def _fmt(n: float) -> str:
    return f"{n:,.0f}"


def svg(rows: list[dict], t: dict) -> str:
    """Horizontal stacked bars: LMD + EXP per day, greedy vs optimised, per player."""
    w, left, right, bar, gap, group_gap, head = 760, 110, 150, 26, 10, 26, 28
    top = 72
    scale = (w - left - right) / max(x["milp"]["lmd"] + x["milp"]["exp"] for x in rows)
    h = top + len(rows) * (head + 2 * bar + gap + group_gap) - group_gap + 20
    out = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc" '
            f'font-family="{FONT}">'
        ),
        "<title id='title'>Daily output: greedy assignment vs optimised plan</title>",
        "<desc id='desc'>"
        + "; ".join(
            f"{x['player']}: greedy {_fmt(x['greedy']['lmd'])} LMD + {_fmt(x['greedy']['exp'])}"
            f" EXP, optimised {_fmt(x['milp']['lmd'])} LMD + {_fmt(x['milp']['exp'])} EXP"
            for x in rows
        )
        + " per day.</desc>",
        (
            f'<text x="20" y="30" font-size="16" font-weight="600" fill="{t["text"]}">'
            "LMD + EXP per day, 12 h rotation</text>"
        ),
    ]
    # Legend
    lx = 20
    for key, label in (("lmd", "LMD"), ("exp", "EXP (1 EXP = 1 LMD)")):
        out.append(f'<rect x="{lx}" y="44" width="12" height="12" rx="3" fill="{t[key]}"/>')
        out.append(f'<text x="{lx + 18}" y="54" font-size="13" fill="{t["muted"]}">{label}</text>')
        lx += 18 + 8 * len(label) + 24
    y = top
    for x in rows:
        out.append(
            f'<text x="20" y="{y + 16}" font-size="13" font-weight="600" fill="{t["text"]}">'
            f'{x["player"]} <tspan font-weight="400" fill="{t["muted"]}">'
            f"({x['operators']} operators)</tspan></text>"
        )
        y += head
        base = x["greedy"]["lmd"] + x["greedy"]["exp"]
        for key, label in (("greedy", "Greedy"), ("milp", "Optimised")):
            v = x[key]
            out.append(
                f'<text x="{left - 10}" y="{y + bar / 2 + 5}" font-size="13" text-anchor="end" '
                f'fill="{t["text"]}">{label}</text>'
            )
            x0 = left
            for part in ("lmd", "exp"):
                width = v[part] * scale
                if width < 1:
                    continue
                # 2px surface gap between stacked segments
                width_drawn = width - (2 if part == "lmd" and v["exp"] else 0)
                out.append(
                    f'<rect x="{x0:.1f}" y="{y}" width="{width_drawn:.1f}" height="{bar}" '
                    f'rx="6" fill="{t[part]}"/>'
                )
                x0 += width
            total = v["lmd"] + v["exp"]
            note = _fmt(total)
            if key == "milp":
                note += f"  ({(total / base - 1) * 100:+.1f}%)"
            out.append(
                f'<text x="{x0 + 8:.1f}" y="{y + bar / 2 + 5}" font-size="13" '
                f'fill="{t["text"]}">{note}</text>'
            )
            y += bar + gap
        y += group_gap - gap
        out.append(
            f'<line x1="20" x2="{w - 20}" y1="{y - group_gap / 2}" y2="{y - group_gap / 2}" '
            f'stroke="{t["line"]}" stroke-width="1"/>'
        )
    out.pop()  # no rule under the last group
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--render", action="store_true", help="redraw from results.json only")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.render:
        rows = json.loads(RESULTS.read_text(encoding="utf-8"))
    else:
        rows = compute()
        RESULTS.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, theme in THEMES.items():
        path = OUT / f"plan-vs-greedy-{name}.svg"
        path.write_text(svg(rows, theme), encoding="utf-8", newline="\n")
        print(path)


if __name__ == "__main__":
    main()
