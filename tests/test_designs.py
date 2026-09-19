"""Bundled design presets must exist, follow the documented layout and use valid blocks."""

import json
import re
from pathlib import Path

import pytest

from mcblueprint.validator import validate

DESIGNS_DIR = Path(__file__).resolve().parent.parent / "designs"
PRESETS = sorted(p for p in DESIGNS_DIR.glob("*.md") if p.name != "README.md")
REQUIRED_HEADINGS = ("## 概要", "## Palette", "## 構造ルール")


def json_blocks(text: str) -> list[dict]:
    return [json.loads(m) for m in re.findall(r"```json\n(.*?)```", text, re.S)]


def test_bundled_presets_exist() -> None:
    assert {p.stem for p in PRESETS} >= {"medieval", "japanese", "modern"}
    assert (DESIGNS_DIR / "README.md").is_file()
    assert (DESIGNS_DIR / "local" / ".gitkeep").is_file()


@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_preset_layout(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.startswith(f"# {path.stem}")
    for heading in REQUIRED_HEADINGS:
        assert heading in text, heading
    assert re.fullmatch(r"[a-z0-9_]+", path.stem)


@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_preset_palettes_validate(path: Path) -> None:
    blocks = json_blocks(path.read_text(encoding="utf-8"))
    palettes = [b["palettes"] for b in blocks if "palettes" in b]
    assert palettes, "preset needs a ```json block with a palettes object"
    for palette_set in palettes:
        operations = [
            {"type": "set", "position": [i, 0, 0], "palette": name}
            for i, name in enumerate(palette_set)
        ]
        data = {
            "formatVersion": 1,
            "minecraftVersion": "1.21.11",
            "name": path.stem,
            "palettes": palette_set,
            "operations": operations,
        }
        assert validate(data) == [], path.stem


def test_readme_lists_every_preset() -> None:
    readme = (DESIGNS_DIR / "README.md").read_text(encoding="utf-8")
    for path in PRESETS:
        assert f"[{path.name}]({path.name})" in readme, path.name
