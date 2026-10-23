"""Base output for an assignment of owned operators, using the guide's formulas.

Simple skills come parsed from the workbook (``excel.py``). Skills whose value
depends on the rest of the base are written here, each with the cell it comes from.

Output is measured per day with the in-game recipe numbers:
- Pure Gold: 72 min per bar -> 20 bars/day at +0%.
- Tactical Battle Record (lvl 3 FAC): 1000 EXP per 180 min -> 8000 EXP/day at +0%.
- Lvl 3 TP order mix 30/50/20% of 2/3/4-gold orders (TP!E45:I45), 500 LMD per gold
  and 144/210/276 min -> 1450 LMD per 203.4 min -> 10265 LMD/day at +0%.
- Drones: "10% Drone Recovery Speed ~ 5% productivity" (PP!B5), all sent to the
  best TP.
"""

import re
from dataclasses import dataclass, field

from .excel import Effect, Skill, norm
from .roster import Owned

GOLD_PER_DAY = 20.0
EXP_PER_DAY = 8000.0
TP_LMD_PER_DAY = 1440 / (0.3 * 144 + 0.5 * 210 + 0.2 * 276) * 1450
LMD_PER_GOLD = 500.0

FAC_INNATE = TP_INNATE = 3.0  # lvl 3 FAC/TP (FAC!B4, TP!B4)
PP_INNATE = 5.0  # PP!B4
HR_INNATE = 5.0  # HR!B4

# TP!D193: Proviso's order multiplier in a lvl 3 TP (E0, E2).
PROVISO_MULT = {0: 1.275862, 2: 1.551724}
# NEW!F23: Closure's orders are 1200 LMD for 2 gold in 144 min.
CLOSURE_MULT = 1440 / 144 * 1200 / TP_LMD_PER_DAY
# TP!J21:J28: Shamare team by (Tequila tier, better-orders tier); None = absent.
SHAMARE_TEAM = {
    (2, 2): 138.21,
    (2, 0): 128.12,
    (2, None): 124.39,
    (0, 2): 115.52,
    (0, 0): 110.08,
    (0, None): 108.07,
    (None, 2): 92.8,
    (None, 0): 91.6,  # "Shamare + other"; E0 better-orders is not listed separately
    (None, None): 91.6,
}
# TP!H36:N36 / game "higher-yield Precious Metal orders": Bibeak-type skills.
_BETTER_ORDERS = re.compile(r"better orders|higher-yield Precious Metal orders")

# CC!B38:P43: "Smileys" (-0.05 MD in CC) that Młynar E2 applies base-wide.
SMILEYS = {
    "Młynar", "Dobermann", "Scavenger", "Projekt Red", "Nearl", "Greythroat",
    "Heavyrain", "Coldshot", "Flametail", "Viviana", "Mon3tr", "Raidian",
}  # fmt: skip
# CC!F48:N48: -0.05 MD in FAC/TP/PP/RR/HR each, from CC (minimum promotion).
BASEWIDE_MD = {"Closure": 0, "Dur-nar": 1, "Executor": 2, "Reed": 2, "Kestrel": 2}
# SPECIAL!B270:N270 and SPECIAL!B256: Black Steel Worldwide.
BSW = {"Jessica", "Vanilla", "Almond", "Liskarm", "Franka"}
# SPECIAL!B419:J424: Elite Operators for Mantra / Kal'tsit Alter.
ELITE_OPS = {"Mantra", "Kal'tsit Alter", "Rosmontis", "Raidian", "Mechanist", "Logos",
             "Blaze", "Blaze Alter"}  # fmt: skip
LGD = {"Ch'en", "Swire", "Hoshiguma", "Hoshiguma Alter"}  # CC!B198:F198
A1 = {"Fang", "Kroos"}  # FAC!B197:F197, Reserve Op A1 partners
GLASGOW = {"Morgan", "Siege", "Vina Victoria", "Indra", "Dagda"}  # TP!B154:J154

