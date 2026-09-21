"""Read the style of an existing structure out of a BlockVolume: which blocks play
which role (walls, floors, roof, ...), the storey layout, the roof shape and the
window / door rhythm. ``mcblueprint design`` turns the result into a design preset.

Everything here is a heuristic over a plain block grid; it is meant to give a human
or an AI a good first draft, not a faithful reconstruction.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import mode

from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.support import SMALL_PLANTS, short_id
from mcblueprint.volume import BlockVolume

ROLE_ORDER = (
    "wall",
    "post",
    "beam",
    "floor",
    "roof",
    "ridge",
    "gable",
    "foundation",
    "ceiling",
    "interior",
    "window",
    "door",
    "light",
    "decoration",
)
PALETTE_ROLES = ("wall", "post", "beam", "floor", "roof", "ridge", "gable", "foundation", "ceiling")
ROOF_RATIO = 0.5  # share of stairs / slabs in a layer for it to count as roof
FLOOR_RATIO = 0.5  # share of the widest floor layer for another layer to count as a floor

LIGHT_NAMES = frozenset(
    {
        "lantern",
        "soul_lantern",
        "torch",
        "wall_torch",
        "soul_torch",
        "soul_wall_torch",
        "redstone_torch",
        "glowstone",
        "sea_lantern",
        "shroomlight",
        "redstone_lamp",
        "end_rod",
        "campfire",
        "soul_campfire",
        "ochre_froglight",
        "verdant_froglight",
        "pearlescent_froglight",
        "copper_bulb",
    }
)
DECORATION_NAMES = frozenset(
    {
        "bell",
        "chain",
        "ladder",
        "bookshelf",
        "chiseled_bookshelf",
        "chest",
        "barrel",
        "flower_pot",
        "lectern",
        "anvil",
        "cauldron",
        "composter",
        "hay_block",
        "cobweb",
        "vine",
        "moss_carpet",
        "lightning_rod",
        "scaffolding",
        "crafting_table",
        "furnace",
        "smoker",
        "blast_furnace",
        "loom",
        "grindstone",
        "stonecutter",
        "cartography_table",
        "fletching_table",
        "smithing_table",
        "jukebox",
        "note_block",
    }
)
DECORATION_SUFFIXES = (
    "_fence",
    "_wall",
    "_carpet",
    "_banner",
    "_sign",
    "_hanging_sign",
    "_bed",
    "_leaves",
    "_sapling",
    "_candle",
    "_head",
    "_skull",
    "_shelf",
)
WINDOW_SUFFIXES = ("_pane", "_bars", "_glass")
DOOR_SUFFIXES = ("_door", "_trapdoor", "_fence_gate")
POST_MARKERS = ("_log", "_wood", "_pillar")
ROOF_SUFFIXES = ("_stairs", "_slab")


def kind_of(name: str) -> str | None:
    """Fixed role of a block by name, or None for structural blocks."""
    if name.endswith(WINDOW_SUFFIXES) or name == "glass" or name == "tinted_glass":
        return "window"
    if name.endswith(DOOR_SUFFIXES):
        return "door"
    if name in LIGHT_NAMES or name.endswith("_candle"):
        return "light"
    if (
        name in DECORATION_NAMES
        or name.endswith(DECORATION_SUFFIXES)
        or name in SMALL_PLANTS
        or name.startswith("potted_")
        or name.endswith(("_bush", "_flower", "_grass"))
    ):
        return "decoration"
    return None


def palette_id(state: BlockState) -> str:
    """Block id for a palette entry: orientation is set by the operations later, so only
    a horizontal ``axis`` (beams) survives."""
    axis = state.get("axis")
    if axis in ("x", "z") and short_id(state).endswith(("_log", "_wood", "_pillar", "_stem")):
        return f"{state.id}[axis={axis}]"
    return state.id


@dataclass
class RoofInfo:
    style: str  # gable | hip
    ridge: str | None  # x | z for gable
    block: str
    ridge_block: str | None
    gable_block: str | None
    overhang: int
    rise: int


@dataclass
class WindowInfo:
    block: str
    width: int
    height: int
    sill: int
    count: int
    spacing: int | None


@dataclass
class DesignAnalysis:
    bounds: AABB
    footprint: AABB  # walls (without the roof overhang)
    roles: dict[str, Counter[str]] = field(default_factory=dict)
    floor_levels: list[int] = field(default_factory=list)
    wall_height: int | None = None
    storey_heights: list[int] = field(default_factory=list)
    wall_thickness: int | None = None
    roof: RoofInfo | None = None
    windows: WindowInfo | None = None
    doors: Counter[str] = field(default_factory=Counter)
    door_count: int = 0
    lights: Counter[str] = field(default_factory=Counter)
    decoration: Counter[str] = field(default_factory=Counter)
    role_map: dict[Vec3, str] = field(default_factory=dict)

    @property
    def size(self) -> Vec3:
        return self.bounds.size

    def top(self, role: str) -> str | None:
        counter = self.roles.get(role)
        return counter.most_common(1)[0][0] if counter else None

    def palette(self, role: str, limit: int = 5, minimum: float = 0.08) -> list[tuple[str, int]]:
        """``(block id, weight)`` with weights in percent, largest first."""
        counter = self.roles.get(role)
        if not counter:
            return []
        total = sum(counter.values())
        entries = [(k, v / total) for k, v in counter.most_common(limit) if v / total >= minimum]
        if not entries:
            entries = [(counter.most_common(1)[0][0], 1.0)]
        weights = [max(1, round(share * 100)) for _, share in entries]
        return list(zip((k for k, _ in entries), weights, strict=True))


def analyze(volume: BlockVolume) -> DesignAnalysis:
    cells = {pos: state for pos, state in volume if not state.id.endswith("air")}
    bounds = volume.bounds()
    if bounds is None or not cells:
        raise ValueError("nothing to analyze")
    names = {pos: short_id(state) for pos, state in cells.items()}
    fixed = {pos: kind_of(name) for pos, name in names.items()}
    structural = {pos for pos, kind in fixed.items() if kind is None}

    roof_base = _roof_base(structural, names, bounds)
    roles: dict[Vec3, str] = {}
    for pos, kind in fixed.items():
        if kind is not None:
            roles[pos] = kind
    band = {p for p in structural if roof_base is not None and p.y >= roof_base}
    stairs_top = max((p.y for p in band if names[p].endswith("_stairs")), default=None)
    roof_id = Counter(names[p] for p in band if names[p].endswith("_stairs")).most_common(1)
    gable_id = Counter(
        names[p]
        for p in band
        if not names[p].endswith(ROOF_SUFFIXES) and (stairs_top is None or p.y <= stairs_top)
    ).most_common(1)
    # the eaves: layers just below the roof band that still carry the roof's stairs
    eaves: set[int] = set()
    if roof_base is not None and roof_id:
        y = roof_base - 1
        while any(p.y == y and names[p] == roof_id[0][0] for p in structural):
            eaves.add(y)
            y -= 1
    for pos in structural:
        name = names[pos]
        if pos in band:
            if name.endswith(ROOF_SUFFIXES):
                roles[pos] = "roof"
            elif stairs_top is not None and pos.y > stairs_top:
                roles[pos] = "ridge"
            else:
                roles[pos] = "gable"
            continue
        if pos.y in eaves and name.endswith(ROOF_SUFFIXES):
            roles[pos] = "roof"
            continue
        if pos.y in eaves and gable_id and name == gable_id[0][0]:
            roles[pos] = "gable"
            continue
        exterior = any(
            (pos + d) not in cells
            for d in (Vec3(1, 0, 0), Vec3(-1, 0, 0), Vec3(0, 0, 1), Vec3(0, 0, -1))
        )
        if pos.y == bounds.min.y and exterior:
            roles[pos] = "foundation"
        elif exterior:
            if any(m in name for m in POST_MARKERS):
                axis = cells[pos].get("axis")
                roles[pos] = "beam" if axis in ("x", "z") else "post"
            else:
                roles[pos] = "wall"
        elif (pos + Vec3(0, 1, 0)) not in cells:
            roles[pos] = "floor"
        elif (pos - Vec3(0, 1, 0)) not in cells:
            roles[pos] = "ceiling"
        else:
            roles[pos] = "interior"

    counters: dict[str, Counter[str]] = {role: Counter() for role in ROLE_ORDER}
    for pos, role in roles.items():
        counters[role][palette_id(cells[pos])] += 1
    result = DesignAnalysis(bounds, _footprint(roles, ("wall", "post"), bounds))
    result.roles = {role: c for role, c in counters.items() if c}
    result.role_map = roles

    result.floor_levels = _floor_levels(roles)
    base = result.floor_levels[0] if result.floor_levels else bounds.min.y
    wall_top = (roof_base - 1) if roof_base is not None else bounds.max.y
    wall_ys = [p.y for p, r in roles.items() if r in ("wall", "post")]
    if wall_ys:
        wall_top = min(wall_top, max(wall_ys))
        result.wall_height = wall_top - base
    result.storey_heights = [
        b - a for a, b in zip(result.floor_levels, result.floor_levels[1:], strict=False)
    ]
    result.wall_thickness = _wall_thickness(roles, result.footprint, base)
    result.roof = _roof_info(roles, cells, names, roof_base, result.footprint)
    result.windows = _window_info(roles, cells, result.floor_levels, base)
    for pos, role in roles.items():
        if role == "door":
            state = cells[pos]
            if state.get("half") != "upper":
                result.doors[state.id] += 1
                result.door_count += 1
        elif role == "light":
            result.lights[cells[pos].id] += 1
        elif role == "decoration":
            result.decoration[cells[pos].id] += 1
    return result


# --- helpers ------------------------------------------------------------------


def _roof_base(structural: set[Vec3], names: dict[Vec3, str], bounds: AABB) -> int | None:
    """Lowest layer from which stairs / slabs dominate the structural blocks."""
    by_y: dict[int, list[str]] = {}
    for pos in structural:
        by_y.setdefault(pos.y, []).append(names[pos])
    roofish = [
        y
        for y, layer in by_y.items()
        if sum(1 for n in layer if n.endswith(ROOF_SUFFIXES)) >= ROOF_RATIO * len(layer)
    ]
    if not roofish:
        return None
    base = min(roofish)
    # a roof sits on top of the walls: ignore stray stair layers at the very bottom
    return base if base > bounds.min.y else None


def _footprint(roles: dict[Vec3, str], wanted: tuple[str, ...], bounds: AABB) -> AABB:
    points = [p for p, r in roles.items() if r in wanted]
    if not points:
        return bounds
    return AABB(
        Vec3(min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)),
        Vec3(max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)),
    )


def _floor_levels(roles: dict[Vec3, str]) -> list[int]:
    per_y: Counter[int] = Counter(p.y for p, r in roles.items() if r == "floor")
    if not per_y:
        return []
    widest = max(per_y.values())
    return sorted(y for y, n in per_y.items() if n >= FLOOR_RATIO * widest)


def _wall_thickness(roles: dict[Vec3, str], footprint: AABB, base: int) -> int | None:
    """Mode of the run of wall cells met when walking inwards from each side."""
    y = base + 2 if base + 2 <= footprint.max.y else footprint.max.y
    solid = {
        (p.x, p.z) for p, r in roles.items() if p.y == y and r in ("wall", "post", "window", "door")
    }
    if not solid:
        return None
    runs_x, runs_z = [], []
    for z in range(footprint.min.z, footprint.max.z + 1):
        for x0, step in ((footprint.min.x, 1), (footprint.max.x, -1)):
            x = x0
            while footprint.min.x <= x <= footprint.max.x and (x, z) not in solid:
                x += step  # skip the gap outside a round or recessed wall
            n = 0
            while (x, z) in solid and n < 6:
                n, x = n + 1, x + step
            if n:
                runs_x.append(n)
    for x in range(footprint.min.x, footprint.max.x + 1):
        for z0, step in ((footprint.min.z, 1), (footprint.max.z, -1)):
            z = z0
            while footprint.min.z <= z <= footprint.max.z and (x, z) not in solid:
                z += step
            n = 0
            while (x, z) in solid and n < 6:
                n, z = n + 1, z + step
            if n:
                runs_z.append(n)
    modes = [mode(runs) for runs in (runs_x, runs_z) if runs]
    return min(modes) if modes else None


def _roof_info(
    roles: dict[Vec3, str],
    cells: dict[Vec3, BlockState],
    names: dict[Vec3, str],
    roof_base: int | None,
    footprint: AABB,
) -> RoofInfo | None:
    if roof_base is None:
        return None
    stairs = [p for p, r in roles.items() if r == "roof" and names[p].endswith("_stairs")]
    slabs = [p for p, r in roles.items() if r == "roof" and names[p].endswith("_slab")]
    if not stairs and not slabs:
        return None
    facing: Counter[str] = Counter(cells[p].get("facing") or "?" for p in stairs)
    total = sum(facing.values()) or 1
    ns = facing["north"] + facing["south"]
    ew = facing["east"] + facing["west"]
    if not stairs:
        style, ridge = "flat", None
    elif ns >= 0.85 * total:
        style, ridge = "gable", "x"
    elif ew >= 0.85 * total:
        style, ridge = "gable", "z"
    elif all(facing[d] >= 0.1 * total for d in ("north", "south", "east", "west")):
        style, ridge = "hip", None
    else:
        style, ridge = "gable", ("x" if ns >= ew else "z")
    block_counter: Counter[str] = Counter(palette_id(cells[p]) for p in (stairs or slabs))
    roof_cells = [p for p, r in roles.items() if r in ("roof", "gable", "ridge")]
    rx = min(p.x for p in roof_cells)
    rz = min(p.z for p in roof_cells)
    overhang = max(0, footprint.min.x - rx, footprint.min.z - rz)
    top_slabs = [p for p in slabs if p.y == max(q.y for q in roof_cells)]
    ridge_counter = Counter(palette_id(cells[p]) for p in top_slabs)
    ridge_role = roles_counter(roles, cells, "ridge")
    gable_counter = roles_counter(roles, cells, "gable")
    return RoofInfo(
        style,
        ridge,
        block_counter.most_common(1)[0][0],
        (ridge_counter or ridge_role).most_common(1)[0][0]
        if (ridge_counter or ridge_role)
        else None,
        gable_counter.most_common(1)[0][0] if gable_counter else None,
        overhang,
        max(p.y for p in roof_cells) - roof_base + 1,
    )


def roles_counter(roles: dict[Vec3, str], cells: dict[Vec3, BlockState], role: str) -> Counter[str]:
    return Counter(palette_id(cells[p]) for p, r in roles.items() if r == role)


def _window_info(
    roles: dict[Vec3, str], cells: dict[Vec3, BlockState], floors: list[int], base: int
) -> WindowInfo | None:
    windows = {p for p, r in roles.items() if r == "window"}
    if not windows:
        return None
    groups = _connected(windows)
    sizes: Counter[tuple[int, int]] = Counter()
    sills: Counter[int] = Counter()
    block_counter: Counter[str] = Counter()
    faces: dict[tuple[str, int, int], list[tuple[int, int]]] = {}
    for group in groups:
        xs = [p.x for p in group]
        ys = [p.y for p in group]
        zs = [p.z for p in group]
        if max(xs) == min(xs) and max(zs) == min(zs):
            # a single column: it sits in a wall running along the axis whose
            # neighbours are present
            sample = next(iter(group))
            along_x = (sample + Vec3(1, 0, 0)) in cells or (sample - Vec3(1, 0, 0)) in cells
        else:
            along_x = (max(xs) - min(xs)) >= (max(zs) - min(zs))
        width = (max(xs) - min(xs) if along_x else max(zs) - min(zs)) + 1
        height = max(ys) - min(ys) + 1
        sizes[(width, height)] += 1
        floor_below = max((f for f in floors if f < min(ys)), default=base)
        sills[min(ys) - floor_below] += 1
        for p in group:
            block_counter[cells[p].id] += 1
        key = ("z", min(zs), floor_below) if along_x else ("x", min(xs), floor_below)
        faces.setdefault(key, []).append((min(xs) if along_x else min(zs), width))
    gaps: Counter[int] = Counter()
    for entries in faces.values():
        entries.sort()
        for (a, w), (b, _) in zip(entries, entries[1:], strict=False):
            if b - a - w >= 0:
                gaps[b - a - w] += 1
    (width, height), _ = sizes.most_common(1)[0]
    return WindowInfo(
        block_counter.most_common(1)[0][0],
        width,
        height,
        sills.most_common(1)[0][0],
        len(groups),
        gaps.most_common(1)[0][0] if gaps else None,
    )


def _connected(cells: set[Vec3]) -> list[set[Vec3]]:
    remaining = set(cells)
    groups = []
    while remaining:
        start = remaining.pop()
        group = {start}
        frontier = [start]
        while frontier:
            p = frontier.pop()
            for d in (
                Vec3(1, 0, 0),
                Vec3(-1, 0, 0),
                Vec3(0, 1, 0),
                Vec3(0, -1, 0),
                Vec3(0, 0, 1),
                Vec3(0, 0, -1),
            ):
                q = p + d
                if q in remaining:
                    remaining.remove(q)
                    group.add(q)
                    frontier.append(q)
        groups.append(group)
    return groups
