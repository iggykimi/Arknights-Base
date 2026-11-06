"""Base skills from the EN game data, to fill what the guide leaves out.

The guide only lists skills worth using (it drops e.g. +10-20% workers and most
order-limit skills), and sometimes only the E2 version. The game's own
``building_data.json`` has every skill; it is downloaded once, pinned to a commit
of ArknightsAssets/ArknightsGamedata, and cached under ``.cache/``.
"""

import json
import re
import urllib.request
from dataclasses import replace
from pathlib import Path

from .excel import Effect, Skill, extract_skills, operator_ids, ramp_avg

COMMIT = "ecca6444cc87b91e2a04d6a3a0c24799e8a68c0e"  # 2026-11-01, EN
URL = "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/{}/en/gamedata/excel/{}"
FILES = ("building_data.json", "character_table.json")
ROOMS = {"CONTROL": "CC", "MANUFACTURE": "FAC", "TRADING": "TP", "POWER": "PP",
         "MEETING": "RR", "WORKSHOP": "WS", "HIRE": "HR", "TRAINING": "TR",
         "DORMITORY": "DORM"}  # fmt: skip
PRODUCT = {"Battle Record": "EXP", "Precious Metal": "Gold", "Originium": "Orundum"}

_NUM = r"([+-]?\d+(?:\.\d+)?)"
_ATOMS = [
    (rf"^(?:(Battle Record|Precious Metal|Originium)(?: formula related)? )?productivity {_NUM}%$",
     lambda m: {"pct": float(m[2]), "unit": PRODUCT.get(m[1])}),
    (rf"^capacity limit {_NUM}$", lambda m: {"cap": int(float(m[1]))}),
    (rf"^Morale consumed (?:each|per) hour (?:is reduced by )?{_NUM}$",
     lambda m: {"self_md": float(m[1])}),
    (rf"^order acquisition efficiency {_NUM}%$", lambda m: {"pct": float(m[1])}),
    (rf"^(?:the )?order limit {_NUM}$", lambda m: {}),
    (rf"^increases the drone recovery rate by {_NUM}%$", lambda m: {"pct": float(m[1])}),
    (rf"^Clue search speed increases by {_NUM}%$", lambda m: {"pct": float(m[1])}),
    (rf"^HR contacting speed {_NUM}%$", lambda m: {"pct": float(m[1])}),
    (rf"^the production rate of byproduct increases by {_NUM}%$", lambda m: {"pct": float(m[1])}),
    (rf"^restores {_NUM} Morale per hour to all Operators (?:assigned to|in) that Dormitory$",
     lambda m: {"aoe_mr": float(m[1])}),
    ((rf"^restores {_NUM} Morale per hour to another Operator assigned to that Dormitory "
     r"whose Morale is not full$"), lambda m: {"st_mr": float(m[1])}),
    (rf"^self Morale recovered (?:per hour )?{_NUM}(?: per hour)?$", lambda m: {"self_mr": float(m[1])}),
]  # fmt: skip


def clean(text: str) -> str:
    """Drop rich-text tags, the "When this Operator is assigned to X," lead and the
    "(Only the strongest effect ...)" notes."""
    text = re.sub(r"<[^>]*>", "", text or "")
    # Only the bare "assigned to <building>," lead: anything else ("and Gummy is in a
    # Trading Post", "with Amiya", "if Ines is...") is a condition and must stay.
    text = re.sub(
        r"^When this Operator is assigned to (?:a|an|the) (?:Factory|Trading Post|Power Plant|"
        r"Reception Room|Control Center|Dormitory|Workshop|HR Office|Training Room)"
        r"(?: to process any material)?, ",
        "",
        text,
    )
    return re.sub(r"\s*\([^)]*(?:strongest|most effective)[^)]*\)", "", text).strip()


# The game's four ways of writing a ramp -> (start, per hour, end); counted as the
# first-12 h mean, like the guide does.
_RAMPS = [
    ((r"(?:productivity|drone recovery rate is) \+(\d+)% in the first hour and thereafter "
     r"\+(\d+)% per hour, up to \+(\d+)%"), lambda m: (m[1], m[2], m[3])),
    (r"productivity per hour \+(\d+)%, up to \+(\d+)%", lambda m: ("0", m[1], m[2])),
    ((r"Clue search speed increases by (\d+)%, then by another (\d+)% per hour, up to a "
     r"maximum of (\d+)%"), lambda m: (m[1], m[2], m[3])),
]  # fmt: skip


