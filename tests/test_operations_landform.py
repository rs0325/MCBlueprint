import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse


def landform(**extra: Any) -> dict[str, Any]:
    return {
        "type": "landform",
        "shape": "hill",
        "from": [-2, -3, -2],
        "to": [2, -3, 2],
        "height": 4,
        "surface": "grass_block",
        "subsurface": "stone",
        **extra,
    }


def run(data: dict[str, Any]) -> BlockVolume:
    volume = BlockVolume()
    build_operation(data, "operations[0]").apply(ExecutionContext(volume, random.Random(0), {}))
    return volume


def blueprint(operation: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "landform",
        "operations": [operation],
        **extra,
    }


class TestLandformGeometry:
    def test_even_and_odd_hills_are_symmetric_and_reach_full_height(self) -> None:
        for size in (3, 4, 5, 6):
            low = -size // 2
            high = low + size - 1
            volume = run(landform(**{"from": [low, 0, low], "to": [high, 0, high]}))
            # 奇数幅では中央の1セル、偶数幅では中央の2セルが指定高さになる。
            centers = {low + (size - 1) // 2, low + size // 2}
            for x in range(low, high + 1):
                for z in range(low, high + 1):
                    assert volume.get(Vec3(x, 0, z)) == volume.get(
                        Vec3(high - (x - low), 0, z)
                    )
                    assert volume.get(Vec3(x, 0, z)) == volume.get(
                        Vec3(x, 0, high - (z - low))
                    )
            peaks = [
                (x, z)
                for x in centers
                for z in centers
                if volume.get(Vec3(x, 4, z)) == B("grass_block")
            ]
            assert peaks

    def test_hill_bounds_are_envelope_and_ellipse_corners_are_empty(self) -> None:
        operation = build_operation(landform(), "operations[0]")
        assert operation.bounds().min == Vec3(-2, -3, -2)
        assert operation.bounds().max == Vec3(2, 1, 2)
        volume = run(landform())
        assert volume.get(Vec3(-2, -3, -2)) is None
        assert volume.get(Vec3(0, 1, 0)) == B("grass_block")
        assert len(list(volume)) < 5 * 5 * 5

    def test_negative_reversed_coordinates_and_contiguous_layers(self) -> None:
        volume = run(landform(**{"from": [2, -3, 2], "to": [-2, -3, -2]}))
        for y in (-3, -2, -1, 0, 1):
            assert volume.get(Vec3(0, y, 0)) == (B("grass_block") if y == 1 else B("stone"))

    def test_plateau_has_flat_interior_and_rounded_edge(self) -> None:
        volume = run(
            landform(
                shape="plateau",
                **{"from": [0, 5, 0], "to": [6, 5, 6]},
                height=3,
                edgeWidth=2,
            )
        )
        assert volume.get(Vec3(3, 8, 3)) == B("grass_block")
        assert volume.get(Vec3(1, 7, 1)) == B("grass_block")
        assert volume.get(Vec3(0, 5, 0)) == B("grass_block")
        assert volume.get(Vec3(0, 6, 0)) is None
        assert volume.get(Vec3(3, 7, 3)) == B("stone")

    def test_generation_is_deterministic_and_operation_order_is_last_write_wins(self) -> None:
        first = run(landform())
        second = run(landform())
        assert list(first) == list(second)
        volume = BlockVolume()
        ctx = ExecutionContext(volume, random.Random(0), {})
        build_operation(landform(), "operations[0]").apply(ctx)
        build_operation(
            {"type": "set", "position": [0, 1, 0], "block": "diamond_block"}, "operations[1]"
        ).apply(ctx)
        assert volume.get(Vec3(0, 1, 0)) == B("diamond_block")


class TestLandformValidation:
    @pytest.mark.parametrize(
        ("changes", "message"),
        [
            ({"shape": "mountain"}, "shape"),
            ({"height": 0}, "height"),
            ({"surface": None}, "missing required 'surface'"),
            ({"subsurface": None}, "missing required 'subsurface'"),
            ({"shape": "plateau", "edgeWidth": 0}, "edgeWidth"),
            (
                {"shape": "plateau", "edgeWidth": 2, "from": [0, -3, 0], "to": [2, -3, 2]},
                "footprint",
            ),
            ({"edgeWidth": 1}, "only valid for a plateau"),
            ({"to": [2, 0, 2]}, "same y"),
            ({"from": [0, -3, 0], "to": [1, -3, 2]}, "at least 3 x 3"),
        ],
    )
    def test_invalid_operation(self, changes: dict[str, Any], message: str) -> None:
        with pytest.raises(BlueprintError, match=message):
            build_operation(landform(**changes), "operations[0]")

    def test_material_validation_and_bounds_limit(self) -> None:
        assert validate(blueprint(landform())) == []
        errors = validate(blueprint(landform(surface="bad_block")))
        assert any("surface" in error.path for error in errors)
        errors = validate(blueprint(landform(surface={"palette": "missing"})))
        assert any("surface.palette" in error.path for error in errors)
        too_wide = landform(**{"from": [0, 0, 0], "to": [1024, 0, 2]})
        assert any("dimension" in error.message.lower() for error in validate(blueprint(too_wide)))

    def test_material_is_checked_for_selected_minecraft_version(self) -> None:
        operation = landform(surface="cinnabar")
        old_errors = validate(blueprint(operation, minecraftVersion="1.21.11"))
        new_errors = validate(blueprint(operation, minecraftVersion="26.3"))
        assert any("surface" in error.path for error in old_errors)
        assert not any("surface" in error.path for error in new_errors)
