# Plan de base (2-4-3, roster actual)

Generado con `python -m riic` a partir de `Collection.txt`, `Arknights Base Combo Guide.xlsx` y los datos del juego EN (las habilidades que la guía no lista). No editar a mano: cambia el roster o los supuestos y vuelve a generarlo.

Los dos turnos se eligen a la vez para rotar cada 12 h; el A es el que más produce. «Horas» es lo que aguanta el operador que antes se queda sin moral (24 de moral, CC lvl 5).

## Turno A

| Instalación | Operadores | Producto | Productividad | Por día | Horas |
|---|---|---|---|---|---|
| CC | Paprika, Mon3tr, Civilight Eterna, Yahata Umiri, Wiš'adel | — | — | — | 34.3 |
| FAC1 | Dorothy, Purestream, Spot | Gold | +105.0% | 41 barras | 53.3 |
| FAC2 | Gravel, Haze, Totter | Gold | +97.5% | 40 barras | 53.3 |
| FAC3 | Bena, Bubble, Ceobe | Gold | +77.8% | 36 barras | 120.0 |
| FAC4 | Crownslayer, Tragodia, Vigna | EXP | +105.0% | 16.400 EXP | 53.3 |
| TP1 | Mitm, Shamare, Tequila | LMD | +120.1% | 22.592 LMD | 34.3 |
| TP2 | Archetto, Closure, Quartz | LMD | +126.8% | 23.280 LMD | 53.3 |
| PP1 | Greyy | drones | +25.0% | — | 43.6 |
| PP2 | Indigo | drones | +20.0% | — | 43.6 |
| PP3 | Liskarm | drones | +20.0% | — | 43.6 |
| RR | Typhon, Vigil | pistas | +120.0% | — | 43.6 |
| HR | Haruka | contacto | +60.0% | — | 43.6 |

- **LMD/día:** 65.078
- **EXP/día:** 16.400
- **Oro:** 116.0 barras/día fabricadas, 116.0 pedidas por los TP (drones incluidos)
- **Drones:** +65% de recuperación, al TP que más LMD da

## Turno B

| Instalación | Operadores | Producto | Productividad | Por día | Horas |
|---|---|---|---|---|---|
| CC | Amiya, Kal'tsit, Togawa Sakiko, Wakaba Mutsumi, Misumi Uika | — | — | — | 30.0 |
| FAC1 | Jessica, Mizuki, Steward | Gold | +98.0% | 40 barras | 36.9 |
| FAC2 | Cuora, Noir Corne, Vermeil | Gold | +84.0% | 37 barras | 36.9 |
| FAC3 | Almond, Aroma, Popukar | Gold | +83.0% | 37 barras | 24.0 |
| FAC4 | Fang, Perfumer, Vanilla | Gold | +81.8% | 36 barras | 36.9 |
| TP1 | Gummy, Lappland, Texas | LMD | +105.0% | 21.044 LMD | 25.3 |
| TP2 | Hoederer, Mantra, Proviso | LMD | +176.2% | 28.354 LMD | 36.9 |
| PP1 | Greyy Alter | drones | +28.0% | — | 32.0 |
| PP2 | Blaze Alter | drones | +25.0% | — | 32.0 |
| PP3 | Goldenglow | drones | +25.0% | — | 32.0 |
| RR | Ch'en Alter 2, Ines | pistas | +125.5% | — | 32.0 |
| HR | Penance | contacto | +55.0% | — | 19.2 |

- **LMD/día:** 74.633
- **EXP/día:** 0
- **Oro:** 149.3 barras/día fabricadas, 149.3 pedidas por los TP (drones incluidos)
- **Drones:** +78% de recuperación, al TP que más LMD da

## Fijos

- **TR (entrenador):** Logos
- **WS:** Kal'tsit Alter
- **DORM1:** Entelechia (+0.30 AoE) + Conviction (+0.70 ST); 3 plazas para descansar
- **DORM2:** Durin (+0.25 AoE) + Gracebearer (+0.70 ST); 3 plazas para descansar
- **DORM3:** Lumen (+0.25 AoE) + Saileach (+0.70 ST); 3 plazas para descansar
- **DORM4:** Ambriel (+0.20 AoE) + Czerny (+0.65 ST); 3 plazas para descansar
- **Activity Room:** cualquiera; solo da confianza, no produce.

## Supuestos

- Instalaciones a nivel máximo, DORMs a lvl 5 (20 niveles), Office lvl 3, ambiente >4k (+15% RR).
- 1 EXP vale 1 LMD (CE-5 y LS-5 dan lo mismo por cordura). `--exp-weight` lo cambia.
- Pedidos lvl 3: 30/50/20% de 2/3/4 oros, 500 LMD por oro (TP!E45). Proviso E2 ×1.5517 (TP!J193); Closure: 1200 LMD por 2 oros en 144 min (NEW!F23).
- Drones: uno cada 6 min y 3 min de trabajo cada uno (datos del juego), medio día de TP con +0% de recuperación; cada 10% más ≈ 5% (PP!B5). Todos a un TP.
- Rampas (Ceobe, Fang, Kroos, Ines, Spuria): media de las primeras 12 h, como el Excel.
- Greyy Alter: 23% (+1% por cada 10 de capacidad de drones; 235 en EN, PP!B65).
- Dawnstreak = Ch'en Alter 2 (char_1050_chen3), comprobado con los datos del juego.
- Texas solo da productividad con Lappland en el mismo TP (+65%, «Feud» en el juego).
