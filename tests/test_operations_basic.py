import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import AABB, BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation
from mcblueprint.operations.line import line_cells
from mcblueprint.volume import BlockVolume

STONE = BlockState.parse("stone")


def run(data: dict[str, Any]) -> tuple[Any, set[Vec3], list[Vec3]]:
    data = {"block": "stone", **data}
    op = build_operation(data, "operations[0]")
    ctx = ExecutionContext(BlockVolume(), random.Random(0), {})
    op.apply(ctx)
    return op, set(ctx.volume.positions()), list(op.cells())


def box_cells(a: Vec3, b: Vec3) -> set[Vec3]:
    box = AABB.of(a, b)
    return {
        Vec3(x, y, z)
        for x in range(box.min.x, box.max.x + 1)
        for y in range(box.min.y, box.max.y + 1)
        for z in range(box.min.z, box.max.z + 1)
    }


class TestSet:
    def test_single_cell(self) -> None:
        op, cells, _ = run({"type": "set", "position": [1, 2, 3]})
        assert cells == {Vec3(1, 2, 3)}
        assert op.bounds() == AABB(Vec3(1, 2, 3), Vec3(1, 2, 3))


class TestFill:
    def test_any_corner_order(self) -> None:
        op, cells, ordered = run({"type": "fill", "from": [2, 1, 2], "to": [0, 0, 0]})
        assert cells == box_cells(Vec3(0, 0, 0), Vec3(2, 1, 2))
        assert len(ordered) == 18
        assert op.bounds() == AABB(Vec3(0, 0, 0), Vec3(2, 1, 2))

    def test_order_is_y_z_x(self) -> None:
        _, _, ordered = run({"type": "fill", "from": [0, 0, 0], "to": [1, 1, 1]})
        assert ordered == [
            Vec3(0, 0, 0),
            Vec3(1, 0, 0),
            Vec3(0, 0, 1),
            Vec3(1, 0, 1),
            Vec3(0, 1, 0),
            Vec3(1, 1, 0),
            Vec3(0, 1, 1),
            Vec3(1, 1, 1),
        ]


class TestBox:
    def test_hollow_default(self) -> None:
        op, cells, _ = run({"type": "box", "from": [0, 0, 0], "to": [4, 4, 4]})
        assert op.mode == "hollow"
        assert len(cells) == 125 - 27
        assert Vec3(2, 2, 2) not in cells
        assert Vec3(0, 2, 2) in cells and Vec3(4, 2, 2) in cells
        assert Vec3(2, 0, 2) in cells and Vec3(2, 4, 2) in cells
        assert Vec3(2, 2, 0) in cells and Vec3(2, 2, 4) in cells

    def test_solid(self) -> None:
        _, cells, _ = run({"type": "box", "from": [0, 0, 0], "to": [2, 2, 2], "mode": "solid"})
        assert cells == box_cells(Vec3(0, 0, 0), Vec3(2, 2, 2))

    def test_thin_box_is_full(self) -> None:
        _, cells, _ = run({"type": "box", "from": [0, 0, 0], "to": [5, 1, 5]})
        assert cells == box_cells(Vec3(0, 0, 0), Vec3(5, 1, 5))

    def test_invalid_mode(self) -> None:
        with pytest.raises(BlueprintError, match="mode"):
            run({"type": "box", "from": [0, 0, 0], "to": [1, 1, 1], "mode": "thick"})


class TestFloor:
    def test_layer(self) -> None:
        op, cells, _ = run({"type": "floor", "from": [3, 5, 3], "to": [0, 5, 0]})
        assert cells == box_cells(Vec3(0, 5, 0), Vec3(3, 5, 3))
        assert op.bounds() == AABB(Vec3(0, 5, 0), Vec3(3, 5, 3))

    def test_requires_same_y(self) -> None:
        with pytest.raises(BlueprintError, match="same y"):
            run({"type": "floor", "from": [0, 0, 0], "to": [3, 1, 3]})


