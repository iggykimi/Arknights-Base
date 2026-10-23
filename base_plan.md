# Plan de base (2-4-3, roster actual)

Generado con `python -m riic` a partir de `Collection.txt`, `Arknights Base Combo Guide.xlsx` y los datos del juego EN (las habilidades que la guía no lista). No editar a mano: cambia el roster o los supuestos y vuelve a generarlo.

El turno A es la mejor asignación posible; el turno B es la mejor con los operadores que quedan, para rotar cada 12 h. «Horas» es lo que aguanta el operador que antes se queda sin moral (24 de moral, CC lvl 5).

## Turno A

| Instalación | Operadores | Producto | Productividad | Por día | Horas |
|---|---|---|---|---|---|
| CC | Amiya, Kal'tsit, Młynar, Wiš'adel, Coldshot | — | — | — | 36.9 |
| FAC1 | Ceobe, Purestream, Vermeil | Gold | +100.8% | 40 barras | 53.3 |
| FAC2 | Dorothy, Gravel, Spot | Gold | +100.0% | 40 barras | 53.3 |
| FAC3 | Mizuki, Steward, Vanilla | Gold | +95.0% | 39 barras | 53.3 |
| FAC4 | Crownslayer, Tragodia, Vigna | EXP | +105.0% | 16.400 EXP | 53.3 |
| TP1 | Archetto, Hoederer, Proviso | LMD | +187.1% | 29.469 LMD | 53.3 |
| TP2 | Closure, Lappland, Texas | LMD | +116.3% | 22.200 LMD | 32.0 |
| PP1 | Greyy Alter | drones | +28.0% | — | 53.3 |
| PP2 | Blaze Alter | drones | +25.0% | — | 53.3 |
| PP3 | Goldenglow | drones | +25.0% | — | 53.3 |
| RR | Ch'en Alter 2, Ines | pistas | +130.5% | — | 53.3 |
| HR | Penance | contacto | +55.0% | — | 25.3 |

- **LMD/día:** 63.162
- **EXP/día:** 16.400
- **Oro:** 119.2 barras/día fabricadas, 118.9 pedidas por los TP (drones incluidos)
- **Drones:** +78% de recuperación, al TP que más LMD da

## Turno B

| Instalación | Operadores | Producto | Productividad | Por día | Horas |
|---|---|---|---|---|---|
| CC | Paprika, Mon3tr, Dobermann, Flametail, Heavyrain | — | — | — | 43.6 |
| FAC1 | Aroma, Fang, Haze | Gold | +83.8% | 37 barras | 26.7 |
| FAC2 | Almond, Kroos, Popukar | Gold | +77.5% | 36 barras | 24.0 |
| FAC3 | Bena, Bubble, Snow Hunter | Gold | +66.0% | 33 barras | 26.7 |
| FAC4 | Jessica, Perfumer, Totter | EXP | +82.5% | 14.600 EXP | 36.9 |
| TP1 | Mitm, Shamare, Tequila | LMD | +120.1% | 22.592 LMD | 26.7 |
| TP2 | Midnight, Mousse, Quartz | LMD | +104.0% | 20.942 LMD | 36.9 |
| PP1 | Greyy | drones | +25.0% | — | 32.0 |
| PP2 | Indigo | drones | +20.0% | — | 32.0 |
| PP3 | Liskarm | drones | +20.0% | — | 32.0 |
| RR | Typhon, Vigil | pistas | +105.0% | — | 32.0 |
| HR | Haruka | contacto | +50.0% | — | 32.0 |

- **LMD/día:** 50.876
- **EXP/día:** 14.600
- **Oro:** 105.5 barras/día fabricadas, 101.8 pedidas por los TP (drones incluidos)
- **Drones:** +65% de recuperación, al TP que más LMD da

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
- Drones: 10% de recuperación ≈ 5% de productividad (PP!B5), todos al mejor TP.
- Rampas (Ceobe, Fang, Kroos, Ines, Spuria): media de las primeras 12 h, como el Excel.
- Greyy Alter: 23% (+1% por cada 10 de capacidad de drones; 235 en EN, PP!B65).
- Dawnstreak = Ch'en Alter 2 (char_1050_chen3), comprobado con los datos del juego.
- Texas solo da productividad con Lappland en el mismo TP (+65%, «Feud» en el juego).
