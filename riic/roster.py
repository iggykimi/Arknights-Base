"""Read a player's owned roster: ``players/<user>/roster.json``.

The file is what ``krooster.fetch`` saves from a public Krooster profile, keyed by
game char id, so names come from the game data and the guide (``names``) and need
no guessing: alters, Amiya's variants and Krooster's own spellings all resolve.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Owned:
    name: str  # Excel spelling
    elite: int
    level: int | None
    potential: int


def parse_krooster(data: dict[str, dict], names: dict[str, str]) -> dict[str, Owned]:
    """char id -> elite, level, potential; ``names`` maps char ids to the guide's spelling."""
    roster: dict[str, Owned] = {}
    for cid, o in data.items():
        if cid not in names:
            raise ValueError(f"{cid} is newer than the game data: update COMMIT in gamedata.py")
        name = names[cid]
        if name in roster:
            raise ValueError(f"Duplicate operator {name!r} in roster")
        roster[name] = Owned(name, o["elite"], o["level"], o["potential"])
    return roster


def load_roster(path: Path, names: dict[str, str]) -> dict[str, Owned]:
    return parse_krooster(json.loads(path.read_text(encoding="utf-8")), names)
