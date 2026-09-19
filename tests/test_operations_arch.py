import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation, build_operations
from mcblueprint.operations.arch import (
    arch_rise,
    curve_rows,
    opening_cells,
    ring_cells,
    ring_steps,
    runs,
)
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse
AIR = B("air")


def run(*ops: dict[str, Any]) -> BlockVolume:
    ctx = ExecutionContext(BlockVolume(), random.Random(0), {})
    for op in build_operations(list(ops), "operations"):
        op.apply(ctx)
    return ctx.volume


def blueprint(*operations: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "n",
        "operations": list(operations),
        **extra,
    }


def wall(x0: int, x1: int, y1: int) -> dict[str, Any]:
    return {"type": "fill", "from": [x0, 0, 0], "to": [x1, y1, 0], "block": "oak_planks"}


def row_widths(width: int, style: str) -> list[int]:
    return [b - a + 1 for a, b in curve_rows(width, style)]


class TestGeometry:
    @pytest.mark.parametrize(
        ("width", "style", "widths"),
        [
            (1, "round", [1]),
            (3, "round", [3, 3]),
            (5, "round", [5, 5, 3]),
            (7, "round", [7, 7, 5, 3]),
            (9, "round", [9, 9, 9, 7, 5]),
            (3, "pointed", [3, 3, 1]),
            (5, "pointed", [5, 5, 5, 3, 1]),
            (7, "pointed", [7, 7, 7, 5, 5, 3, 1]),
            (3, "flat", [3]),
            (4, "round", [4, 4]),
            (6, "round", [6, 6, 4]),
        ],
    )
    def test_curve_rows(self, width: int, style: str, widths: list[int]) -> None:
        assert row_widths(width, style) == widths
        assert arch_rise(width, style) == len(widths) - 1
        # every row is centred on the opening
        for a, b in curve_rows(width, style):
            assert a == width - 1 - b

    def test_opening_has_straight_part_below_the_curve(self) -> None:
        cells = opening_cells(5, 6, "round")
        assert {(u, v) for (u, v) in cells if v < 3} == {(u, v) for u in range(5) for v in range(3)}
        assert {u for (u, v) in cells if v == 5} == {1, 2, 3}
        assert (0, 5) not in cells

    def test_height_below_rise_is_an_error(self) -> None:
        with pytest.raises(BlueprintError, match="at least 3 for a round arch of width 5"):
            opening_cells(5, 2, "round")

    def test_ring_excludes_floor_and_touches_every_opening_cell(self) -> None:
        opening = opening_cells(3, 3, "flat")
        ring = ring_cells(opening)
        assert min(v for _, v in ring) == 0
        assert ring == {(-1, 0), (-1, 1), (-1, 2), (3, 0), (3, 1), (3, 2), (0, 3), (1, 3), (2, 3)}

    def test_ring_thickness_grows_outwards(self) -> None:
        opening = opening_cells(3, 2, "flat")
        thin, thick = ring_cells(opening), ring_cells(opening, 2)
        assert thin < thick
        assert (-2, 0) in thick and (-2, 0) not in thin
        assert (-1, 2) in thick  # diagonal corner reached in two steps
        assert min(v for _, v in thick) == 0

    def test_ring_steps_round_thin_ring(self) -> None:
        # rows: 0..1 straight, 2..3 full width, 4 -> u 1..3; ring crown at row 5
        # the crown (row 5, over the narrowed top row) stays plain
        opening = opening_cells(5, 5, "round")
        steps = ring_steps(opening, ring_cells(opening), 5)
        assert steps == [((0, 4), "inner", -1), ((4, 4), "inner", 1)]

    def test_no_curve_keeps_crown_stairs(self) -> None:
        # a width-3 round opening is still full width at the top: classic corbels
        opening = opening_cells(3, 3, "round")
        steps = ring_steps(opening, ring_cells(opening), 3)
        assert steps == [((0, 3), "inner", -1), ((2, 3), "inner", 1)]

    def test_ring_steps_thick_ring_has_outer_corners(self) -> None:
        opening = opening_cells(5, 5, "round")
        steps = ring_steps(opening, ring_cells(opening, 2), 5)
        kinds = {cell: kind for cell, kind, _ in steps}
        assert kinds[(0, 4)] == "inner"
        assert kinds[(-1, 4)] == "outer" and kinds[(0, 5)] == "outer"
        assert (1, 5) not in kinds  # ceiling over the top row stays flat
        assert (1, 6) not in kinds and (2, 6) not in kinds  # top row of the ring stays plain
        assert (-2, 3) not in kinds  # top of the straight jamb

    def test_flat_lintel_ends_are_inner_steps_only(self) -> None:
        opening = opening_cells(3, 3, "flat")
        steps = ring_steps(opening, ring_cells(opening), 3)
        assert steps == [((0, 3), "inner", -1), ((2, 3), "inner", 1)]

    def test_single_column_has_no_steps(self) -> None:
        opening = opening_cells(1, 2, "flat")
        assert ring_steps(opening, ring_cells(opening), 1) == []

    def test_runs_merge_consecutive_cells(self) -> None:
        assert runs({(0, 0), (1, 0), (3, 0), (0, 1)}) == [(0, 0, 1), (0, 3, 3), (1, 0, 0)]


