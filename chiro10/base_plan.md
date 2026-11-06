# Plan de base (2-4-3, roster actual)

Generado con `python -m riic` a partir de `chiro10.json`, `Arknights Base Combo Guide.xlsx` y los datos del juego EN (las habilidades que la guía no lista). No editar a mano: cambia el roster o los supuestos y vuelve a generarlo.

Los dos turnos se eligen a la vez para rotar cada 12 h; el A es el que más produce. «Horas» es lo que aguanta el operador que antes se queda sin moral (24 de moral, CC lvl 5).

## Turno A

| Instalación | Operadores | Producto | Productividad | Por día | Horas |
|---|---|---|---|---|---|
| CC | Amiya, Mon3tr, Civilight Eterna, Wiš'adel, Młynar | — | — | — | 36.9 |
| FAC1 | Almond, Bryophyta, Haze | Gold | +90.0% | 38 barras | 34.3 |
| FAC2 | Aroma, Minimalist, Purestream | Gold | +90.0% | 38 barras | 40.0 |
| FAC3 | Jessica, Meteor, Perfumer | Gold | +70.0% | 34 barras | 68.6 |
| FAC4 | FEater, Tragodia, Vigna | EXP | +100.0% | 16.000 EXP | 68.6 |
| TP1 | Jaye, Paprika, Shamare | LMD | +101.6% | 20.695 LMD | 40.0 |
| TP2 | Catapult, Closure, SilverAsh | LMD | +116.3% | 22.200 LMD | 68.6 |
| PP1 | Greyy Alter | drones | +28.0% | — | 68.6 |
| PP2 | Blaze Alter | drones | +25.0% | — | 68.6 |
| PP3 | Greyy | drones | +25.0% | — | 68.6 |
| RR | Ch'en Alter 2, Ines | pistas | +145.5% | — | 68.6 |
| HR | Penance | contacto | +55.0% | — | 28.2 |

- **LMD/día:** 61.910
- **EXP/día:** 16.000
- **Oro:** 110.0 barras/día fabricadas, 111.3 pedidas por los TP (drones incluidos) — los TP podrían vender más; el LMD ya cuenta solo el oro fabricado
- **Drones:** +78% de recuperación, al TP que más LMD da

## Turno B

| Instalación | Operadores | Producto | Productividad | Por día | Horas |
|---|---|---|---|---|---|
| CC | Togawa Sakiko, Wakaba Mutsumi, Misumi Uika, Yahata Umiri, Yūtenji Nyamu | — | — | — | 30.0 |
| FAC1 | Fang, Thorns Alter, Totter | Gold | +88.2% | 38 barras | 36.9 |
| FAC2 | Fartooth, Popukar, Vanilla | Gold | +72.0% | 34 barras | 26.7 |
| FAC3 | Figurino, Silence, Snow Hunter | Gold | +62.0% | 32 barras | 26.7 |
| FAC4 | Beanstalk, Cement, Kroos | Gold | +59.5% | 32 barras | 36.9 |
| TP1 | Lappland, Mousse, Texas | LMD | +105.0% | 21.044 LMD | 25.3 |
| TP2 | Gummy, Proviso, Snowsant | LMD | +156.0% | 26.283 LMD | 36.9 |
| PP1 | Lucilla | drones | +20.0% | — | 32.0 |
| PP2 | PhonoR-0 | drones | +20.0% | — | 32.0 |
| PP3 | Pudding | drones | +20.0% | — | 32.0 |
| RR | Surfer, Vigil | pistas | +101.0% | — | 19.2 |
| HR | Haruka | contacto | +60.0% | — | 32.0 |

- **LMD/día:** 68.175
- **EXP/día:** 0
- **Oro:** 136.3 barras/día fabricadas, 136.7 pedidas por los TP (drones incluidos)
- **Drones:** +60% de recuperación, al TP que más LMD da

## Fijos

- **TR (entrenador):** Logos
- **WS:** Kal'tsit
- **DORM1:** Lumen (+0.30 AoE) + Conviction (+0.70 ST); 3 plazas para descansar
- **DORM2:** Ambriel (+0.20 AoE) + Gracebearer (+0.70 ST); 3 plazas para descansar
- **DORM3:** Durin (+0.20 AoE) + Saileach (+0.70 ST); 3 plazas para descansar
- **DORM4:** Entelechia (+0.20 AoE) + Czerny (+0.65 ST); 3 plazas para descansar
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
