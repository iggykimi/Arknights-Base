# Arknights-Base

What it is, how to use it and how it computes: [`README.md`](README.md). This file holds only what an
agent needs.

- `players/<user>/base_plan.md` and `skills_owned.csv` are generated: do not edit them by hand,
  regenerate them with `python -m riic` (everyone) or `python -m riic <user>`. `roster.json` is
  written by the Krooster download; a player's settings go in their `settings.json`, not in the code.
- Before calling something done: `ruff check riic tests` and `python -m pytest -q` (~9 min; they use
  the real guide workbook and the game data cached in `.cache/`). The workbook is not in the repo:
  download it as the README says. Without it the tests that read it skip, so a green run without
  the workbook proves nothing about the model.
- Tests read `tests/data/*.json`, frozen copies of the rosters. If a test depends on a specific
  promotion, it must come from those copies, never from `players/`.
- A new formula cites its workbook cell (`FAC!B33`), is checked against the game text
  (`building_data.json`) and gets a test with the number the guide publishes, not the one the code
  gives. If it is a conditional skill, its operator goes in `MODELLED`.
- Rule names use the guide's spelling; `test_rule_names_exist` checks it.
- An optimizer change is measured on both rosters (daily value and time) before it stays: candidate
  pruning and round order change the plan more than the solver gap does.
- Newer game data (or a Krooster id it does not recognise): change `COMMIT` in
  `riic/gamedata.py` and run the tests.
