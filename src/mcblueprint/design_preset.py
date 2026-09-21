"""Render a :class:`~mcblueprint.analysis.DesignAnalysis` as a design preset
(``designs/<name>.md``) in the layout documented in ``designs/README.md``.

The text is a first draft: the numbers and palettes are measured from the source
structure, the sentences are templates, and the file says so at the top.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mcblueprint.analysis import PALETTE_ROLES, DesignAnalysis
from mcblueprint.model.vec import Vec3

ROLE_LABELS = {
    "wall": "壁",
    "post": "柱",
    "beam": "梁",
    "floor": "床",
    "roof": "屋根",
    "ridge": "棟",
    "gable": "妻壁",
    "foundation": "土台",
    "ceiling": "天井",
    "interior": "内部",
    "window": "窓",
    "door": "ドア",
    "light": "照明",
    "decoration": "装飾",
}
VIEW_SYMBOLS = {
    "wall": "#",
    "post": "P",
    "beam": "B",
    "floor": "_",
    "roof": "/",
    "ridge": "^",
    "gable": "G",
    "foundation": "=",
    "ceiling": "-",
    "interior": ".",
    "window": "o",
    "door": "D",
    "light": "*",
    "decoration": "+",
}
MAX_VIEW_WIDTH = 60
MAX_VIEW_HEIGHT = 40
MIN_ROLE_CELLS = 3  # roles with fewer blocks are noise (a chimney, a stray slab)


@dataclass
class PartInfo:
    name: str
    size: Vec3
    description: str | None
    path: str


def short(block_id: str) -> str:
    return block_id[len("minecraft:") :] if block_id.startswith("minecraft:") else block_id


def palettes_json(analysis: DesignAnalysis) -> dict[str, Any]:
    palettes: dict[str, list[dict[str, Any]]] = {}
    for role in PALETTE_ROLES:
        counter = analysis.roles.get(role)
        if not counter or sum(counter.values()) < MIN_ROLE_CELLS:
            continue
        palettes[role] = [
            {"block": block, "weight": weight} for block, weight in analysis.palette(role)
        ]
    return {"palettes": palettes}


def render_preset(
    name: str,
    analysis: DesignAnalysis,
    *,
    source: str,
    parts: list[PartInfo] | None = None,
    reference: PartInfo | None = None,
    views: bool = True,
) -> str:
    a = analysis
    size = a.size
    lines: list[str] = [f"# {name}", ""]
    lines.append(
        f"> `mcblueprint design` が `{source}` から推定した生成物。Palette と数値は元の建物の実測、"
        "文章はひな形なので、用途や禁止事項を書き足し、間違った推定は直して使う。"
    )
    lines += ["", "## 概要", ""]
    lines.append(_summary_sentence(a))
    lines.append("")
    lines.append("向いている建物: （書き足す）")
    lines += [
        "",
        "## Palette",
        "",
        "```json",
        json.dumps(palettes_json(a), ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    lines.append(
        "- 向き（`facing` / `half`）は Operation が付けるので Palette には書いていない。"
        "原木の `axis` だけ残している。"
    )
    lines += ["", "## 構造ルール", ""]
    lines += _structure_rules(a)
    lines += ["", "## 寸法の目安", "", "| 建物 | 幅 × 奥行き × 高さ | 階数 |", "|---|---|---|"]
    storeys = max(1, len(a.floor_levels))
    lines.append(f"| 元の建物（{source}） | {size.x} × {size.z} × {size.y} | {storeys} |")
    lines += ["", "## 装飾", ""]
    lines += _decoration_lines(a)
    if parts or reference:
        lines += ["", "## 部品", ""]
        if parts:
            lines += ["| 名前 | 大きさ | 内容 |", "|---|---|---|"]
            for part in parts:
                size_text = f"{part.size.x} × {part.size.y} × {part.size.z}"
                lines.append(f"| `{part.name}` | {size_text} | {part.description or ''} |")
            lines.append("")
            first = parts[0]
            lines.append("`component` Operation で配置する（`rotation` で向きを変える）:")
            lines.append("")
            lines.append("```json")
            lines.append(
                json.dumps(
                    {"type": "component", "name": first.name, "position": [0, 1, 0]},
                    ensure_ascii=False,
                )
            )
            lines.append("```")
        if reference:
            lines.append("")
            lines.append(
                f"- 元の建物全体は部品 `{reference.name}`（{reference.path}、"
                f"{reference.size.x} × {reference.size.y} × {reference.size.z}）として置いてある。"
                "そのまま配置するか、`mcblueprint preview` の断面で作りを確かめる。"
            )
    lines += ["", "## 禁止事項", "", "- （書き足す。使わないブロック、崩れやすい構成）"]
    if views:
        view_lines = _views(a)
        if view_lines:
            lines += ["", "## 参考図", ""]
            lines += view_lines
    return "\n".join(lines).rstrip() + "\n"


def _summary_sentence(a: DesignAnalysis) -> str:
    size = a.size
    parts = [f"{size.x} × {size.z} × {size.y} の建物"]
    wall = a.top("wall")
    if wall:
        parts.append(f"壁は `{short(wall)}`")
    if a.roof:
        style = {"gable": "切妻", "hip": "寄棟", "flat": "陸屋根"}.get(a.roof.style, a.roof.style)
        parts.append(f"屋根は `{short(a.roof.block)}` の{style}")
    post = a.top("post")
    if post:
        parts.append(f"角に `{short(post)}` の柱")
    storeys = max(1, len(a.floor_levels))
    parts.append(f"{storeys} 階建て" if storeys > 1 else "平屋")
    return "、".join(parts) + "。"


def _structure_rules(a: DesignAnalysis) -> list[str]:
    lines: list[str] = []
    base = a.floor_levels[0] if a.floor_levels else a.bounds.min.y
    if a.roles.get("foundation"):
        lines.append(
            "- **土台**: `foundation` で 1 段。1 階の床はこの土台と同じ高さ（ドア下段の 1 つ下）。"
        )
    wall_bits = []
    if a.wall_thickness:
        wall_bits.append(f"厚さ {a.wall_thickness}")
    if a.wall_height:
        wall_bits.append(f"高さ {a.wall_height}（床の 1 つ上から {a.wall_height} 段）")
    lines.append(
        f"- **壁**: `wall` の Palette。{'、'.join(wall_bits) if wall_bits else ''}".rstrip("。 ")
    )
    post = a.top("post")
    if post and sum(a.roles["post"].values()) >= MIN_ROLE_CELLS:
        lines.append(
            f"- **柱**: 外周の角に `{short(post)}`（`wall` で `from == to`、または `pillar`）。"
            "壁と同じ高さ。"
        )
    beam = a.top("beam")
    if beam and sum(a.roles["beam"].values()) >= MIN_ROLE_CELLS:
        lines.append(
            f"- **梁**: `{short(beam)}` を水平に渡す（`line` / `fill`、`axis` は向きに合わせる）。"
        )
    if a.storey_heights:
        floors = ", ".join(str(y - base) for y in a.floor_levels)
        heights = "/".join(str(h) for h in a.storey_heights)
        lines.append(
            f"- **階高**: {heights}（床の高さは 1 階を 0 として {floors}）。"
            "各階に `floor` を張り、`stairs` / `spiral_stairs` でつなぐ。"
        )
    elif a.wall_height:
        lines.append(f"- **階高**: 平屋。壁 {a.wall_height} 段。")
    if a.roof:
        r = a.roof
        bits = [f'`style: "{r.style}"`']
        if r.ridge:
            bits.append(f'`ridge: "{r.ridge}"`')
        bits.append(f"`overhang: {r.overhang}`")
        bits.append(f'`block: "{short(r.block)}"`')
        if r.gable_block:
            bits.append(f'`gable: "{short(r.gable_block)}"`')
        if r.ridge_block:
            bits.append(f'`ridgeBlock: "{short(r.ridge_block)}"`')
        lines.append(
            f"- **屋根**: `roof` に {', '.join(bits)}。`from` / `to` は壁の最上段。"
            f"屋根の高さは {r.rise}。"
        )
    if a.windows:
        w = a.windows
        spacing = f"、間隔 {w.spacing}" if w.spacing is not None else ""
        lines.append(
            f"- **窓**: `window` に `{short(w.block)}`、幅 {w.width} × 高さ {w.height}、"
            f"床から {w.sill}{spacing}（元の建物に {w.count} 箇所）。"
        )
    if a.doors:
        door = a.doors.most_common(1)[0][0]
        lines.append(
            f"- **入口**: `doorway` に `{short(door)}`（{a.door_count} 箇所）。"
            "ドア下段は床の 1 つ上。"
        )
    if a.lights:
        light = a.lights.most_common(1)[0][0]
        lines.append(
            f"- **照明**: `{short(light)}` を {sum(a.lights.values())} 個。"
            "支持のあるブロックの上か、完全ブロックの下に吊る。"
        )
    return lines


def _decoration_lines(a: DesignAnalysis) -> list[str]:
    lines = []
    for block, count in a.lights.most_common(4):
        lines.append(f"- `{short(block)}` × {count}（置き場所: 書き足す）")
    for block, count in a.decoration.most_common(6):
        lines.append(f"- `{short(block)}` × {count}")
    if not lines:
        lines.append("- （元の建物に装飾はない。ランタン・鉢植え・旗などを書き足す）")
    return lines


def _views(a: DesignAnalysis) -> list[str]:
    size = a.size
    if size.x > MAX_VIEW_WIDTH or size.z > MAX_VIEW_HEIGHT or size.y > MAX_VIEW_HEIGHT:
        return []
    roles = a.role_map
    lo, hi = a.bounds.min, a.bounds.max
    legend = " ".join(f"{sym}={ROLE_LABELS[r]}" for r, sym in VIEW_SYMBOLS.items() if r in a.roles)
    lines = [
        f"記号: {legend}",
        "",
        "平面図（上から。各列の最上段のブロック。上が北 = -z）",
        "",
        "```text",
    ]
    for z in range(lo.z, hi.z + 1):
        row = ""
        for x in range(lo.x, hi.x + 1):
            top = None
            for y in range(hi.y, lo.y - 1, -1):
                role = roles.get(Vec3(x, y, z))
                if role is not None:
                    top = role
                    break
            row += VIEW_SYMBOLS.get(top, " ") if top else " "
        lines.append(row.rstrip())
    lines += ["```", "", "正面（南から見た立面。手前のブロック）", "", "```text"]
    for y in range(hi.y, lo.y - 1, -1):
        row = ""
        for x in range(lo.x, hi.x + 1):
            front = None
            for z in range(hi.z, lo.z - 1, -1):
                role = roles.get(Vec3(x, y, z))
                if role is not None:
                    front = role
                    break
            row += VIEW_SYMBOLS.get(front, " ") if front else " "
        lines.append(row.rstrip())
    lines.append("```")
    return lines
