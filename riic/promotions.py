"""python -m riic.promotions: what each promotion would add to the base.

For every owned operator whose next promotion unlocks a CC, FAC, TP or PP skill,
the whole plan (both shifts) is rebuilt with that operator promoted, and the
gain is the change in daily LMD + EXP over the 12 h rotation.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from . import optimize
from .excel import operator_ids
from .gamedata import all_skills, download, rarities
from .model import MODELLED, Roster, Settings
from .optimize import build_plan, plan_value
from .roster import load_roster

ROOT = Path(__file__).resolve().parent.parent
PRODUCTIVE = ("CC", "FAC", "TP", "PP")
OUT = "no entra en el plan"
GAP = 1e-4  # comparing plans needs the solver closer to the optimum than one plan does


def max_elite(stars: int) -> int:
    return 0 if stars <= 2 else 1 if stars == 3 else 2


def daily(r: Roster, s: Settings) -> tuple[float, float, dict[str, str]]:
    """(LMD, EXP) per day over a 12 h A/B rotation, and where each operator works."""
    optimize.MIP_GAP = GAP  # per process: workers import a fresh module
    plan = build_plan(r, s)
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
    owned, skills, settings, op, target = job
    owned = dict(owned)
    owned[op] = replace(owned[op], elite=target, level=1)
    lmd, exp, where = daily(Roster(owned, skills), settings)
    return op, target, lmd, exp, where.get(op, OUT)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--excel", type=Path, default=ROOT / "Arknights Base Combo Guide.xlsx")
    ap.add_argument("--collection", type=Path, default=ROOT / "Collection.txt")
    ap.add_argument("--cache", type=Path, default=ROOT / ".cache" / "gamedata")
    ap.add_argument("--out", type=Path, default=ROOT / "promotions.md")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    settings = Settings()
    skills = all_skills(args.excel, args.cache)
    stars = rarities(download(args.cache), operator_ids(args.excel))
    r = Roster(load_roster(args.collection), skills)
    base_lmd, base_exp, _ = daily(r, settings)
    jobs = candidates(r, stars)
    print(f"{len(jobs)} promociones a probar")

    texts = {(op, t): new for op, t, new in jobs}
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(_run, [(r.owned, skills, settings, op, t) for op, t, _ in jobs]))

    rows = []
    for op, target, lmd, exp, where in results:
        gain = (lmd - base_lmd) + (exp - base_exp) * settings.exp_weight
        rows.append((gain, op, target, lmd - base_lmd, exp - base_exp, where))
    rows.sort(reverse=True)
    # An operator who stays out of the plan cannot change it: what moves is solver noise.
    noise = max((abs(g) for g, *_, w in rows if w == OUT), default=0.0)

    lines = [
        "# Promociones que merecen la pena para la base",
        "",
        (
            "Generado con `python -m riic.promotions`. Cada fila rehace el plan entero (turnos A y B) "
            "con ese operador promocionado y compara con el plan actual. Ganancia = LMD + EXP por día "
            f"con rotación de 12 h. Ruido medido: ±{noise:.0f} (lo que se mueve el plan con "
            "promociones de operadores que no llegan a usarse); por debajo, «(ruido)». Una "
            "ganancia negativa sale porque el turno A se elige antes que el B: el promocionado "
            "mejora A y le quita al B más de lo que A gana."
        ),
        "",
        f"Plan actual: {base_lmd:,.0f} LMD + {base_exp:,.0f} EXP al día.".replace(",", "."),
        "",
        "| Operador | Promoción | Ganancia/día | LMD | EXP | Dónde trabaja | Qué desbloquea |",
        "|---|---|---|---|---|---|---|",
    ]
    for gain, op, target, d_lmd, d_exp, where in rows:
        o = r.owned[op]
        unlocks = "; ".join(
            sorted({f"{s.facility} E{s.elite}: {s.text[:70]}" for s in texts[(op, target)]})
        )
        mark = "" if gain > noise else " (ruido)"
        lines.append(
            f"| {op} ({stars.get(op, '?')}★) | E{o.elite}→E{target} | {gain:+,.0f}{mark} "
            f"| {d_lmd:+,.0f} | {d_exp:+,.0f} | {where} | {unlocks} |".replace(",", ".")
        )
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
