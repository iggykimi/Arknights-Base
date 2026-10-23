"""Checks against the real roster and workbook. Expected numbers come from the
guide's own cells, cited next to each assertion."""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from riic.excel import extract_skills, norm, operator_ids
from riic.gamedata import download, fill_gaps, load_skills
from riic.model import Context, Roster, Settings, cc_buffs, fac_pct, rr_pct, tp_result
from riic.optimize import all_assigned, build_plan, plan_value
from riic.roster import load_roster

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
def roster(skills):
    return Roster(load_roster(ROOT / "Collection.txt"), skills)


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


def test_plan_end_to_end(roster):
    plan = build_plan(roster, Settings())
    ops = all_assigned(plan)
    assert len(ops) == len(set(ops)), "an operator is in two places"
    assert set(ops) <= set(roster.owned)
    for shift in (plan.a, plan.b):
        for team, _ in shift.facs:
            assert all(roster.active.get((o, "FAC")) for o in team)
        for team in shift.tps:
            assert all(roster.active.get((o, "TP")) for o in team)
        out = plan_value(plan, roster, shift)
        assert out.gold_needed <= out.gold_made * 1.02, "TPs sell more gold than FACs make"
    assert plan_value(plan, roster, plan.a).value >= plan_value(plan, roster, plan.b).value
