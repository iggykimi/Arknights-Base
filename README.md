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

Resumen del plan actual (layout 2-4-3), de media con la rotación: **57.312 LMD y 15.350 EXP al día**.

- **Turno A:** Proviso + Texas + Lappland (+172%) y Closure + Hoederer + Quartz (+121%) en los TP;
  tres fábricas de oro y una de EXP en torno al +95%; Amiya y Kal'tsit en el CC.
- **Turno B:** Archetto + Exusiai Alter + Lemuen (+125%) y Shamare + Tequila + Mitm (+120%) en
  los TP; Vermeil, Dorothy y Bubble en las fábricas de oro.
- El oro está cuadrado en los dos turnos: las fábricas hacen lo que los TP venden. Con menos
  fábricas de oro los TP se quedan parados, y entonces da igual lo fuertes que sean: cada barra se
  vende a 500 LMD (600 con Closure), tenga o no Proviso.
- Ninguna promoción compensa por la base. La mejor es Tequila a E2 (+989 al día, ~1,4%): su
  equipo con Shamare pasa de +110% a +128%. Les siguen Waai Fu y Minimalist a E2 (+650).

## Uso

```bash
git lfs pull                       # el Excel de la guía (190 MB) está en LFS
pip install openpyxl scipy pytest
python -m riic                     # regenera base_plan.md y skills_owned.csv (~3 min)
python -m riic.promotions          # regenera promotions.md (~30 min, 12 procesos)
python -m pytest -q                # tests contra los ficheros reales (~2 min)
```

Para actualizar el roster, copia la página *Collection* de [Krooster](https://www.krooster.com)
en `Collection.txt` y vuelve a ejecutar. Opciones de `python -m riic`:

- `--layout 243|252|333|342`: TP, FAC y PP de la base.
- `--office-level N`: afecta a Entelechia y a Mr.Nothing (por defecto 3).
- `--exp-weight X`: cuántos LMD vale 1 EXP (por defecto 1, como dan por cordura CE-5 y LS-5).
- `--gold-facs N`: fija cuántas fábricas hacen oro en cada turno. Con un valor fijo por recurso el
  optimizador se va a los extremos; para un reparto concreto de oro y EXP, fíjalo con esta opción
  en vez de subir `--exp-weight`.

## Cómo calcula

**Datos.** Tres fuentes:

1. `Collection.txt`: mis operadores con élite, nivel y potencial. Los alters vienen con su título
   («Breacher», «Dawnstreak»…), que se traduce al nombre de la guía.
2. `Arknights Base Combo Guide.xlsx`: habilidades por élite y fórmulas de los equipos (Vermeil,
   Mizuki, Shamare, Proviso…). Cada fórmula del código cita la celda de la que sale.
3. Datos del juego EN (`building_data.json`), descargados una vez a `.cache/` y fijados a un
   commit. Rellenan lo que la guía no lista (habilidades flojas, versiones de E0) y sirven para
   validar la guía.

**Producción por día.** Oro: 20 barras a +0% (72 min por barra). EXP: 8.000 (Tactical Battle
Record, 1.000 EXP en 3 h). TP: pedidos de 2/3/4 oros al 30/50/20%, 500 LMD por oro; Proviso sube
de media ×1,55 el LMD de cada pedido y Closure los cambia por los suyos (1.200 LMD por 2 oros en
144 min). Drones: uno cada 6 min más lo que den las centrales, 3 min de producción cada uno, al
mejor TP. Si los TP piden más oro del que se fabrica, venden menos.

**Reglas.** Una habilidad solo cuenta si el operador ya llega a esa élite y nivel. Los buffs del
mismo tipo no se suman (solo el mayor). Proviso no funciona con Tequila ni con los que mejoran
pedidos. Las rampas («+20% que sube un 1% por hora») cuentan su media de 12 h, como la guía.

**Optimización.** Fábricas y TP de los dos turnos se eligen a la vez con programación lineal entera
(`scipy.optimize.milp`): cada operador trabaja en un solo equipo y turno, y cada turno vende solo el
oro que fabrica. CC, centrales, recepción y RRHH se eligen alrededor, y se repite hasta que nada
cambia. Los huecos libres del CC van primero a quien sube pistas o RRHH y luego a quien reduce el
gasto de moral. La moral no se optimiza: solo se comprueba que cada operador aguanta su turno.

## Validación

Los tests (`python -m pytest -q`) comprueban el modelo contra fuentes que no son el propio código:

- **Contra el juego:** para cada uno de mis operadores e instalación, el % que usa el modelo es el
  que da el juego (unas 100 combinaciones), y cada número leído de la guía aparece en el texto del
  juego.
- **Contra la guía:** el modelo reproduce los resultados que publica el Excel: Mizuki + 2
  Standard +90%, Proviso con dos de 30% +153,79%, Shamare +110,08%, Bubble +90–95%, Dorothy +95%,
  Penguin Logistics +100%, Exusiai Alter + Archetto + Lemuen +115%, Reserve A1 +70–85%, y las
  parejas de recepción.
- **Contra mi roster:** las élites leídas de Krooster, que ningún operador esté en dos sitios y que
  todos los nombres de las reglas existan.
- **Rotación:** los dos turnos gastan unas 365 de moral al día y las 12 plazas libres de los
  dormitorios recuperan unas 650 (2 por hora a nivel 5 según el juego, más la habilidad de grupo).
  Cada operador necesita de media unas 3 h de dormitorio al día.

Dos datos solo están en la guía y no se pueden comprobar en el juego: los números de los pedidos de
Closure (NEW!F23) y que Exusiai Alter active el +25% de Lemuen (TP!B241).

## Límites

- El solver para a un 0,1% del óptimo: por debajo de unos ±300 LMD al día, dos planes empatan.
- Sin modelar, porque con este roster no cambian el plan: Jaye (su equipo da como mucho +97%),
  Alanna (los robots rinden menos en las centrales de lo que ella suma), SilverAsh Alter (pide 3
  de Kjerag en un TP), los equipos Worldly Plight y Perception Information, y el sesgo de pistas.
- Supuestos: instalaciones al máximo, dormitorios a nivel 5, ambiente >4k, servidor EN (235 drones
  de capacidad).

## Estructura

```
riic/roster.py      lectura de Collection.txt
riic/excel.py       habilidades y fórmulas de la guía
riic/gamedata.py    habilidades del juego que la guía no trae
riic/model.py       fórmulas y producción diaria
riic/optimize.py    elección de equipos
riic/__main__.py    python -m riic: base_plan.md y skills_owned.csv
riic/promotions.py  python -m riic.promotions: promotions.md
tests/              comprobaciones contra el juego, el Excel y el plan
```
