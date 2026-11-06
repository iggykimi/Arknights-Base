"""python -m riic: rebuild the base plan from the roster and the guide workbook."""

import argparse
import csv
from pathlib import Path

from .gamedata import all_skills
from .model import (
    EXP_PER_DAY,
    GOLD_PER_DAY,
    LAYOUTS,
    MODELLED,
    Roster,
    Settings,
    dorm_aoe,
    dorm_st,
    evaluate,
    fac_pct,
    hours,
    hr_pct,
    pp_pct,
    rr_pct,
    tp_result,
    unlocked,
)
from .optimize import Plan, build_plan
from .roster import load_roster

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--excel", type=Path, default=ROOT / "Arknights Base Combo Guide.xlsx")
    ap.add_argument("--collection", type=Path, default=ROOT / "Collection.txt",
                    help="Krooster Collection page (.txt) or rosters/USER.json")  # fmt: skip
    ap.add_argument("--out", type=Path, default=ROOT)
    ap.add_argument("--cache", type=Path, default=ROOT / ".cache" / "gamedata")
    ap.add_argument("--layout", choices=sorted(LAYOUTS), default="243")
    ap.add_argument("--office-level", type=int, default=3)
    ap.add_argument("--exp-weight", type=float, default=1.0, help="LMD worth of 1 EXP")
    ap.add_argument("--gold-facs", type=int, help="fix the Gold FACs per shift")
    args = ap.parse_args()

    settings = Settings(
        args.layout, args.office_level, exp_weight=args.exp_weight, gold_facs=args.gold_facs
    )
    skills, names = all_skills(args.excel, args.cache)
    r = Roster(load_roster(args.collection, names), skills)
    plan = build_plan(r, settings)

    write_skills(r, args.out / "skills_owned.csv")
    rows = facility_rows(plan, r)
    text = render_plan(plan, r, rows, args.collection.name)
    (args.out / "base_plan.md").write_text(text, encoding="utf-8", newline="\n")
    print(args.out / "base_plan.md", args.out / "skills_owned.csv", sep="\n")


def write_skills(r: Roster, path: Path) -> None:
    """The workbook filtered to owned operators: one row per skill clause."""
    seen = set()
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["operador", "elite_actual", "instalacion", "elite_requerida",
                    "nivel_requerido", "activa", "calculo", "habilidad", "seccion", "fuente"])  # fmt: skip
        for s in sorted(r.skills, key=lambda s: (s.operator.casefold(), s.facility, s.elite)):
            o = r.owned.get(s.operator)
            key = (s.operator, s.facility, s.elite, s.level, s.text)
            if not o or key in seen:
                continue
            seen.add(key)
            active = unlocked(o, s)
            modelled = s.operator in MODELLED.get(s.facility, ()) or (
                s.facility == "TP" and s.operator in r.better_orders
            )
            calc = "numerico" if s.effect else ("formula" if modelled else "no")
            w.writerow([s.operator, o.elite, s.facility, s.elite, s.level or "",
                        "si" if active else "no", calc, s.text, s.section, s.cell])  # fmt: skip


def facility_rows(plan: Plan, r: Roster) -> list[dict]:
    rows = []
    for name, shift in (("A", plan.a), ("B", plan.b)):
        ctx = plan.context(shift, r)

        def row(fac, ops, product, pct, per_day, unit, facility, _name=name, _shift=shift):
            rows.append({
                "turno": _name, "instalacion": fac, "operadores": ", ".join(ops),
                "producto": product, "productividad_pct": round(pct, 1),
                "produccion_dia": round(per_day), "unidad": unit,
                "horas_min": round(min(hours(o, facility, _shift, r) for o in ops), 1),
            })  # fmt: skip

        row("CC", shift.cc, "", 0, 0, "", "CC")
        for i, (team, prod) in enumerate(shift.facs, 1):
            pct = fac_pct(team, prod, r, ctx)
            per_day = (GOLD_PER_DAY if prod == "Gold" else EXP_PER_DAY) * (1 + pct / 100)
            row(
                f"FAC{i}",
                team,
                prod,
                pct,
                per_day,
                "barras" if prod == "Gold" else "EXP",
                "FAC",
            )
        for i, team in enumerate(shift.tps, 1):
            t = tp_result(team, r, ctx)
            row(
                f"TP{i}",
                team,
                "LMD",
                (1 + t.pct / 100) * t.mult * 100 - 100,
                t.lmd,
                "LMD",
                "TP",
            )
        for i, op in enumerate(shift.pps, 1):
            row(f"PP{i}", (op,), "drones", pp_pct(op, r, ctx), 0, "", "PP")
        if shift.rr:
            row("RR", shift.rr, "pistas", rr_pct(shift.rr, r, ctx), 0, "", "RR")
        if shift.hr:
            row("HR", (shift.hr,), "contacto", hr_pct(shift.hr, r, ctx), 0, "", "HR")
    return rows


