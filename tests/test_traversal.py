import json
from pathlib import Path
from typing import Any

import pytest

from mcblueprint.cli import main
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model import BlockState, Vec3
from mcblueprint.operations.building import BuildingOperation
from mcblueprint.operations.transform import Transform
from mcblueprint.traversal import check_building, check_route
from mcblueprint.volume import BlockVolume

B = BlockState.parse
VERSION = "1.21.11"


def building(**changes: Any) -> dict[str, Any]:
    return {"type": "building", "position": [0, 0, 0], "width": 7, "depth": 8,
            "floors": 2, "wall": "stone_bricks", "floor": "oak_planks",
            "roof": "oak_stairs", "stairs": "oak_stairs", "window": "glass",
            "door": "oak_door", **changes}


def blueprint(*ops: dict[str, Any]) -> dict[str, Any]:
    return {"formatVersion": 1, "minecraftVersion": VERSION, "name": "traversal",
            "operations": list(ops)}


def generated(**changes: Any) -> tuple[BlockVolume, BuildingOperation]:
    bp = load_blueprint_dict(blueprint(building(**changes)))
    return generate(bp), bp.operations[0]


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("floors", [1, 2])
def test_building_entry_and_floors_are_reachable_in_both_directions(
    angle: int, floors: int
) -> None:
    volume, op = generated(angle=angle, floors=floors, position=[-8, -3, 12])
    before = dict(volume)
    results = check_building(volume, op.layout, VERSION)
    assert len(results) == floors
    assert all(r.status == "reachable" for r in results)
    for result in results:
        assert result.path[0] == result.start and result.path[-1] == result.end
        reverse = check_route(volume, result.end, result.start, VERSION)
        assert reverse.status == "reachable"
    assert dict(volume) == before
    assert results == check_building(volume, op.layout, VERSION)


@pytest.mark.parametrize("failure", [
    "closed-opening", "low-ceiling", "reverse-stairs", "missing-floor",
])
def test_building_failure_fixtures(failure: str) -> None:
    volume, op = generated()
    if failure == "closed-opening":
        for z in (3, 4):
            volume.set(Vec3(1, 4, z), B("oak_planks"))
    elif failure == "low-ceiling":
        volume.set(Vec3(1, 3, 2), B("stone"))
    elif failure == "reverse-stairs":
        for i in range(4):
            volume.set(Vec3(1, 1 + i, 2 + i), B("oak_stairs[facing=north]"))
    else:
        volume.set(op.layout.arrivals[-1] - Vec3(0, 1, 0), B("air"))
    result = check_building(volume, op.layout, VERSION)[-1]
    assert result.status == "blocked", result
    assert result.issues
    assert result.path == ()


def corridor() -> BlockVolume:
    volume = BlockVolume()
    for x in range(4):
        volume.set(Vec3(x, 0, 0), B("stone"))
    return volume


@pytest.mark.parametrize("door", ["oak_door", "copper_door", "waxed_oxidized_copper_door"])
@pytest.mark.parametrize("opened", ["true", "false"])
def test_normal_doors_can_be_opened(door: str, opened: str) -> None:
    volume = corridor()
    for half, y in (("lower", 1), ("upper", 2)):
        volume.set(Vec3(1, y, 0), B(f"{door}[half={half},open={opened}]"))
    assert check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION).status == "reachable"


@pytest.mark.parametrize("state", ["iron_door", "oak_fence", "oak_slab[type=bottom]",
                                  "oak_stairs[shape=inner_left]", "oak_stairs[half=top]",
                                  "oak_stairs[waterlogged=true]", "water", "ladder"])
def test_unsupported_shape_is_not_treated_as_air(state: str) -> None:
    volume = corridor()
    volume.set(Vec3(1, 1, 0), B(state))
    result = check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION)
    assert result.status == "unsupported"
    assert any(
        i.position == Vec3(1, 1, 0) and i.block == B(state).to_string() for i in result.issues
    )


def test_broken_door_pair_is_unsupported() -> None:
    volume = corridor()
    volume.set(Vec3(1, 1, 0), B("oak_door"))
    result = check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION)
    assert result.status == "unsupported"
    assert any(i.reason == "unsupported_door_pair" for i in result.issues)


def test_known_alternative_path_is_not_rejected_by_unknown_shape() -> None:
    volume = corridor()
    for x in range(4):
        volume.set(Vec3(x, 0, 1), B("stone"))
    volume.set(Vec3(1, 1, 0), B("oak_fence"))
    result = check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION)
    assert result.status == "reachable"
    assert Vec3(1, 1, 0) not in result.path


def test_jump_and_missing_floor_and_outside_are_blocked() -> None:
    volume = corridor()
    volume.set(Vec3(1, 1, 0), B("stone"))
    assert check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION).status == "blocked"
    volume.set(Vec3(1, 1, 0), B("air"))
    volume.set(Vec3(1, 0, 0), B("air"))
    assert check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION).status == "blocked"
    result = check_route(volume, Vec3(-100, 1, 0), Vec3(3, 1, 0), VERSION)
    assert result.issues[0].reason == "outside_search_bounds"
    assert check_route(BlockVolume(), Vec3(0, 1, 0), Vec3(1, 1, 0), VERSION).status == "blocked"


