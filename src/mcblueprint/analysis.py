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
from mcblueprint.operations.transform import Transform
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
MIN_BEAM_CELLS = 3  # beams shorter than this are noise
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
    "_trapdoor",
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
DOOR_SUFFIXES = ("_door", "_fence_gate")
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
    style: str  # gable | hip | flat | dome | cone | stepped
    ridge: str | None  # x | z for gable
    block: str
    ridge_block: str | None
    gable_block: str | None
    overhang: int
    rise: int
    radius: int | None = None  # base radius of a dome / cone


@dataclass
class WindowInfo:
    block: str
    width: int
    height: int
    sill: int
    count: int
    spacing: int | None


@dataclass
class OpeningPart:
    """A window or door together with the decoration around it, normalised so that
    the outside faces north (-z) and the minimum corner is the origin."""

    kind: str  # window | door
    cells: dict[Vec3, BlockState]
    count: int
    opening: AABB  # where the panes / door sit inside the part

    @property
    def size(self) -> Vec3:
        return AABB(
            Vec3(
                min(p.x for p in self.cells),
                min(p.y for p in self.cells),
                min(p.z for p in self.cells),
            ),
            Vec3(
                max(p.x for p in self.cells),
                max(p.y for p in self.cells),
                max(p.z for p in self.cells),
            ),
        ).size


@dataclass
class Band:
    """A row of one block running around the walls at ``height`` rows above the floor."""

    height: int
    block: str
    coverage: float  # share of the row (wall band) or of the perimeter (trim) it covers


@dataclass
class WallDecor:
    bands: list[Band] = field(default_factory=list)  # rows of a different block in the wall
    trims: list[Band] = field(default_factory=list)  # protruding rows outside the wall
    items: Counter[str] = field(default_factory=Counter)  # sporadic protruding decoration
    post_spacing: int | None = None  # centre-to-centre distance of posts along a face
    beam_heights: list[int] = field(default_factory=list)


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
    walls: WallDecor | None = None
    shape: str = "rectangle"  # rectangle | round | irregular
    radius: int | None = None  # of a round footprint
    role_map: dict[Vec3, str] = field(default_factory=dict)
    states: dict[Vec3, BlockState] = field(default_factory=dict)
    parts: list[OpeningPart] = field(default_factory=list)

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
    shaped_roof = roof_base is None
    if shaped_roof:
        roof_base = _shrinking_roof_base(structural, fixed, bounds)
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
            if shaped_roof or name.endswith(ROOF_SUFFIXES):
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
    result.states = cells

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
    result.shape, result.radius = _footprint_shape(roles, result.footprint, base)
    if shaped_roof:
        result.roof = _shaped_roof_info(roles, cells, roof_base, result.footprint)
    else:
        result.roof = _roof_info(roles, cells, names, roof_base, result.footprint)
    result.windows = _window_info(roles, cells, result.floor_levels, base)
    result.parts = extract_opening_parts(result)
    result.walls = analyze_walls(result)
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


def _shrinking_roof_base(
    structural: set[Vec3], fixed: dict[Vec3, str | None], bounds: AABB
) -> int | None:
    """Lowest layer of a run of top layers whose horizontal extent keeps shrinking
    (a dome, a cone or a stepped roof made of full blocks)."""
    extent: dict[int, int] = {}
    for y in range(bounds.min.y, bounds.max.y + 1):
        layer = [p for p in structural if p.y == y]
        if not layer:
            continue
        w = max(p.x for p in layer) - min(p.x for p in layer) + 1
        d = max(p.z for p in layer) - min(p.z for p in layer) + 1
        extent[y] = w * d
    ys = sorted(extent)
    if len(ys) < 3:
        return None
    base = None
    for upper, lower in zip(reversed(ys), reversed(ys[:-1]), strict=False):
        if extent[upper] < extent[lower]:
            base = lower  # the wider layer below is still part of the roof
        else:
            break
    if base is None or base <= bounds.min.y + 1 or bounds.max.y - base < 1:
        return None  # a single narrower top row is not a roof
    # a dome or cone may sit on a neck of the same width (a drum): take it as well,
    # down to the first layer that is wider again
    index = ys.index(base)
    while index > 0 and extent[ys[index - 1]] == extent[base] and ys[index - 1] > bounds.min.y + 1:
        index -= 1
    return ys[index]