def _shift_table(rows: list[dict], name: str) -> list[str]:
    out = ["| Instalación | Operadores | Producto | Productividad | Por día | Horas |",
           "|---|---|---|---|---|---|"]  # fmt: skip
    for x in rows:
        if x["turno"] != name:
            continue
        pct = f"+{x['productividad_pct']}%" if x["producto"] else "—"
        day = f"{x['produccion_dia']:,} {x['unidad']}".replace(",", ".") if x["unidad"] else "—"
        out.append(f"| {x['instalacion']} | {x['operadores']} | {x['producto'] or '—'} "
                   f"| {pct} | {day} | {x['horas_min']} |")  # fmt: skip
    return out


def render_plan(plan: Plan, r: Roster, rows: list[dict], source: str) -> str:
    s = plan.settings
    lines = [
        f"# Plan de base ({s.layout[0]}-{s.layout[1]}-{s.layout[2]}, roster actual)",
        "",
        (
            f"Generado con `python -m riic` a partir de `{source}`, "
            "`Arknights Base Combo Guide.xlsx` y los datos del juego EN (las habilidades que "
            "la guía no lista). No editar a mano: cambia el roster o los supuestos y vuelve a "
            "generarlo."
        ),
        "",
        (
            "Los dos turnos se eligen a la vez para rotar cada 12 h; el A es el que más "
            "produce. «Horas» es lo que aguanta el "
            "operador que antes se queda sin moral (24 de moral, CC lvl 5)."
        ),
    ]
    for name, shift in (("A", plan.a), ("B", plan.b)):
        out = evaluate(shift, r, plan.context(shift, r))
        lines += ["", f"## Turno {name}", "", *_shift_table(rows, name), ""]
        lines += [
            f"- **LMD/día:** {out.lmd:,.0f}".replace(",", "."),
            f"- **EXP/día:** {out.exp:,.0f}".replace(",", "."),
            f"- **Oro:** {out.gold_made:.1f} barras/día fabricadas, "
            f"{out.gold_needed:.1f} pedidas por los TP (drones incluidos)"
            + (
                " — los TP podrían vender más; el LMD ya cuenta solo el oro fabricado"
                if out.gold_needed > out.gold_made + 0.5
                else ""
            ),
            f"- **Drones:** +{out.drone_pct:.0f}% de recuperación, al TP que más LMD da",
        ]
        short = [x for x in rows if x["turno"] == name and x["horas_min"] < 12]
        if short:
            lines.append("- **No llegan a 12 h:** " + ", ".join(
                f"{x['instalacion']} ({x['horas_min']} h)" for x in short))  # fmt: skip

    lines += ["", "## Fijos", ""]
    lines.append(f"- **TR (entrenador):** {plan.trainer or '—'}")
    lines.append(f"- **WS:** {plan.workshop or '—'}")
    for i, (aoe, st) in enumerate(plan.dorms, 1):
        parts = []
        if aoe:
            parts.append(f"{aoe} (+{dorm_aoe(aoe, r, s):.2f} AoE)")
        if st:
            parts.append(f"{st} (+{dorm_st(st, r):.2f} ST)")
        lines.append(f"- **DORM{i}:** {' + '.join(parts) or '—'}; 3 plazas para descansar")
    lines.append("- **Activity Room:** cualquiera; solo da confianza, no produce.")

    lines += ["", "## Supuestos", ""]
    lines += [
        (
            f"- Instalaciones a nivel máximo, DORMs a lvl 5 ({s.dorm_levels} niveles), "
            f"Office lvl {s.office_level}, ambiente >4k (+15% RR)."
        ),
        "- 1 EXP vale 1 LMD (CE-5 y LS-5 dan lo mismo por cordura). `--exp-weight` lo cambia.",
        (
            "- Pedidos lvl 3: 30/50/20% de 2/3/4 oros, 500 LMD por oro (TP!E45). "
            "Proviso E2 ×1.5517 (TP!J193); Closure: 1200 LMD por 2 oros en 144 min (NEW!F23)."
        ),
        (
            "- Drones: uno cada 6 min y 3 min de trabajo cada uno (datos del juego), medio "
            "día de TP con +0% de recuperación; cada 10% más ≈ 5% (PP!B5). Todos a un TP."
        ),
        "- Rampas (Ceobe, Fang, Kroos, Ines, Spuria): media de las primeras 12 h, como el Excel.",
        "- Greyy Alter: 23% (+1% por cada 10 de capacidad de drones; 235 en EN, PP!B65).",
        "- Dawnstreak = Ch'en Alter 2 (char_1050_chen3), comprobado con los datos del juego.",
        "- Texas solo da productividad con Lappland en el mismo TP (+65%, «Feud» en el juego).",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
