"""Support (attachment) checks for common blocks that pop off without a supporting block.

This is a warning-level lint over a generated :class:`BlockVolume`, limited to
frequently used attached blocks (lanterns, torches, wall-mounted items, doors,
beds, plants, ...). Unknown blocks and positions outside the structure are never
reported, so a clean result does not prove the build is physically valid.
"""

from __future__ import annotations

from dataclasses import dataclass

from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.volume import BlockVolume

DIRECTIONS: dict[str, Vec3] = {
    "north": Vec3(0, 0, -1),
    "south": Vec3(0, 0, 1),
    "east": Vec3(1, 0, 0),
    "west": Vec3(-1, 0, 0),
    "up": Vec3(0, 1, 0),
    "down": Vec3(0, -1, 0),
}
UP = DIRECTIONS["up"]
DOWN = DIRECTIONS["down"]

AIR_IDS = frozenset({"air", "cave_air", "void_air"})

# Blocks that never provide a sturdy face (partial shapes, plants, liquids, ...).
NON_SUPPORTING_IDS = frozenset(
    {
        "water",
        "lava",
        "fire",
        "soul_fire",
        "torch",
        "soul_torch",
        "redstone_torch",
        "wall_torch",
        "soul_wall_torch",
        "redstone_wall_torch",
        "lantern",
        "soul_lantern",
        "chain",
        "iron_bars",
        "ladder",
        "vine",
        "lever",
        "tripwire",
        "tripwire_hook",
        "redstone_wire",
        "repeater",
        "comparator",
        "cake",
        "flower_pot",
        "end_rod",
        "lightning_rod",
        "cobweb",
        "short_grass",
        "grass",
        "tall_grass",
        "fern",
        "large_fern",
        "dead_bush",
        "seagrass",
        "tall_seagrass",
        "lily_pad",
        "sugar_cane",
        "bamboo",
        "kelp",
        "kelp_plant",
        "wheat",
        "carrots",
        "potatoes",
        "beetroots",
        "nether_wart",
        "melon_stem",
        "pumpkin_stem",
        "sweet_berry_bush",
        "brown_mushroom",
        "red_mushroom",
        "dandelion",
        "poppy",
        "blue_orchid",
        "allium",
        "azure_bluet",
        "oxeye_daisy",
        "cornflower",
        "lily_of_the_valley",
        "wither_rose",
        "torchflower",
        "pitcher_plant",
        "sunflower",
        "lilac",
        "rose_bush",
        "peony",
        "candle",
        "bell",
        "conduit",
        "scaffolding",
        "moss_carpet",
        "snow",
    }
)
NON_SUPPORTING_SUFFIXES = (
    "_pane",
    "_door",
    "_carpet",
    "_pressure_plate",
    "_button",
    "_sign",
    "_banner",
    "_rail",
    "_candle",
    "_sapling",
    "_tulip",
    "_bed",
    "_coral",
    "_coral_fan",
    "_bush",
    "_fungus",
    "_roots",
    "_vines",
    "_head",
    "_skull",
    "_propagule",
    "_fence_gate",
)
CENTER_SUPPORT_SUFFIXES = ("_fence", "_wall")  # torches / lanterns can sit on or hang from these
HANG_SUPPORT_IDS = frozenset({"chain", "iron_bars"})

FLOOR_TORCHES = frozenset({"torch", "soul_torch", "redstone_torch"})
WALL_TORCHES = frozenset({"wall_torch", "soul_wall_torch", "redstone_wall_torch"})
LANTERNS = frozenset({"lantern", "soul_lantern"})

DIRT_LIKE = frozenset(
    {
        "grass_block",
        "dirt",
        "coarse_dirt",
        "podzol",
        "rooted_dirt",
        "moss_block",
        "farmland",
        "mud",
        "mycelium",
    }
)
SMALL_PLANTS = frozenset(
    {
        "short_grass",
        "grass",
        "tall_grass",
        "fern",
        "large_fern",
        "dead_bush",
        "dandelion",
        "poppy",
        "blue_orchid",
        "allium",
        "azure_bluet",
        "oxeye_daisy",
        "cornflower",
        "lily_of_the_valley",
        "wither_rose",
        "torchflower",
        "sunflower",
        "lilac",
        "rose_bush",
        "peony",
        "sweet_berry_bush",
    }
)
CROPS = frozenset({"wheat", "carrots", "potatoes", "beetroots", "melon_stem", "pumpkin_stem"})


