"""Rebuild the README figures: one shift of a base and the plan against a greedy fill.

    python scripts/figures.py           # rebuild both plans per player (~5 min each)
    python scripts/figures.py --render  # redraw the SVGs from docs/figures/results.json

The base schematic is drawn from players/iggykimi/base_plan.md as it is on disk,
so regenerate that plan first if it is stale.

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
import re
import sys
from dataclasses import replace
from pathlib import Path
from xml.sax.saxutils import escape

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


def _number(es: str) -> str:
    """'16.400' (Spanish thousands) -> '16,400'."""
    return es.replace(".", ",") if re.fullmatch(r"\d{1,3}(\.\d{3})+", es) else es


def read_plan(path: Path, shift: str) -> dict:
    """One shift of a generated base_plan.md, plus the rooms that never rotate.

    Returns {"rooms": {code: {"ops", "product", "pct", "per_day"}}, "lmd", "exp",
    "gold", "drones"}. Reads the Markdown, not the planner, so it needs no workbook."""
    text = path.read_text(encoding="utf-8")
    start = text.index(f"## Turno {shift}\n")
    section = text[start : text.index("\n## ", start)]
    rooms = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6 or not re.fullmatch(r"[A-Z]+\d?", cells[0]):
            continue
        code, ops, product, pct, per_day, _hours = cells
        amount, _, unit = per_day.partition(" ")
        rooms[code] = {
            "ops": ops.split(", "),
            "product": product if product != "—" else "",
            "pct": pct if pct != "—" else "",
            "per_day": f"{_number(amount)} {unit}".strip() if per_day != "—" else "",
        }
    fixed = text.split("## Fijos", 1)[1].split("## ", 1)[0]
    for code, value in re.findall(r"^- \*\*(TR|WS|DORM\d)[^:]*:\*\* (.+)$", fixed, re.MULTILINE):
        names = re.findall(r"([^+;()]+?) \(\+[\d.]+ \w+\)", value) or [value]
        rooms[code] = {"ops": [n.strip() for n in names], "product": "", "pct": "", "per_day": ""}

    def bullet(label: str) -> str:
        return re.search(rf"^- \*\*{label}:\*\* (.+)$", section, re.MULTILINE).group(1)

    gold = re.match(r"([\d.]+) barras/día fabricadas, ([\d.]+) pedidas", bullet("Oro"))
    return {
        "rooms": rooms,
        "lmd": _number(bullet("LMD/día")),
        "exp": _number(bullet("EXP/día")),
        "gold": gold.groups(),
        "drones": re.match(r"\+(\d+)%", bullet("Drones")).group(1),
    }


# What each room code is called and makes, in English (base_plan.md is in Spanish).
ROOM_NAMES = {"CC": "Control center", "FAC": "Factory", "TP": "Trading post",
              "PP": "Power plant", "RR": "Reception room", "HR": "HR office",
              "WS": "Workshop", "TR": "Training room", "DORM": "Dormitory"}  # fmt: skip
PRODUCTS = {"Gold": "Gold", "EXP": "EXP", "LMD": "LMD", "drones": "Drones",
            "pistas": "Clues", "contacto": "Recruiting", "": ""}  # fmt: skip
UNITS = {"barras": "gold bars a day", "EXP": "EXP a day", "LMD": "LMD a day"}
ROOM_ROLE = {"CC": "Buffs other rooms", "WS": "Crafts materials", "TR": "Trains skills"}


def _room_name(code: str) -> str:
    kind, num = re.fullmatch(r"([A-Z]+?)(\d?)", code).groups()
    return f"{ROOM_NAMES[kind]} {num}".strip()


def base_svg(plan: dict, player: str, shift: str, t: dict) -> str:
    """Floor plan of a 2-4-3 base: the 9 build slots on the left, the control center
    and dormitories in the middle, the fixed rooms on the right, each with its team."""
    w, top, gap = 860, 96, 9
    cols = {"left": (20, 144), "mid": (486, 180), "right": (682, 158)}
    block = 3 * 128 + 2 * gap  # height of the three floors of build slots
    rooms = plan["rooms"]
    out = []

    def text(x, y, s, size=13, fill="text", weight=None, anchor=None):
        extra = (f' font-weight="{weight}"' if weight else "") + (
            f' text-anchor="{anchor}"' if anchor else ""
        )
        out.append(
            f'<text x="{x}" y="{y}" font-size="{size}" fill="{t[fill]}"{extra}>{escape(s)}</text>'
        )

    def room(code, x, y, rw, rh):
        r = rooms[code]
        kind = "exp" if r["product"] == "EXP" else "lmd" if r["product"] in ("Gold", "LMD") else ""
        if kind:
            out.append(
                f'<rect x="{x + 0.75}" y="{y + 0.75}" width="{rw - 1.5}" height="{rh - 1.5}" '
                f'rx="6" fill="{t[kind]}" fill-opacity="0.1" stroke="{t[kind]}" '
                'stroke-width="1.5"/>'
            )
        else:
            out.append(
                f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{rw - 1}" height="{rh - 1}" rx="6" '
                f'fill="none" stroke="{t["line"]}"/>'
            )
        tx, ty = x + 12, y + 22
        text(tx, ty, _room_name(code), weight=600)
        if code.startswith("DORM"):
            text(x + rw - 12, ty, "+3 resting", 12, "muted", anchor="end")
            text(tx, ty + 20, ", ".join(r["ops"]))
            return
        lines = []
        product = PRODUCTS[r["product"]]
        if product or r["pct"]:
            lines.append((f"{product} {r['pct']}".strip(), "text"))
        if r["per_day"]:
            amount, unit = r["per_day"].split(" ", 1)
            lines.append((f"{amount} {UNITS[unit]}", "muted"))
        if code in ROOM_ROLE:
            lines.append((ROOM_ROLE[code], "muted"))
        for s, fill in lines:
            ty += 18
            text(tx, ty, s, 12, fill)
        ty += 4
        for op in r["ops"]:
            ty += 18
            text(tx, ty, op)

    # Build slots, laid out so gold flows left to right: factories, then the
    # trading posts that sell it, then the power plants that speed them up.
    x0, rw = cols["left"]
    for i, row in enumerate((("FAC1", "FAC2", "FAC3"), ("FAC4", "TP1", "TP2"),
                             ("PP1", "PP2", "PP3"))):  # fmt: skip
        for j, code in enumerate(row):
            room(code, x0 + j * (rw + gap), top + i * (128 + gap), rw, 128)
    x0, rw = cols["mid"]
    cc_h = 148  # five operators
    room("CC", x0, top, rw, cc_h)
    dorms = sorted(c for c in rooms if c.startswith("DORM"))
    dh = (block - cc_h - len(dorms) * gap) / len(dorms)
    for i, code in enumerate(dorms):
        room(code, x0, top + cc_h + gap + i * (dh + gap), rw, dh)
    x0, rw = cols["right"]
    right = ("RR", "HR", "WS", "TR")
    rh = (block - (len(right) - 1) * gap) / len(right)
    for i, code in enumerate(right):
        room(code, x0, top + i * (rh + gap), rw, rh)

    y = top + block + 26
    made, sold = (f"{float(g):.0f}" for g in plan["gold"])
    text(20, y, "Percentages are each room's speed-up from its operators' skills. "
         f"Gold: {made} bars a day made, {sold} sold.", 12, "muted")  # fmt: skip
    text(20, y + 18, f"Power plants make drones recover {plan['drones']}% faster; all drones "
         "go to the trading post that earns most.", 12, "muted")  # fmt: skip
    text(20, y + 36, "Workshop, training room and dormitories stay the same in both shifts. "
         "Each dormitory has 5 beds: 2 skilled operators and 3 resting.",
         12, "muted")  # fmt: skip
    h = y + 48

    head = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc" '
            f'font-family="{FONT}">'
        ),
        f"<title id='title'>{player}'s base, shift {shift}</title>",
        "<desc id='desc'>"
        + escape(
            "; ".join(
                f"{_room_name(c)}: {', '.join(r['ops'])}"
                + (f" ({PRODUCTS[r['product']]} {r['pct']})" if r["pct"] else "")
                for c, r in rooms.items()
            )
        )
        + ".</desc>",
    ]
    text(20, 30, f"{player}'s base, shift {shift}", 16, weight=600)
    text(20, 52, f"While this shift works the base makes {plan['lmd']} LMD and "
         f"{plan['exp']} EXP a day (drones included).", 13, "muted")  # fmt: skip
    lx = 20
    for kind, label in (("lmd", "Gold and LMD"), ("exp", "EXP"), ("", "Support")):
        stroke = t[kind] if kind else t["line"]
        fill = f'fill="{t[kind]}" fill-opacity="0.1"' if kind else 'fill="none"'
        out.append(
            f'<rect x="{lx + 0.75}" y="68.75" width="16" height="12" rx="3" {fill} '
            f'stroke="{stroke}" stroke-width="1.5"/>'
        )
        text(lx + 22, 79, label, 12, "muted")
        lx += 22 + 7 * len(label) + 20
    return "\n".join([*head, *out, "</svg>"]) + "\n"


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
        path = OUT / f"base-shift-{name}.svg"
        plan = read_plan(PLAN, SHIFT)
        path.write_text(base_svg(plan, PLAN.parent.name, SHIFT, theme), encoding="utf-8",
                        newline="\n")  # fmt: skip
        print(path)


if __name__ == "__main__":
    main()
