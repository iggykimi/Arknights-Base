# Arknights-Base

Qué es, cómo se usa y cómo calcula: [`README.md`](README.md). Aquí solo lo que necesita un agente.

- `base_plan.md`, `promotions.md` y `skills_owned.csv` son generados: no se editan a mano, se
  regeneran con `python -m riic` / `python -m riic.promotions`.
- Antes de dar algo por hecho: `ruff check riic tests` y `python -m pytest -q` (~2 min, usan el Excel
  real de LFS y los datos del juego cacheados en `.cache/`).
- Una fórmula nueva cita su celda del Excel (`FAC!B33`) y, si cambia números del plan, lleva un test
  con el valor que da la guía, no el que da el código.
- Un título de alter nuevo en Krooster hace fallar `roster.py` a propósito: se añade a `ALTER_TITLES`.
- Datos del juego más nuevos: cambiar `COMMIT` en `riic/gamedata.py` y pasar los tests (el de
  `test_guide_numbers_match_the_game` compara guía y juego).
- Pendiente: optimizar los turnos A y B a la vez (hoy A se elige primero; ver «Límites» del README).
