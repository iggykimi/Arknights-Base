"""Extract base skills from the "Arknights Base Combo Guide" workbook.

Each facility sheet lays operators out as a row of names with their skill text in
the cells right below, e.g. ``F85=Gravel`` / ``F86=E1: +35% Gold (Metalwork)``.
A row of facility labels above the names (``B80=FAC``) says where the skill
applies; on single-facility sheets it is the sheet itself.

Simple skills ("+35% Gold (Metalwork)", "+0.7 ST MR", "-0.25 self MD") are parsed
into numbers. Anything with a condition stays as text and is either modelled by
hand in ``model.py`` or reported as not modelled.

The workbook is the community's, not part of this repo: download it from
GUIDE_URL as .xlsx and save it as WORKBOOK, or point $RIIC_WORKBOOK or --excel
at it.
"""

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import openpyxl

GUIDE_URL = "https://docs.google.com/spreadsheets/d/1zYc2JU46X0XWmV7s1503bN4feRdOMa1eehrTQ2jGaiE"
WORKBOOK = Path(
    os.environ.get("RIIC_WORKBOOK")
    or Path(__file__).resolve().parent.parent / "Arknights Base Combo Guide.xlsx"
)


def missing_workbook(path: Path) -> str:
    """Why the workbook is needed and where to get it."""
    return (
        f"Guide workbook not found: {path}\n"
        f"Download the Arknights Base Combo Guide from {GUIDE_URL}\n"
        "(File > Download > Microsoft Excel (.xlsx)) and save it there, "
        "or pass --excel PATH or set RIIC_WORKBOOK."
    )


def require_workbook(path: Path) -> Path:
    """``path`` if it exists; otherwise exit with where to download it."""
    if not path.is_file():
        raise SystemExit(missing_workbook(path))
    return path


SKILL_SHEETS = (
    "CC",
    "FAC",
    "TP",
    "PP",
    "RR",
    "WS",
    "HR",
    "TR",
    "DORM",
    "SPECIAL",
    "NEW",
)
FACILITIES = {"CC", "FAC", "TP", "PP", "RR", "WS", "HR", "TR", "DORM", "RS"}
PRODUCTS = {"Gold", "EXP", "Orundum"}

# Excel spelling variants of the same operator (keys are normalised names).
ALIASES = {"mlynar": "Młynar", "phonor0": "PhonoR-0", "confess47": "CONFESS-47"}


def norm(name: str) -> str:
    folded = unicodedata.normalize("NFKD", name.replace("ł", "l")).casefold()
    return "".join(ch for ch in folded if ch.isalnum())


@dataclass(frozen=True)
class Effect:
    """Numbers of a simple skill at one promotion. ``pct`` is the facility's own
    unit: productivity for FAC/TP, drone rate for PP, clue speed for RR, contact
    speed for HR, byproduct rate for WS, training speed for TR."""

    pct: float = 0.0
    unit: str | None = None  # the word after "%": Gold, EXP, PP, RR, HR, Speed...
    tag: str | None = None  # Standard, Rhine Tech, Metalwork, Pinus Sylverstris...
    cap: int = 0
    cap_product: str | None = None
    self_md: float = 0.0
    st_mr: float = 0.0
    aoe_mr: float = 0.0
    self_mr: float = 0.0

    @property
    def product(self) -> str | None:
        """Gold/EXP/Orundum when a FAC skill only works for that product."""
        return self.unit if self.unit in PRODUCTS else None


@dataclass
class Skill:
    operator: str
    facility: str
    elite: int  # minimum promotion
    level: int | None  # minimum level when the guide says "lvl 30"
    text: str  # the clause for this promotion, as written in the guide
    effect: Effect | None  # None when the clause has conditions
    sheet: str
    cell: str
    section: str


_HEAD = re.compile(r"^E(\d)((?:[/+]\d)*)(?: (?:lvl )?(\d+))?: (.*)$", re.DOTALL)
_PCT = re.compile(
    r"^(?P<v>[+-]\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)*)% ?"
    r"(?P<kind>Gold|EXP|Orundum|PP|HR|RR|byproduct rate|Speed)?"
    r"(?: \((?P<tag>[^)]+)\))?$"
)
# "+20% ramp to +25% (+1% per hour)": counted as its first-12 h mean, like the guide.
_RAMP = re.compile(
    r"^\+(?P<a>[\d/]+)% ?(?P<kind>Gold|EXP|PP|RR)? ramp to \+(?P<b>[\d/]+)% "
    r"\(\+(?P<r>\d+)% per hour\)$"
)
_CAP = re.compile(r"^(?P<v>[+-]\d+(?:/\d+)*) CAP(?: (?P<prod>EXP|Gold))?$")
_MD = re.compile(r"^(?P<v>[+-]\d*\.?\d+(?:/\d*\.?\d+)*) self MD$")
_MR = re.compile(r"^(?P<v>[+-]\d*\.?\d+(?:/\d*\.?\d+)*) (?P<kind>ST|AoE|self) MR$")


def ramp_avg(start: float, end: float, per_hour: float, hours: int = 12) -> float:
    """Mean over the first ``hours`` hours, counted per whole hour like the guide."""
    return sum(min(end, start + per_hour * h) for h in range(hours)) / hours


def _pick(values: str, index: int) -> float:
    """ "-0.25/0.3" -> the index-th magnitude with the leading sign applied."""
    sign = -1 if values.startswith("-") else 1
    parts = values.lstrip("+-").split("/")
    return sign * float(parts[index] if index < len(parts) else parts[-1])


