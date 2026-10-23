"""Choose operators for every facility to maximise LMD + EXP per day.

Factories and Trading Posts of both 12 h shifts are chosen in one integer
program: Trading Posts can only sell the gold the Factories make, and every
operator works in one shift at most. The CC, PP, RR and HR only add flat buffs,
so they are chosen around that core and the whole is repeated until the
assignment stops changing.
"""

from dataclasses import dataclass, replace
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


def _teams(r: Roster, ctx: Context, available: set[str]):
    """Candidate (kind, team, value per day, TPResult) for one shift's context."""
    fac_pool = sorted(r.in_facility("FAC") & available)
    tp_pool = r.in_facility("TP") & available
    if r.has("Morgan", 2):
        tp_pool |= GLASGOW & available & set(r.owned)  # skill-less partners for Morgan
    teams = []
    for team in combinations(fac_pool, 3):
        for product, per_day in (("Gold", GOLD_PER_DAY), ("EXP", EXP_PER_DAY)):
            value = per_day * (1 + fac_pct(team, product, r, ctx) / 100)
            teams.append((product, team, value, None))
    for team in combinations(sorted(tp_pool), 3):
        if res := tp_result(team, r, ctx):
            teams.append(("TP", team, res.lmd, res))
    by_kind = [_diverse([t for t in teams if t[0] == kind]) for kind in ("Gold", "EXP", "TP")]
    return [t for kind in by_kind for t in kind]


def _production(r: Roster, ctxs: list[Context], available: set[str], drones: list[float]):
    """Best FAC and TP teams for every shift at once, as an integer program.

    One binary per candidate team and shift, and one continuous "LMD sold" per TP
    team, bounded by what the team can sell and, per shift, by the gold that
    shift's Gold FACs make. The drones' extra LMD is a constant upper bound on the
    shift's best TP, also paid in gold. Returns [(facs, tps)] per shift."""
    s = ctxs[0].settings
    teams = [(k, *t) for k, ctx in enumerate(ctxs) for t in _teams(r, ctx, available)]
    n = len(teams)
    tp_idx = [i for i, t in enumerate(teams) if t[1] == "TP"]
    y_col = {i: n + j for j, i in enumerate(tp_idx)}  # LMD sold by TP team i
    d_col = [n + len(tp_idx) + k for k in range(len(ctxs))]  # drone LMD per shift
    n_vars = n + len(tp_idx) + len(ctxs)

    c = np.zeros(n_vars)
    for i, (_, kind, _, value, _) in enumerate(teams):
        if kind == "EXP":
            c[i] = -value * s.exp_weight
    c[n:] = -1.0

    rows, cols, vals, lo, hi = [], [], [], [], []

    def add(entries, low, high):
        for col, val in entries:
            rows.append(len(lo))
            cols.append(col)
            vals.append(val)
        lo.append(low)
        hi.append(high)

    per_op: dict[str, list[int]] = {}
    for i, (_, _, team, _, _) in enumerate(teams):
        for o in team:
            per_op.setdefault(o, []).append(i)
    for idx in per_op.values():
        add([(i, 1) for i in idx], 0, 1)  # one team, one shift
    for k in range(len(ctxs)):
        mine = [i for i, t in enumerate(teams) if t[0] == k]
        add([(i, 1) for i in mine if teams[i][1] != "TP"], 0, s.fac_count)
        if s.gold_facs is not None:
            add([(i, 1) for i in mine if teams[i][1] == "Gold"], s.gold_facs, s.gold_facs)
        add([(i, 1) for i in mine if teams[i][1] == "TP"], 0, s.tp_count)
        gold = [(i, -teams[i][3]) for i in mine if teams[i][1] == "Gold"]
        gold += [(y_col[i], 1 / teams[i][4].lmd_per_gold) for i in mine if i in y_col]
        add([*gold, (d_col[k], 1 / 500)], -np.inf, 0)  # gold sold <= gold made
    for i in tp_idx:
        add([(y_col[i], 1), (i, -teams[i][3])], -np.inf, 0)  # sold <= capacity

    drone_cap = []
    for k in range(len(ctxs)):
        best_tp = max((t[3] for t in teams if t[0] == k and t[1] == "TP"), default=0)
        drone_cap.append(best_tp * drones[k] / 2 / 100)
    upper = np.r_[np.ones(n), np.full(len(tp_idx), np.inf), drone_cap]
    res = milp(
        c,
        constraints=LinearConstraint(
            sparse.csr_array((vals, (rows, cols)), shape=(len(lo), n_vars)), lo, hi
        ),
        integrality=np.r_[np.ones(n), np.zeros(n_vars - n)],
        bounds=Bounds(np.zeros(n_vars), upper),
        # Within 0.1% of the optimum is far below the guide's own rounding; some
        # CC buffs make HiGHS spend minutes proving the last decimals otherwise.
        options={"mip_rel_gap": MIP_GAP, "time_limit": 120},
    )
    if res.x is None:
        raise RuntimeError(f"MILP failed: {res.message}")
    out = []
    for k in range(len(ctxs)):
        chosen = [teams[i] for i in range(n) if teams[i][0] == k and res.x[i] > 0.5]
        facs = [(team, kind) for _, kind, team, _, _ in chosen if kind != "TP"]
        out.append((facs, [team for _, kind, team, _, _ in chosen if kind == "TP"]))
    return out


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


