# Arknights-Base

Qué es, cómo se usa y cómo calcula: [`README.md`](README.md). Aquí solo lo que necesita un agente.

- `players/<usuario>/base_plan.md` y `skills_owned.csv` son generados: no se editan a mano, se
  regeneran con `python -m riic` (todos) o `python -m riic <usuario>`. `roster.json` lo escribe la
  descarga de Krooster; los ajustes de un jugador van en su `settings.json`, no en el código.
- Antes de dar algo por hecho: `ruff check riic tests` y `python -m pytest -q` (~9 min, usan el Excel
  real de LFS y los datos del juego cacheados en `.cache/`).
- Los tests leen `tests/data/*.json`, copias congeladas de los rosters. Si un test depende de una
  élite concreta, que sea de esas copias, nunca de `players/`.
- Una fórmula nueva cita su celda del Excel (`FAC!B33`), se contrasta con el texto del juego
  (`building_data.json`) y lleva un test con el número que publica la guía, no el que da el código.
  Si es una habilidad condicional, su operador va en `MODELLED`.
- Los nombres de las reglas usan la ortografía de la guía; `test_rule_names_exist` lo vigila.
- Un cambio en el optimizador se mide en los dos rosters (valor al día y tiempo) antes de quedarse:
  la poda de candidatos y el orden de las rondas cambian el plan más que el gap del solver.
- Datos del juego más nuevos (o un id de Krooster que no reconocen): cambiar `COMMIT` en
  `riic/gamedata.py` y pasar los tests.
