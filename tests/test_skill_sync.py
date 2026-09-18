"""The Claude Code skill is a copy of the Codex skill; both must stay identical."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEX_SKILL = REPO_ROOT / ".agents" / "skills" / "minecraft-blueprint"
CLAUDE_SKILL = REPO_ROOT / ".claude" / "skills" / "minecraft-blueprint"


def relative_files(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in root.rglob("*") if p.is_file()}


def test_skill_directories_exist() -> None:
    assert (CODEX_SKILL / "SKILL.md").is_file()
    assert (CLAUDE_SKILL / "SKILL.md").is_file()


def test_same_file_set() -> None:
    assert relative_files(CODEX_SKILL) == relative_files(CLAUDE_SKILL)


@pytest.mark.parametrize("relative", sorted(relative_files(CODEX_SKILL)), ids=str)
def test_file_contents_match(relative: Path) -> None:
    codex = (CODEX_SKILL / relative).read_text(encoding="utf-8")
    claude = (CLAUDE_SKILL / relative).read_text(encoding="utf-8")
    assert codex == claude, f"{relative} differs; copy .agents/skills to .claude/skills"


def test_skill_frontmatter() -> None:
    text = (CODEX_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: minecraft-blueprint\n")
    assert "\ndescription: " in text.split("---")[1]
