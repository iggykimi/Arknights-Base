# Arknights-Base

Qué es, cómo se usa y cómo calcula: [`README.md`](README.md). Aquí solo lo que necesita un agente.

- `base_plan.md`, `promotions.md` y `skills_owned.csv` (y los de `chiro10/`) son generados: no se
  editan a mano, se regeneran con `python -m riic` / `python -m riic.promotions` (para chiro10,
  `--collection rosters/chiro10.json` y su `--out`, ver README).
- Un roster nuevo de Krooster en JSON: `python -m riic.krooster USUARIO` (perfil público).
- Antes de dar algo por hecho: `ruff check riic tests` y `python -m pytest -q` (~9 min, usan el Excel
  real de LFS y los datos del juego cacheados en `.cache/`).
- Una fórmula nueva cita su celda del Excel (`FAC!B33`), se contrasta con el texto del juego
  (`building_data.json`) y lleva un test con el número que publica la guía, no el que da el código.
  Si es una habilidad condicional, su operador va en `MODELLED`.
- Los nombres de las reglas usan la ortografía de la guía; `test_rule_names_exist` lo vigila.
- Un título de alter nuevo en Krooster hace fallar `roster.py` a propósito: se añade a `ALTER_TITLES`.
- Datos del juego más nuevos: cambiar `COMMIT` en `riic/gamedata.py` y pasar los tests.
