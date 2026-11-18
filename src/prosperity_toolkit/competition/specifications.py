"""IMC Prosperity 4 round specifications, product universes, and position limits.

Attribution:
    Product symbols, day indices, voucher strikes, and per-product position limits are
    corroborated across the MIT-licensed `kevin-fu1/imc-prosperity-4-backtester`
    (`prosperity4bt/constants.py`), `ADnocap/IMC_Prosperity4`, and raw historical CSVs.
    Note: The official IMC Notion wiki HTML requires interactive login and could not be
    scraped programmatically, so per-limit provenance is explicitly tracked in
    `docs/competition/COMPETITION_SPECIFICATION.md`.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

PROSPERITY4_ROUND_DAYS: Mapping[int, tuple[int, ...]] = MappingProxyType({
    0: (-2, -1),
    1: (-2, -1, 0),
    2: (-1, 0, 1),
    3: (0, 1, 2),
    4: (1, 2, 3),
    5: (2, 3, 4),
})

PROSPERITY4_VOUCHER_STRIKES: Mapping[str, int] = MappingProxyType({
    "VEV_4000": 4000,
    "VEV_4500": 4500,
    "VEV_5000": 5000,
    "VEV_5100": 5100,
    "VEV_5200": 5200,
    "VEV_5300": 5300,
    "VEV_5400": 5400,
    "VEV_5500": 5500,
    "VEV_6000": 6000,
    "VEV_6500": 6500,
})

PROSPERITY4_R5_CATEGORIES: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "Galaxy Sounds": (
        "GALAXY_SOUNDS_DARK_MATTER",
        "GALAXY_SOUNDS_BLACK_HOLES",
        "GALAXY_SOUNDS_PLANETARY_RINGS",
        "GALAXY_SOUNDS_SOLAR_WINDS",
        "GALAXY_SOUNDS_SOLAR_FLAMES",
    ),
    "Sleep Pods": (
        "SLEEP_POD_SUEDE",
        "SLEEP_POD_LAMB_WOOL",
        "SLEEP_POD_POLYESTER",
        "SLEEP_POD_NYLON",
        "SLEEP_POD_COTTON",
    ),
    "Microchips": (
        "MICROCHIP_CIRCLE",
        "MICROCHIP_OVAL",
        "MICROCHIP_SQUARE",
        "MICROCHIP_RECTANGLE",
        "MICROCHIP_TRIANGLE",
    ),
    "Pebbles": (
        "PEBBLES_XS",
        "PEBBLES_S",
        "PEBBLES_M",
        "PEBBLES_L",
        "PEBBLES_XL",
    ),
    "Robots": (
        "ROBOT_VACUUMING",
        "ROBOT_MOPPING",
        "ROBOT_DISHES",
        "ROBOT_LAUNDRY",
        "ROBOT_IRONING",
    ),
    "UV-Visors": (
        "UV_VISOR_YELLOW",
        "UV_VISOR_AMBER",
        "UV_VISOR_ORANGE",
        "UV_VISOR_RED",
        "UV_VISOR_MAGENTA",
    ),
    "Translators": (
        "TRANSLATOR_SPACE_GRAY",
        "TRANSLATOR_ASTRO_BLACK",
        "TRANSLATOR_ECLIPSE_CHARCOAL",
        "TRANSLATOR_GRAPHITE_MIST",
        "TRANSLATOR_VOID_BLUE",
    ),
    "Panels": (
        "PANEL_1X2",
        "PANEL_2X2",
        "PANEL_1X4",
        "PANEL_2X4",
        "PANEL_4X4",
    ),
    "Oxygen Shakes": (
        "OXYGEN_SHAKE_MORNING_BREATH",
        "OXYGEN_SHAKE_EVENING_BREATH",
        "OXYGEN_SHAKE_MINT",
        "OXYGEN_SHAKE_CHOCOLATE",
        "OXYGEN_SHAKE_GARLIC",
    ),
    "Snackpacks": (
        "SNACKPACK_CHOCOLATE",
        "SNACKPACK_VANILLA",
        "SNACKPACK_PISTACHIO",
        "SNACKPACK_STRAWBERRY",
        "SNACKPACK_RASPBERRY",
    ),
})

_R5_LIMITS: dict[str, int] = {
    sym: 10
    for group in PROSPERITY4_R5_CATEGORIES.values()
    for sym in group
}

PROSPERITY4_POSITION_LIMITS: Mapping[str, int] = MappingProxyType({
    "EMERALDS": 80,
    "TOMATOES": 80,
    "ASH_COATED_OSMIUM": 80,
    "INTARIAN_PEPPER_ROOT": 80,
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    **dict.fromkeys(PROSPERITY4_VOUCHER_STRIKES, 300),
    **_R5_LIMITS,
})

PROSPERITY4_ROUND_PRODUCTS: Mapping[int, tuple[str, ...]] = MappingProxyType({
    0: ("EMERALDS", "TOMATOES"),
    1: ("ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"),
    2: ("ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"),
    3: ("HYDROGEL_PACK", "VELVETFRUIT_EXTRACT", *PROSPERITY4_VOUCHER_STRIKES.keys()),
    4: ("HYDROGEL_PACK", "VELVETFRUIT_EXTRACT", *PROSPERITY4_VOUCHER_STRIKES.keys()),
    5: tuple(sym for group in PROSPERITY4_R5_CATEGORIES.values() for sym in group),
})


def get_round_products(round_num: int) -> tuple[str, ...]:
    """Return the official tradable symbols for a Prosperity 4 round (0–5)."""
    if round_num not in PROSPERITY4_ROUND_PRODUCTS:
        msg = f"Unknown Prosperity 4 round {round_num}; expected 0..5"
        raise ValueError(msg)
    return PROSPERITY4_ROUND_PRODUCTS[round_num]


def get_round_position_limits(round_num: int) -> dict[str, int]:
    """Return per-symbol position limits for a Prosperity 4 round (0–5)."""
    return {sym: PROSPERITY4_POSITION_LIMITS[sym] for sym in get_round_products(round_num)}
