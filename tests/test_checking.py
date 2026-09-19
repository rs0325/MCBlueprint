import json
from pathlib import Path

import pytest

from mcblueprint import components
from mcblueprint.checking import (
    check_component,
    check_paths,
    check_preset,
    iter_targets,
    list_components,
    preset_snippets,
)
from mcblueprint.cli import EXIT_OK, EXIT_USAGE_ERROR, EXIT_VALIDATION_ERROR, main
from mcblueprint.errors import BlueprintError

REPO_ROOT = Path(__file__).resolve().parent.parent

GOOD_PRESET = """# good

```json
{ "palettes": { "wall": [ { "block": "minecraft:stone_bricks", "weight": 1 } ] } }
```

```json
{ "type": "roof", "from": [0, 5, 0], "to": [10, 5, 8], "block": "dark_oak_stairs" }
```

```json
{ "operations": [ { "type": "set", "position": [0, 0, 0], "block": "stone" } ] }
```

```json
[1, 2, 3]
```
"""

BAD_PRESET = """# bad

```json
{ "palettes": { "wall": [ { "block": "minecraft:stone_brickz", "weight": 1 } ] } }
```

```json
{ "type": "roof", "from": [0, 5, 0], "to": [10, 5, 8], "block": "oak_stairs", "gable": "no_such" }
```

```json
{ not json }
```
"""


def component(name: str, operations: list[dict], **extra: object) -> str:
    return json.dumps({"formatVersion": 1, "name": name, "operations": operations, **extra})


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "designs" / "local").mkdir(parents=True)
    (tmp_path / "components").mkdir()
    (tmp_path / "designs" / "good.md").write_text(GOOD_PRESET, encoding="utf-8")
    (tmp_path / "designs" / "README.md").write_text(
        "# not a preset\n```json\n{ bad\n```\n", encoding="utf-8"
    )
    (tmp_path / "designs" / "local" / "bad.md").write_text(BAD_PRESET, encoding="utf-8")
    (tmp_path / "components" / "lamp.json").write_text(
        component(
            "lamp",
            [
                {"type": "set", "position": [0, 0, 0], "block": "minecraft:stone"},
                {"type": "set", "position": [0, 1, 0], "block": "minecraft:lantern"},
            ],
            description="a lantern on a stone",
        ),
        encoding="utf-8",
    )
    (tmp_path / "components" / "floating.json").write_text(
        component(
            "floating",
            [
                {"type": "set", "position": [1, 0, 0], "block": "minecraft:stone"},
                {"type": "set", "position": [0, 1, 0], "block": "minecraft:lantern"},
            ],
        ),
        encoding="utf-8",
    )
    (tmp_path / "components" / "broken.json").write_text(
        component("broken", [{"type": "set", "position": [0, 0, 0], "block": "no_such_block"}]),
        encoding="utf-8",
    )
    (tmp_path / "components" / "README.md").write_text("# components\n", encoding="utf-8")
    return tmp_path


class TestPresets:
    def test_snippets_report_parse_errors_per_block(self) -> None:
        snippets = preset_snippets(BAD_PRESET)
        assert [i for i, _, _ in snippets] == [0, 1, 2]
        assert snippets[2][1] is None and "Expecting" in (snippets[2][2] or "")

    def test_good_preset(self, tree: Path) -> None:
        result = check_preset(tree / "designs" / "good.md", "1.21.11")
        assert result.ok and result.kind == "preset"

    def test_bad_preset_paths(self, tree: Path) -> None:
        result = check_preset(tree / "designs" / "local" / "bad.md", "1.21.11")
        assert [e.path for e in result.errors] == [
            "json[0].palettes.wall[0].block",
            "json[1].operations[0].gable",
            "json[2]",
        ]
        assert "Invalid JSON" in result.errors[2].message

    def test_bundled_presets_pass(self) -> None:
        for path in (REPO_ROOT / "designs").glob("*.md"):
            if path.name != "README.md":
                assert check_preset(path, "1.21.11").ok, path.name


