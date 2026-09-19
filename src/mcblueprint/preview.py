"""Preview images of a generated BlockVolume (requires the optional ``Pillow`` dependency).

Views: ``top`` (plan, lighter = higher), ``north`` / ``south`` / ``east`` / ``west``
(elevations seen from that side), ``isometric`` (2:1 pixel isometric, viewed from
the south-east).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
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


def block_color(state: BlockState) -> RGB | None:
    """Approximate colour for a block, or None for air-like blocks."""
    default, keywords = _color_table()
    name = state.id.split(":", 1)[-1]
    # dyed blocks (white_concrete, light_gray_terracotta, red_bed, ...) take the dye colour
    for dye in sorted(DYES, key=len, reverse=True):
        if name.startswith(dye + "_"):
            color = keywords[dye]
            assert color is not None
            if "terracotta" in name:
                return _blend(color, TERRACOTTA_TINT, 0.4)
            if "glass" in name:
                return _blend(color, (235, 245, 250), 0.5)
            return color
    best: str | None = None
    for keyword in keywords:
        if keyword in name and (best is None or len(keyword) > len(best)):
            best = keyword
    if best is None:
        return default
    return keywords[best]


def shade(color: RGB, factor: float) -> RGB:
    return tuple(max(0, min(255, round(c * factor))) for c in color)  # type: ignore[return-value]


# --- rendering ----------------------------------------------------------------


def render(volume: BlockVolume, view: str, scale: int = 8) -> Any:
    if view not in VIEWS:
        raise BlueprintError(f"Unknown view {view!r}; choose from {', '.join(VIEWS)}")
    bounds = volume.bounds()
    if bounds is None:
        raise BlueprintError("Nothing to preview: no blocks were generated")
    if view == "top":
        return _render_top(volume, bounds, scale)
    if view == "isometric":
        return _render_isometric(volume, bounds, scale)
    return _render_elevation(volume, bounds, scale, view)


def _visible(volume: BlockVolume) -> Iterable[tuple[Vec3, RGB]]:
    for pos, state in volume:
        color = block_color(state)
        if color is not None:
            yield pos, color


def _render_top(volume: BlockVolume, bounds: AABB, scale: int) -> Any:
    Image, ImageDraw = _pil()
    size = bounds.size
    image = Image.new("RGB", (size.x * scale, size.z * scale), BACKGROUND)
    draw = ImageDraw.Draw(image)
    highest: dict[tuple[int, int], tuple[int, RGB]] = {}
    for pos, color in _visible(volume):
        key = (pos.x, pos.z)
        if key not in highest or pos.y > highest[key][0]:
            highest[key] = (pos.y, color)
    span = max(1, size.y - 1)
    for (x, z), (y, color) in highest.items():
        factor = 0.6 + 0.4 * (y - bounds.min.y) / span
        px, pz = (x - bounds.min.x) * scale, (z - bounds.min.z) * scale
        draw.rectangle([px, pz, px + scale - 1, pz + scale - 1], fill=shade(color, factor))
    _grid(draw, image.size, scale)
    return image


def _render_elevation(volume: BlockVolume, bounds: AABB, scale: int, view: str) -> Any:
    Image, ImageDraw = _pil()
    size = bounds.size
    # horizontal screen axis and the depth axis (nearest block wins)
    if view in ("north", "south"):
        width = size.x
        column = lambda p: p.x - bounds.min.x if view == "south" else bounds.max.x - p.x  # noqa: E731
        depth = lambda p: p.z if view == "north" else -p.z  # noqa: E731
    else:
        width = size.z
        column = lambda p: p.z - bounds.min.z if view == "west" else bounds.max.z - p.z  # noqa: E731
        depth = lambda p: p.x if view == "west" else -p.x  # noqa: E731
    image = Image.new("RGB", (width * scale, size.y * scale), BACKGROUND)
    draw = ImageDraw.Draw(image)
    nearest: dict[tuple[int, int], tuple[int, RGB]] = {}
    for pos, color in _visible(volume):
        key = (column(pos), pos.y)
        d = depth(pos)
        if key not in nearest or d < nearest[key][0]:
            nearest[key] = (d, color)
    for (c, y), (_, color) in nearest.items():
        px, py = c * scale, (bounds.max.y - y) * scale
        draw.rectangle([px, py, px + scale - 1, py + scale - 1], fill=shade(color, 0.9))
    _grid(draw, image.size, scale)
    return image


def _render_isometric(volume: BlockVolume, bounds: AABB, scale: int) -> Any:
    Image, ImageDraw = _pil()
    s = max(2, scale)
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
        draw.polygon(top, fill=color)
        draw.polygon(right, fill=shade(color, 0.75))
        draw.polygon(left, fill=shade(color, 0.6))
    return image


def _grid(draw: Any, size: tuple[int, int], scale: int) -> None:
    if scale < 6:
        return
    w, h = size
    for x in range(0, w, scale):
        draw.line([(x, 0), (x, h)], fill=GRID)
    for y in range(0, h, scale):
        draw.line([(0, y), (w, y)], fill=GRID)


def write_previews(
    volume: BlockVolume,
    out_dir: Path,
    stem: str,
    views: Iterable[str] = DEFAULT_VIEWS,
    scale: int = 8,
) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for view in views:
        image = render(volume, view, scale)
        path = out_dir / f"{stem}-{view}.png"
        image.save(path)
        written.append(path)
    return written
