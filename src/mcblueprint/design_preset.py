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
ROOF_STYLE_LABELS = {
    "gable": "切妻",
    "hip": "寄棟",
    "flat": "陸屋根",
    "dome": "ドーム",
    "cone": "円錐",
    "stepped": "段積み",
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
    kind: str | None = None  # window | door for parts cut out of the build
    count: int = 0


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
    lines += _structure_rules(a, parts)
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
            if any(part.kind for part in parts):
                lines.append("")
                lines.append(
                    "- 建物から切り出した窓・入口の部品は外側が北（-z）を向くように正規化してある。"
                    "北面の壁はそのまま、東面は `rotation: 90`、南面は `180`、西面は `270` で置く。"
                    "原点は部品の最小コーナー（窓・ドアの位置は部品の説明にある）。"
                )
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
    shape = {
        "rectangle": "",
        "round": f"円形（半径 {a.radius}）の",
        "irregular": "不定形（L 字など）の",
    }
    parts = [f"{size.x} × {size.z} × {size.y} の{shape.get(a.shape, '')}建物"]
    wall = a.top("wall")
    if wall:
        parts.append(f"壁は `{short(wall)}`")
    if a.roof:
        style = ROOF_STYLE_LABELS.get(a.roof.style, a.roof.style)
        parts.append(f"屋根は `{short(a.roof.block)}` の{style}")
    post = a.top("post")
    if post:
        parts.append(f"角に `{short(post)}` の柱")
    storeys = max(1, len(a.floor_levels))
    parts.append(f"{storeys} 階建て" if storeys > 1 else "平屋")
    return "、".join(parts) + "。"


def _part_hint(parts: list[PartInfo] | None, kind: str) -> str:
    names = [part for part in (parts or []) if part.kind == kind]
    if not names:
        return ""
    listed = "、".join(f"`{part.name}`（{part.count} 箇所）" for part in names)
    return f"枠や飾りは部品 {listed} を `component` で置く（`## 部品`）。"


def _structure_rules(a: DesignAnalysis, parts: list[PartInfo] | None = None) -> list[str]:
    lines: list[str] = []
    base = a.floor_levels[0] if a.floor_levels else a.bounds.min.y
    if a.roles.get("foundation"):
        lines.append(
            "- **土台**: `foundation` で 1 段。1 階の床はこの土台と同じ高さ（ドア下段の 1 つ下）。"
        )
    if a.shape == "round":
        lines.append(
            f"- **外形**: 円形、外壁の半径 {a.radius}"
            "（`tower` の `radius`、または `cylinder` の hollow）。"
        )
    elif a.shape == "irregular":
        lines.append(
            "- **外形**: 矩形ではない（L 字など）。参考図の平面図に合わせて `wall` を分けて書く。"
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
    if a.roof and a.roof.style in ("dome", "cone", "stepped"):
        r = a.roof
        how = {
            "dome": f"`sphere`（hollow、半径 {r.radius}）の上半分を屋上に載せ、"
            "下半分を `fill` の `air` で消す",
            "cone": f"`circle`（solid）を半径 {r.radius} から 1 段ごとに 1 ずつ縮めて積む",
            "stepped": "`fill` を 1 段ごとに内側へ縮めて積む（`roof` の `hip` でも近い形になる）",
        }[r.style]
        lines.append(
            f"- **屋根**: `{short(r.block)}` の{ROOF_STYLE_LABELS[r.style]}、高さ {r.rise}、"
            f"張り出し {r.overhang}。{how}。"
        )
    elif a.roof:
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
    lines += _wall_decor_lines(a)
    if a.windows:
        w = a.windows
        spacing = f"、間隔 {w.spacing}" if w.spacing is not None else ""
        lines.append(
            f"- **窓**: `window` に `{short(w.block)}`、幅 {w.width} × 高さ {w.height}、"
            f"床から {w.sill}{spacing}（元の建物に {w.count} 箇所）。" + _part_hint(parts, "window")
        )
    if a.doors:
        door = a.doors.most_common(1)[0][0]
        lines.append(
            f"- **入口**: `doorway` に `{short(door)}`（{a.door_count} 箇所）。"
            "ドア下段は床の 1 つ上。" + _part_hint(parts, "door")
        )
    if a.lights:
        light = a.lights.most_common(1)[0][0]
        lines.append(
            f"- **照明**: `{short(light)}` を {sum(a.lights.values())} 個。"
            "支持のあるブロックの上か、完全ブロックの下に吊る。"
        )
    return lines


def _wall_decor_lines(a: DesignAnalysis) -> list[str]:
    d = a.walls
    if d is None:
        return []
    bits: list[str] = []
    for band in d.bands:
        bits.append(f"床から {band.height} 段目は `{short(band.block)}` の帯（`fill` で 1 周）")
    for trim in d.trims:
        bits.append(
            f"床から {trim.height} 段目の外側に `{short(trim.block)}` を 1 周"
            f"（壁の外に張り出す飾り。周囲の {round(trim.coverage * 100)}%）"
        )
    if d.post_spacing:
        bits.append(f"柱は {d.post_spacing} ブロックおき（中心どうし）")
    if d.beam_heights:
        heights = ", ".join(str(h) for h in d.beam_heights)
        bits.append(f"床から {heights} 段目に水平の梁（木組み。間は `wall` の Palette で埋める）")
    if not bits:
        return []
    return [f"- **壁の装飾**: {'。'.join(bits)}。"]


def _decoration_lines(a: DesignAnalysis) -> list[str]:
    lines = []
    if a.walls is not None:
        for block, count in a.walls.items.most_common(6):
            lines.append(f"- `{short(block)}` × {count}（壁の外側に張り出す飾り）")
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
    lines = [f"記号: {legend}（上が北 = -z、左が西 = -x）", ""]
    floors = a.floor_levels or [lo.y]
    for index, floor in enumerate(floors, start=1):
        y = floor + 2  # window height: walls, windows and posts show up
        if y > hi.y:
            continue
        lines += [f"{index} 階の平面図（床の 2 段上 y={y}。ドアは 1 段上から）", "", "```text"]
        for z in range(lo.z, hi.z + 1):
            row = ""
            for x in range(lo.x, hi.x + 1):
                role = roles.get(Vec3(x, y, z))
                if roles.get(Vec3(x, y - 1, z)) == "door":
                    role = "door"
                row += VIEW_SYMBOLS.get(role, " ") if role else " "
            lines.append(row.rstrip())
        lines += ["```", ""]
    lines += ["屋根の平面図（上から。各列の最上段のブロック）", "", "```text"]
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
    lines += ["```", ""]
    for title, columns, depth in (
        ("南から見た立面（手前のブロック）", range(lo.x, hi.x + 1), "z"),
        ("東から見た立面（手前のブロック）", range(hi.z, lo.z - 1, -1), "x"),
    ):
        lines += [title, "", "```text"]
        for y in range(hi.y, lo.y - 1, -1):
            row = ""
            for c in columns:
                front = None
                if depth == "z":
                    scan = (Vec3(c, y, z) for z in range(hi.z, lo.z - 1, -1))
                else:
                    scan = (Vec3(x, y, c) for x in range(hi.x, lo.x - 1, -1))
                for pos in scan:
                    role = roles.get(pos)
                    if role is not None:
                        front = role
                        break
                row += VIEW_SYMBOLS.get(front, " ") if front else " "
            lines.append(row.rstrip())
        lines += ["```", ""]
    while lines and lines[-1] == "":
        lines.pop()
    return lines