def parse_description(text: str) -> Effect | None:
    """Simple skills only; anything with a condition returns None."""
    fields: dict = {}
    for pattern, parts in _RAMPS:
        if m := re.search(pattern, text):
            start, per_hour, end = (float(x) for x in parts(m))
            fields["pct"] = ramp_avg(start, end, per_hour)
            text = (text[: m.start()] + text[m.end() :]).strip(" ,.")
            if not text:
                return Effect(**fields)
    for atom in re.split(r",? and |; furthermore, |, ", text.rstrip(".")):
        for pattern, build in _ATOMS:
            if m := re.match(pattern, atom.strip()):
                fields.update(build(m))
                break
        else:
            return None
    return Effect(**fields)


# Skill families that other skills count (Mizuki, Dorothy, Bryophyta, Highmore).
TAGS = {"Standardization": "Standard", "Rhine Tech": "Rhine Tech", "Metalwork": "Metalwork",
        "Pinus Sylvestris": "Pinus Sylverstris"}  # fmt: skip


def _tagged(effect: Effect | None, buff_name: str) -> Effect | None:
    tag = next((v for k, v in TAGS.items() if k in buff_name), None)
    return replace(effect, tag=tag) if effect and tag else effect


def download(cache: Path) -> Path:
    folder = cache / COMMIT[:12]
    folder.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        if not (folder / name).exists():
            tmp = folder / (name + ".part")
            urllib.request.urlretrieve(URL.format(COMMIT, name), tmp)
            tmp.replace(folder / name)
    return folder


# Amiya's class variants live in patch_table, not character_table. They have no base
# skills of their own: in the base they are Amiya.
PATCH_NAMES = {"char_1001_amiya2": "Amiya (Guard)", "char_1037_amiya3": "Amiya (Medic)"}


def char_names(folder: Path, excel_names: dict[str, str]) -> dict[str, str]:
    """Char id -> operator name, in the guide's spelling where the guide has it
    (``excel_names``: char id -> guide name)."""
    chars = json.loads((folder / "character_table.json").read_text(encoding="utf-8"))
    return {cid: c["name"] for cid, c in chars.items()} | PATCH_NAMES | excel_names


def load_skills(folder: Path, excel_names: dict[str, str]) -> list[Skill]:
    """Every base skill in the game, named like the guide where the guide has the
    character (``excel_names``: char id -> guide name)."""
    names = char_names(folder, excel_names)
    building = json.loads((folder / "building_data.json").read_text(encoding="utf-8"))
    skills = []
    for cid, entry in building["chars"].items():
        name = names.get(cid)
        if not name:
            continue
        for slot in entry["buffChar"]:
            for data in slot["buffData"]:
                buff = building["buffs"][data["buffId"]]
                facility = ROOMS.get(buff["roomType"])
                if not facility:
                    continue
                phase = data["cond"]["phase"]
                elite = phase if isinstance(phase, int) else int(str(phase)[-1])
                level = data["cond"]["level"]
                raw = re.sub(r"<[^>]*>", "", buff["description"] or "")
                text = clean(buff["description"])
                general_ws = facility != "WS" or "to process any material" in raw
                skills.append(
                    Skill(
                        operator=name,
                        facility=facility,
                        elite=elite,
                        level=level if level > 1 else None,
                        text=text,
                        effect=_tagged(parse_description(text), buff["buffName"])
                        if general_ws
                        else None,
                        sheet="gamedata",
                        cell=f"gamedata:{data['buffId']}",
                        section="General Crafters" if facility == "WS" and general_ws else "",
                    )
                )
    return skills


def fill_gaps(excel: list[Skill], game: list[Skill]) -> list[Skill]:
    """The guide's skills plus each game skill whose (operator, facility, promotion)
    the guide does not cover."""
    covered = {(s.operator, s.facility, s.elite) for s in excel}
    return excel + [s for s in game if (s.operator, s.facility, s.elite) not in covered]


def all_skills(workbook: Path, cache: Path) -> tuple[list[Skill], dict[str, str]]:
    """The guide's skills, completed with the game's, and char id -> operator name."""
    folder, excel_names = download(cache), operator_ids(workbook)
    game = load_skills(folder, excel_names)
    return fill_gaps(extract_skills(workbook), game), char_names(folder, excel_names)


def rarities(folder: Path, excel_names: dict[str, str]) -> dict[str, int]:
    """Operator -> stars (1-6), named like the guide."""
    chars = json.loads((folder / "character_table.json").read_text(encoding="utf-8"))
    return {
        excel_names.get(cid) or c["name"]: int(str(c["rarity"])[-1])  # "TIER_5" -> 5
        for cid, c in chars.items()
        if cid.startswith("char_")  # traps and tokens reuse operator names
    }
