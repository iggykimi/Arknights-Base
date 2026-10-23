# Arknights-Base

Planificador de la base (RIIC) de Arknights para mi roster. Lee qué operadores tengo y a qué élite
y nivel, se queda con las habilidades de base que ya puedo usar, calcula la producción con las
fórmulas de la guía de la comunidad y elige la asignación que más LMD y EXP saca al día.

## Resultados

| Fichero | Qué contiene |
|---|---|
| [`base_plan.md`](base_plan.md) | El plan: quién va en cada instalación, en dos turnos de 12 h, con la producción y las horas de moral. |
| [`promotions.md`](promotions.md) | Cuánto ganaría la base si promocionara a cada operador. |
| [`skills_owned.csv`](skills_owned.csv) | La guía filtrada a mis operadores: cada habilidad, si está activa a mi élite y si el modelo la calcula. |

Resumen del plan actual (layout 2-4-3):

- **Turno A:** 63.162 LMD y 16.400 EXP al día. Proviso + Archetto + Hoederer en un TP (+187%),
  Closure + Texas + Lappland en el otro (+116%); tres fábricas de oro y una de EXP, todas en torno
  al +100%; Amiya y Kal'tsit en el CC.
- **Turno B:** 50.876 LMD y 14.600 EXP al día con los operadores que quedan (Shamare + Tequila +
  Mitm en un TP).
- El oro está cuadrado: las fábricas hacen lo que los TP venden. El cuello de botella son los TP,
  por eso Ave Mujica en el CC rinde lo mismo que Amiya + Kal'tsit: añade oro que no se vende.
- Ninguna promoción compensa por la base. La única que se nota es Tequila a E2 (unos +800 al día,
  ~1%): su equipo con Shamare pasa de +110% a +128%.

## Uso

```bash
git lfs pull                       # el Excel de la guía (190 MB) está en LFS
pip install openpyxl scipy pytest
python -m riic                     # regenera base_plan.md y skills_owned.csv (~1 min)
python -m riic.promotions          # regenera promotions.md (~20 min, 12 procesos)
python -m pytest -q                # 15 tests contra los ficheros reales (~2 min)
```

Para actualizar el roster, copia la página *Collection* de [Krooster](https://www.krooster.com)
en `Collection.txt` y vuelve a ejecutar. Opciones de `python -m riic`:

- `--layout 243|252|333|342`: TP, FAC y PP de la base.
- `--office-level N`: afecta a Entelechia y a Mr.Nothing (por defecto 3).
- `--exp-weight X`: cuántos LMD vale 1 EXP (por defecto 1, como dan por cordura CE-5 y LS-5).

## Cómo calcula

**Datos.** Tres fuentes, de más a menos peso:

1. `Collection.txt`: mis operadores con élite, nivel y potencial. Los alters vienen con su título
   («Breacher», «Dawnstreak»…), que se traduce al nombre de la guía.
2. `Arknights Base Combo Guide.xlsx`: habilidades por élite y fórmulas de los equipos (Vermeil,
   Mizuki, Shamare, Proviso…). Cada fórmula del código cita la celda de la que sale.
3. Datos del juego EN (`building_data.json`), descargados una vez a `.cache/` y fijados a un
   commit. Rellenan lo que la guía no lista (habilidades flojas, versiones de E0) y sirven para
   comprobar que los números de la guía coinciden con el juego.

**Producción por día.** Oro: 20 barras a +0%. EXP: 8.000 (Tactical Battle Record). TP: pedidos de
2/3/4 oros al 30/50/20%, 500 LMD por oro. Proviso sube de media ×1,55 el LMD de los pedidos y Closure
los cambia por los suyos. Los drones van al mejor TP (10% de recuperación ≈ 5% de
productividad). Si los TP piden más oro del que se fabrica, venden menos.

**Reglas que se respetan.** Una habilidad solo cuenta si mi operador ya llega a esa élite y nivel. Los
buffs del CC del mismo tipo no se suman (solo el mayor). Proviso no funciona con Tequila ni con
los que mejoran pedidos. Las rampas cuentan su media de 12 h.

**Optimización.** Fábricas y TP se eligen juntos con programación lineal entera
(`scipy.optimize.milp`), porque están ligados por el oro. CC, centrales, recepción y RRHH se
eligen alrededor, y se repite hasta que nada cambia. La moral no se optimiza: solo se comprueba
que cada operador aguanta su turno.

## Límites

- El turno A se elige antes que el B. Por eso, en `promotions.md`, las diferencias de unos
  ±500 al día son ruido y alguna promoción sale negativa. Optimizar los dos turnos a la vez lo
  quitaría.
- Sin modelar, porque con este roster no cambian el plan: Jaye, Alanna, Exusiai Alter en TP, los
  Abyssal Hunters, el equipo Worldly Plight y el sesgo de pistas de la recepción.
- Supuestos: instalaciones al máximo, dormitorios a nivel 5, ambiente >4k, servidor EN.

## Estructura

```
riic/roster.py      lectura de Collection.txt
riic/excel.py       habilidades y fórmulas de la guía
riic/gamedata.py    habilidades del juego que la guía no trae
riic/model.py       fórmulas y producción diaria
riic/optimize.py    elección de equipos
riic/__main__.py    python -m riic: base_plan.md y skills_owned.csv
riic/promotions.py  python -m riic.promotions: promotions.md
tests/              comprobaciones contra el Excel, el juego y el plan
```
