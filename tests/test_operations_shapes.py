import random
from collections import deque
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import AABB, Vec3
from mcblueprint.operations import ExecutionContext, build_operation
from mcblueprint.operations.shapes import disc_cells, disc_offsets, inside, sphere_offsets
from mcblueprint.volume import BlockVolume


def run(data: dict[str, Any]) -> tuple[Any, set[Vec3]]:
    data = {"block": "stone", **data}
    op = build_operation(data, "operations[0]")
    ctx = ExecutionContext(BlockVolume(), random.Random(0), {})
    op.apply(ctx)
    return op, set(ctx.volume.positions())


def is_8_connected(cells: set[tuple[int, int]]) -> bool:
    start = next(iter(cells))
    seen = {start}
    queue = deque([start])
    while queue:
        u, v = queue.popleft()
        for du in (-1, 0, 1):
            for dv in (-1, 0, 1):
                n = (u + du, v + dv)
                if n in cells and n not in seen:
                    seen.add(n)
                    queue.append(n)
    return seen == cells


class TestPredicates:
    def test_inside_matches_float_formula(self) -> None:
        for r in range(1, 12):
            for d_sq in range(0, (r + 2) ** 2):
                assert inside(d_sq, r) == (d_sq < (r + 0.5) ** 2)

    @pytest.mark.parametrize("radius", range(1, 15))
    def test_hollow_is_one_block_boundary(self, radius: int) -> None:
        solid = disc_cells(radius, "solid")
        ring = disc_cells(radius, "hollow")
        assert ring <= solid
        for u, v in solid:
            touches_outside = any(
                (u + du, v + dv) not in solid for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1))
            )
            assert ((u, v) in ring) == touches_outside


class TestCircle:
    @pytest.mark.parametrize(
        ("radius", "hollow_count", "solid_count"),
        [(1, 8, 9), (2, 12, 21), (3, 16, 37), (5, 28, 97), (6, 36, 137)],
    )
    def test_known_sizes(self, radius: int, hollow_count: int, solid_count: int) -> None:
        assert len(list(disc_offsets(radius, "hollow", "y"))) == hollow_count
        assert len(list(disc_offsets(radius, "solid", "y"))) == solid_count

    def test_radius_2_pattern(self) -> None:
        ring = {(p.x, p.z) for p in disc_offsets(2, "hollow", "y")}
        expected = {
            (-1, -2), (0, -2), (1, -2),
            (-2, -1), (2, -1),
            (-2, 0), (2, 0),
            (-2, 1), (2, 1),
            (-1, 2), (0, 2), (1, 2),
        }  # fmt: skip
        assert ring == expected

    @pytest.mark.parametrize("radius", range(1, 15))
    def test_ring_is_closed(self, radius: int) -> None:
        ring = {(p.x, p.z) for p in disc_offsets(radius, "hollow", "y")}
        assert is_8_connected(ring)
        # every ring cell touches the outside (some 4-neighbour is not solid)
        solid = {(p.x, p.z) for p in disc_offsets(radius, "solid", "y")}
        for u, v in ring:
            assert any(
                (u + du, v + dv) not in solid for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1))
            )

    def test_symmetry(self) -> None:
        disc = {(p.x, p.z) for p in disc_offsets(4, "solid", "y")}
        assert disc == {(-u, v) for u, v in disc} == {(u, -v) for u, v in disc}
        assert disc == {(v, u) for u, v in disc}

    def test_default_axis_y_and_center(self) -> None:
        op, cells = run({"type": "circle", "center": [10, 5, -3], "radius": 2, "mode": "solid"})
        assert op.axis == "y"
        assert all(p.y == 5 for p in cells)
        assert Vec3(10, 5, -3) in cells
        assert Vec3(12, 5, -3) in cells
        assert op.bounds() == AABB(Vec3(8, 5, -5), Vec3(12, 5, -1))

    def test_axis_x(self) -> None:
        op, cells = run({"type": "circle", "center": [0, 0, 0], "radius": 2, "axis": "x"})
        assert all(p.x == 0 for p in cells)
        assert {(p.y, p.z) for p in cells} == {(p.x, p.z) for p in disc_offsets(2, "hollow", "y")}
        assert op.bounds() == AABB(Vec3(0, -2, -2), Vec3(0, 2, 2))

    def test_axis_z(self) -> None:
        _, cells = run({"type": "circle", "center": [0, 0, 0], "radius": 3, "axis": "z"})
        assert all(p.z == 0 for p in cells)
        assert {(p.x, p.y) for p in cells} == {(p.x, p.z) for p in disc_offsets(3, "hollow", "y")}

    def test_invalid_axis_and_radius(self) -> None:
        with pytest.raises(BlueprintError, match="axis"):
            run({"type": "circle", "center": [0, 0, 0], "radius": 2, "axis": "w"})
        with pytest.raises(BlueprintError, match="radius"):
            run({"type": "circle", "center": [0, 0, 0], "radius": 0})


