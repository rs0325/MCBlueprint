# medieval — 中世ヨーロッパ風

## 概要

石と木を組み合わせた中世ヨーロッパの村・城の様式。家、塔、城壁、教会、鍛冶屋、市場など幅広く使える。石は苔や割れを混ぜて古びた質感にし、木部は濃い色でコントラストを付ける。

## Palette

```json
{
  "palettes": {
    "stone_wall": [
      { "block": "minecraft:stone_bricks", "weight": 65 },
      { "block": "minecraft:mossy_stone_bricks", "weight": 20 },
      { "block": "minecraft:cracked_stone_bricks", "weight": 15 }
    ],
    "foundation": [
      { "block": "minecraft:cobblestone", "weight": 60 },
      { "block": "minecraft:mossy_cobblestone", "weight": 25 },
      { "block": "minecraft:andesite", "weight": 15 }
    ],
    "plaster": [
      { "block": "minecraft:white_terracotta", "weight": 80 },
      { "block": "minecraft:light_gray_terracotta", "weight": 20 }
    ],
    "timber": [
      { "block": "minecraft:dark_oak_planks", "weight": 70 },
      { "block": "minecraft:spruce_planks", "weight": 30 }
    ],
    "floor": [
      { "block": "minecraft:spruce_planks", "weight": 75 },
      { "block": "minecraft:dark_oak_planks", "weight": 25 }
    ],
    "roof_tile": [
      { "block": "minecraft:dark_oak_stairs[facing=south,half=bottom]", "weight": 100 }
    ]
  }
}
```

- 屋根は `roof` に `"block": "dark_oak_stairs"` を渡す（向きは自動）。Palette で屋根を作る場合は向きを自分で書く。
- 塔・城壁は `stone_wall`、民家の 2 階は `plaster` + `timber` の柱（ハーフティンバー）。

## 構造ルール

- **土台**: `foundation` で 1 段。地面と面一（`origin.y` を土台の 1 つ上にする）。
- **1 階の壁**: 石（`stone_wall`）、厚さ 1。角に `oak_log` または `dark_oak_log` の柱（`pillar`）。
- **2 階の壁**: 漆喰（`plaster`）に `timber` の柱と梁。1 階より 1 ブロック張り出させると中世らしい。
- **階高**: 床から次の床まで 4（室内空間 3）。塔は 5 ごとに床。
- **屋根**: `roof` の `gable`、`overhang: 1`、妻壁は `spruce_planks` または `plaster`。塔は `hip`（正方形なら方形）または円錐風に `circle` を縮めて積む。
- **窓**: `window` に `glass_pane`、幅 1〜2、高さ 2。2 階の窓は小さめ。
- **入口**: `doorway` に `oak_door` または `spruce_door`。大きな建物は幅 2 の両開き。
- **塔**: `cylinder`（hollow）+ `repeat` の `circle` 床。屋上は外壁より半径 +1 の床と胸壁（`stone_brick_wall` は接続が要るので `stone_bricks` の 1 段で可）。
- **城壁**: 厚さ 2〜3、高さ 8〜12、上に幅 1 の歩廊と 1 マスおきの胸壁（`repeat` で `set`）。

## 寸法の目安

| 建物 | 幅 × 奥行き × 高さ |
|---|---|
| 民家 | 9〜13 × 7〜11 × 10〜14（2 階建て） |
| 塔 | 直径 9〜15 × 高さ 20〜40 |
| 城壁 | 厚さ 2〜3 × 高さ 8〜12 |
| 教会・広間 | 15〜25 × 9〜13 × 12〜18 |

## 装飾

- ランタン（`lantern`）は入口の両脇の壁に付けた `dark_oak_fence` の下、または `pillar` の上。ハーフブロックには付けない。
- 窓の下に `dark_oak_stairs[half=top]` の飾り、軒下に `dark_oak_slab[type=top]`。
- 煙突は `bricks` の `pillar` に `campfire[lit=true]`（真下は完全ブロック）。
- 庭に `cobblestone_wall` の柵と `oak_fence` の門。

## 禁止事項

- 純白のコンクリート、ガラスブロックの多用、ネザーブロック（`crimson` / `warped`）は様式に合わない。
- 石だけ・木だけの単色の壁にしない（必ず Palette で混ぜる）。
- 屋根を平らにしない（陸屋根は使わない）。