def _footprint_shape(roles: dict[Vec3, str], footprint: AABB, base: int) -> tuple[str, int | None]:
    """``rectangle`` / ``round`` (with its radius) / ``irregular`` from a wall layer."""
    y = min(base + 2, footprint.max.y)
    walls = {
        (p.x, p.z) for p, r in roles.items() if p.y == y and r in ("wall", "post", "window", "door")
    }
    if not walls:
        return "rectangle", None
    xs = [x for x, _ in walls]
    zs = [z for _, z in walls]
    lo_x, hi_x, lo_z, hi_z = min(xs), max(xs), min(zs), max(zs)
    perimeter = {
        (x, z)
        for x in range(lo_x, hi_x + 1)
        for z in range(lo_z, hi_z + 1)
        if x in (lo_x, hi_x) or z in (lo_z, hi_z)
    }
    if len(perimeter & walls) >= 0.9 * len(perimeter):
        return "rectangle", None
    from mcblueprint.operations.shapes import disc_cells

    width, depth = hi_x - lo_x + 1, hi_z - lo_z + 1
    if abs(width - depth) <= 1 and width >= 3:
        radius = (width - 1) // 2
        cx, cz = lo_x + radius, lo_z + radius
        ring = {(cx + u, cz + v) for u, v in disc_cells(radius, "hollow")}
        if len(ring & walls) >= 0.8 * len(ring) and len(walls - ring) <= 0.2 * len(walls):
            return "round", radius
    return "irregular", None


def _shaped_roof_info(
    roles: dict[Vec3, str], cells: dict[Vec3, BlockState], roof_base: int | None, footprint: AABB
) -> RoofInfo | None:
    if roof_base is None:
        return None
    roof = [p for p, r in roles.items() if r == "roof"]
    if not roof:
        return None
    top = max(p.y for p in roof)
    radii = []
    for y in range(roof_base, top + 1):
        layer = [p for p in roof if p.y == y]
        if not layer:
            continue
        w = max(p.x for p in layer) - min(p.x for p in layer) + 1
        d = max(p.z for p in layer) - min(p.z for p in layer) + 1
        radii.append((max(w, d) - 1) / 2)
    base_layer = [p for p in roof if p.y == roof_base]
    lo = Vec3(min(p.x for p in base_layer), roof_base, min(p.z for p in base_layer))
    hi = Vec3(max(p.x for p in base_layer), roof_base, max(p.z for p in base_layer))
    round_base = _looks_round({(p.x, p.z) for p in base_layer}, lo, hi)
    if round_base:
        # a cone loses radius steadily (mean ~ half the base); a dome stays wide first
        style = "dome" if sum(radii) / len(radii) >= 0.62 * radii[0] else "cone"
    else:
        style = "stepped"
    block = Counter(palette_id(cells[p]) for p in roof).most_common(1)[0][0]
    overhang = max(0, footprint.min.x - lo.x, footprint.min.z - lo.z)
    return RoofInfo(style, None, block, None, None, overhang, top - roof_base + 1, int(radii[0]))


def _looks_round(cells: set[tuple[int, int]], lo: Vec3, hi: Vec3) -> bool:
    from mcblueprint.operations.shapes import disc_cells

    width, depth = hi.x - lo.x + 1, hi.z - lo.z + 1
    if abs(width - depth) > 1 or width < 3:
        return False
    radius = (width - 1) // 2
    cx, cz = lo.x + radius, lo.z + radius
    disc = {(cx + u, cz + v) for u, v in disc_cells(radius, "solid")}
    corners = {(lo.x, lo.z), (hi.x, lo.z), (lo.x, hi.z), (hi.x, hi.z)}
    return not (corners & cells) and len(cells & disc) >= 0.8 * len(cells)


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


# --- opening parts ------------------------------------------------------------

STRUCTURE_ROLES = frozenset(
    {"floor", "ceiling", "interior", "roof", "gable", "ridge", "foundation"}
)
OUTWARD_ANGLE = {(0, -1): 0, (1, 0): 270, (0, 1): 180, (-1, 0): 90}  # (dx, dz) -> rotation


