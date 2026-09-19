# modern — モダン

## 概要

直線的で装飾の少ない現代建築の様式。住宅、オフィス、駅、橋に向く。白と灰色のコンクリートに大きなガラス面、陸屋根（平らな屋根）、片持ちの張り出しが特徴。

## Palette

```json
{
  "palettes": {
    "concrete": [
      { "block": "minecraft:white_concrete", "weight": 70 },
      { "block": "minecraft:light_gray_concrete", "weight": 30 }
    ],
    "dark_concrete": [
      { "block": "minecraft:gray_concrete", "weight": 70 },
      { "block": "minecraft:black_concrete", "weight": 30 }
    ],
    "floor": [
      { "block": "minecraft:smooth_quartz", "weight": 70 },
      { "block": "minecraft:quartz_block", "weight": 30 }
    ],
    "deck": [
      { "block": "minecraft:stripped_oak_wood[axis=x]", "weight": 100 }
    ],
    "foundation": [
      { "block": "minecraft:polished_andesite", "weight": 70 },
      { "block": "minecraft:andesite", "weight": 30 }
    ]
  }
}
```

- ガラス面は `window` に `glass`（ブロック）または `light_gray_stained_glass` を使い、幅 3〜6、高さ 2〜3 と大きく取る。
- アクセントに `stripped_oak_wood` / `stripped_spruce_wood` の木部を 1 面だけ使う。

## 構造ルール

- **土台**: `foundation` で 1 段、建物の外周より 1 ブロック広く。
- **壁**: `concrete` 厚さ 1。1 面は `dark_concrete` にして塊の対比を作る。
- **階高**: 4（室内 3）。吹き抜けは 2 階分。
- **屋根**: `floor` で平らに（`roof` は使わない）。屋根の縁に `smooth_quartz_slab[type=bottom]` のパラペットを 1 周。
- **張り出し**: 2 階を 1 階より 2〜3 ブロック張り出させ、下を `pillar`（`polished_andesite` または `stripped_oak_wood`）で支える。
- **窓**: `window` に `glass`、床から 1 ブロック上に高さ 2〜3。角を回り込む窓は `axis` を変えて 2 つ置く。
- **入口**: `doorway` に `iron_door` は開かないので `glass`（`window`）で囲った `dark_oak_door` か、幅 2 の開口のみ。
- **階段**: `stairs` に `smooth_quartz` か `stairs` の `block` に `quartz_stairs`。手すりは `iron_bars`（`window` の `block` に指定すると接続が付く）。
- **デッキ・バルコニー**: `deck` を張り、縁に `iron_bars` の手すり。

## 寸法の目安

| 建物 | 幅 × 奥行き × 高さ |
|---|---|
| 住宅（2 階建て） | 13〜17 × 9〜13 × 9〜10 |
| オフィス | 15〜25 × 15〜25 × 12〜20（3〜5 階） |
| 駅・ホール | 20〜30 × 10〜15 × 6〜8 |

## 装飾

- `sea_lantern` または `end_rod` を天井に埋め込む（`end_rod` は真上の完全ブロックに付ける）。
- `flower_pot` は床（完全ブロック）の上、`azalea` の植栽は `dirt` の上に。
- 外構に `smooth_stone_slab` の通路と `water` の細い池（囲いの中だけ）。

## 禁止事項

- 石レンガ、丸石、原木の露出、階段ブロックの屋根。
- 小さな窓を多数並べない（大きな面で少数）。
- 装飾の多用（1 面につきアクセント 1 つまで）。
