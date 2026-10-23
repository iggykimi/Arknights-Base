"""Parse a Krooster "Collection" text export into the owned roster.

The export is a flat list of lines. Each operator block looks like::

    [Alter title]      <- optional, e.g. "Breacher" for Hoshiguma the Breacher
    Name
    <blank>
    Potential 3Elite 2 / LV / 90 / Skill ... / module code   (all optional)

so an operator name is any line followed by a blank line, and a title is the
non-stat line right before it.
"""

import re
from dataclasses import dataclass
from pathlib import Path

# Krooster shows alters as "<title>\n<base name>"; the Excel calls them "<base> Alter".
ALTER_TITLES = {
    "Reignfrost": "SilverAsh Alter",
    "Dawnstreak": "Ch'en Alter 2",  # char_1050_chen3; Ch'en Alter is "the Holungday"
    "Breacher": "Hoshiguma Alter",
    "New Covenant": "Exusiai Alter",
    "Igniting Spark": "Blaze Alter",
    "Flame Shadow": "Reed Alter",
    "Keen Glint": "Kroos Alter",
    "Decadenza": "Lappland Alter",
    "Prerita": "Pramanix Alter",
    "Fire-sharpened": "Fang Alter",
    "Lightningbearer": "Greyy Alter",
    "Purgatory": "Lava Alter",
    "Distilled": "Perfumer Alter",
    "Purifier": "Hibiscus Alter",
    "Lightchaser": "Astgenne Alter",
    # Amiya's class variants have their own base skills, absent from the guide.
    "Guard": "Amiya (Guard)",
    "Medic": "Amiya (Medic)",
}
# Krooster spelling -> Excel spelling, where they differ beyond case/punctuation.
RENAMES = {"Kal'tsit·Esperanta": "Kal'tsit Alter", "Miss.Christine": "Miss Christine"}
# Krooster prints "Maxed" instead of stats for fully promoted low rarities; the export
# carries no rarity, so the max promotion is listed per operator: (elite, level).
MAXED = {"Melantha": (1, 55), "12F": (0, 30)}

_STAT = re.compile(r"^(Potential \d|Elite \d|LV$|\d+$|Skill \d|Maxed$|[A-Z0-9]{2,3}-[A-Z]{2}\d?$)")


@dataclass(frozen=True)
class Owned:
    name: str  # Excel spelling
    elite: int
    level: int | None
    potential: int


def parse_collection(text: str) -> dict[str, Owned]:
    lines = [ln.strip() for ln in text.splitlines()]
    start = lines.index("Collection") + 1
    end = len(lines) - 1 - lines[::-1].index("Collection")
    lines = lines[start:end]

    roster: dict[str, Owned] = {}
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if not line or nxt not in ("", "Maxed") or _STAT.match(line):
            continue
        prev = lines[i - 1] if i else ""
        if prev and not _STAT.match(prev):
            if prev not in ALTER_TITLES:
                raise ValueError(f"Unknown alter title {prev!r} before {line!r}")
            name = ALTER_TITLES[prev]
        else:
            name = RENAMES.get(line, line)

        elite, level, potential = 0, None, 1
        if nxt == "Maxed":
            if name not in MAXED:
                raise ValueError(f"Maxed operator {name!r} needs an entry in MAXED")
            elite, level = MAXED[name]
        j = i + 2
        while j < len(lines) and lines[j] and _STAT.match(lines[j]):
            if m := re.search(r"Potential (\d)", lines[j]):
                potential = int(m[1])
            if m := re.search(r"Elite (\d)", lines[j]):
                elite = int(m[1])
            if lines[j] == "LV" and j + 1 < len(lines) and lines[j + 1].isdigit():
                level = int(lines[j + 1])
            j += 1
        if name in roster:
            raise ValueError(f"Duplicate operator {name!r} in collection")
        roster[name] = Owned(name, elite, level, potential)
    return roster


def load_roster(path: Path) -> dict[str, Owned]:
    return parse_collection(path.read_text(encoding="utf-8"))