def extract_opening_parts(analysis: DesignAnalysis) -> list[OpeningPart]:
    """Windows and doors with their surroundings, grouped by shape (most common first).
    Openings without any decoration are left out."""
    cells, roles = analysis.states, analysis.role_map
    groups: list[tuple[str, set[Vec3]]] = []
    for kind in ("window", "door"):
        members = {p for p, r in roles.items() if r == kind}
        groups.extend((kind, g) for g in _connected(members))
    located = []
    for kind, group in groups:
        placement = _locate_opening(kind, group, cells, analysis.bounds)
        if placement is not None:
            located.append((kind, group, *placement))
    # a wall block that mostly appears next to openings is a frame, not the wall
    near: Counter[str] = Counter()
    total: Counter[str] = Counter()
    regions = [region for _, _, region, _ in located]
    for pos, state in cells.items():
        if roles.get(pos) in ("wall", "post", "beam"):
            block = palette_id(state)
            total[block] += 1
            if any(region.contains(pos) for region in regions):
                near[block] += 1
    frame_ids = {block for block, n in total.items() if near[block] >= 0.5 * n}
    found: dict[
        tuple[str, frozenset[tuple[Vec3, str]]], list[tuple[dict[Vec3, BlockState], AABB]]
    ] = {}
    for kind, group, region, outward in located:
        part = _cut_opening(group, region, outward, cells, roles, frame_ids)
        if part is None:
            continue
        normalised, opening = part
        key = (kind, frozenset((p, st.to_string()) for p, st in normalised.items()))
        found.setdefault(key, []).append((normalised, opening))
    parts = [
        OpeningPart(kind, hits[0][0], len(hits), hits[0][1]) for (kind, _), hits in found.items()
    ]
    parts.sort(key=lambda part: (part.kind != "window", -part.count, len(part.cells)))
    return parts


def _locate_opening(
    kind: str, group: set[Vec3], cells: dict[Vec3, BlockState], bounds: AABB
) -> tuple[AABB, Vec3] | None:
    """The region around an opening (1 block in the wall plane, 2 above a door, 1 in
    front and behind) and the outward direction of its wall."""
    xs = [p.x for p in group]
    ys = [p.y for p in group]
    zs = [p.z for p in group]
    along_x = _wall_runs_along_x(group, cells, xs, zs)
    normal = Vec3(0, 0, 1) if along_x else Vec3(1, 0, 0)
    outward = _outward(group, cells, normal, bounds)
    if outward is None:
        return None
    lo = Vec3(min(xs), min(ys), min(zs))
    hi = Vec3(max(xs), max(ys), max(zs))
    above = 2 if kind == "door" else 1
    below = 0 if kind == "door" else 1
    region = AABB(Vec3(lo.x - 1, lo.y - below, lo.z - 1), Vec3(hi.x + 1, hi.y + above, hi.z + 1))
    return region, outward


def _cut_opening(
    group: set[Vec3],
    region: AABB,
    outward: Vec3,
    cells: dict[Vec3, BlockState],
    roles: dict[Vec3, str],
    frame_ids: set[str],
) -> tuple[dict[Vec3, BlockState], AABB] | None:
    picked: dict[Vec3, BlockState] = {}
    for pos, state in cells.items():
        if not region.contains(pos):
            continue
        role = roles.get(pos)
        if role in STRUCTURE_ROLES:
            continue
        if role in ("wall", "post", "beam") and palette_id(state) not in frame_ids:
            continue
        picked[pos] = state
    if set(picked) <= group:
        return None  # nothing but the panes / door itself
    angle = OUTWARD_ANGLE[(outward.x, outward.z)]
    transform = Transform.rotation(angle, Vec3(0, 0, 0))
    rotated = {transform.apply(p): transform.apply_state(st) for p, st in picked.items()}
    origin = Vec3(min(p.x for p in rotated), min(p.y for p in rotated), min(p.z for p in rotated))
    normalised = {p - origin: st for p, st in rotated.items()}
    moved = [transform.apply(p) - origin for p in group]
    opening = AABB(
        Vec3(min(p.x for p in moved), min(p.y for p in moved), min(p.z for p in moved)),
        Vec3(max(p.x for p in moved), max(p.y for p in moved), max(p.z for p in moved)),
    )
    return normalised, opening