class TestComponents:
    def test_component_size_description_and_warning(self, tree: Path) -> None:
        lamp = check_component(tree / "components" / "lamp.json", "1.21.11")
        assert lamp.ok and lamp.size is not None and lamp.size.to_list() == [1, 2, 1]
        assert lamp.description == "a lantern on a stone" and lamp.warnings == []
        floating = check_component(tree / "components" / "floating.json", "1.21.11")
        assert floating.ok and len(floating.warnings) == 1
        assert "lantern" in floating.warnings[0].block.id

    def test_component_errors_are_relative_to_the_file(self, tree: Path) -> None:
        broken = check_component(tree / "components" / "broken.json", "1.21.11")
        assert [e.path for e in broken.errors] == ["operations[0].block"]
        assert broken.size is None

    def test_bundled_components_pass(self) -> None:
        for path in (REPO_ROOT / "components").glob("*.json"):
            result = check_component(path, "1.21.11")
            assert result.ok and not result.warnings, path.name

    def test_list_components_first_hit_wins(self, tree: Path) -> None:
        other = tree / "other"
        other.mkdir()
        (other / "lamp.json").write_text(
            component("lamp", [{"type": "set", "position": [0, 0, 0], "block": "no"}]),
            encoding="utf-8",
        )
        results = list_components([tree / "components", other, tree / "missing"])
        assert [r.path.stem for r in results] == ["broken", "floating", "lamp"]
        assert results[2].path.parent == tree / "components"


class TestDriver:
    def test_iter_targets_recurses_and_skips_readmes(self, tree: Path) -> None:
        targets = list(iter_targets([tree / "designs", tree / "components"]))
        names = [(p.name, kind) for p, kind in targets]
        assert ("README.md", "preset") not in names
        assert ("bad.md", "preset") in names and ("lamp.json", "component") in names
        with pytest.raises(BlueprintError, match="no such file"):
            list(iter_targets([tree / "nope"]))
        (tree / "x.txt").write_text("", encoding="utf-8")
        with pytest.raises(BlueprintError, match="not a preset"):
            list(iter_targets([tree / "x.txt"]))

    def test_check_paths_defaults_to_oldest_version(self, tree: Path) -> None:
        results = check_paths([tree / "designs"])
        assert [r.path.name for r in results] == ["good.md", "bad.md"]
        with pytest.raises(BlueprintError, match="Unsupported Minecraft version"):
            check_paths([tree / "designs"], "0.0.1")


class TestCli:
    def test_check_reports_and_exit_codes(
        self, tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tree)
        assert main(["check"]) == EXIT_VALIDATION_ERROR
        out = capsys.readouterr().out
        assert "bad.md (preset)" in out and "broken.json (component)" in out
        assert "ERROR json[0].palettes.wall[0].block" in out
        assert "WARNING [0, 1, 0] minecraft:lantern" in out
        assert "5 files checked: 4 error(s), 1 warning(s)." in out
        assert "good.md" not in out and "lamp.json" not in out

    def test_check_explicit_paths_and_strict(
        self, tree: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        good = str(tree / "designs" / "good.md")
        floating = str(tree / "components" / "floating.json")
        assert main(["check", good]) == EXIT_OK
        assert "1 file checked: 0 error(s), 0 warning(s)." in capsys.readouterr().out
        assert main(["check", floating]) == EXIT_OK
        assert main(["check", floating, "--strict"]) == EXIT_VALIDATION_ERROR
        assert main(["check", str(tree / "nope")]) == EXIT_USAGE_ERROR
        assert main(["check", good, "--minecraft-version", "26.3"]) == EXIT_OK
        assert main(["check", good, "--minecraft-version", "9.9"]) == EXIT_USAGE_ERROR

    def test_check_without_targets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert main(["check"]) == EXIT_USAGE_ERROR
        assert "Nothing to check" in capsys.readouterr().err

    def test_components_listing(
        self, tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tree)
        assert main(["components"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "lamp" in out and "1x2x1" in out and "a lantern on a stone" in out
        assert "[1 error(s)]" in out and "[1 warning(s)]" in out
        assert main(["components", "--json"]) == EXIT_OK
        rows = json.loads(capsys.readouterr().out)["components"]
        assert {r["name"] for r in rows} == {"broken", "floating", "lamp"}
        assert next(r for r in rows if r["name"] == "lamp")["size"] == [1, 2, 1]

    def test_components_none_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert main(["components"]) == EXIT_OK
        assert "No components found" in capsys.readouterr().out

    def test_bundled_check_passes(self, capsys: pytest.CaptureFixture[str]) -> None:
        with components.component_search_paths([REPO_ROOT / "components"]):
            assert (
                main(
                    ["check", str(REPO_ROOT / "designs"), str(REPO_ROOT / "components"), "--strict"]
                )
                == EXIT_OK
            )
        assert "0 error(s), 0 warning(s)" in capsys.readouterr().out