class TestArch:
    def test_round_arch_in_wall(self) -> None:
        volume = run(
            wall(0, 8, 8),
            {
                "type": "arch",
                "position": [2, 0, 0],
                "axis": "x",
                "width": 5,
                "height": 6,
                "style": "round",
                "block": "stone_bricks",
                "trim": "stone_brick_stairs",
            },
        )
        stone = B("stone_bricks")
        # jambs, springing, crown
        assert volume.get(Vec3(1, 0, 0)) == stone and volume.get(Vec3(7, 3, 0)) == stone
        assert volume.get(Vec3(1, 4, 0)) == stone and volume.get(Vec3(7, 4, 0)) == stone
        assert volume.get(Vec3(4, 6, 0)) == stone
        # opening: straight part, springing row, narrowed rows
        assert volume.get(Vec3(4, 0, 0)) == AIR and volume.get(Vec3(2, 3, 0)) == AIR
        assert volume.get(Vec3(4, 5, 0)) == AIR
        # the ring's steps over the opening become upside-down stairs whose full side
        # faces away from the centre; the opening itself stays clear
        assert volume.get(Vec3(2, 5, 0)) == B("stone_brick_stairs[facing=west,half=top]")
        assert volume.get(Vec3(6, 5, 0)) == B("stone_brick_stairs[facing=east,half=top]")
        # the crown over the top row is plain blocks
        assert volume.get(Vec3(3, 6, 0)) == stone and volume.get(Vec3(5, 6, 0)) == stone
        assert volume.get(Vec3(2, 4, 0)) == AIR and volume.get(Vec3(3, 5, 0)) == AIR
        # nothing below the floor, wall untouched elsewhere
        assert volume.get(Vec3(0, 0, 0)) == B("oak_planks")
        assert volume.get(Vec3(8, 8, 0)) == B("oak_planks")

    def test_pointed_apex_is_one_block(self) -> None:
        volume = run(
            {
                "type": "arch",
                "position": [0, 0, 0],
                "width": 5,
                "height": 7,
                "style": "pointed",
                "block": "stone_bricks",
            }
        )
        assert volume.get(Vec3(2, 6, 0)) == AIR
        assert volume.get(Vec3(1, 6, 0)) == B("stone_bricks")
        assert volume.get(Vec3(2, 7, 0)) == B("stone_bricks")
        assert volume.get(Vec3(1, 5, 0)) == AIR and volume.get(Vec3(0, 5, 0)) == B("stone_bricks")

    def test_flat_lintel_with_corner_trims(self) -> None:
        volume = run(
            {
                "type": "arch",
                "position": [0, 0, 0],
                "width": 3,
                "height": 3,
                "style": "flat",
                "block": "stone_bricks",
                "trim": "stone_brick_slab",
            }
        )
        assert volume.get(Vec3(1, 3, 0)) == B("stone_bricks")
        assert volume.get(Vec3(0, 3, 0)) == B("stone_brick_slab[type=top]")
        assert volume.get(Vec3(2, 3, 0)) == B("stone_brick_slab[type=top]")
        assert volume.get(Vec3(0, 2, 0)) == AIR and volume.get(Vec3(1, 2, 0)) == AIR

    def test_axis_z_and_depth(self) -> None:
        volume = run(
            {
                "type": "arch",
                "position": [0, 0, 0],
                "axis": "z",
                "width": 3,
                "height": 3,
                "depth": 2,
                "block": "stone_bricks",
                "trim": "stone_brick_stairs",
            }
        )
        assert volume.get(Vec3(0, 0, -1)) == B("stone_bricks")
        assert volume.get(Vec3(1, 0, -1)) == B("stone_bricks")
        assert volume.get(Vec3(2, 0, -1)) is None
        assert volume.get(Vec3(1, 1, 1)) == AIR and volume.get(Vec3(0, 2, 0)) == AIR
        assert volume.get(Vec3(0, 3, 0)) == B("stone_brick_stairs[facing=north,half=top]")
        assert volume.get(Vec3(1, 3, 2)) == B("stone_brick_stairs[facing=south,half=top]")

    def test_hollow_false_keeps_the_wall(self) -> None:
        volume = run(
            wall(0, 4, 4),
            {
                "type": "arch",
                "position": [1, 0, 0],
                "width": 3,
                "height": 3,
                "style": "flat",
                "hollow": False,
                "block": "stone_bricks",
            },
        )
        assert volume.get(Vec3(2, 1, 0)) == B("oak_planks")
        assert volume.get(Vec3(0, 1, 0)) == B("stone_bricks")

    def test_fill_replaces_air(self) -> None:
        volume = run(
            {
                "type": "arch",
                "position": [0, 0, 0],
                "width": 3,
                "height": 2,
                "style": "round",
                "block": "stone_bricks",
                "fill": "glass",
            }
        )
        assert volume.get(Vec3(1, 0, 0)) == B("glass")
        assert volume.get(Vec3(1, 1, 0)) == B("glass")

    def test_explicit_trim_properties_are_kept(self) -> None:
        volume = run(
            {
                "type": "arch",
                "position": [0, 0, 0],
                "width": 3,
                "height": 2,
                "block": "stone_bricks",
                "trim": "stone_brick_stairs[half=bottom]",
            }
        )
        assert volume.get(Vec3(0, 2, 0)) == B("stone_brick_stairs[facing=west,half=bottom]")

    def test_thick_ring_gets_outer_and_inner_stairs(self) -> None:
        volume = run(
            {
                "type": "arch",
                "position": [3, 0, 0],
                "width": 5,
                "height": 6,
                "style": "round",
                "thickness": 2,
                "block": "stone_bricks",
                "trim": "stone_brick_stairs",
            }
        )
        outer_w, outer_e = (
            "stone_brick_stairs[facing=east,half=bottom]",
            "stone_brick_stairs[facing=west,half=bottom]",
        )
        inner_w, inner_e = (
            "stone_brick_stairs[facing=west,half=top]",
            "stone_brick_stairs[facing=east,half=top]",
        )
        # 2-thick jambs, a 45-degree chamfer of normal stairs on the outside ...
        assert volume.get(Vec3(1, 0, 0)) == B("stone_bricks") and volume.get(Vec3(2, 0, 0)) == B(
            "stone_bricks"
        )
        assert volume.get(Vec3(2, 5, 0)) == B(outer_w) and volume.get(Vec3(3, 6, 0)) == B(outer_w)
        assert volume.get(Vec3(8, 5, 0)) == B(outer_e) and volume.get(Vec3(7, 6, 0)) == B(outer_e)
        # ... upside-down stairs over the opening, and a plain crown on top
        assert volume.get(Vec3(3, 5, 0)) == B(inner_w) and volume.get(Vec3(7, 5, 0)) == B(inner_e)
        for x in (4, 5, 6):
            assert volume.get(Vec3(x, 6, 0)) == B("stone_bricks")
            assert volume.get(Vec3(x, 7, 0)) == B("stone_bricks")
        assert volume.get(Vec3(5, 5, 0)) == AIR

    def test_slab_trim_types(self) -> None:
        volume = run(
            {
                "type": "arch",
                "position": [3, 0, 0],
                "width": 3,
                "height": 3,
                "style": "round",
                "thickness": 2,
                "block": "stone_bricks",
                "trim": "stone_brick_slab",
            }
        )
        assert volume.get(Vec3(3, 3, 0)) == B("stone_brick_slab[type=top]")
        assert volume.get(Vec3(2, 3, 0)) == B("stone_brick_slab[type=bottom]")

    def test_too_small_height_reports_path(self) -> None:
        with pytest.raises(BlueprintError, match=r"operations\[0\]: height must be at least 5"):
            build_operation(
                {
                    "type": "arch",
                    "position": [0, 0, 0],
                    "width": 5,
                    "height": 4,
                    "style": "pointed",
                    "block": "stone_bricks",
                },
                "operations[0]",
            )

    def test_bounds_cover_ring(self) -> None:
        op = build_operation(
            {"type": "arch", "position": [2, 1, 3], "width": 3, "height": 4, "block": "stone"},
            "operations[0]",
        )
        bounds = op.bounds()
        assert bounds.min == Vec3(1, 1, 3) and bounds.max == Vec3(5, 5, 3)


