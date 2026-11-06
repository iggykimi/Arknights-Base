# Arknights-Base

Planificador de la base (RIIC) de Arknights. Para cada jugador lee de Krooster qué operadores tiene
y a qué élite y nivel, se queda con las habilidades de base que ya puede usar, calcula la producción
con las fórmulas de la guía de la comunidad y elige, con programación lineal entera, la asignación
de dos turnos de 12 h que más LMD y EXP saca al día.

## Jugadores

| Jugador | Plan | Habilidades |
|---|---|---|
| iggykimi | [`players/iggykimi/base_plan.md`](players/iggykimi/base_plan.md) | [`skills_owned.csv`](players/iggykimi/skills_owned.csv) |
| chiro10 | [`players/chiro10/base_plan.md`](players/chiro10/base_plan.md) | [`skills_owned.csv`](players/chiro10/skills_owned.csv) |

Cada plan dice quién va en cada instalación y turno, la producción y el oro de cada turno, y las
horas de moral. `skills_owned.csv` es la guía filtrada a ese roster: cada habilidad, si está
activa a su élite y si el modelo la calcula.

## Uso

```bash
git lfs pull                     # el Excel de la guía (190 MB) está en LFS
pip install numpy openpyxl scipy pytest
python -m riic                   # descarga los rosters de Krooster y rehace todos los planes
python -m riic chiro10           # solo un jugador
python -m riic nuevo_usuario     # añade un jugador: crea players/nuevo_usuario/
python -m riic --no-fetch        # rehace los planes con los rosters ya guardados
python -m pytest -q              # tests (~9 min)
```

Cada plan tarda unos 4 minutos. El perfil de Krooster tiene que ser público.

**Ajustes por jugador.** Lo que no sea el valor por defecto va en `players/<usuario>/settings.json`,
por ejemplo `{"layout": "252", "office_level": 2}`. Los mismos ajustes como opción de la línea de
comandos valen solo para esa ejecución:

- `layout` (`--layout 243|252|333|342`): TP, FAC y PP de la base. Por defecto 243.
- `office_level` (`--office-level N`): afecta a Entelechia y a Mr.Nothing. Por defecto 3.
- `exp_weight` (`--exp-weight X`): cuántos LMD vale 1 EXP. Por defecto 1, como dan por cordura CE-5
  y LS-5.
- `gold_facs` (`--gold-facs N`): fija cuántas fábricas hacen oro en cada turno. Para un reparto
  concreto de oro y EXP, mejor esto que subir `exp_weight`: con un valor fijo por recurso el
  optimizador se va a los extremos.

`python -m riic.promotions <usuario>` calcula cuánto ganaría la base promocionando a cada operador
(más de 1 h).

## Cómo calcula

**Datos.** Tres fuentes:

1. `players/<usuario>/roster.json`: lo que guarda Krooster, por id de personaje. Los nombres salen
   de los datos del juego y de la guía, así que alters y variantes se resuelven solos.
2. `Arknights Base Combo Guide.xlsx`: habilidades por élite y fórmulas de los equipos (Vermeil,
   Mizuki, Shamare, Proviso…). Cada fórmula del código cita la celda de la que sale.
3. Datos del juego EN (`building_data.json`, `character_table.json`), descargados una vez a
   `.cache/` y fijados a un commit. Rellenan lo que la guía no lista (habilidades flojas, versiones
   de E0) y sirven para validar la guía.

**Producción por día.** Oro: 20 barras a +0% (72 min por barra). EXP: 8.000 (Tactical Battle
Record, 1.000 EXP en 3 h). TP: pedidos de 2/3/4 oros al 30/50/20%, 500 LMD por oro; Proviso sube
de media ×1,55 el LMD de cada pedido y Closure los cambia por los suyos (1.200 LMD por 2 oros en
144 min). Drones: uno cada 6 min más lo que den las centrales, 3 min de trabajo cada uno
(`laborRecoverTime` y `tradingReduceTimeUnit` del juego), todos a un TP; sin bonus son medio día
más de ese TP, y piden su oro. Si los TP piden más oro del que se fabrica, venden menos.

**Reglas.** Una habilidad solo cuenta si el operador ya llega a esa élite y nivel. Los buffs del
mismo tipo no se suman (solo el mayor). Proviso no funciona con Tequila ni con los que mejoran
pedidos. Las rampas («+20% que sube un 1% por hora») cuentan su media de 12 h, como la guía.

