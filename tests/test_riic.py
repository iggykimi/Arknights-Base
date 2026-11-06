"""Checks against the real roster and workbook. Expected numbers come from the
guide's own cells, cited next to each assertion."""

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from riic import model
from riic.excel import extract_skills, norm, operator_ids
from riic.gamedata import (
    ROOMS,
    char_names,
    clean,
    download,
    fill_gaps,
    load_skills,
    parse_description,
)
from riic.model import (
    LMD_PER_GOLD,
    Context,
    Roster,
    Settings,
    TPResult,
    cc_buffs,
    economy,
    fac_pct,
    rr_pct,
    tp_result,
)
from riic.optimize import _production, all_assigned, build_plan, plan_value
from riic.roster import Owned, load_roster

ROOT = Path(__file__).resolve().parent.parent


WORKBOOK = ROOT / "Arknights Base Combo Guide.xlsx"


@pytest.fixture(scope="session")
def guide_skills():
    return extract_skills(WORKBOOK)


@pytest.fixture(scope="session")
def game_skills():
    return load_skills(download(ROOT / ".cache" / "gamedata"), operator_ids(WORKBOOK))


@pytest.fixture(scope="session")
def skills(guide_skills, game_skills):
    return fill_gaps(guide_skills, game_skills)


@pytest.fixture(scope="session")
def names():
    return char_names(download(ROOT / ".cache" / "gamedata"), operator_ids(WORKBOOK))


@pytest.fixture(scope="session")
def roster(skills, names):
    return Roster(load_roster(ROOT / "Collection.txt", names), skills)


@pytest.fixture(scope="session")
def chiro10(skills, names):
    return Roster(load_roster(ROOT / "rosters" / "chiro10.json", names), skills)


def ctx_with(cc, r, ines=False):
    s = Settings()
    ctx = Context(s, ines_working=ines)
    ctx.cc = cc_buffs(cc, r, s)
    return ctx


def test_collection_promotions(roster):
    o = roster.owned
    assert o["Ch'en Alter 2"].elite == 2  # "Dawnstreak" title
    assert "Ch'en Alter" not in o
    assert o["Lumen"].elite == 1  # the old CSV said E2
    assert o["Melantha"].elite == 1  # listed as "Maxed"
    assert o["Warmy"].elite == 0
    assert o["Durin"].level == 30


@pytest.mark.parametrize("which", ["roster", "chiro10"])
def test_every_owned_operator_has_skills(which, request, skills):
    # Krooster's "Varkáris" once kept Valkáris out of every plan without an error.
    r = request.getfixturevalue(which)
    no_skills = {"Amiya (Guard)", "Amiya (Medic)"}  # not in building_data: they are Amiya
    assert sorted(set(r.owned) - no_skills - {s.operator for s in skills}) == []


def test_chiro10_promotions(chiro10):
    o = chiro10.owned
    assert len(o) == 272
    assert (o["Amiya"].elite, o["Amiya"].level, o["Amiya"].potential) == (2, 60, 6)
    assert "Amiya (Guard)" in o and "Amiya (Medic)" in o


def test_drones_follow_the_game():
    """240 drones a day (laborRecoverTime) x 3 min each (tradingReduceTimeUnit) at +0%
    recovery; PP!B5: each +10% recovery adds ~5% of the TP's output."""
    folder = download(ROOT / ".cache" / "gamedata")
    b = json.loads((folder / "building_data.json").read_text(encoding="utf-8"))
    base = 86400 / b["laborRecoverTime"] * b["tradingReduceTimeUnit"] / 86400
    tp = TPResult(0, 1.0, LMD_PER_GOLD)
    for drone_pct in (0, 10, 78):
        out = economy([(0, "Gold")] * 10, [tp], drone_pct, Settings())
        expected = tp.lmd * (1 + base * (1 + drone_pct / 100))
        assert out.lmd == pytest.approx(expected)
    plus_10 = economy([(0, "Gold")] * 10, [tp], 10, Settings()).lmd
    assert plus_10 - economy([(0, "Gold")] * 10, [tp], 0, Settings()).lmd == pytest.approx(
        0.05 * tp.lmd
    )


