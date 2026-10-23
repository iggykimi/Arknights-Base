# Plan de base (2-4-3, roster actual)

Generado con `python -m riic` a partir de `Collection.txt`, `Arknights Base Combo Guide.xlsx` y los datos del juego EN (las habilidades que la guía no lista). No editar a mano: cambia el roster o los supuestos y vuelve a generarlo.

El turno A es la mejor asignación posible; el turno B es la mejor con los operadores que quedan, para rotar cada 12 h. «Horas» es lo que aguanta el operador que antes se queda sin moral (24 de moral, CC lvl 5).

## Turno A

| Instalación | Operadores | Producto | Productividad | Por día | Horas |
|---|---|---|---|---|---|
| CC | Amiya, Kal'tsit, Civilight Eterna, Yahata Umiri, Wiš'adel | — | — | — | 32.0 |
| FAC1 | Aroma, Purestream, Steward | Gold | +95.0% | 39 barras | 34.3 |
| FAC2 | Jessica, Mizuki, Vanilla | Gold | +95.0% | 39 barras | 53.3 |
| FAC3 | Almond, Gravel, Totter | Gold | +92.5% | 38 barras | 30.0 |
| FAC4 | Perfumer, Tragodia, Vigna | EXP | +95.0% | 15.600 EXP | 53.3 |
| TP1 | Lappland, Proviso, Texas | LMD | +171.6% | 27.876 LMD | 32.0 |
| TP2 | Closure, Hoederer, Quartz | LMD | +120.9% | 22.680 LMD | 53.3 |
| PP1 | Greyy Alter | drones | +28.0% | — | 43.6 |
| PP2 | Blaze Alter | drones | +25.0% | — | 43.6 |
| PP3 | Goldenglow | drones | +25.0% | — | 43.6 |
| RR | Ch'en Alter 2, Ines | pistas | +145.5% | — | 43.6 |
| HR | Penance | contacto | +65.0% | — | 22.9 |

- **LMD/día:** 61.428
- **EXP/día:** 15.600
- **Oro:** 116.5 barras/día fabricadas, 115.3 pedidas por los TP (drones incluidos)
- **Drones:** +78% de recuperación, al TP que más LMD da

## Turno B

| Instalación | Operadores | Producto | Productividad | Por día | Horas |
|---|---|---|---|---|---|
| CC | Paprika, Mon3tr, Yūtenji Nyamu, Młynar, Coldshot | — | — | — | 40.0 |
| FAC1 | Ceobe, Cuora, Vermeil | Gold | +90.8% | 38 barras | 48.0 |
| FAC2 | Dorothy, Haze, Silence | Gold | +85.0% | 37 barras | 48.0 |
| FAC3 | Bena, Bubble, Spot | Gold | +76.0% | 35 barras | 48.0 |
| FAC4 | Crownslayer, Fang, Popukar | EXP | +88.8% | 15.100 EXP | 32.0 |
| TP1 | Archetto, Exusiai Alter, Lemuen | LMD | +125.0% | 23.097 LMD | 48.0 |
| TP2 | Mitm, Shamare, Tequila | LMD | +120.1% | 22.592 LMD | 32.0 |
| PP1 | Greyy | drones | +25.0% | — | 48.0 |
| PP2 | Indigo | drones | +20.0% | — | 48.0 |
| PP3 | Liskarm | drones | +20.0% | — | 48.0 |
| RR | Typhon, Vigil | pistas | +110.0% | — | 48.0 |
| HR | Haruka | contacto | +50.0% | — | 48.0 |

- **LMD/día:** 53.196
- **EXP/día:** 15.100
- **Oro:** 110.3 barras/día fabricadas, 106.4 pedidas por los TP (drones incluidos)
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