def parse_effect(body: str, index: int) -> Effect | None:
    """Parse the clause after "E0/2:"; ``index`` picks the value for that promotion."""
    body = " ".join(body.split())
    pct, unit, tag, cap, cap_product = 0.0, None, None, 0, None
    self_md = st_mr = aoe_mr = self_mr = 0.0
    for atom in re.split(r"(?<!\d)[,.](?!\d)\s*|\s+and\s+", body):
        atom = atom.strip().rstrip(".")
        if not atom:
            continue
        if m := _RAMP.match(atom):
            pct = ramp_avg(_pick(m["a"], index), _pick(m["b"], index), float(m["r"]))
            unit = m["kind"]
        elif m := _PCT.match(atom):
            pct = _pick(m["v"], index)
            unit = m["kind"]
            tag = m["tag"]
        elif m := _CAP.match(atom):
            cap = int(_pick(m["v"], index))
            cap_product = m["prod"]
        elif m := _MD.match(atom):
            self_md = _pick(m["v"], index)
        elif m := _MR.match(atom):
            value = _pick(m["v"], index)
            if m["kind"] == "ST":
                st_mr = value
            elif m["kind"] == "AoE":
                aoe_mr = value
            else:
                self_mr = value
        else:
            return None
    return Effect(pct, unit, tag, cap, cap_product, self_md, st_mr, aoe_mr, self_mr)


def split_clauses(text: str) -> list[str]:
    """Split a skill cell into "E<n>: ..." clauses, joining wrapped lines."""
    clauses: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if _HEAD.match(line) or not clauses:
            clauses.append(line)
        else:
            clauses[-1] += " " + line
    return [c for c in clauses if _HEAD.match(c)]


def expand_clause(clause: str) -> list[tuple[int, int | None, str, int]]:
    """ "E0/2: +30/35% EXP" -> [(0, None, body, 0), (2, None, body, 1)].

    "E0+1:" means both promotions share one clause (same values). A level applies
    to the last promotion only: "E0/0 lvl 30: +0.2/0.25" is E0, then E0 at lvl 30."""
    m = _HEAD.match(clause)
    assert m
    out = [(int(m[1]), None, m[4], 0)]
    for i, (sep, e) in enumerate(re.findall(r"([/+])(\d)", m[2] or ""), start=1):
        out.append((int(e), None, m[4], i if sep == "/" else 0))
    if m[3]:
        elite, _, body, idx = out[-1]
        out[-1] = (elite, int(m[3]), body, idx)
    return out


def _cell_text(value) -> str:
    return str(value).strip() if value is not None else ""


def operator_ids(path: Path) -> dict[str, str]:
    """Game character id -> guide spelling, from the hidden "op" sheet (op!C:D)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ids = {
        r[2]: ALIASES.get(norm(r[3]), r[3].strip())
        for r in wb["op"].iter_rows(values_only=True)
        if r[2] and r[3]
    }
    wb.close()
    return ids


def extract_skills(path: Path) -> list[Skill]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    names = {norm(r[3]): r[3].strip() for r in wb["op"].iter_rows(values_only=True) if r[3]}
    names.update(ALIASES)

    skills: dict[tuple, Skill] = {}
    for sheet in SKILL_SHEETS:
        grid: dict[tuple[int, int], str] = {}
        for row in wb[sheet].iter_rows():
            for c in row:
                if (t := _cell_text(c.value)) and hasattr(c, "column"):
                    grid[(c.row, c.column)] = t
        name_at = {k: names[norm(v)] for k, v in grid.items() if norm(v) in names}
        # Rows labelling columns with facilities ("FAC | ... | Substitutes:"); every
        # label is kept so a "Substitutes:"/"Bonus" column is not taken for its neighbour.
        header_rows = {
            r: {c: t.strip() for (rr, c), t in grid.items() if rr == r}
            for r in {r for (r, _), t in grid.items() if t.strip() in FACILITIES}
        }

        section = sheet
        for r in sorted({r for r, _ in grid}):
            b = grid.get((r, 2), "")
            # Section headers ("Gold Workers", "RR (6* Operators, Simple)"), not the
            # facility labels, skill numbers or sentences in column B.
            if (
                b[:1].isalpha()
                and (r, 2) not in name_at
                and b not in FACILITIES
                and not _HEAD.match(b)
                and not b.endswith((".", ":"))
                and len(b) < 70
            ):
                section = b
            for (rr, c), op in sorted(name_at.items()):
                if rr != r:
                    continue
                facility = _facility_for(sheet, r, c, header_rows)
                if facility is None:
                    continue
                below = r + 1
                while below <= r + 8 and (below, c) not in name_at:
                    text = grid.get((below, c), "")
                    for clause in split_clauses(text):
                        for elite, level, body, idx in expand_clause(clause):
                            key = (op, facility, elite, level, body)
                            ref = f"{sheet}!{_col(c)}{below}"
                            if key in skills:
                                continue
                            skills[key] = Skill(
                                operator=op,
                                facility=facility,
                                elite=elite,
                                level=level,
                                text=body,
                                effect=parse_effect(body, idx),
                                sheet=sheet,
                                cell=ref,
                                section=section,
                            )
                    below += 1
    wb.close()
    return list(skills.values())


def _facility_for(sheet, row, col, header_rows) -> str | None:
    if sheet in FACILITIES:
        return sheet
    for r in range(row - 1, row - 12, -1):
        if r in header_rows:
            cols = [c for c in header_rows[r] if c <= col]
            label = header_rows[r][max(cols)] if cols else None
            return label if label in FACILITIES else None
    return None


def _col(c: int) -> str:
    s = ""
    while c:
        c, rem = divmod(c - 1, 26)
        s = chr(65 + rem) + s
    return s