class TestDoorwayAndWindowArch:
    def test_doorway_arch_keeps_door_and_clears_curve(self) -> None:
        volume = run(
            wall(0, 6, 8),
            {
                "type": "doorway",
                "position": [2, 0, 0],
                "facing": "south",
                "width": 3,
                "height": 3,
                "arch": {"style": "round", "block": "stone_bricks", "trim": "stone_brick_stairs"},
            },
        )
        # springing row is the doorway's top row; the curve adds one clear row
        assert volume.get(Vec3(3, 2, 0)) == AIR and volume.get(Vec3(3, 3, 0)) == AIR
        assert volume.get(Vec3(2, 3, 0)) == AIR
        assert volume.get(Vec3(2, 4, 0)) == B("stone_brick_stairs[facing=west,half=top]")
        assert volume.get(Vec3(3, 4, 0)) == B("stone_bricks")
        assert volume.get(Vec3(1, 1, 0)) == B("stone_bricks")
        assert volume.get(Vec3(5, 5, 0)) == B("oak_planks")

    def test_doorway_arch_places_door_after_the_arch(self) -> None:
        volume = run(
            wall(0, 5, 6),
            {
                "type": "doorway",
                "position": [2, 0, 0],
                "facing": "south",
                "width": 2,
                "door": "oak_door",
                "arch": {"style": "pointed", "block": "stone_bricks", "trim": "stone_brick_stairs"},
            },
        )
        assert volume.get(Vec3(2, 0, 0)) == B("oak_door[facing=south,half=lower,hinge=right]")
        assert volume.get(Vec3(3, 1, 0)) == B("oak_door[facing=south,half=upper,hinge=left]")
        assert volume.get(Vec3(2, 2, 0)) == AIR
        assert volume.get(Vec3(2, 3, 0)) == B("stone_brick_stairs[facing=west,half=top]")
        assert volume.get(Vec3(3, 3, 0)) == B("stone_brick_stairs[facing=east,half=top]")

    def test_doorway_arch_axis_follows_facing(self) -> None:
        volume = run(
            {
                "type": "doorway",
                "position": [0, 0, 0],
                "facing": "east",
                "width": 3,
                "height": 2,
                "arch": {"style": "flat", "block": "stone_bricks"},
            }
        )
        assert volume.get(Vec3(0, 0, -1)) == B("stone_bricks")
        assert volume.get(Vec3(0, 2, 1)) == B("stone_bricks")
        assert volume.get(Vec3(0, 1, 2)) == AIR

    def test_window_arch_fills_curve_with_panes(self) -> None:
        volume = run(
            {
                "type": "window",
                "position": [1, 1, 0],
                "axis": "x",
                "width": 3,
                "height": 2,
                "arch": {"style": "pointed", "block": "stone_bricks", "trim": "stone_brick_stairs"},
            }
        )
        pane = B("glass_pane[east=true,west=true]")
        assert volume.get(Vec3(2, 1, 0)) == pane and volume.get(Vec3(2, 4, 0)) == pane
        assert volume.get(Vec3(1, 3, 0)) == pane
        assert volume.get(Vec3(1, 4, 0)) == B("stone_brick_stairs[facing=west,half=top]")
        assert volume.get(Vec3(2, 5, 0)) == B("stone_bricks")
        assert volume.get(Vec3(0, 1, 0)) == B("stone_bricks")

    def test_arch_must_be_object_with_block(self) -> None:
        with pytest.raises(BlueprintError, match=r"\.arch"):
            build_operation(
                {"type": "doorway", "position": [0, 0, 0], "facing": "south", "arch": "round"},
                "operations[0]",
            )
        with pytest.raises(BlueprintError, match=r"\.arch"):
            build_operation(
                {"type": "window", "position": [0, 0, 0], "axis": "x", "arch": {"style": "round"}},
                "operations[0]",
            )

    def test_arch_thickness_passes_through(self) -> None:
        volume = run(
            {
                "type": "doorway",
                "position": [3, 0, 0],
                "facing": "south",
                "width": 3,
                "height": 3,
                "arch": {"block": "stone_bricks", "thickness": 2},
            }
        )
        assert volume.get(Vec3(1, 1, 0)) == B("stone_bricks")
        assert volume.get(Vec3(2, 1, 0)) == B("stone_bricks")