@dataclass(frozen=True)
class SupportWarning:
    position: Vec3
    block: BlockState
    message: str

    def format(self) -> str:
        return f"WARNING {self.position} {self.block}\n  {self.message}"


def format_warnings(warnings: list[SupportWarning]) -> str:
    if not warnings:
        return ""
    noun = "warning" if len(warnings) == 1 else "warnings"
    return "\n\n".join(w.format() for w in warnings) + f"\n\n{len(warnings)} {noun} found."


def short_id(state: BlockState) -> str:
    return state.id.split(":", 1)[1] if state.id.startswith("minecraft:") else state.id


# --- face sturdiness ---------------------------------------------------------


def _is_non_supporting(name: str) -> bool:
    return name in AIR_IDS or name in NON_SUPPORTING_IDS or name.endswith(NON_SUPPORTING_SUFFIXES)


def supports_from_top(state: BlockState) -> bool:
    """Can a torch-like block stand on this block's top face?"""
    name = short_id(state)
    if name.endswith("_trapdoor"):
        return state.get("open") != "true" and state.get("half") == "top"
    if name.endswith("_slab"):
        return state.get("type") in ("top", "double")
    if name.endswith("_stairs"):
        return state.get("half") == "top"
    if name == "snow":
        return state.get("layers") == "8"
    if name.endswith(CENTER_SUPPORT_SUFFIXES):
        return True
    if _is_non_supporting(name):
        return False
    return True


def supports_from_bottom(state: BlockState) -> bool:
    """Can a lantern hang from this block's bottom face?"""
    name = short_id(state)
    if name.endswith("_trapdoor"):
        return state.get("open") != "true" and state.get("half") == "bottom"
    if name.endswith("_slab"):
        return state.get("type") in ("bottom", "double")
    if name.endswith("_stairs"):
        return state.get("half") == "bottom"
    if name in HANG_SUPPORT_IDS or name.endswith(CENTER_SUPPORT_SUFFIXES):
        return True
    if _is_non_supporting(name):
        return False
    return True


def supports_from_side(state: BlockState, facing: str) -> bool:
    """Can a wall-mounted block that points ``facing`` attach to this block's face?"""
    name = short_id(state)
    if name.endswith("_stairs"):
        return state.get("facing") == facing
    if name.endswith(("_slab", "_trapdoor")) or name.endswith(CENTER_SUPPORT_SUFFIXES):
        return False
    if _is_non_supporting(name):
        return False
    return True


# --- checks -----------------------------------------------------------------


def check_support(volume: BlockVolume) -> list[SupportWarning]:
    bounds = volume.bounds()
    if bounds is None:
        return []
    warnings: list[SupportWarning] = []
    for pos, state in volume:
        message = _check_one(volume, bounds, pos, state)
        if message is not None:
            warnings.append(SupportWarning(pos, state, message))
    warnings.sort(key=lambda w: (w.position.y, w.position.z, w.position.x))
    return warnings


def _neighbour(volume: BlockVolume, bounds: AABB, pos: Vec3) -> BlockState | None:
    """Block at ``pos``: air when unset inside the structure, None when outside (unknown)."""
    if not bounds.contains(pos):
        return None
    return volume.get(pos) or BlockState.of("air")