class TestCylinder:
    def test_hollow_stack(self) -> None:
        op, cells = run({"type": "cylinder", "center": [0, 0, 0], "radius": 3, "height": 4})
        ring = {(p.x, p.z) for p in disc_offsets(3, "hollow", "y")}
        assert cells == {Vec3(u, y, v) for y in range(4) for u, v in ring}
        assert Vec3(0, 0, 0) not in cells  # no bottom cap
        assert op.bounds() == AABB(Vec3(-3, 0, -3), Vec3(3, 3, 3))

    def test_solid_and_axis_x(self) -> None:
        op, cells = run(
            {
                "type": "cylinder",
                "center": [1, 2, 3],
                "radius": 2,
                "height": 3,
                "axis": "x",
                "mode": "solid",
            }
        )
        assert {p.x for p in cells} == {1, 2, 3}
        assert Vec3(1, 2, 3) in cells and Vec3(3, 2, 3) in cells
        assert len(cells) == 21 * 3
        assert op.bounds() == AABB(Vec3(1, 0, 1), Vec3(3, 4, 5))

    def test_requires_height(self) -> None:
        with pytest.raises(BlueprintError, match="height"):
            run({"type": "cylinder", "center": [0, 0, 0], "radius": 2})


class TestSphere:
    @pytest.mark.parametrize("radius", [1, 2, 3, 5])
    def test_solid_contains_axis_extremes_and_is_symmetric(self, radius: int) -> None:
        ball = set(sphere_offsets(radius, "solid"))
        for axis in ("x", "y", "z"):
            assert Vec3(0, 0, 0).with_axis(axis, radius) in ball
            assert Vec3(0, 0, 0).with_axis(axis, -radius) in ball
            assert Vec3(0, 0, 0).with_axis(axis, radius + 1) not in ball
        assert ball == {Vec3(-p.x, p.y, p.z) for p in ball}
        assert ball == {Vec3(p.y, p.x, p.z) for p in ball}

    def test_hollow_is_shell(self) -> None:
        shell = set(sphere_offsets(3, "hollow"))
        ball = set(sphere_offsets(3, "solid"))
        steps = [
            Vec3(1, 0, 0),
            Vec3(-1, 0, 0),
            Vec3(0, 1, 0),
            Vec3(0, -1, 0),
            Vec3(0, 0, 1),
            Vec3(0, 0, -1),
        ]
        assert shell == {p for p in ball if any(p + d not in ball for d in steps)}
        assert Vec3(0, 0, 0) not in shell
        assert Vec3(0, 3, 0) in shell

    def test_equator_matches_circle(self) -> None:
        ball = set(sphere_offsets(4, "solid"))
        equator = {(p.x, p.z) for p in ball if p.y == 0}
        assert equator == {(p.x, p.z) for p in disc_offsets(4, "solid", "y")}

    def test_operation(self) -> None:
        op, cells = run({"type": "sphere", "center": [0, 10, 0], "radius": 2})
        assert op.mode == "hollow"
        assert Vec3(0, 12, 0) in cells and Vec3(0, 10, 0) not in cells
        assert op.bounds() == AABB(Vec3(-2, 8, -2), Vec3(2, 12, 2))