def test_skill_clauses(skills):
    by = {(s.operator, s.facility, s.elite, s.level): s for s in skills}
    gravel = by[("Gravel", "FAC", 1, None)].effect
    assert (gravel.pct, gravel.product, gravel.tag) == (
        35,
        "Gold",
        "Metalwork",
    )  # FAC!F86
    assert by[("Vermeil", "FAC", 0, None)].effect.self_md == -0.25  # FAC!B33
    assert by[("Durin", "DORM", 0, None)].effect.aoe_mr == 0.2  # DORM!D94 "E0/0 lvl 30"
    assert by[("Durin", "DORM", 0, 30)].effect.aoe_mr == 0.25
    assert ("Kal'tsit Alter", "WS", 2, None) in by  # NEW!B14, Kal'tsit·Esperanta


def test_guide_numbers_match_the_game(roster, guide_skills, game_skills):
    """Every number read from the guide for an owned operator is in the game's text,
    alone or as the sum of two skills (the guide adds Whislash's 30% + 25%)."""
    game: dict[tuple[str, str], str] = {}
    for s in game_skills:
        game[(s.operator, s.facility)] = game.get((s.operator, s.facility), "") + " " + s.text
    wrong = []
    for s in guide_skills:
        if s.operator not in roster.owned or not s.effect or not s.effect.pct:
            continue
        if "ramp" in s.text:
            continue  # stored as a 12 h mean; test_model_matches_game_slots checks it
        text = game.get((s.operator, s.facility))
        if text is None:
            continue
        nums = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)%", text)]
        sums = {a + b for i, a in enumerate(nums) for b in nums[i + 1 :]}
        if abs(s.effect.pct) not in set(nums) | sums:
            wrong.append(f"{s.operator} {s.facility} E{s.elite}: {s.text} | game: {text}")
    assert not wrong, "\n".join(wrong)


def test_one_spelling_per_operator(skills):
    # "Mlynar" (op sheet) vs "Młynar" once split Młynar's skills from his roster entry.
    spellings: dict[str, set[str]] = {}
    for s in skills:
        spellings.setdefault(norm(s.operator), set()).add(s.operator)
    assert {k: v for k, v in spellings.items() if len(v) > 1} == {}


def test_model_matches_game_slots(roster):
    """For every owned operator, the % the model uses equals the game's: per skill
    slot, the best promotion reached replaces the lower ones and slots add up."""
    folder = download(ROOT / ".cache" / "gamedata")
    building = json.loads((folder / "building_data.json").read_text(encoding="utf-8"))
    ids = {v: k for k, v in operator_ids(WORKBOOK).items()}
    wrong, compared = [], 0
    for op, o in roster.owned.items():
        entry = building["chars"].get(ids.get(op, ""))
        if not entry:
            continue
        found: dict[str, list] = {}
        for slot in entry["buffChar"]:
            reached = [
                d for d in slot["buffData"]
                if (int(str(d["cond"]["phase"])[-1]), d["cond"]["level"]) <= (o.elite, o.level or 1)
            ]  # fmt: skip
            if reached:
                buff = building["buffs"][reached[-1]["buffId"]]
                if (fac := ROOMS.get(buff["roomType"])) in ("FAC", "TP", "PP", "RR", "HR"):
                    found.setdefault(fac, []).append(parse_description(clean(buff["description"])))
        for fac, effects in found.items():
            if None in effects or op in model.MODELLED.get(fac, ()):
                continue  # conditional skills have their own formula and test
            compared += 1
            game = sorted(round(e.pct, 2) for e in effects if e.pct)
            mine = sorted(round(e.pct, 2) for e in roster.effects(op, fac) if e.pct)
            if game != mine:
                wrong.append(f"{op} {fac}: game {game} model {mine}")
    assert compared > 80
    assert not wrong, "\n".join(wrong)