LAYOUTS = {"243": (2, 4, 3), "252": (2, 5, 2), "333": (3, 3, 3), "342": (3, 4, 2)}

# Conditional skills that have a formula below, by facility.
MODELLED = {
    "FAC": {"Mizuki", "Dorothy", "Purestream", "Ceobe", "Fang", "Kroos", "Totter",
            "Minimalist", "Vermeil", "Bubble", "Astgenne Alter", "Waai Fu", "Leto",
            "Miss Christine", "Fang Alter", "Aroma", "Almond", "Viy"},
    "TP": {"Shamare", "Tequila", "Proviso", "Closure", "Kichisei", "Archetto", "Hoederer",
           "Lemuen", "Quartz", "Underflow", "Texas", "Lappland", "Mantra", "Snowsant",
           "Vigil", "Mitm", "Morgan"},
    "PP": {"Greyy Alter", "Spuria", "Friston-3", "PhonoR-0", "Philae"},
    "RR": {"Ines", "Ch'en Alter 2", "Surfer", "Typhon"},
    "HR": {"Tin Man", "Mr.Nothing", "Brigid", "Kal'tsit Alter"},
    "DORM": {"Lumen", "Entelechia"},
    "CC": {"Amiya", "Paprika", "Ascalon", "Wang", "Kal'tsit", "Mon3tr", "Hoshiguma Alter",
           "Togawa Sakiko", "Wakaba Mutsumi", "Misumi Uika", "Yahata Umiri", "Yūtenji Nyamu",
           "Civilight Eterna", "Wiš'adel", *SMILEYS, *BASEWIDE_MD},
}  # fmt: skip


@dataclass(frozen=True)
class Settings:
    layout: str = "243"
    office_level: int = 3  # HR!B5: upgrading Office no longer matters; most bases have 3
    dorm_levels: int = 20  # 4 DORMs at lvl 5
    rr_bonus: float = 11 + 15  # RR!F24 lvl 3 + RR!H24 ambience >4k
    exp_weight: float = 1.0  # value of 1 EXP in LMD

    @property
    def tp_count(self) -> int:
        return LAYOUTS[self.layout][0]

    @property
    def fac_count(self) -> int:
        return LAYOUTS[self.layout][1]

    @property
    def pp_count(self) -> int:
        return LAYOUTS[self.layout][2]


def ramp_avg(start: float, end: float, per_hour: float, hours: int = 12) -> float:
    """Mean over the first ``hours`` hours, counted per whole hour like the guide."""
    return sum(min(end, start + per_hour * h) for h in range(hours)) / hours


def unlocked(o: Owned, s: Skill) -> bool:
    """A level condition ("E0 lvl 30") only binds at that promotion; any higher
    promotion already passed it, even back at level 1."""
    if o.elite != s.elite:
        return o.elite > s.elite
    return s.level is None or (o.level or 0) >= s.level


class Roster:
    """Owned operators and the skills they can use at their current promotion."""

    def __init__(self, owned: dict[str, Owned], skills: list[Skill]):
        spelling = {norm(s.operator): s.operator for s in skills}
        self.owned = {spelling.get(norm(n), n): o for n, o in owned.items()}
        self.skills = skills
        # RR!B39:B95 groups Reception Room workers under "RR (6* Operators...)" headers.
        self.rarity = {
            s.operator: int(m[1])
            for s in skills
            if s.facility == "RR" and (m := re.search(r"(\d)\* Operators", s.section))
        }
        self.active: dict[tuple[str, str], list[Skill]] = {}
        for s in skills:
            o = self.owned.get(s.operator)
            if o and unlocked(o, s):
                self.active.setdefault((s.operator, s.facility), []).append(s)
        # Operator -> best active "better orders" tier (0 slightly, 2 increased).
        self.better_orders = {}
        for (op, fac), active in self.active.items():
            tiers = [s.elite for s in active if fac == "TP" and _BETTER_ORDERS.search(s.text)]
            if tiers and op not in ("Shamare", "Texas"):
                self.better_orders[op] = 2 if max(tiers) >= 2 else 0

    def elite(self, op: str) -> int:
        o = self.owned.get(op)
        return o.elite if o else -1

    def has(self, op: str, elite: int = 0) -> bool:
        return self.elite(op) >= elite

    def effects(self, op: str, facility: str) -> list[Effect]:
        """Parsed effects, keeping per unit only the best promotion that applies."""
        best: dict[tuple, tuple[int, Effect]] = {}
        for s in self.active.get((op, facility), []):
            if s.effect is None:
                continue
            key = (s.effect.unit, s.effect.tag, s.effect.cap_product, bool(s.effect.cap),
                   bool(s.effect.st_mr), bool(s.effect.aoe_mr), bool(s.effect.self_mr))  # fmt: skip
            if key not in best or s.elite >= best[key][0]:
                best[key] = (s.elite, s.effect)
        return [e for _, e in best.values()]

    def in_facility(self, facility: str) -> set[str]:
        return {op for op, f in self.active if f == facility}


