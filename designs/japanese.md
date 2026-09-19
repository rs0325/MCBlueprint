# japanese — 和風

## 概要

木造の日本家屋の様式。平屋・町家・寺社・門・塀に向く。白い漆喰の壁に濃い木の柱と梁、勾配の緩い瓦屋根、縁側と格子が特徴。

## Palette

```json
{
  "palettes": {
    "plaster": [
      { "block": "minecraft:white_concrete", "weight": 70 },
      { "block": "minecraft:white_terracotta", "weight": 30 }
    ],
    "timber": [
      { "block": "minecraft:dark_oak_planks", "weight": 80 },
      { "block": "minecraft:spruce_planks", "weight": 20 }
    ],
    "floor": [
      { "block": "minecraft:spruce_planks", "weight": 70 },
      { "block": "minecraft:stripped_spruce_wood[axis=y]", "weight": 30 }
    ],
    "foundation": [
      { "block": "minecraft:stone", "weight": 50 },
      { "block": "minecraft:andesite", "weight": 30 },
      { "block": "minecraft:cobblestone", "weight": 20 }
    ],
    "gravel_garden": [
      { "block": "minecraft:gravel", "weight": 80 },
      { "block": "minecraft:andesite", "weight": 20 }
    ]
  }
}
```

- 瓦屋根は `roof` に `"block": "deepslate_tile_stairs"` を渡す（濃い灰色）。茅葺きなら `spruce_stairs`。
- 畳風の床は `green_wool` と `moss_carpet`（カーペットは床の上に置く）。

## 構造ルール

- **土台**: `foundation` で 1 段。建物は土台より 1 ブロック内側に建て、周囲に `gravel_garden` の砂利を敷く。
- **柱**: 外周の角と 3〜4 ブロックおきに `dark_oak_log` の `pillar`（高さは壁と同じ）。柱の間を `plaster` で埋める。
- **階高**: 平屋は壁 4（室内 3）。2 階建ては 4 + 4。
- **屋根**: `roof` の `gable` または `hip`、`overhang: 2`（深い軒が和風の要）。妻壁は `timber`。屋根の下に `dark_oak_slab[type=top]` の軒天を 1 周。
- **縁側**: 南面に幅 1〜2 の `spruce_slab[type=bottom]` を床と同じ高さで張り出させる。
- **窓**: `window` に `oak_fence` または `dark_oak_fence`（格子）、幅 2〜3、高さ 2。ガラスは使わない。
- **入口**: `doorway` に `spruce_door` または `dark_oak_door`。門は `pillar` 2 本と `dark_oak_slab` の屋根。
- **塀**: `cobblestone` の腰壁 1 段 + `plaster` 2 段 + `dark_oak_slab[type=bottom]` の笠。

## 寸法の目安

| 建物 | 幅 × 奥行き × 高さ |
|---|---|
| 平屋 | 11〜15 × 7〜11 × 8〜10 |
| 町家（2 階建て） | 7〜9 × 11〜15 × 11〜13 |
| 門 | 幅 5〜7 × 奥行き 3 × 高さ 5〜6 |
| 塀 | 高さ 4 |

## 装飾

- 入口の脇に `lantern` を `dark_oak_fence` の柱の上に置く（吊るなら真上は完全ブロック）。
- 庭に `stone` の飛び石（`set` を点々と）、`azalea_leaves` や `bamboo` の植栽（竹は土の上）。
- 屋内は `dark_oak_trapdoor[half=top]` の欄間、`bookshelf` の棚。

## 禁止事項

- 石レンガ・レンガ・コンクリートの原色（漆喰は白のみ）。
- 急勾配の切妻や尖塔。
- ガラス板の窓（格子を使う）。
