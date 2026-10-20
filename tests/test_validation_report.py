import json
from pathlib import Path

import pytest

from mcblueprint.cli import main
from mcblueprint.diagnostics import validation_report
from mcblueprint.errors import ValidationError


def blueprint(tmp_path: Path, operations: list[dict]) -> Path:
    path = tmp_path / "diagnostics.json"
    path.write_text(json.dumps({
        "formatVersion": 1, "minecraftVersion": "1.21.11", "name": "diagnostics",
        "operations": operations,
    }), encoding="utf-8")
    return path


def bad_operations(count: int) -> list[dict]:
    return [{"type": "set", "position": [i, 0, 0], "block": "nope"} for i in range(count)]


def test_many_errors_and_retrieval(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = blueprint(tmp_path, bad_operations(120))
    assert main(["validate", str(path), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["source"] == path.as_posix()
    assert report["valid"] is False and report["exitCode"] == 1
    assert report["strict"] is False
    assert report["counts"] == {
        "total": 120, "errors": 120, "warnings": 0, "byKind": {"semantic": 120},
        "matched": 120, "shown": 50, "omitted": 70, "filteredOut": 0,
        "groups": 1, "groupsOmitted": 0,
    }
    assert report["groups"][0]["count"] == 120
    assert report["retrieval"]["nextOffset"] == 50
    first = report["diagnostics"][0]
    assert first == {
        "id": 1, "kind": "semantic", "severity": "error", "path": "operations[0].block",
        "message": "Unknown block id.", "opType": "set", "value": "nope", "position": None,
    }
    assert main(["validate", str(path), "--json", "--offset", "50", "--limit", "0"]) == 1
    page = json.loads(capsys.readouterr().out)
    assert len(page["diagnostics"]) == 70
    assert page["diagnostics"][0]["id"] == 51
    assert page["retrieval"]["nextOffset"] is None


@pytest.mark.parametrize("flags,matched,filtered", [
    (["--kind", "schema"], 0, 12),
    (["--path", "operations[1]"], 1, 11),
    (["--path", "operations[1].block"], 1, 11),
    (["--path", "operations[1]", "--path", "operations[2]"], 2, 10),
    (["--offset", "99"], 12, 0),
])
def test_filters_preserve_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flags: list[str],
    matched: int, filtered: int,
) -> None:
    path = blueprint(tmp_path, bad_operations(12))
    assert main(["validate", str(path), "--json", *flags]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["counts"]["matched"] == matched
    assert report["counts"]["filteredOut"] == filtered
    assert report["counts"]["omitted"] == matched - report["counts"]["shown"]


@pytest.mark.parametrize("strict,exit_code", [(False, 0), (True, 1)])
def test_support_and_strict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], strict: bool, exit_code: int,
) -> None:
    path = blueprint(tmp_path, [
        {"type": "fill", "from": [0, 0, 0], "to": [2, 3, 2], "block": "air"},
        {"type": "set", "position": [1, 1, 1], "block": "lantern[hanging=true]"},
    ])
    flags = ["--strict"] if strict else []
    assert main(["validate", str(path), "--json", *flags]) == exit_code
    report = json.loads(capsys.readouterr().out)
    assert report["valid"] == (exit_code == 0)
    warning = report["diagnostics"][0]
    assert warning["kind"] == "support" and warning["severity"] == "warning"
    assert warning["path"] is None and warning["position"] == [1, 1, 1]
    assert warning["value"] == "minecraft:lantern[hanging=true]"
    assert main(["validate", str(path), "--json", "--path", "operations", *flags]) == exit_code
    assert json.loads(capsys.readouterr().out)["counts"]["shown"] == 0


def test_schema_and_no_results(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = blueprint(tmp_path, [{"type": "set", "position": [0, 0, 0], "block": "stone"}])
    assert main(["validate", str(path), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["counts"]["total"] == 0 and report["diagnostics"] == report["groups"] == []
    path = blueprint(tmp_path, [{"type": "set", "position": [0, 0, 0], "block": 7}])
    assert main(["validate", str(path), "--json", "--kind", "schema"]) == 1
    item = json.loads(capsys.readouterr().out)["diagnostics"][0]
    assert item["kind"] == "schema" and item["value"] == 7


@pytest.mark.parametrize("flag", ["--limit", "--offset"])
def test_negative_limits(tmp_path: Path, flag: str) -> None:
    assert main(["validate", str(tmp_path / "missing.json"), flag, "-1"]) == 2


def test_text_filtered_result(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = blueprint(tmp_path, bad_operations(2))
    assert main(["validate", str(path), "--limit", "1"]) == 1
    output = capsys.readouterr().out
    assert "operations[0].block" in output and "operations[1].block" not in output
    assert "omitted 1" in output and "--limit 0" in output


def test_groups_are_limited_to_displayed_causes() -> None:
    errors = [ValidationError(f"operations[{i}]", f"cause {i % 3}") for i in range(60)]
    report = validation_report(
        "house.json", errors, [], strict=False, kinds=[], paths=[], limit=1, offset=4,
    )
    assert len(report["groups"]) == 1
    assert report["groups"][0]["message"] == "cause 1"
    assert report["groups"][0]["count"] == 20
    assert report["counts"]["groupsOmitted"] == 2


def test_json_io_error_uses_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(tmp_path / "missing.json"), "--json"]) == 2
    output = capsys.readouterr()
    assert output.out == "" and "not found" in output.err


def reject_nonfinite(token: str) -> None:
    raise ValueError(f"非標準JSON数値: {token}")


@pytest.mark.parametrize("number,expected", [
    ("1e999", "Infinity"), ("-1e999", "-Infinity"), ("NaN", "NaN"),
])
def test_json_nonfinite_value(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], number: str, expected: str,
) -> None:
    path = blueprint(tmp_path, [{"type": "set", "position": [0, 0, 0], "block": "NUMBER"}])
    path.write_text(path.read_text(encoding="utf-8").replace('"NUMBER"', number), encoding="utf-8")
    assert main(["validate", str(path), "--json"]) == 1
    report = json.loads(capsys.readouterr().out, parse_constant=reject_nonfinite)
    assert report["diagnostics"][0]["value"] == expected
    assert report["valid"] is False and report["exitCode"] == 1


def test_nested_nonfinite_values() -> None:
    value = {"values": [float("inf"), {"negative": float("-inf"), "nan": float("nan")}],
             "finite": 1.5, "text": "Infinity", "empty": None}
    report = validation_report(
        "house.json", [ValidationError("operations", "原因", value=value)], [],
        strict=False, kinds=[], paths=[], limit=0, offset=0,
    )
    encoded = json.dumps(report, allow_nan=False)
    parsed = json.loads(encoded, parse_constant=reject_nonfinite)
    assert parsed["diagnostics"][0]["value"] == {
        "values": ["Infinity", {"negative": "-Infinity", "nan": "NaN"}],
        "finite": 1.5, "text": "Infinity", "empty": None,
    }
    assert value["values"][0] == float("inf")