def _check_one(volume: BlockVolume, bounds: AABB, pos: Vec3, state: BlockState) -> str | None:
    name = short_id(state)

    if name in LANTERNS:
        if state.get("hanging") == "true":
            return _need(volume, bounds, pos + UP, supports_from_bottom, "a solid block above")
        return _need(volume, bounds, pos + DOWN, supports_from_top, "a solid block below")

    if name in FLOOR_TORCHES or name == "candle" or name.endswith("_candle"):
        return _need(volume, bounds, pos + DOWN, supports_from_top, "a solid block below")

    if name.endswith("_pressure_plate"):
        return _need(volume, bounds, pos + DOWN, supports_from_top, "a solid block below")

    if name.endswith("_carpet") or name == "moss_carpet" or name == "snow":
        below = _neighbour(volume, bounds, pos + DOWN)
        if below is not None and short_id(below) in AIR_IDS:
            return "Needs a block below; found air."
        return None

    if name in WALL_TORCHES or name.endswith(("_wall_sign", "_wall_banner")) or name == "ladder":
        return _need_wall(volume, bounds, pos, state.get("facing"))

    if name.endswith("_button") or name == "lever":
        face = state.get("face") or "wall"
        if face == "floor":
            return _need(volume, bounds, pos + DOWN, supports_from_top, "a solid block below")
        if face == "ceiling":
            return _need(volume, bounds, pos + UP, supports_from_bottom, "a solid block above")
        return _need_wall(volume, bounds, pos, state.get("facing"))

    if name.endswith("_door"):
        return _check_door(volume, bounds, pos, state)

    if name.endswith("_bed"):
        return _check_bed(volume, bounds, pos, state)

    if name in SMALL_PLANTS or name.endswith(("_sapling", "_tulip")):
        return _need_below_in(volume, bounds, pos, DIRT_LIKE, "dirt, grass or similar")

    if name in CROPS:
        return _need_below_in(volume, bounds, pos, {"farmland"}, "farmland")

    if name == "nether_wart":
        return _need_below_in(volume, bounds, pos, {"soul_sand"}, "soul sand")

    return None


def _need(
    volume: BlockVolume,
    bounds: AABB,
    support_pos: Vec3,
    predicate,
    description: str,
) -> str | None:
    support = _neighbour(volume, bounds, support_pos)
    if support is None or predicate(support):
        return None
    return f"Needs {description}; found {support}."


def _need_wall(volume: BlockVolume, bounds: AABB, pos: Vec3, facing: str | None) -> str | None:
    if facing not in ("north", "south", "east", "west"):
        return None
    support = _neighbour(volume, bounds, pos - DIRECTIONS[facing])
    if support is None or supports_from_side(support, facing):
        return None
    return f"Needs a solid block behind it (opposite to facing={facing}); found {support}."


def _need_below_in(
    volume: BlockVolume, bounds: AABB, pos: Vec3, allowed: set[str] | frozenset[str], what: str
) -> str | None:
    below = _neighbour(volume, bounds, pos + DOWN)
    if below is None or short_id(below) in allowed:
        return None
    return f"Needs {what} below; found {below}."


def _check_door(volume: BlockVolume, bounds: AABB, pos: Vec3, state: BlockState) -> str | None:
    half = state.get("half") or "lower"  # the default (as written by ``import``)
    if half == "lower":
        below = _neighbour(volume, bounds, pos + DOWN)
        if below is not None and not supports_from_top(below):
            return f"Needs a solid block below; found {below}."
        other = _neighbour(volume, bounds, pos + UP)
        if other is not None and not _same_door(state, other, "upper"):
            return f"Upper half of the door is missing above; found {other}."
        return None
    if half == "upper":
        other = _neighbour(volume, bounds, pos + DOWN)
        if other is not None and not _same_door(state, other, "lower"):
            return f"Lower half of the door is missing below; found {other}."
    return None


def _same_door(door: BlockState, other: BlockState, half: str) -> bool:
    return (
        other.id == door.id
        and (other.get("half") or "lower") == half
        and (other.get("facing") or "north") == (door.get("facing") or "north")
        and (other.get("hinge") or "left") == (door.get("hinge") or "left")
    )


def _check_bed(volume: BlockVolume, bounds: AABB, pos: Vec3, state: BlockState) -> str | None:
    facing = state.get("facing")
    part = state.get("part")
    if facing not in DIRECTIONS or part not in ("foot", "head"):
        return None
    direction = DIRECTIONS[facing]
    other_pos = pos + direction if part == "foot" else pos - direction
    other = _neighbour(volume, bounds, other_pos)
    if other is None:
        return None
    expected = "head" if part == "foot" else "foot"
    if other.id != state.id or other.get("part") != expected or other.get("facing") != facing:
        return f"Bed {expected} is missing at {other_pos}; found {other}."
    return None