def _wall_runs_along_x(
    group: set[Vec3], cells: dict[Vec3, BlockState], xs: list[int], zs: list[int]
) -> bool:
    if max(xs) - min(xs) != max(zs) - min(zs):
        return (max(xs) - min(xs)) > (max(zs) - min(zs))
    sample = next(iter(group))
    x_side = sum((sample + d) in cells for d in (Vec3(1, 0, 0), Vec3(-1, 0, 0)))
    z_side = sum((sample + d) in cells for d in (Vec3(0, 0, 1), Vec3(0, 0, -1)))
    return x_side >= z_side


def _outward(
    group: set[Vec3], cells: dict[Vec3, BlockState], normal: Vec3, bounds: AABB
) -> Vec3 | None:
    """The side of the wall that leaves the structure without meeting a block."""
    sample = sorted(group, key=lambda p: (p.y, p.x, p.z))[len(group) // 2]
    scores = {}
    for sign in (1, -1):
        step = normal * sign
        p = sample + step
        blocked = 0
        while bounds.contains(p):
            if p in cells and p not in group:
                blocked += 1
                break
            p = p + step
        scores[sign] = blocked
    if scores[1] == scores[-1]:
        return normal * -1 if scores[1] == 0 else None
    return normal * (1 if scores[1] < scores[-1] else -1)


# --- wall decoration ----------------------------------------------------------

BAND_SHARE = 0.7  # share of a wall row one block must take to count as a band
TRIM_SHARE = 0.5  # share of the perimeter a protruding row must cover to count as a trim
NOT_WALL_DECOR = frozenset(
    {"roof", "gable", "ridge", "foundation", "window", "door", "light", "beam", "post"}
)


def analyze_walls(analysis: DesignAnalysis) -> WallDecor:
    roles, cells = analysis.role_map, analysis.states
    fp = analysis.footprint
    base = analysis.floor_levels[0] if analysis.floor_levels else analysis.bounds.min.y
    top = fp.max.y
    decor = WallDecor()
    main_wall = analysis.top("wall")

    # bands: a wall row dominated by a block other than the wall's main block
    rows: dict[int, Counter[str]] = {}
    for pos, role in roles.items():
        if role == "wall":
            rows.setdefault(pos.y, Counter())[palette_id(cells[pos])] += 1
    for y in sorted(rows):
        counter = rows[y]
        block, count = counter.most_common(1)[0]
        share = count / sum(counter.values())
        if block != main_wall and share >= BAND_SHARE:
            decor.bands.append(Band(y - base, block, round(share, 2)))

    # protruding decoration: blocks outside the walls' footprint at wall height
    perimeter = 2 * (fp.size.x + fp.size.z)
    outside: dict[int, Counter[str]] = {}
    for pos, state in cells.items():
        if not (base < pos.y <= top):
            continue
        if fp.min.x <= pos.x <= fp.max.x and fp.min.z <= pos.z <= fp.max.z:
            continue
        if roles.get(pos) in NOT_WALL_DECOR:
            continue
        outside.setdefault(pos.y, Counter())[palette_id(state)] += 1
    for y in sorted(outside):
        for block, count in outside[y].most_common():
            coverage = count / perimeter
            if coverage >= TRIM_SHARE:
                decor.trims.append(Band(y - base, block, round(coverage, 2)))
            else:
                decor.items[block] += count

    # posts: distance between neighbouring posts along each face
    columns = {(p.x, p.z) for p, r in roles.items() if r == "post"}
    gaps: Counter[int] = Counter()
    faces = [sorted(x for x, zz in columns if zz == z) for z in (fp.min.z, fp.max.z)]
    faces += [sorted(zz for xx, zz in columns if xx == x) for x in (fp.min.x, fp.max.x)]
    for along in faces:
        if len(along) >= 3:  # corner posts alone say nothing about a rhythm
            gaps.update(b - a for a, b in zip(along, along[1:], strict=False))
    if gaps:
        decor.post_spacing = gaps.most_common(1)[0][0]

    beams: Counter[int] = Counter(p.y - base for p, r in roles.items() if r == "beam")
    decor.beam_heights = sorted(y for y, n in beams.items() if n >= MIN_BEAM_CELLS)
    return decor