# --------------------------------------------------------------------------- CC


@dataclass(frozen=True)
class CCBuffs:
    fac: float = 0.0  # to all FACs; only the highest applies (CC!B212)
    gold_fac: float = 0.0  # Sakiko, stacks with the above (SPECIAL!B361)
    tp: float = 0.0  # to all TPs; only the highest applies (CC!B228)
    rr: float = 0.0
    rr_ines: float = 0.0  # Wiš'adel E0: +5% RR for Ines (SPECIAL!B401)
    hr: float = 0.0
    kaltsit: bool = False  # Friston-3 condition


def cc_buffs(cc: tuple[str, ...], r: Roster, s: Settings) -> CCBuffs:
    fac = tp = rr = hr = 0.0
    if "Kal'tsit" in cc and r.has("Kal'tsit", 2):
        fac = max(fac, 2)  # CC!J220
    if "Mon3tr" in cc and r.has("Mon3tr", 2):
        fac = max(fac, 2)  # CC!H222
    if (
        "Hoshiguma Alter" in cc
        and r.has("Hoshiguma Alter", 2)
        and any(o in LGD and o != "Hoshiguma Alter" for o in cc)
    ):
        fac = max(fac, 3)  # CC!D222
    for op in ("Amiya", "Paprika"):
        if op in cc and r.has(op):
            tp = max(tp, 7)  # CC!B236, CC!F236
    if "Ascalon" in cc and r.has("Ascalon", 2):
        tp = max(tp, 7)  # CC!L238
    if "Wang" in cc and r.has("Wang"):  # CC!B220
        if s.tp_count + s.pp_count >= s.fac_count:
            tp = max(tp, 7)
        else:
            fac = max(fac, 2)

    # SPECIAL!B371:P375: Ave Mujica's Passion.
    passion = 0
    if "Wakaba Mutsumi" in cc:
        passion += 20
    if "Yahata Umiri" in cc:
        passion += 10
        hr = max(hr, 10)
    if "Yūtenji Nyamu" in cc:
        passion += 10
        rr = max(rr, 5)
    if "Misumi Uika" in cc:
        passion += 20  # +1 per operator in DORMs; 4 DORMs x 5 (SPECIAL!F375)
    if "Wakaba Mutsumi" in cc:
        tp = max(tp, passion // 8)
    gold_fac = 0.0
    if "Togawa Sakiko" in cc and r.has("Togawa Sakiko"):
        step = 1.0 if r.has("Togawa Sakiko", 2) else 0.5
        gold_fac = step + step * (passion // 20)

    if "Civilight Eterna" in cc and r.has("Civilight Eterna", 2):
        rr = max(rr, 15)  # CC!D253
    rr_ines = 5.0 if "Wiš'adel" in cc and r.has("Wiš'adel") else 0.0
    return CCBuffs(fac, gold_fac, tp, rr, rr_ines, hr, "Kal'tsit" in cc)


# Operators whose CC skill changes output; the rest of CC is morale drain only.
CC_PRODUCTIVE = (
    "Amiya", "Paprika", "Ascalon", "Wang", "Kal'tsit", "Mon3tr", "Hoshiguma Alter",
    "Hoshiguma", "Togawa Sakiko", "Wakaba Mutsumi", "Misumi Uika", "Yahata Umiri",
    "Yūtenji Nyamu", "Civilight Eterna", "Wiš'adel",
)  # fmt: skip


# -------------------------------------------------------------------------- FAC


def fac_pct(team: tuple[str, ...], product: str, r: Roster, ctx: "Context") -> float:
    """Productivity of a lvl 3 FAC making ``product``, innate and CC included."""
    total = FAC_INNATE + ctx.cc.fac + (ctx.cc.gold_fac if product == "Gold" else 0)
    caps: dict[str, int] = {}
    standard = rhine_tech = 0
    for op in team:
        for e in r.effects(op, "FAC"):
            if e.product in (None, product):
                total += e.pct
                standard += e.tag == "Standard" and e.pct > 0
                rhine_tech += e.tag == "Rhine Tech" and e.pct > 0
            if e.cap and e.cap_product in (None, product):
                caps[op] = caps.get(op, 0) + e.cap
    for op in team:
        total += _fac_special(op, team, product, r, ctx, standard, rhine_tech, caps)

    if "Waai Fu" in team and r.has("Waai Fu", 2):
        # FAC!B315: +5% per 5% the others give with plain skills, max +40%.
        plain = sum(
            e.pct for o in team if o != "Waai Fu" for e in r.effects(o, "FAC")
            if e.product in (None, product) and e.pct > 0
        )  # fmt: skip
        total += min(40, 5 * (plain // 5))
    if "Astgenne Alter" in team:
        caps["Astgenne Alter"] = 5 * rhine_tech  # FAC!J180
    if "Vermeil" in team and r.has("Vermeil", 1):
        total += 2 * sum(caps.values())  # FAC!B33: +2% per CAP from self and others
    elif "Bubble" in team and r.has("Bubble", 1):
        total += sum(3 * c if c > 16 else c for c in caps.values())  # FAC!B108
    return total


def _fac_special(op, team, product, r: Roster, ctx, standard, rhine_tech, caps) -> float:
    e = r.elite(op)
    if op == "Mizuki" and e >= 0:
        return 5 * standard  # FAC!B156
    if op == "Dorothy" and e >= 0:
        return 5 * rhine_tech  # FAC!B180
    if op == "Purestream" and e >= 1 and product == "Gold":
        return 20 * ctx.settings.tp_count  # FAC!D220
    if op == "Ceobe" and e >= 2:
        return ramp_avg(20, 25, 1)  # FAC!D55
    if op == "Fang" and e >= 0:
        return ramp_avg(20, 25, 1)  # FAC!J342
    if op == "Kroos" and e >= 0:
        return ramp_avg(15, 25, 2)  # FAC!P342
    if op == "Totter" and e >= 0:
        return 27.5  # FAC!B346, first 12 h average
    if op == "Minimalist" and e >= 0:
        er = 64 if ctx.settings.pp_count >= 3 else 40  # FAC!F317: 40/25% max at E2
        return 5 * (er // (8 if e >= 2 else 16))
    if e < 2:
        return 0.0
    if op == "Leto" and product == "EXP" and ctx.gummy_in_tp:
        return 35  # FAC!N270
    if op == "Miss Christine" and product == "EXP" and "Tragodia" in team:
        return 30  # FAC!H35
    if op == "Fang Alter":
        return 10 * len(A1 & set(team) - {op})  # FAC!B200, Fang + Kroos -> FAC!J188 70-85%
    if op == "Aroma" and product == "Gold":
        return ramp_avg(0, 20, 2)  # FAC!J243
    if op == "Almond" and product == "Gold":
        return 2 * min(3, len(BSW & set(r.owned)))  # FAC!N241, BSW in the base
    if op == "Viy":
        return 10 * 3  # FAC!N313: +10% per TR level, TR lvl 3
    return 0.0


# --------------------------------------------------------------------------- TP


@dataclass(frozen=True)
class TPResult:
    pct: float  # productivity, innate and CC included
    mult: float  # LMD per order relative to a normal lvl 3 TP
    lmd_per_gold: float

    @property
    def lmd(self) -> float:
        return TP_LMD_PER_DAY * (1 + self.pct / 100) * self.mult

    @property
    def gold(self) -> float:
        return self.lmd / self.lmd_per_gold


def tp_result(team: tuple[str, ...], r: Roster, ctx: "Context") -> TPResult | None:
    """None when the team breaks a rule (Proviso with Tequila, two order manipulators)."""
    base = TP_INNATE + ctx.cc.tp
    proviso = "Proviso" in team and r.has("Proviso")
    closure = "Closure" in team and r.has("Closure", 2)
    shamare = "Shamare" in team and r.has("Shamare", 2)
    if proviso + closure + shamare > 1:
        return None
    if proviso and any(o == "Tequila" or o in r.better_orders for o in team):
        return None  # TP!B173: Proviso doesn't work with Tequila nor better-orders skills

    if shamare:
        teq = (2 if r.has("Tequila", 2) else 0) if "Tequila" in team else None
        orders = [r.better_orders[o] for o in team if o in r.better_orders]
        bib = max(orders) if orders else None
        if len(team) < 3:
            return TPResult(base + 45 * (len(team) - 1), 1.0, LMD_PER_GOLD)
        return TPResult(base + SHAMARE_TEAM[(teq, bib)], 1.0, LMD_PER_GOLD)

    pct = base + sum(_tp_pct(op, team, r, ctx) for op in team)
    if proviso:
        return TPResult(pct, PROVISO_MULT[2 if r.has("Proviso", 2) else 0], LMD_PER_GOLD)
    if closure:
        return TPResult(pct + 10, CLOSURE_MULT, 600.0)
    return TPResult(pct, 1.0, LMD_PER_GOLD)


def _tp_pct(op: str, team, r: Roster, ctx: "Context") -> float:
    e = r.elite(op)
    others = len(team) - 1
    if op == "Kichisei":
        return (20 if e >= 2 else 10) * others  # TP!D240
    if op == "Archetto":
        return (2 if e >= 2 else 1) * ctx.settings.dorm_levels  # TP!P240
    if op == "Hoederer":
        return (30 if e >= 2 else 25) + (5 if ctx.ines_working else 0)  # TP!N240
    if op == "Lemuen":
        exu = e >= 2 and ({"Exusiai", "Exusiai Alter"} & set(team))
        return 20 + (25 if exu else 0)  # TP!B240:B241
    if op == "Quartz" and e >= 1:
        return 30 + 2 * ctx.recipe_types  # TP!L253
    if op == "Underflow":
        return 30 if e >= 2 else 25  # TP!J240 (no Ulpianus)
    if op == "Texas":
        return 65 if "Lappland" in team else 0  # TP!D90
    if op == "Vigil" and e >= 2:
        return 25 + 5 * 3  # TP!F240, RR lvl 3
    if op == "Mitm" and e >= 2:
        return 15 + 5 * 3  # TP!N273, RR lvl 3
    if op == "Morgan" and e >= 2:
        # TP!B155: +20% per other Glasgow operator (+55% for Siege); TP!J141 checks it.
        return sum(55 if o == "Siege" else 20 for o in team if o in GLASGOW and o != op)
    if op == "Mantra" and e >= 2:
        return 25 + 2 * min(10, ctx.elite_facilities)  # SPECIAL!B421
    if op == "Snowsant":
        rest = sum(_tp_pct(o, team, r, ctx) for o in team if o != op)
        return min(35 if e >= 2 else 25, 5 * (rest // 5))  # TP!H253
    return sum(x.pct for x in r.effects(op, "TP"))


# ------------------------------------------------------------------- PP/RR/HR


def pp_pct(op: str, r: Roster, ctx: "Context") -> float:
    """Drone recovery rate of one PP, innate included."""
    e = r.elite(op)
    if op == "Greyy Alter":
        return PP_INNATE + 23  # PP!B64: +1% per 10 drone cap; EN cap is 235
    if op == "Spuria":
        return PP_INNATE + (ramp_avg(15, 20, 1) if e >= 2 else ramp_avg(10, 15, 1))
    bonus = sum(x.pct for x in r.effects(op, "PP"))
    if op == "Friston-3" and ctx.cc.kaltsit:
        bonus += 5  # PP!J102
    if op == "PhonoR-0" and ctx.logos_trainer:
        bonus += 5  # PP!L100
    if op == "Philae" and e >= 2:
        bonus += 0.5 * ctx.settings.dorm_levels  # PP!F62
    return PP_INNATE + bonus


RARITY_RR = {6: 5, 5: 4, 4: 2}  # RR!B24:B27
ELITE_RR = {2: 16, 1: 8, 0: 0}  # RR!D24:D26


def rr_individual(op: str, team, r: Roster, ctx: "Context") -> float:
    """RR!B20: 5% innate + rarity + promotion + skill."""
    e = r.elite(op)
    skill = sum(x.pct for x in r.effects(op, "RR"))
    if op == "Ines" and e >= 2:
        skill = ramp_avg(20, 30, 2) + ctx.cc.rr_ines  # RR!B60
    elif op == "Ch'en Alter 2" and e >= 2:
        skill = 20  # RR!L47, no Worldly Plight
    elif op == "Surfer":
        skill = 10 + ((20 if e >= 2 else 15) if BSW & set(team) else 0)  # RR!R75
    elif op == "Typhon":
        skill = 10  # RR!N45, no Sami partner modelled
    return 5 + RARITY_RR.get(r.rarity.get(op, 0), 0) + ELITE_RR[max(e, 0)] + skill


def rr_pct(team: tuple[str, ...], r: Roster, ctx: "Context") -> float:
    """RR!B21: level + ambience + both operators + CC buff."""
    return ctx.settings.rr_bonus + ctx.cc.rr + sum(rr_individual(o, team, r, ctx) for o in team)


def hr_pct(op: str, r: Roster, ctx: "Context") -> float:
    e = r.elite(op)
    if op == "Tin Man":
        skill = 5 + (2 if e >= 2 else 1) * ctx.settings.dorm_levels  # HR!B36
    elif op == "Mr.Nothing":
        skill = 35  # HR!B66
    elif op == "Brigid":
        skill = 45 if e >= 2 else 30  # HR!F25
    elif op == "Kal'tsit Alter" and e >= 2:
        skill = 30 + 4 * min(5, ctx.elite_facilities)  # NEW!D15
    else:
        skill = sum(x.pct for x in r.effects(op, "HR"))
    return HR_INNATE + skill + ctx.cc.hr


# ------------------------------------------------------------------------ DORM


def dorm_aoe(op: str, r: Roster, s: Settings) -> float:
    e = r.elite(op)
    if op == "Lumen":
        return (0.15 if e >= 2 else 0.1) + 0.05 * s.pp_count  # DORM!D81
    if op == "Entelechia":
        extra = {3: 0.2, 2: 0.1} if e >= 2 else {3: 0.1, 2: 0.05}
        return 0.1 + extra.get(s.office_level, 0)  # DORM!H81
    return max((x.aoe_mr for x in r.effects(op, "DORM")), default=0.0)


def dorm_st(op: str, r: Roster) -> float:
    return max((x.st_mr for x in r.effects(op, "DORM")), default=0.0)


# ---------------------------------------------------------------------- totals


@dataclass
class Context:
    """What one facility needs to know about the rest of the base."""

    settings: Settings
    cc: CCBuffs = field(default_factory=CCBuffs)
    ines_working: bool = False
    recipe_types: int = 2
    elite_facilities: int = 0
    logos_trainer: bool = False
    gummy_in_tp: bool = False  # Leto E2 (FAC!N270)


@dataclass
class Shift:
    cc: tuple[str, ...]
    facs: list[tuple[tuple[str, ...], str]]  # (team, product)
    tps: list[tuple[str, ...]]
    pps: list[str]
    rr: tuple[str, ...]
    hr: str | None

    def operators(self) -> set[str]:
        ops = set(self.cc) | set(self.pps) | set(self.rr)
        ops |= {o for t, _ in self.facs for o in t} | {o for t in self.tps for o in t}
        return ops | ({self.hr} if self.hr else set())


@dataclass
class Output:
    gold_made: float
    gold_needed: float
    lmd: float
    exp: float
    drone_pct: float
    value: float


def economy(
    facs: list[tuple[float, str]], tps: list[TPResult], drone_pct: float, s: Settings
) -> Output:
    """facs: (productivity, product). Drones go to the TP making the most LMD."""
    gold_made = sum(GOLD_PER_DAY * (1 + p / 100) for p, prod in facs if prod == "Gold")
    exp = sum(EXP_PER_DAY * (1 + p / 100) for p, prod in facs if prod == "EXP")
    lmd = sum(t.lmd for t in tps)
    gold_needed = sum(t.gold for t in tps)
    if tps:
        best = max(tps, key=lambda t: t.lmd)
        extra = best.lmd * drone_pct / 2 / 100
        lmd += extra
        gold_needed += extra / best.lmd_per_gold
    if gold_needed > gold_made:
        lmd *= gold_made / gold_needed  # TPs stall without gold
    return Output(gold_made, gold_needed, lmd, exp, drone_pct, lmd + exp * s.exp_weight)


def evaluate(shift: Shift, r: Roster, ctx: Context) -> Output:
    ctx.cc = cc_buffs(shift.cc, r, ctx.settings)
    facs = [(fac_pct(t, p, r, ctx), p) for t, p in shift.facs]
    tps = [tp_result(t, r, ctx) for t in shift.tps]
    drone = sum(pp_pct(o, r, ctx) for o in shift.pps)
    return economy(facs, [t for t in tps if t], drone, ctx.settings)


def self_md(op: str, facility: str, r: Roster) -> float:
    """Self morale drain in the operator's active clauses for ``facility``.

    Clauses gated by "if ..." (a partner, being alone) are skipped: the planner
    never builds those conditions. "when with Lappland" counts, since Texas is only
    placed with her."""
    active = [s for s in r.active.get((op, facility), []) if " if " not in s.text]
    texts = {s.text for s in active if s.sheet != "gamedata"}
    guide = sum(float(m) for t in texts for m in re.findall(r"([+-]\d*\.?\d+) self MD", t))
    return guide + sum(s.effect.self_md for s in active if s.sheet == "gamedata" and s.effect)


def hours(op: str, facility: str, shift: Shift, r: Roster) -> float:
    """Hours from 24 morale to 0 (INFO!E26): 1/h base, -0.25 from a lvl 5 CC."""
    drain = 1 - 0.25 + self_md(op, facility, r)
    smileys = sum(1 for o in shift.cc if o in SMILEYS)
    if facility == "CC":
        drain -= 0.05 * smileys
    else:
        if facility in ("FAC", "TP"):
            drain -= 0.1  # lvl 3 innate
        if facility == "TP" and any("Shamare" in t and op in t for t in shift.tps):
            drain += 0.25 if op != "Shamare" else 0  # TP!B39: +0.25 MD for her partners
        if facility in ("FAC", "TP", "PP", "RR", "HR"):
            if "Młynar" in shift.cc and r.has("Młynar", 2):
                drain -= 0.05 * smileys + (0.1 if facility in ("PP", "RR", "HR") else 0)
            drain -= 0.05 * sum(
                1 for o in shift.cc if o in BASEWIDE_MD and r.has(o, BASEWIDE_MD[o])
            )
            if "Wiš'adel" in shift.cc and r.has("Wiš'adel", 2):
                drain -= 0.2 if "Civilight Eterna" in shift.cc else 0.1  # SPECIAL!B403
    return 24 / drain if drain > 0 else float("inf")
