"""python -m riic.promotions USER: what each promotion would add to the base.

For every owned operator whose next promotion unlocks a CC, FAC, TP or PP skill,
the whole plan (both shifts) is rebuilt with that operator promoted, and the
gain is the change in daily LMD + EXP over the 12 h rotation. The current plan
stays a candidate, so a promotion never shows a loss it could not cause.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from . import optimize
from .__main__ import PLAYERS, player_settings
from .excel import WORKBOOK, require_workbook
from .gamedata import all_skills, download, rarities
from .model import MODELLED, Roster
from .optimize import Plan, build_plan, plan_value
from .roster import load_roster

ROOT = Path(__file__).resolve().parent.parent
PRODUCTIVE = ("CC", "FAC", "TP", "PP")
OUT = "no entra en el plan"
GAP = 1e-4  # comparing plans needs the solver closer to the optimum than one plan does
TIE = 50  # LMD+EXP per day: below this a promotion changes nothing


def max_elite(stars: int) -> int:
    return 0 if stars <= 2 else 1 if stars == 3 else 2


def daily(r: Roster, plan: Plan) -> tuple[float, float, dict[str, str]]:
    """(LMD, EXP) per day over a 12 h A/B rotation, and where each operator works."""
    a, b = plan_value(plan, r, plan.a), plan_value(plan, r, plan.b)
    where = {o: f"turno A {_place(plan.a, o)}" for o in plan.a.operators()}
    where |= {o: f"turno B {_place(plan.b, o)}" for o in plan.b.operators()}
    return (a.lmd + b.lmd) / 2, (a.exp + b.exp) / 2, where


def _place(shift, op) -> str:
    if op in shift.cc:
        return "CC"
    for i, (t, p) in enumerate(shift.facs, 1):
        if op in t:
            return f"FAC{i} ({p})"
    for i, t in enumerate(shift.tps, 1):
        if op in t:
            return f"TP{i}"
    return "PP" if op in shift.pps else "RR" if op in shift.rr else "HR"


def candidates(r: Roster, stars: dict[str, int]):
    """(operator, target promotion, skills it unlocks) for productive skills."""
    out = []
    for op, o in sorted(r.owned.items()):
        top = max_elite(stars.get(op, 6))
        for target in range(o.elite + 1, top + 1):
            new = [
                s
                for s in r.skills
                if s.operator == op
                and s.facility in PRODUCTIVE
                and o.elite < s.elite <= target
                and (s.effect or op in MODELLED.get(s.facility, ()))
            ]
            if any(s.elite == target for s in new):
                out.append((op, target, new))
    return out


def _run(job):
    owned, skills, settings, current, op, target = job
    optimize.MIP_GAP = GAP  # per process: workers import a fresh module
    owned = dict(owned)
    owned[op] = replace(owned[op], elite=target, level=1)
    r = Roster(owned, skills)
    best = max(
        (daily(r, build_plan(r, settings)), daily(r, current)),
        key=lambda d: d[0] + d[1] * settings.exp_weight,
    )
    lmd, exp, where = best
    return op, target, lmd, exp, where.get(op, OUT)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--excel", type=Path, default=WORKBOOK, help="guide workbook (.xlsx)")
    ap.add_argument("user", help="a players/ folder")
    ap.add_argument("--cache", type=Path, default=ROOT / ".cache" / "gamedata")
    ap.add_argument("--workers", type=int, default=6, help="12 ran out of memory")
    args = ap.parse_args()

    folder = PLAYERS / args.user
    settings = player_settings(folder)
    skills, names = all_skills(require_workbook(args.excel), args.cache)
    stars = rarities(download(args.cache), names)
    r = Roster(load_roster(folder / "roster.json", names), skills)
    out = folder / "promotions.md"
    optimize.MIP_GAP = GAP
    current = build_plan(r, settings)
    base_lmd, base_exp, _ = daily(r, current)
    jobs = candidates(r, stars)
    print(f"{len(jobs)} promociones a probar")

    texts = {(op, t): new for op, t, new in jobs}
    with ProcessPoolExecutor(args.workers) as pool:
        args_ = [(r.owned, skills, settings, current, op, t) for op, t, _ in jobs]
        results = list(pool.map(_run, args_))

    rows = []
    for op, target, lmd, exp, where in results:
        gain = (lmd - base_lmd) + (exp - base_exp) * settings.exp_weight
        rows.append((gain, op, target, lmd - base_lmd, exp - base_exp, where))
    rows.sort(reverse=True)
    # A rebuilt plan that leaves the promoted operator out is just another plan for
    # the current roster: its gain measures how far build_plan is from the optimum.
    noise = max((g for g, *_, where in rows if where == OUT), default=0.0)
    floor = max(TIE, noise)

    lines = [
        "# Promociones que merecen la pena para la base",
        "",
        (
            f"Generado con `python -m riic.promotions {args.user}`.Cada fila rehace el plan entero (turnos A y B) "
            "con ese operador promocionado y compara con el plan actual, que sigue siendo una "
            "opción. Ganancia = LMD + EXP por día con rotación de 12 h; por debajo de "
            f"{TIE}, «(nada)»."
        ),
        "",
        f"Plan actual: {base_lmd:,.0f} LMD + {base_exp:,.0f} EXP al día.".replace(",", "."),
        "",
        (
            f"Ruido del optimizador: {noise:+,.0f} al día (la mayor ganancia de un operador que "
            "no entra en el plan, que solo puede venir de encontrar otro plan mejor). Las "
            "ganancias por debajo de eso no son fiables: «(ruido)»."
        ).replace(",", "."),
        "",
        "| Operador | Promoción | Ganancia/día | LMD | EXP | Dónde trabaja | Qué desbloquea |",
        "|---|---|---|---|---|---|---|",
    ]
    for gain, op, target, d_lmd, d_exp, where in rows:
        o = r.owned[op]
        unlocks = "; ".join(
            sorted({f"{s.facility} E{s.elite}: {s.text[:70]}" for s in texts[(op, target)]})
        )
        mark = "" if gain > floor else " (nada)" if gain < TIE else " (ruido)"
        lines.append(
            f"| {op} ({stars.get(op, '?')}★) | E{o.elite}→E{target} | {gain:+,.0f}{mark} "
            f"| {d_lmd:+,.0f} | {d_exp:+,.0f} | {where} | {unlocks} |".replace(",", ".")
        )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(out)


if __name__ == "__main__":
    main()