def test_rule_names_exist(skills):
    # "Greythroat" vs "GreyThroat" once kept a Smiley out of every plan.
    known = {s.operator for s in skills}
    groups = {"SMILEYS": model.SMILEYS, "BASEWIDE_MD": model.BASEWIDE_MD,
              "CC_PRODUCTIVE": model.CC_PRODUCTIVE, **model.MODELLED}  # fmt: skip
    assert {k: sorted(set(v) - known) for k, v in groups.items() if set(v) - known} == {}


def test_game_data_fills_what_the_guide_leaves_out(roster):
    beagle = roster.effects("Beagle", "FAC")  # +10%, +6 CAP: only in the game data
    assert [(e.pct, e.cap) for e in beagle] == [(10, 6)]
    assert roster.better_orders["Mitm"] == 0  # guide lists only Mitm's E2 TP skill
    assert "Ines" in roster.in_facility("HR")


def test_only_promoted_skills_count(roster):
    ctx = ctx_with((), roster)
    # Warmy's +30% Gold needs E2 (FAC!L86); she is E0.
    assert fac_pct(("Purestream", "Warmy", "Almond"), "Gold", roster, ctx) == 3 + 40 + 25


def test_mizuki_standard_team(roster):
    # FAC!J142: Mizuki + 2 Standards = +90%, plus the lvl 3 innate 3%.
    ctx = ctx_with((), roster)
    assert fac_pct(("Mizuki", "Jessica", "Vanilla"), "EXP", roster, ctx) == 93


def test_bubble_counts_big_capacity_triple(roster):
    # FAC!B108: Bubble E1 gives 1%/CAP for operators adding <=16 CAP, 3%/CAP above.
    # Bubble 10 CAP, Bena 17 CAP and -20% (FAC!J106), Ceobe 8 CAP + 12 h ramp (FAC!H112).
    ctx = ctx_with((), roster)
    expected = 3 + 10 + 3 * 17 - 20 + 8 + 23.75
    assert fac_pct(("Bubble", "Bena", "Ceobe"), "Gold", roster, ctx) == pytest.approx(expected)


def promoted(roster, skills, **elites):
    owned = {n: replace(o, elite=elites.get(n, o.elite)) for n, o in roster.owned.items()}
    return Roster(owned, skills)


def test_promoted_skills(roster, skills):
    r = promoted(roster, skills, **{"Fang Alter": 2, "Vigil": 2})
    ctx = ctx_with((), r)
    # FAC!J188: Fang Alter + Fang + Kroos, +70-85% before the lvl 3 innate.
    assert 70 <= fac_pct(("Fang Alter", "Fang", "Kroos"), "Gold", r, ctx) - 3 <= 85
    # TP!F244: Vigil E2 gives 40% with a lvl 3 RR.
    assert tp_result(("Vigil",), r, ctx).pct == 3 + 40


def test_guide_team_numbers(skills):
    """Teams whose final number the guide publishes, with the promotions it assumes."""
    elites = {"Bubble": 1, "Vulcan": 2, "Ceobe": 2, "Dorothy": 2, "Silence Alter": 2,
              "Ptilopsis": 2, "Exusiai": 2, "Texas": 2, "Lappland": 2, "Exusiai Alter": 2,
              "Archetto": 2, "Lemuen": 2, "Ch'en": 2, "Vigil": 2, "Ines": 2}  # fmt: skip
    r = Roster({n: Owned(n, e, 90, 1) for n, e in elites.items()}, skills)
    ctx = ctx_with((), r)
    fac = fac_pct(("Bubble", "Vulcan", "Ceobe"), "Gold", r, ctx) - 3
    assert 90 <= fac <= 95  # FAC!J94
    assert fac_pct(("Dorothy", "Silence Alter", "Ptilopsis"), "Gold", r, ctx) - 3 == 95  # FAC!J166
    assert tp_result(("Exusiai", "Texas", "Lappland"), r, ctx).pct - 3 == 100  # TP!J81
    assert tp_result(("Exusiai Alter", "Archetto", "Lemuen"), r, ctx).pct - 3 == 115  # BIN!F1607
    rr = Settings().rr_bonus
    assert rr_pct(("Ch'en", "Vigil"), r, ctx) - rr == pytest.approx(102)  # RR!L27
    assert rr_pct(("Ines", "Vigil"), r, ctx) - rr == pytest.approx(104.5)  # RR!L26


