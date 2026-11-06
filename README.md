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

Resumen del plan actual (layout 2-4-3), de media con la rotación: **69.856 LMD y 8.200 EXP al día**
(78.056 en total; el plan anterior, valorado con los drones bien contados, daba 74.050).

- **Turno A:** Shamare + Tequila + Mitm (+120%) y Closure + Archetto + Quartz (+127%) en los TP;
  tres fábricas de oro (Dorothy, Gravel, Bubble) y una de EXP (Tragodia + Vigna, +105%).
- **Turno B:** Proviso + Hoederer + Mantra (+176%, recibe los drones) y Texas + Lappland + Gummy
  en los TP; cuatro fábricas de oro y la banda Ave Mujica entera en el CC.
- El oro está cuadrado en los dos turnos. Los drones son medio día más de un TP, así que piden
  bastante oro: por eso el turno B pasa a cuatro fábricas de oro y se fabrica menos EXP.
- Chiro10: [`chiro10/base_plan.md`](chiro10/base_plan.md), 65.043 LMD y 8.000 EXP al día.

## Uso

```bash
git lfs pull                       # el Excel de la guía (190 MB) está en LFS
pip install openpyxl scipy pytest
python -m riic                     # regenera base_plan.md y skills_owned.csv (~4 min)
python -m riic.promotions --workers 6   # regenera promotions.md (más de 1 h; con 12 procesos se queda sin memoria)
python -m pytest -q                # tests contra los ficheros reales (~9 min)
```

Para actualizar el roster, copia la página *Collection* de [Krooster](https://www.krooster.com)
en `Collection.txt` y vuelve a ejecutar.

### Otro jugador (chiro10)

Si su perfil de Krooster es público, se descarga por usuario. El JSON va por id de personaje, así
que no depende de cómo escriba Krooster los nombres ni de los títulos de los alters:

```bash
python -m riic.krooster chiro10                                     # rosters/chiro10.json
python -m riic --collection rosters/chiro10.json --out chiro10      # chiro10/base_plan.md
python -m riic.promotions --collection rosters/chiro10.json --out chiro10/promotions.md
```

Opciones de `python -m riic`:

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
144 min). Drones: uno cada 6 min más lo que den las centrales, 3 min de producción cada uno
(`laborRecoverTime` y `tradingReduceTimeUnit` del juego), todos a un TP que el optimizador elige
dentro del mismo programa: sin bonus son medio día más de ese TP, y piden su oro. Si los TP piden
más oro del que se fabrica, venden menos.

**Reglas.** Una habilidad solo cuenta si el operador ya llega a esa élite y nivel. Los buffs del
mismo tipo no se suman (solo el mayor). Proviso no funciona con Tequila ni con los que mejoran
pedidos. Las rampas («+20% que sube un 1% por hora») cuentan su media de 12 h, como la guía.

**Optimización.** Fábricas y TP de los dos turnos se eligen a la vez con programación lineal entera
(`scipy.optimize.milp`): cada operador trabaja en un solo equipo y turno, y cada turno vende solo el
oro que fabrica. Los drones de cada turno van a un TP que el programa elige a la vez. Como
candidatos entran los 20 mejores equipos de cada operador, en tres capas: cada una se calcula sin
los operadores de los mejores equipos de la anterior, para que al turno B le queden equipos sin las
estrellas del A (con una sola capa, el turno B de chiro10 se quedaba sin TP). Centrales, CC,
recepción y RRHH se eligen alrededor; los CC de los dos turnos, juntos, para no partir una banda
como Ave Mujica. Se repite hasta seis rondas desde dos arranques (el segundo, con los CC
intercambiados) y se queda el mejor plan visto. Los huecos libres del CC van primero a quien sube pistas o RRHH y luego a quien reduce el
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
- **Contra los datos del juego (drones):** 240 drones al día y 3 min de trabajo por dron, leídos de
  `building_data.json`.
- **Contra los rosters:** las élites leídas de Krooster (mío y de chiro10), que todo operador del
  roster tenga habilidades (un nombre mal escrito ya no se pierde en silencio), que ningún operador
  esté en dos sitios, que los dos turnos llenen todas las instalaciones y que todos los nombres de
  las reglas existan. El lector del JSON se contrastó con mi `Collection.txt`: las mismas élites y
  niveles; de los tres nombres escritos distinto, dos eran solo mayúsculas y el tercero, Varkáris,
  dejaba a Valkáris fuera del plan (corregido).
- **Rotación:** los dos turnos gastan unas 365 de moral al día y las 12 plazas libres de los
  dormitorios recuperan unas 650 (2 por hora a nivel 5 según el juego, más la habilidad de grupo).
  Cada operador necesita de media unas 3 h de dormitorio al día.

Dos datos solo están en la guía y no se pueden comprobar en el juego: los números de los pedidos de
Closure (NEW!F23) y que Exusiai Alter active el +25% de Lemuen (TP!B241).

## Límites

- El solver para a un 0,1% del óptimo, y elegir producción y CC por turnos no garantiza el óptimo
  global. `promotions.md` mide ese ruido en cada ejecución y marca «(ruido)» lo que queda por debajo.
- Sin modelar, porque con este roster no cambian el plan: Jaye (su equipo da como mucho +97%),
  Alanna (los robots rinden menos en las centrales de lo que ella suma), SilverAsh Alter (pide 3
  de Kjerag en un TP), los equipos Worldly Plight y Perception Information, y el sesgo de pistas.
- Supuestos: instalaciones al máximo, dormitorios a nivel 5, ambiente >4k, servidor EN (235 drones
  de capacidad), layout 2-4-3 y Office 3 (también para chiro10: cámbialos con las opciones).
- Las horas de moral pueden salir algo cortas: si la guía repite una habilidad en dos hojas (Almond),
  su gasto de moral se suma dos veces. Solo afecta a la columna «Horas», no a la producción.

## Estructura

```
riic/roster.py      lectura del roster: Collection.txt o rosters/<usuario>.json
riic/krooster.py    python -m riic.krooster USUARIO: descarga un perfil público
rosters/            rosters descargados de Krooster (chiro10)
chiro10/            plan, promociones y habilidades de chiro10
riic/excel.py       habilidades y fórmulas de la guía
riic/gamedata.py    habilidades del juego que la guía no trae
riic/model.py       fórmulas y producción diaria
riic/optimize.py    elección de equipos
riic/__main__.py    python -m riic: base_plan.md y skills_owned.csv
riic/promotions.py  python -m riic.promotions: promotions.md
tests/              comprobaciones contra el juego, el Excel y el plan
```
