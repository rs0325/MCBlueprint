# Operation 早見表

正本は `docs/OPERATIONS.md`。すべての配置系 Operation は `block` または `palette` のどちらか一方と、任意の `comment` を取る。
`mode` は `"hollow"`（中空、既定）か `"solid"`（充填）。

## 基本

| type | 必須 | 任意 | 生成されるもの |
|---|---|---|---|
| `set` | `position` | | 1 ブロック |
| `fill` | `from`, `to` | | 直方体（充填） |
| `box` | `from`, `to` | `mode` | 直方体。`hollow` は 6 面 1 ブロック厚の殻 |
| `wall` | `from`, `to`（同じ y）, `height` | `thickness`(1) | `from`/`to` が X または Z を共有すれば直線の壁、そうでなければ矩形の外周壁。y から上へ `height` 段 |
| `floor` | `from`, `to`（同じ y） | | 1 段の平面。天井にも使う |
| `line` | `from`, `to` | | 2 点を結ぶ線（斜めも可） |

## 図形

| type | 必須 | 任意 | 生成されるもの |
|---|---|---|---|
| `circle` | `center`, `radius` | `axis`(`y`), `mode` | `axis` に垂直な円。`hollow` はリング、`solid` は円盤 |
| `cylinder` | `center`（底面中心）, `radius`, `height` | `axis`(`y`), `mode` | 円柱。`hollow` は側面のみ（底・天井なし） |
| `sphere` | `center`, `radius` | `mode` | 球。`hollow` は球殻 |

- `hollow` の円・球は常に 1 ブロック厚で隙間がない。
- 直径 D の塔は `radius = (D - 1) / 2`（奇数直径）。偶数直径は作れないので 1 大きい奇数にする。

## 構造（ネスト）

`block` / `palette` は持たず、`operations` に任意の Operation を入れる（深さ 8 まで）。

| type | 必須 | 任意 | 動作 |
|---|---|---|---|
| `mirror` | `axis`, `at`, `operations` | `keepOriginal`(true) | `operations` を実行し、`axis = at` の平面で鏡像化したものも実行。`at` は `.5` 可（例 `4.5` で 4 と 5 の間）。`facing` / 接続 / `shape` / `hinge` は自動で反転 |
| `repeat` | `count`(1〜512), `offset`, `operations` | | `operations` を `count` 回、`offset × i` ずつずらして実行 |
| `translate` | `offset`, `operations` | | `operations` を `offset` だけ平行移動して実行 |
| `rotate` | `angle`(90/180/270), `center`, `operations` | | `operations` を `center` を通る鉛直軸まわりに時計回りで回転して実行。`facing` / `axis` / 接続も回る |

```json
{
  "type": "repeat",
  "count": 4,
  "offset": [0, 5, 0],
  "operations": [
    { "type": "floor", "from": [-4, 1, -4], "to": [4, 1, 4], "block": "oak_planks" },
    { "type": "set", "position": [5, 3, 0], "block": "glass_pane[north=true,south=true]" }
  ]
}
```

```json
{
  "type": "mirror",
  "axis": "z",
  "at": 4,
  "operations": [
    { "type": "repeat", "count": 4, "offset": [0, 1, 1], "operations": [
      { "type": "fill", "from": [-1, 5, -1], "to": [11, 5, -1], "block": "dark_oak_stairs[facing=south]" }
    ] }
  ]
}
```

（北側の斜面を 4 段作り、`z = 4` で南側へ鏡像 → 切妻屋根）

## 編集（配置済みの結果を読んで動作。順序が重要）

| type | 必須 | 動作 |
|---|---|---|
| `replace` | `from`, `to`, `match`（ブロック文字列または配列）, `block` / `palette` | 範囲内で `match` に一致するブロックを置き換える。`match` にプロパティを書かなければ ID だけで一致。未設定セルは `air` として扱う |
| `copy` | `from`, `to`, `offset` | 範囲の現在の内容を `offset` だけずらした位置へ複製（配置済みセルのみ、向きはそのまま） |

```json
{ "type": "replace", "from": [0, 1, 0], "to": [10, 5, 8], "match": "white_terracotta", "palette": "plaster" }
```

## よくある組み合わせ

| 作りたいもの | 書き方 |
|---|---|
| 部屋（外壁 + 床 + 天井） | `box`（hollow）1 つ。または `floor` + `wall` + `floor` |
| 中身が空の建物 | `fill` で全体 → `fill` で内側を `air` |
| 窓を等間隔に並べる | `repeat` の中に `set`（`air` またはガラス） |
| 左右対称の建物 | 片側を書いて `mirror` |
| 四方に同じ部品（塔の 4 隅など） | 部品を 1 つ書き、`rotate` 90 / 180 / 270 で残り 3 つ |
| 同じ階を積む | 1 階を作って `copy` で `offset: [0, 階高, 0]` |
| 壁に質感を後付け | 壁を単色で作って `replace` で Palette に置き換え |
| 塔 | `cylinder`（hollow）+ `repeat` で各階の `circle`（solid）床 |
| ドーム | `sphere`（hollow）→ 下半分を `fill` で `air` |
| 柱 | `wall` で `from == to`、または `fill` の 1 列 |
| 出入口 | 壁の後に `set` で `air` を 2 段、その後ドアを 2 段（`half=lower` / `upper`） |
