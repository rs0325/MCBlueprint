"""Preview images of a generated BlockVolume (requires the optional ``Pillow`` dependency).

Views: ``top`` (plan, lighter = higher), ``north`` / ``south`` / ``east`` / ``west``
(elevations seen from that side), ``isometric`` (2:1 pixel isometric, viewed from
the south-east) and horizontal sections (``render_layer``: one y level, with the
level below ghosted for context).

Every cell gets a flat colour plus simple shading: a light line where a block's
top face is exposed, a dark line where a side face is exposed (elevations, top
view and sections), and darker side faces with outlines in the isometric view.
``grid`` draws heavier lines every N blocks with world coordinates in a margin,
and ``origin`` marks the blueprint origin in red.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.volume import BlockVolume

RGB = tuple[int, int, int]
VIEWS = ("top", "north", "south", "east", "west", "isometric")
DEFAULT_VIEWS = ("top", "north", "east", "isometric")
BACKGROUND: RGB = (245, 245, 245)
GRID: RGB = (225, 225, 225)
MAJOR_GRID: RGB = (160, 160, 160)
LABEL: RGB = (90, 90, 90)
ORIGIN: RGB = (220, 40, 40)
GHOST_BLEND = 0.7  # how far the layer below is faded towards the background
MARGIN = 14  # pixels reserved for coordinate labels when a grid is drawn


def _pil() -> Any:
    try:
        from PIL import Image, ImageDraw
    except ImportError:  # pragma: no cover - exercised via the CLI test with a stub
        raise BlueprintError(
            "Preview needs the optional dependency Pillow: pip install 'mcblueprint[preview]'"
        ) from None
    return Image, ImageDraw


# --- colours ------------------------------------------------------------------


@cache
def _color_table() -> tuple[RGB, dict[str, RGB | None]]:
    text = resources.files("mcblueprint").joinpath("data", "colors.json").read_text("utf-8")
    data = json.loads(text)
    keywords = {k: (tuple(v) if v is not None else None) for k, v in data["keywords"].items()}
    return tuple(data["default"]), keywords


DYES = (
    "white", "light_gray", "gray", "black", "brown", "red", "orange", "yellow",
    "lime", "green", "cyan", "light_blue", "blue", "purple", "magenta", "pink",
)  # fmt: skip
TERRACOTTA_TINT: RGB = (150, 95, 75)


def _blend(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(round(x * (1 - t) + y * t) for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


def color_keyword(state: BlockState) -> str | None:
    """The ``colors.json`` keyword (or dye name) that decides the block's colour,
    or None when the block falls back to the default colour."""
    _, keywords = _color_table()
    name = state.id.split(":", 1)[-1]
    for dye in sorted(DYES, key=len, reverse=True):
        if name.startswith(dye + "_"):
            return dye
    best: str | None = None
    for keyword in keywords:
        if keyword in name and (best is None or len(keyword) > len(best)):
            best = keyword
    return best


def block_color(state: BlockState) -> RGB | None:
    """Approximate colour for a block, or None for air-like blocks."""
    default, keywords = _color_table()
    name = state.id.split(":", 1)[-1]
    keyword = color_keyword(state)
    if keyword is None:
        return default
    color = keywords[keyword]
    if keyword in DYES and name.startswith(keyword + "_"):
        # dyed blocks (white_concrete, light_gray_terracotta, red_bed, ...) take the dye colour
        assert color is not None
        if "terracotta" in name:
            return _blend(color, TERRACOTTA_TINT, 0.4)
        if "glass" in name:
            return _blend(color, (235, 245, 250), 0.5)
    return color


def uncoloured_blocks(volume: BlockVolume) -> list[str]:
    """Block ids in ``volume`` that have no entry in ``colors.json`` (drawn grey)."""
    seen: set[str] = set()
    for _, state in volume:
        if state.id not in seen and color_keyword(state) is None:
            seen.add(state.id)
    return sorted(seen)


def shade(color: RGB, factor: float) -> RGB:
    return tuple(max(0, min(255, round(c * factor))) for c in color)  # type: ignore[return-value]


# --- rendering ----------------------------------------------------------------


@dataclass(frozen=True)
class Options:
    scale: int = 8
    grid: int | None = None  # draw major grid lines and labels every ``grid`` blocks
    origin: Vec3 | None = None  # blueprint origin to mark


def render(volume: BlockVolume, view: str, scale: int = 8, options: Options | None = None) -> Any:
    if view not in VIEWS:
        raise BlueprintError(f"Unknown view {view!r}; choose from {', '.join(VIEWS)}")
    bounds = volume.bounds()
    if bounds is None:
        raise BlueprintError("Nothing to preview: no blocks were generated")
    options = options or Options(scale=scale)
    if view == "top":
        return _render_top(volume, bounds, options)
    if view == "isometric":
        return _render_isometric(volume, bounds, options)
    return _render_elevation(volume, bounds, options, view)


def render_layer(
    volume: BlockVolume, y: int, scale: int = 8, options: Options | None = None
) -> Any:
    """Horizontal section at level ``y`` over the volume's full x/z extent; blocks of
    the level below that are not covered are drawn faded."""
    bounds = volume.bounds()
    if bounds is None:
        raise BlueprintError("Nothing to preview: no blocks were generated")
    if not bounds.min.y <= y <= bounds.max.y:
        raise BlueprintError(
            f"Layer y={y} is outside the structure (y {bounds.min.y}..{bounds.max.y})"
        )
    options = options or Options(scale=scale)
    cells: dict[tuple[int, int], RGB] = {}
    ghosts: dict[tuple[int, int], RGB] = {}
    for pos, color in _visible(volume):
        if pos.y == y:
            cells[(pos.x, pos.z)] = color
        elif pos.y == y - 1:
            ghosts[(pos.x, pos.z)] = _blend(color, BACKGROUND, GHOST_BLEND)
    canvas = _Canvas(
        bounds.size.x,
        bounds.size.z,
        options,
        lambda c: bounds.min.x + c,
        lambda r: bounds.min.z + r,
    )
    for (x, z), color in ghosts.items():
        if (x, z) not in cells:
            canvas.cell(x - bounds.min.x, z - bounds.min.z, color)
    for (x, z), color in cells.items():
        cx, cz = x - bounds.min.x, z - bounds.min.z
        canvas.cell(cx, cz, color)
        canvas.edges(cx, cz, color, (x + 1, z) not in cells, (x, z + 1) not in cells)
    canvas.grid(("x", "z"))
    if options.origin is not None:
        canvas.mark(options.origin.x - bounds.min.x, options.origin.z - bounds.min.z)
    return canvas.image


def _visible(volume: BlockVolume) -> Iterable[tuple[Vec3, RGB]]:
    for pos, state in volume:
        color = block_color(state)
        if color is not None:
            yield pos, color


class _Canvas:
    """Cell grid drawing helper: ``columns`` x ``rows`` cells of ``scale`` pixels with an
    optional label margin. ``column_world`` / ``row_world`` map a grid line index to
    the world coordinate written next to it."""

    def __init__(
        self,
        columns: int,
        rows: int,
        options: Options,
        column_world: Callable[[int], int],
        row_world: Callable[[int], int],
    ) -> None:
        Image, ImageDraw = _pil()
        self.scale = options.scale
        self.options = options
        self.margin = MARGIN if options.grid else 0
        self.columns, self.rows = columns, rows
        self.column_world = column_world
        self.row_world = row_world
        self.image = Image.new(
            "RGB", (columns * self.scale + self.margin, rows * self.scale + self.margin), BACKGROUND
        )
        self.draw = ImageDraw.Draw(self.image)

    def _px(self, column: int, row: int) -> tuple[int, int]:
        return self.margin + column * self.scale, self.margin + row * self.scale

    def cell(self, column: int, row: int, color: RGB) -> None:
        px, py = self._px(column, row)
        self.draw.rectangle([px, py, px + self.scale - 1, py + self.scale - 1], fill=color)

    def edges(
        self, column: int, row: int, color: RGB, right_exposed: bool, bottom_exposed: bool
    ) -> None:
        """Dark lines on the right / bottom edge of a cell whose neighbour there is
        missing or lower (reads as a step or a wall in top views)."""
        if self.scale < 4:
            return
        px, py = self._px(column, row)
        dark = shade(color, 0.55)
        if right_exposed:
            self.draw.line(
                [(px + self.scale - 1, py), (px + self.scale - 1, py + self.scale - 1)], fill=dark
            )
        if bottom_exposed:
            self.draw.line(
                [(px, py + self.scale - 1), (px + self.scale - 1, py + self.scale - 1)], fill=dark
            )

    def top_highlight(self, column: int, row: int, color: RGB) -> None:
        """Light line along the top edge of a cell whose top face is exposed (elevations);
        one pixel in so the fine grid line drawn on the edge does not cover it."""
        if self.scale < 4:
            return
        px, py = self._px(column, row)
        self.draw.line([(px, py + 1), (px + self.scale - 1, py + 1)], fill=shade(color, 1.25))

    def grid(self, axes: tuple[str, str]) -> None:
        s = self.scale
        w, h = self.columns * s, self.rows * s
        if s >= 6:
            for c in range(self.columns + 1):
                x = self.margin + c * s
                self.draw.line([(x, self.margin), (x, self.margin + h)], fill=GRID)
            for r in range(self.rows + 1):
                y = self.margin + r * s
                self.draw.line([(self.margin, y), (self.margin + w, y)], fill=GRID)
        if not self.options.grid:
            return
        step = self.options.grid
        for c in range(self.columns + 1):
            world = self.column_world(c)
            if world % step == 0:
                x = self.margin + c * s
                self.draw.line([(x, 0), (x, self.margin + h)], fill=MAJOR_GRID)
                self.draw.text((x + 1, 0), str(world), fill=LABEL)
        for r in range(self.rows + 1):
            world = self.row_world(r)
            if world % step == 0:
                y = self.margin + r * s
                self.draw.line([(0, y), (self.margin + w, y)], fill=MAJOR_GRID)
                self.draw.text((0, y + 1), str(world), fill=LABEL)
        self.draw.text((1, 1), f"{axes[0]} {axes[1]}", fill=LABEL)

    def mark(self, column: int, row: int) -> None:
        if not (0 <= column < self.columns and 0 <= row < self.rows):
            return
        px, py = self._px(column, row)
        s = self.scale
        self.draw.rectangle([px, py, px + s - 1, py + s - 1], outline=ORIGIN, width=max(1, s // 6))
        self.draw.line([(px, py), (px + s - 1, py + s - 1)], fill=ORIGIN)
        self.draw.line([(px + s - 1, py), (px, py + s - 1)], fill=ORIGIN)


def _render_top(volume: BlockVolume, bounds: AABB, options: Options) -> Any:
    size = bounds.size
    highest: dict[tuple[int, int], tuple[int, RGB]] = {}
    for pos, color in _visible(volume):
        key = (pos.x, pos.z)
        if key not in highest or pos.y > highest[key][0]:
            highest[key] = (pos.y, color)
    span = max(1, size.y - 1)
    canvas = _Canvas(
        size.x, size.z, options, lambda c: bounds.min.x + c, lambda r: bounds.min.z + r
    )
    for (x, z), (y, color) in highest.items():
        factor = 0.6 + 0.4 * (y - bounds.min.y) / span
        cx, cz = x - bounds.min.x, z - bounds.min.z
        canvas.cell(cx, cz, shade(color, factor))
        right_lower = (x + 1, z) not in highest or highest[(x + 1, z)][0] < y
        front_lower = (x, z + 1) not in highest or highest[(x, z + 1)][0] < y
        canvas.edges(cx, cz, color, right_lower, front_lower)
    canvas.grid(("x", "z"))
    if options.origin is not None:
        canvas.mark(options.origin.x - bounds.min.x, options.origin.z - bounds.min.z)
    return canvas.image


def _render_elevation(volume: BlockVolume, bounds: AABB, options: Options, view: str) -> Any:
    size = bounds.size
    # horizontal screen axis and the depth axis (nearest block wins)
    if view in ("north", "south"):
        width = size.x
        column = lambda p: p.x - bounds.min.x if view == "south" else bounds.max.x - p.x  # noqa: E731
        depth = lambda p: p.z if view == "north" else -p.z  # noqa: E731
        lo, hi, axes = bounds.min.x, bounds.max.x, ("x", "y")
    else:
        width = size.z
        column = lambda p: p.z - bounds.min.z if view == "west" else bounds.max.z - p.z  # noqa: E731
        depth = lambda p: p.x if view == "west" else -p.x  # noqa: E731
        lo, hi, axes = bounds.min.z, bounds.max.z, ("z", "y")
    # the column index runs with the world axis for south / west, against it otherwise
    forward = view in ("south", "west")
    column_world = (lambda c: lo + c) if forward else (lambda c: hi + 1 - c)
    nearest: dict[tuple[int, int], tuple[int, RGB]] = {}
    for pos, color in _visible(volume):
        key = (column(pos), pos.y)
        d = depth(pos)
        if key not in nearest or d < nearest[key][0]:
            nearest[key] = (d, color)
    canvas = _Canvas(width, size.y, options, column_world, lambda r: bounds.max.y + 1 - r)
    for (c, y), (d, color) in nearest.items():
        row = bounds.max.y - y
        canvas.cell(c, row, shade(color, 0.9))
        if _farther(nearest, (c, y + 1), d):
            canvas.top_highlight(c, row, color)
        canvas.edges(
            c, row, color, _farther(nearest, (c + 1, y), d), _farther(nearest, (c, y - 1), d)
        )
    canvas.grid(axes)
    if options.origin is not None:
        o = options.origin
        canvas.mark(column(o), bounds.max.y - o.y)
    return canvas.image


def _farther(nearest: dict[tuple[int, int], tuple[int, RGB]], key: tuple[int, int], d: int) -> bool:
    """True when nothing is drawn at ``key`` or what is drawn there is behind depth ``d``."""
    return key not in nearest or nearest[key][0] > d


def _render_isometric(volume: BlockVolume, bounds: AABB, options: Options) -> Any:
    Image, ImageDraw = _pil()
    s = max(2, options.scale)
    half = s // 2
    size = bounds.size
    width = (size.x + size.z) * s
    height = (size.x + size.z) * half + size.y * s + s
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    origin_x = size.z * s  # screen x of the world x = min, z = min column
    origin_y = size.y * s

    present = {pos for pos, _ in volume if block_color(volume.get(pos)) is not None}  # type: ignore[arg-type]
    cubes = sorted(_visible(volume), key=lambda item: (item[0].x + item[0].z, item[0].y))
    for pos, color in cubes:
        p = pos - bounds.min
        # a cube is hidden when its top, +x and +z faces are all covered
        if all((pos + d) in present for d in (Vec3(0, 1, 0), Vec3(1, 0, 0), Vec3(0, 0, 1))):
            continue
        cx = origin_x + (p.x - p.z) * s
        cy = origin_y + (p.x + p.z) * half - p.y * s
        top = [(cx, cy), (cx + s, cy + half), (cx, cy + s), (cx - s, cy + half)]
        right = [(cx, cy + s), (cx + s, cy + half), (cx + s, cy + half + s), (cx, cy + 2 * s)]
        left = [(cx - s, cy + half), (cx, cy + s), (cx, cy + 2 * s), (cx - s, cy + half + s)]
        outline = shade(color, 0.45) if s >= 6 else None
        draw.polygon(top, fill=shade(color, 1.05), outline=outline)
        draw.polygon(right, fill=shade(color, 0.75), outline=outline)
        draw.polygon(left, fill=shade(color, 0.6), outline=outline)
    if options.origin is not None and bounds.min.y <= options.origin.y <= bounds.max.y:
        p = options.origin - bounds.min
        if 0 <= p.x < size.x and 0 <= p.z < size.z:
            cx = origin_x + (p.x - p.z) * s
            cy = origin_y + (p.x + p.z) * half - p.y * s
            draw.polygon(
                [(cx, cy), (cx + s, cy + half), (cx, cy + s), (cx - s, cy + half)],
                outline=ORIGIN,
            )
    return image


def layer_name(y: int, bounds: AABB) -> str:
    """``y03`` style suffix, zero-padded so file names sort by level."""
    width = max(len(str(abs(bounds.min.y))), len(str(abs(bounds.max.y))))
    return f"y{y:0{width + (1 if y < 0 else 0)}d}"


def write_previews(
    volume: BlockVolume,
    out_dir: Path,
    stem: str,
    views: Iterable[str] = DEFAULT_VIEWS,
    scale: int = 8,
    layers: Iterable[int] = (),
    options: Options | None = None,
) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    options = options or Options(scale=scale)
    written = []
    for view in views:
        image = render(volume, view, options=options)
        path = out_dir / f"{stem}-{view}.png"
        image.save(path)
        written.append(path)
    bounds = volume.bounds()
    for y in layers:
        image = render_layer(volume, y, options=options)
        assert bounds is not None  # render_layer rejects empty volumes
        path = out_dir / f"{stem}-{layer_name(y, bounds)}.png"
        image.save(path)
        written.append(path)
    return written