def _fill_cc(cc: tuple[str, ...], r: Roster, s: Settings, available: set[str]):
    """Fill free CC slots: first whoever adds clue or HR speed (Civilight Eterna,
    Umiri...), then morale-drain reducers (Młynar, Wiš'adel, Smileys)."""

    def support(cc) -> float:
        b = cc_buffs(tuple(cc), r, s)
        return b.rr + b.rr_ines + b.hr

    out = list(cc)
    while len(out) < 5:
        cands = [o for o in CC_PRODUCTIVE if o in available and o not in out and r.has(o)]
        best = max(cands, key=lambda o: support([*out, o]), default=None)
        if best is None or support([*out, best]) <= support(out):
            break  # only the strongest buff of a kind counts: a second one adds nothing
        out.append(best)
    need = {"Młynar": 2, "Wiš'adel": 2, **BASEWIDE_MD}
    for op in ["Młynar", "Wiš'adel", *sorted(BASEWIDE_MD), *sorted(SMILEYS)]:
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


def build_plan(r: Roster, s: Settings, rounds: int = 6) -> Plan:
    everyone = set(r.owned)
    trainer = "Logos" if r.has("Logos", 2) else None  # TR!J28: unique trainer
    empty = Shift((), [], [], [], (), None)
    plan = Plan(empty, empty, trainer, None, [], s)
    plan.workshop = _workshop(r, everyone - {trainer})
    pool = everyone - {trainer, plan.workshop}

    for _ in range(rounds):
        shifts = [plan.a, plan.b]
        ctxs = [plan.context(sh, r) for sh in shifts]
        drones = [sum(pp_pct(o, r, c) for o in sh.pps) for sh, c in zip(shifts, ctxs)]
        production = _production(r, ctxs, pool - set(plan.a.cc) - set(plan.b.cc), drones)
        used = {o for facs, tps in production for t in [*(t for t, _ in facs), *tps] for o in t}
        new = []
        for (facs, tps), ctx in zip(production, ctxs):
            pps = sorted(
                (r.in_facility("PP") & pool) - used, key=lambda o: (-pp_pct(o, r, ctx), o)
            )[: s.pp_count]
            used |= set(pps)
            cc = _best_cc(r, ctx, pool - used, facs, tps)
            used |= set(cc)
            ctx.cc = cc_buffs(cc, r, s)
            rr = _best_rr(r, ctx, pool - used)
            used |= set(rr)
            hr = _best_hr(r, ctx, pool - used)
            used |= {hr} - {None}
            new.append(Shift(cc, facs, tps, pps, rr, hr))
        if new == [plan.a, plan.b]:
            break
        plan.a, plan.b = new

    if plan_value(plan, r, plan.b).value > plan_value(plan, r, plan.a).value:
        plan.a, plan.b = plan.b, plan.a  # A is the stronger shift
    busy = plan.a.operators() | plan.b.operators()
    plan.dorms = _dorms(r, s, pool - busy)
    free = pool - busy - {o for pair in plan.dorms for o in pair if o}
    plan.a = replace(plan.a, cc=_fill_cc(plan.a.cc, r, s, free))
    plan.b = replace(plan.b, cc=_fill_cc(plan.b.cc, r, s, free - set(plan.a.cc)))
    return plan


def plan_value(plan: Plan, r: Roster, shift: Shift):
    return evaluate(shift, r, plan.context(shift, r))


def all_assigned(plan: Plan) -> list[str]:
    ops = [*plan.a.operators(), *plan.b.operators()]
    ops += [o for o in (plan.trainer, plan.workshop) if o]
    ops += [o for pair in plan.dorms for o in pair if o]
    return ops