**Optimización.** Fábricas y TP de los dos turnos se eligen a la vez con programación lineal entera
(`scipy.optimize.milp`, HiGHS):

- Una variable binaria por equipo candidato y turno; cada operador trabaja en un solo sitio.
- Cada turno vende solo el oro que fabrica: el LMD vendido es continuo y está acotado por la
  capacidad del TP y por el oro del turno.
- Cada equipo de TP tiene un gemelo que se lleva los drones del turno (como mucho uno por turno),
  así que elegir a qué TP van sigue siendo lineal.
- Candidatos: los 20 mejores equipos de cada operador, en tres capas; cada capa se calcula sin los
  operadores de los mejores equipos de la anterior, para que al turno B le queden equipos sin las
  estrellas del A.

Centrales, CC, recepción y RRHH se eligen alrededor, y se repite hasta seis rondas desde dos
arranques. Los CC de los dos turnos se eligen juntos, para no partir una banda como Ave Mujica. Se
queda el mejor plan visto. Meter el CC dentro del programa lineal es exacto, pero se probó y daba
planes peores: HiGHS no cerraba el hueco en el tiempo límite. Los huecos libres del CC van primero
a quien sube pistas o RRHH y luego a quien reduce el gasto de moral. La moral no se optimiza: solo
se comprueba que cada operador aguanta su turno.

## Validación

Los tests comprueban el modelo contra fuentes que no son el propio código, con copias congeladas de
los rosters (`tests/data/`) para que una promoción nueva no rompa nada:

- **Contra el juego:** para cada operador e instalación, el % que usa el modelo es el que da el
  juego (unas 100 combinaciones), y cada número leído de la guía aparece en el texto del juego. Los
  drones salen de `building_data.json`: 240 al día y 3 min de trabajo cada uno.
- **Contra la guía:** el modelo reproduce los resultados que publica el Excel: Mizuki + 2
  Standard +90%, Proviso con dos de 30% +153,79%, Shamare +110,08%, Bubble +90–95%, Dorothy +95%,
  Penguin Logistics +100%, Exusiai Alter + Archetto + Lemuen +115%, Reserve A1 +70–85%, y las
  parejas de recepción.
- **Contra los rosters:** que todo operador tenga habilidades (Krooster escribe «Varkáris» y la
  guía «Valkáris»: con el lector antiguo, de texto, se perdía sin avisar), que ningún operador esté
  en dos sitios, que los dos turnos llenen todas las instalaciones y que todos los nombres de las
  reglas existan.

Dos datos solo están en la guía y no se pueden comprobar en el juego: los números de los pedidos de
Closure (NEW!F23) y que Exusiai Alter active el +25% de Lemuen (TP!B241).

## Límites

- El solver para a un 0,1% del óptimo, y elegir producción y CC por rondas no garantiza el óptimo
  global.
- Sin modelar: el equipo condicional de Jaye, Alanna (los robots rinden menos en las centrales de lo
  que ella suma), SilverAsh Alter (pide 3 de Kjerag en un TP), los equipos Worldly Plight y
  Perception Information, y el sesgo de pistas.
- Supuestos: instalaciones al máximo, dormitorios a nivel 5, ambiente >4k, servidor EN (235 drones
  de capacidad).
- Las horas de moral pueden salir algo cortas: si la guía repite una habilidad en dos hojas
  (Almond), su gasto de moral se suma dos veces. Solo afecta a la columna «Horas».

## Estructura

```
players/<usuario>/  roster.json (Krooster), settings.json (opcional), base_plan.md, skills_owned.csv
riic/__main__.py    python -m riic: descarga rosters y escribe los planes
riic/krooster.py    descarga de un perfil público de Krooster
riic/roster.py      lectura del roster
riic/excel.py       habilidades y fórmulas de la guía
riic/gamedata.py    datos del juego: nombres y habilidades que la guía no trae
riic/model.py       fórmulas y producción diaria
riic/optimize.py    elección de equipos
riic/promotions.py  python -m riic.promotions <usuario>: cuánto da cada promoción
tests/              comprobaciones contra el juego, el Excel y los rosters
```