def test_proviso_with_two_30_percent_workers(roster):
    # TP!N227: Proviso E2, lvl 3 TP, two 30% workers, Amiya in CC -> +153.79% added.
    ctx = ctx_with(("Amiya",), roster)
    t = tp_result(("Proviso", "Gummy", "Midnight"), roster, ctx)
    added = (1 + t.pct / 100) * t.mult * 100 - 100 - 3 - 7
    assert added == pytest.approx(153.79, abs=0.01)


def test_proviso_rejects_tequila(roster):
    ctx = ctx_with((), roster)
    assert tp_result(("Proviso", "Tequila", "Gummy"), roster, ctx) is None  # TP!B173


def test_shamare_e0_tequila_and_better_orders(roster):
    # TP!J25: E0 Tequila + E0 Bibeak-type -> +110.08% (Tequila is E1, Kafka E0).
    t = tp_result(("Shamare", "Tequila", "Kafka"), roster, ctx_with((), roster))
    assert t.pct == pytest.approx(3 + 110.08)


def test_cc_buffs_of_one_kind_do_not_stack(roster):
    # CC!B212, CC!B228: only the highest +% per facility applies.
    buffs = cc_buffs(("Amiya", "Paprika", "Kal'tsit", "Mon3tr"), roster, Settings())
    assert (buffs.tp, buffs.fac) == (7, 2)


def test_reception_room(roster):
    # RR!B20: E2 6* = 5 + 5 + 16 + skill; Ines' 12 h average is 53.5% (RR!B65),
    # Vigil E1 43% (RR!D65); RR lvl 3 11% + ambience 15%.
    assert rr_pct(("Ines", "Vigil"), roster, ctx_with((), roster)) == pytest.approx(26 + 53.5 + 43)


def test_fixed_gold_factories(roster):
    s = Settings(gold_facs=2)
    for facs, _ in _production(roster, [Context(s), Context(s)], set(roster.owned), [0, 0]):
        assert sorted(p for _, p in facs) == ["EXP", "EXP", "Gold", "Gold"]


@pytest.mark.parametrize("which", ["roster", "chiro10"])
def test_plan_end_to_end(which, request):
    roster = request.getfixturevalue(which)
    plan = build_plan(roster, Settings())
    ops = all_assigned(plan)
    assert len(ops) == len(set(ops)), "an operator is in two places"
    assert set(ops) <= set(roster.owned)
    for shift in (plan.a, plan.b):
        # chiro10's shift B once got no TP: every pruned candidate had shift A's stars.
        assert (len(shift.facs), len(shift.tps)) == (4, 2), "a facility is left empty"
        for team, _ in shift.facs:
            assert all(roster.active.get((o, "FAC")) for o in team)
        for team in shift.tps:
            assert all(roster.active.get((o, "TP")) for o in team)
        out = plan_value(plan, roster, shift)
        # TPs may be able to sell more than the FACs make (drones add half a TP-day),
        # but only the gold made is paid: 600 LMD per bar at most (Closure, NEW!F23).
        assert out.lmd <= out.gold_made * 600 + 1, "LMD counted for gold never made"
    assert plan_value(plan, roster, plan.a).value >= plan_value(plan, roster, plan.b).value