class TestWall:
    def test_perimeter(self) -> None:
        op, cells, _ = run({"type": "wall", "from": [0, 0, 0], "to": [4, 0, 4], "height": 3})
        assert not op.is_straight
        expected = {
            p for p in box_cells(Vec3(0, 0, 0), Vec3(4, 2, 4)) if p.x in (0, 4) or p.z in (0, 4)
        }
        assert cells == expected
        assert len(cells) == 16 * 3
        assert op.bounds() == AABB(Vec3(0, 0, 0), Vec3(4, 2, 4))

    def test_perimeter_thickness(self) -> None:
        _, cells, _ = run(
            {"type": "wall", "from": [0, 0, 0], "to": [5, 0, 5], "height": 1, "thickness": 2}
        )
        assert Vec3(1, 0, 1) in cells
        assert Vec3(2, 0, 2) not in cells
        assert Vec3(3, 0, 3) not in cells
        assert len(cells) == 36 - 4

    def test_perimeter_thickness_fills_small_rect(self) -> None:
        _, cells, _ = run(
            {"type": "wall", "from": [0, 0, 0], "to": [3, 0, 3], "height": 1, "thickness": 5}
        )
        assert cells == box_cells(Vec3(0, 0, 0), Vec3(3, 0, 3))

    def test_straight_x(self) -> None:
        op, cells, _ = run({"type": "wall", "from": [0, 2, 5], "to": [4, 2, 5], "height": 2})
        assert op.is_straight
        assert cells == box_cells(Vec3(0, 2, 5), Vec3(4, 3, 5))

    def test_straight_x_thickness_extends_positive_z(self) -> None:
        op, cells, _ = run(
            {"type": "wall", "from": [4, 0, 5], "to": [0, 0, 5], "height": 1, "thickness": 2}
        )
        assert cells == box_cells(Vec3(0, 0, 5), Vec3(4, 0, 6))
        assert op.bounds() == AABB(Vec3(0, 0, 5), Vec3(4, 0, 6))

    def test_straight_z_thickness_extends_positive_x(self) -> None:
        _, cells, _ = run(
            {"type": "wall", "from": [2, 0, 0], "to": [2, 0, 3], "height": 2, "thickness": 3}
        )
        assert cells == box_cells(Vec3(2, 0, 0), Vec3(4, 1, 3))

    def test_single_column(self) -> None:
        _, cells, _ = run({"type": "wall", "from": [1, 0, 1], "to": [1, 0, 1], "height": 4})
        assert cells == {Vec3(1, y, 1) for y in range(4)}

    def test_requires_same_y_and_height(self) -> None:
        with pytest.raises(BlueprintError, match="same y"):
            run({"type": "wall", "from": [0, 0, 0], "to": [3, 1, 3], "height": 1})
        with pytest.raises(BlueprintError, match="height"):
            run({"type": "wall", "from": [0, 0, 0], "to": [3, 0, 3], "height": 0})


class TestLine:
    def test_axis_aligned(self) -> None:
        _, _, ordered = run({"type": "line", "from": [0, 0, 0], "to": [3, 0, 0]})
        assert ordered == [Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(2, 0, 0), Vec3(3, 0, 0)]

    def test_single_point(self) -> None:
        assert list(line_cells(Vec3(1, 1, 1), Vec3(1, 1, 1))) == [Vec3(1, 1, 1)]

    def test_diagonal_3d(self) -> None:
        cells = list(line_cells(Vec3(0, 0, 0), Vec3(4, 2, 4)))
        assert cells[0] == Vec3(0, 0, 0)
        assert cells[-1] == Vec3(4, 2, 4)
        assert len(cells) == 5
        assert cells == [Vec3(0, 0, 0), Vec3(1, 1, 1), Vec3(2, 1, 2), Vec3(3, 2, 3), Vec3(4, 2, 4)]

    def test_negative_direction(self) -> None:
        cells = list(line_cells(Vec3(0, 0, 0), Vec3(-3, -1, 0)))
        assert cells == [Vec3(0, 0, 0), Vec3(-1, 0, 0), Vec3(-2, -1, 0), Vec3(-3, -1, 0)]

    def test_consecutive_cells_are_adjacent(self) -> None:
        cells = list(line_cells(Vec3(-3, 2, 7), Vec3(10, -4, 1)))
        for a, b in zip(cells, cells[1:], strict=False):
            d = b - a
            assert max(abs(d.x), abs(d.y), abs(d.z)) == 1

    def test_bounds(self) -> None:
        op, _, _ = run({"type": "line", "from": [5, 0, -1], "to": [0, 3, 2]})
        assert op.bounds() == AABB(Vec3(0, 0, -1), Vec3(5, 3, 2))


@pytest.mark.parametrize("op_type", ["set", "fill", "box", "wall", "floor", "line"])
def test_palette_and_comment_accepted(op_type: str) -> None:
    data: dict[str, Any] = {"type": op_type, "palette": "p", "comment": "note"}
    if op_type == "set":
        data["position"] = [0, 0, 0]
    else:
        data["from"] = [0, 0, 0]
        data["to"] = [2, 0, 2]
    if op_type == "wall":
        data["height"] = 1
    op = build_operation(data, "operations[0]")
    assert op.spec.palette == "p"
    assert op.comment == "note"
