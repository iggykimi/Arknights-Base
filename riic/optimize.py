"""Choose operators for every facility to maximise LMD + EXP per day.

The production facilities (FAC, TP) are chosen together because Trading Posts
can only sell the gold the Factories make; the CC, PP, RR and HR only add
flat buffs, so they are chosen around that core and the whole is repeated until
the assignment stops changing.
"""

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp

from .model import (
    BASEWIDE_MD,
    CC_PRODUCTIVE,
    ELITE_OPS,
    EXP_PER_DAY,
    GLASGOW,
    GOLD_PER_DAY,
    SMILEYS,
    Context,
    Roster,
    Settings,
    Shift,
    TPResult,
    cc_buffs,
    dorm_aoe,
    dorm_st,
    economy,
    evaluate,
    fac_pct,
    hr_pct,
    pp_pct,
    rr_pct,
    tp_result,
)

PER_OPERATOR = 20  # candidate teams kept per operator and kind
MIP_GAP = 1e-3  # see _production; comparisons between plans need a tighter one


@dataclass
class Plan:
    a: Shift
    b: Shift
    trainer: str | None
    workshop: str | None
    dorms: list[tuple[str | None, str | None]]  # (AoE, single target) per DORM
    settings: Settings

    def context(self, shift: Shift, r: Roster) -> Context:
        """The facts a facility reads from the rest of the base, for this shift."""
        ops = shift.operators()
        elite_facs = sum(1 for t, _ in shift.facs if ELITE_OPS & set(t))
        elite_facs += sum(1 for t in shift.tps if ELITE_OPS & set(t))
        elite_facs += sum(1 for o in shift.pps if o in ELITE_OPS)
        elite_facs += sum(1 for g in (shift.cc, shift.rr) if ELITE_OPS & set(g))
        elite_facs += sum(1 for o in (shift.hr, self.trainer, self.workshop) if o in ELITE_OPS)
        ctx = Context(
            self.settings,
            ines_working="Ines" in ops,
            recipe_types=len({p for _, p in shift.facs}),
            elite_facilities=elite_facs,
            logos_trainer=self.trainer == "Logos",
            gummy_in_tp=any("Gummy" in t for t in shift.tps),
        )
        ctx.cc = cc_buffs(shift.cc, r, self.settings)
        return ctx


