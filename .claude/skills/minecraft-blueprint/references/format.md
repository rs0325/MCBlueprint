# Blueprint JSON 早見表

正本は `docs/FORMAT.md`。ここでは書くのに必要な要点だけをまとめる。

## 骨格

```json
{
  "formatVersion": 1,
  "minecraftVersion": "1.21.11",
  "name": "medieval_tower",
  "description": "何を作ったか、置いた前提",
  "seed": 0,
  "origin": [0, 0, 0],
  "size": [21, 40, 21],
  "palettes": {
    "stone_wall": [
      { "block": "minecraft:stone_bricks", "weight": 70 },
      { "block": "minecraft:mossy_stone_bricks", "weight": 20 },
      { "block": "minecraft:cracked_stone_bricks", "weight": 10 }
    ]
  },
  "operations": [
    { "type": "cylinder", "center": [0, 0, 0], "radius": 10, "height": 40, "mode": "hollow", "palette": "stone_wall" }
  ]
}
```

| キー | 必須 | 意味 |
|---|---|---|
| `formatVersion` | ✓ | 常に `1` |
| `minecraftVersion` | ✓ | 対象バージョン。同梱データがあるもののみ（現在 `1.21.11`） |
| `name` | ✓ | 表示名 |
| `operations` | ✓ | 配列順に適用。後の Operation が前を上書きする |
| `seed` | | Palette の乱数 seed。既定 `0`。同じ seed なら同じ結果 |
| `origin` | | 貼り付け基準点（`//paste` でプレイヤー位置に来る Blueprint 座標）。既定 `[0,0,0]` |
| `size` | | 最大サイズ `[幅X, 高さY, 奥行きZ]`。超えると検証エラー。位置は問わない |
| `palettes` | | 名前 → `{block, weight}` の配列。`weight` 既定 1 |
| `description` / `author` / `metadata` | | 任意。`metadata` は自由なオブジェクト |

上記以外のキー、Operation に定義されていないキーはすべてエラーになる。

## 座標

- Minecraft と同じ: X 東が正、Y 上が正、Z 南が正。整数のみ。負の値も可。
- `from` / `to` は両端を含み、順序は問わない。
- 建物は `origin` を基準に置くと貼り付けやすい（例: 入口の足元を `[0, 0, 0]`）。

## ブロック指定

- `"minecraft:stone_bricks"`、`"stone_bricks"`（`minecraft:` は省略可）
- 状態付き: `"oak_stairs[facing=north,half=top]"`、`"oak_slab[type=top]"`、`"oak_log[axis=x]"`
- 指定しなかったプロパティは Minecraft のデフォルト値になる。
- `"minecraft:air"` を置くと消去できる。
- Operation では `block` か `palette` のどちらか一方だけを指定する。

## よく使うプロパティ

| ブロック | プロパティ | 例 |
|---|---|---|
| 階段 `*_stairs` | `facing`（登る方向 = 高い側）, `half`（`bottom` / `top`）, `shape` | 北向き屋根の斜面は `facing=south` |
| ハーフブロック `*_slab` | `type`（`bottom` / `top` / `double`） | |
| ドア `*_door` | `facing`, `half`（`lower` / `upper`）, `hinge`（`left` / `right`） | 2 段とも置く |
| 原木 `*_log` | `axis`（`x` / `y` / `z`） | 梁は `axis=x` など |
| ガラス板・フェンス・壁 | `north` / `south` / `east` / `west`（`true` / `false`） | 隣とつなぐ方向を `true` |
| トラップドア | `facing`, `half`, `open` | |
| ランタン | `hanging` | |

## 検証エラーの読み方

```text
ERROR operations[4] (cylinder)
  'radius' must be >= 1.
  Current value: -5
```

- 1 行目: 場所（`operations` 配列の index。ネストは `operations[2].operations[0]`）と Operation の種類
- 2 行目: 原因
- 3 行目: 問題の値

すべてのエラーがまとめて表示される。上から順に直す。

`Blueprint is valid.` の後に `WARNING` が出ることがある。支持のないランタン・松明・壁付けブロック・ドア・草花などで、貼り付けると落ちて消える。

```text
WARNING [3, 5, 2] minecraft:lantern[hanging=true]
  Needs a solid block above; found minecraft:oak_slab[type=top].
```

座標は Blueprint 座標、`found` は支持先にあったブロック。警告も 0 件にしてから build する。