class TestValidation:
    def test_valid_blueprint(self) -> None:
        assert (
            validate(
                blueprint(
                    {
                        "type": "arch",
                        "position": [0, 0, 0],
                        "width": 3,
                        "height": 3,
                        "block": "stone_bricks",
                        "trim": "stone_brick_stairs",
                    },
                    {
                        "type": "doorway",
                        "position": [0, 0, 0],
                        "facing": "south",
                        "arch": {"block": "stone_bricks"},
                    },
                )
            )
            == []
        )

    def test_unknown_blocks_in_arch_keys_are_reported(self) -> None:
        errors = validate(
            blueprint(
                {
                    "type": "arch",
                    "position": [0, 0, 0],
                    "width": 3,
                    "height": 3,
                    "block": "stone_bricks",
                    "trim": "no_such_stairs",
                    "fill": "no_such_glass",
                },
                {
                    "type": "window",
                    "position": [0, 0, 0],
                    "axis": "x",
                    "arch": {"block": "stone_bricks", "trim": "no_such_trim"},
                },
            )
        )
        paths = {e.path for e in errors}
        assert paths == {"operations[0].trim", "operations[0].fill", "operations[1].arch.trim"}

    def test_schema_rejects_bad_style_and_missing_block(self) -> None:
        errors = validate(
            blueprint(
                {
                    "type": "arch",
                    "position": [0, 0, 0],
                    "width": 3,
                    "height": 3,
                    "style": "gothic",
                    "block": "stone_bricks",
                }
            )
        )
        assert errors and errors[0].path.startswith("operations[0]")
        errors = validate(
            blueprint(
                {
                    "type": "doorway",
                    "position": [0, 0, 0],
                    "facing": "south",
                    "arch": {"style": "round"},
                }
            )
        )
        assert errors and "arch" in errors[0].path

    def test_height_error_is_a_validation_error(self) -> None:
        errors = validate(
            blueprint(
                {
                    "type": "arch",
                    "position": [0, 0, 0],
                    "width": 5,
                    "height": 2,
                    "block": "stone_bricks",
                }
            )
        )
        assert any("at least 3" in e.message for e in errors)