def write(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_cli_selects_building_or_explicit_route(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    path = write(tmp_path, blueprint(building()))
    assert main(["traverse", str(path), "--building", "0", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["movementModel"] == "walk-straight-v1"
    assert [r["status"] for r in result["results"]] == ["reachable", "reachable"]
    assert main(["traverse", str(path), "--start", "3", "1", "1", "--end", "1", "5", "6"]) == 0
    assert "実機全動作の保証ではありません" in capsys.readouterr().out


@pytest.mark.parametrize("arguments", [["--building", "-1"], ["--building", "9"],
                                       ["--start", "0", "0", "0"],
                                       ["--building", "0", "--end", "0", "0", "0"]])
def test_cli_rejects_bad_target(tmp_path: Path, arguments: list[str]) -> None:
    assert main(["traverse", str(write(tmp_path, blueprint(building()))), *arguments]) == 2


def test_cli_does_not_select_nested_building_implicitly(tmp_path: Path) -> None:
    data = blueprint({"type": "translate", "offset": [10, 0, 0], "operations": [building()]})
    path = write(tmp_path, data)
    assert main(["traverse", str(path), "--building", "0"]) == 2
    assert main(["traverse", str(path), "--start", "13", "1", "1", "--end", "11", "5", "6"]) == 0


def test_cli_failure_is_separate_from_validate(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    data = blueprint(building(), {"type": "set", "position": [1, 4, 6], "block": "air"})
    path = write(tmp_path, data)
    assert main(["validate", str(path)]) == 0
    capsys.readouterr()
    assert main(["traverse", str(path), "--building", "0", "--json"]) == 1
    results = json.loads(capsys.readouterr().out)["results"]
    assert results[-1]["status"] == "blocked"
    assert results[-1]["issues"][0]["reason"] == "missing_floor"


def test_double_slab_floor_and_half_slab_unsupported_support() -> None:
    volume = corridor()
    volume.set(Vec3(1, 0, 0), B("oak_slab[type=double]"))
    assert check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION).status == "reachable"
    volume.set(Vec3(1, 0, 0), B("oak_slab[type=top]"))
    assert check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION).status == "unsupported"


def test_stair_sideways_shortcut_is_not_supported_walk() -> None:
    volume = corridor()
    volume.set(Vec3(1, 0, 0), B("oak_stairs[facing=north]"))
    result = check_route(volume, Vec3(0, 1, 0), Vec3(3, 1, 0), VERSION)
    assert result.status == "blocked"
    assert any(i.reason == "stairs_direction_or_step" for i in result.issues)


@pytest.mark.parametrize("failure,reason,position", [
    ("low-ceiling", "body_or_head_blocked", Vec3(1, 3, 2)),
    ("reverse-stairs", "stairs_direction_or_step", Vec3(1, 1, 2)),
])
def test_stair_blocking_diagnosis_is_visible_in_cli_summary(
    failure: str, reason: str, position: Vec3
) -> None:
    volume, op = generated()
    if failure == "low-ceiling":
        volume.set(position, B("stone"))
    else:
        for i in range(4):
            volume.set(Vec3(1, 1 + i, 2 + i), B("oak_stairs[facing=north]"))
    result = check_building(volume, op.layout, VERSION)[-1]
    assert any(i.position == position and i.reason == reason for i in result.issues[:8])


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("ceiling,status", [("stone", "blocked"), ("oak_fence", "unsupported")])
def test_stair_transition_checks_headroom_remaining_in_lower_column(
    angle: int, reverse: bool, ceiling: str, status: str
) -> None:
    transform = Transform.rotation(angle, Vec3(0, 0, 0))
    volume = BlockVolume()
    for pos, state in (
        (Vec3(0, 0, 0), B("stone")), (Vec3(1, 0, 0), B("stone")),
        (Vec3(1, 1, 0), B("oak_stairs[facing=east]")),
        (Vec3(0, 3, 0), B(ceiling)),
    ):
        volume.set(transform.apply(pos), transform.apply_state(state))
    start, end = transform.apply(Vec3(0, 1, 0)), transform.apply(Vec3(1, 2, 0))
    if reverse:
        start, end = end, start
    result = check_route(volume, start, end, VERSION)
    assert result.status == status
    assert any(i.position == transform.apply(Vec3(0, 3, 0)) for i in result.issues)


@pytest.mark.parametrize("ceiling", ["stone", "oak_fence"])
@pytest.mark.parametrize("reverse", [False, True])
def test_known_detour_can_avoid_transition_head_obstacle(ceiling: str, reverse: bool) -> None:
    volume = BlockVolume()
    for x in range(3):
        for z in range(2):
            volume.set(Vec3(x, 0, z), B("stone"))
    for z in range(2):
        volume.set(Vec3(1, 1, z), B("oak_stairs[facing=east]"))
        volume.set(Vec3(2, 1, z), B("stone"))
    volume.set(Vec3(0, 3, 0), B(ceiling))
    start, end = Vec3(0, 1, 0), Vec3(1, 2, 0)
    if reverse:
        start, end = end, start
    result = check_route(volume, start, end, VERSION)
    assert result.status == "reachable"
    assert Vec3(1, 2, 1) in result.path