def _production(r: Roster, ctx: Context, available: set[str], drone_pct: float):
    """Best disjoint FAC and TP teams, solved as an integer program.

    One binary per candidate team (Gold FAC, EXP FAC, TP) and one continuous
    "LMD sold" per TP, bounded by what the team can sell and, all together, by
    the gold the chosen Gold FACs make. The drones' extra LMD is a constant
    upper bound on the best TP, also paid in gold."""
    s = ctx.settings
    fac_pool = sorted(r.in_facility("FAC") & available)
    tp_pool = r.in_facility("TP") & available
    if r.has("Morgan", 2):
        tp_pool |= GLASGOW & available & set(r.owned)  # skill-less partners for Morgan
    tp_pool = sorted(tp_pool)

    teams: list[tuple[str, tuple[str, ...], float]] = []  # (kind, team, value)
    for team in combinations(fac_pool, 3):
        for product, per_day in (("Gold", GOLD_PER_DAY), ("EXP", EXP_PER_DAY)):
            teams.append((product, team, per_day * (1 + fac_pct(team, product, r, ctx) / 100)))
    tps: list[TPResult] = []
    for team in combinations(tp_pool, 3):
        if res := tp_result(team, r, ctx):
            teams.append(("TP", team, res.lmd))
            tps.append(res)
    if not teams:
        return [], []
    teams = [
        t for kind in ("Gold", "EXP", "TP") for t in _diverse([t for t in teams if t[0] == kind])
    ]
    tps = [tp_result(team, r, ctx) for kind, team, _ in teams if kind == "TP"]

    n = len(teams)
    tp_idx = [i for i, (k, _, _) in enumerate(teams) if k == "TP"]
    n_vars = n + len(tp_idx) + 1  # x teams, y LMD per TP, drone LMD
    drone_cap = max((t.lmd for t in tps), default=0) * drone_pct / 2 / 100

    c = np.zeros(n_vars)
    for i, (kind, _, value) in enumerate(teams):
        if kind == "EXP":
            c[i] = -value * s.exp_weight
    c[n:] = -1.0

    ops = sorted({o for _, team, _ in teams for o in team})
    op_row = {o: k for k, o in enumerate(ops)}
    rows, cols, vals, lo, hi = [], [], [], [], []

    def add(entries, low, high):
        row = len(lo)
        for col, val in entries:
            rows.append(row)
            cols.append(col)
            vals.append(val)
        lo.append(low)
        hi.append(high)

    per_op: dict[int, list[int]] = {}
    for i, (_, team, _) in enumerate(teams):
        for o in team:
            per_op.setdefault(op_row[o], []).append(i)
    for idx in per_op.values():
        add([(i, 1) for i in idx], 0, 1)
    fac_idx = [i for i, (k, _, _) in enumerate(teams) if k != "TP"]
    add([(i, 1) for i in fac_idx], 0, s.fac_count)  # a thin roster may not fill all
    add([(i, 1) for i in tp_idx], 0, s.tp_count)
    for j, i in enumerate(tp_idx):
        add([(n + j, 1), (i, -teams[i][2])], -np.inf, 0)  # sold <= capacity
    gold = [(i, -teams[i][2]) for i, (k, _, _) in enumerate(teams) if k == "Gold"]
    gold += [(n + j, 1 / tps[j].lmd_per_gold) for j in range(len(tp_idx))]
    gold += [(n_vars - 1, 1 / 500)]
    add(gold, -np.inf, 0)  # gold sold <= gold made

    a = sparse.csr_array((vals, (rows, cols)), shape=(len(lo), n_vars))
    integrality = np.r_[np.ones(n), np.zeros(n_vars - n)]
    upper = np.r_[np.ones(n), np.full(len(tp_idx), np.inf), drone_cap]
    res = milp(
        c,
        constraints=LinearConstraint(a, lo, hi),
        integrality=integrality,
        bounds=Bounds(np.zeros(n_vars), upper),
        # Within 0.1% of the optimum is far below the guide's own rounding; some
        # CC buffs make HiGHS spend minutes proving the last decimals otherwise.
        options={"mip_rel_gap": MIP_GAP, "time_limit": 60},
    )
    if res.x is None:
        raise RuntimeError(f"MILP failed: {res.message}")
    chosen = [teams[i] for i in range(n) if res.x[i] > 0.5]
    facs = [(team, kind) for kind, team, _ in chosen if kind != "TP"]
    return facs, [team for kind, team, _ in chosen if kind == "TP"]


def _diverse(teams: list[tuple[str, tuple[str, ...], float]]) -> list:
    """Keep the PER_OPERATOR best teams each operator is in.

    A team below every member's top list would need all its members to be
    unusable elsewhere to be worth picking; dropping those cuts the solve from
    ~38 s to ~3 s on this roster with the same result."""
    seen: dict[str, int] = {}
    kept = []
    for t in sorted(teams, key=lambda t: -t[2]):
        if any(seen.get(o, 0) < PER_OPERATOR for o in t[1]):
            kept.append(t)
            for o in t[1]:
                seen[o] = seen.get(o, 0) + 1
    return kept


def _best_cc(r, ctx: Context, available: set[str], facs, tps) -> tuple[str, ...]:
    """Productive CC members for these teams; ties go to fewer and earlier members."""
    s = ctx.settings
    cands = [o for o in CC_PRODUCTIVE if o in available and r.has(o)]
    best_val, best_cc = -1.0, ()
    for size in range(6):
        for cc in combinations(cands, size):
            ctx.cc = cc_buffs(cc, r, s)
            f = [(fac_pct(t, p, r, ctx), p) for t, p in facs]
            t = [x for x in (tp_result(t, r, ctx) for t in tps) if x]
            val = economy(f, t, 0, s).value
            if val > best_val + 1e-6:
                best_val, best_cc = val, cc
    return best_cc


def _fill_cc(cc: tuple[str, ...], r: Roster, available: set[str]) -> tuple[str, ...]:
    """Fill free CC slots with morale-drain reducers: Młynar, then Smileys."""
    need = {"Młynar": 2, "Wiš'adel": 2, **BASEWIDE_MD}
    order = ["Młynar", "Wiš'adel", *sorted(BASEWIDE_MD), *sorted(SMILEYS)]
    out = list(cc)
    for op in order:
        if len(out) == 5:
            break
        if op in available and op not in out and r.has(op, need.get(op, 0)):
            out.append(op)
    return tuple(out)


def _best_rr(r: Roster, ctx: Context, available: set[str]) -> tuple[str, ...]:
    pool = sorted(r.in_facility("RR") & available)
    return max(combinations(pool, 2), key=lambda t: rr_pct(t, r, ctx), default=())


def _best_hr(r: Roster, ctx: Context, available: set[str]) -> str | None:
    pool = sorted(r.in_facility("HR") & available)
    return max(pool, key=lambda o: hr_pct(o, r, ctx), default=None)


def best_shift(r: Roster, plan: Plan, available: set[str], rounds: int = 5) -> Shift:
    s = plan.settings
    shift = Shift((), [], [], [], (), None)
    for _ in range(rounds):
        ctx = plan.context(shift, r)
        drone = sum(pp_pct(o, r, ctx) for o in shift.pps)
        facs, tps = _production(r, ctx, available - set(shift.cc), drone)
        used = {o for t, _ in facs for o in t} | {o for t in tps for o in t}
        pps = sorted(
            (r.in_facility("PP") & available) - used, key=lambda o: (-pp_pct(o, r, ctx), o)
        )[: s.pp_count]
        used |= set(pps)
        cc = _best_cc(r, ctx, available - used, facs, tps)
        used |= set(cc)
        ctx.cc = cc_buffs(cc, r, s)
        rr = _best_rr(r, ctx, available - used)
        hr = _best_hr(r, ctx, available - used - set(rr))
        new = Shift(cc, facs, tps, pps, rr, hr)
        if new == shift:
            break
        shift = new
    filled = _fill_cc(shift.cc, r, available - shift.operators())
    return Shift(filled, shift.facs, shift.tps, shift.pps, shift.rr, shift.hr)


def _workshop(r: Roster, available: set[str]) -> str | None:
    """Best crafter for every recipe (WS!B161 "General Crafters")."""
    pool = [
        s
        for (op, fac), skills in r.active.items()
        if fac == "WS" and op in available
        for s in skills
        if s.effect and s.section == "General Crafters"
    ]
    return max(pool, key=lambda s: s.effect.pct).operator if pool else None


def _dorms(r: Roster, s: Settings, available: set[str]):
    aoe = sorted((o for o in r.in_facility("DORM") & available if dorm_aoe(o, r, s) > 0),
                 key=lambda o: (-dorm_aoe(o, r, s), o))  # fmt: skip
    chosen_aoe = aoe[:4]
    st = sorted(
        (o for o in r.in_facility("DORM") & available - set(chosen_aoe) if dorm_st(o, r) > 0),
        key=lambda o: (-dorm_st(o, r), o),
    )[:4]
    return [
        (chosen_aoe[i] if i < len(chosen_aoe) else None, st[i] if i < len(st) else None)
        for i in range(4)
    ]


def build_plan(r: Roster, s: Settings) -> Plan:
    everyone = set(r.owned)
    trainer = "Logos" if r.has("Logos", 2) else None  # TR!J28: unique trainer
    plan = Plan(Shift((), [], [], [], (), None), Shift((), [], [], [], (), None),
                trainer, None, [], s)  # fmt: skip
    plan.workshop = _workshop(r, everyone - {trainer})
    fixed = {trainer, plan.workshop} - {None}
    plan.a = best_shift(r, plan, everyone - fixed)
    plan.dorms = _dorms(r, s, everyone - fixed - plan.a.operators())
    in_dorms = {o for pair in plan.dorms for o in pair if o}
    plan.b = best_shift(r, plan, everyone - fixed - plan.a.operators() - in_dorms)
    return plan


def plan_value(plan: Plan, r: Roster, shift: Shift):
    return evaluate(shift, r, plan.context(shift, r))


def all_assigned(plan: Plan) -> list[str]:
    ops = [*plan.a.operators(), *plan.b.operators()]
    ops += [o for o in (plan.trainer, plan.workshop) if o]
    ops += [o for pair in plan.dorms for o in pair if o]
    return ops
