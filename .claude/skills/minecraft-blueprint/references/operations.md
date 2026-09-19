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

## 建築部品（内部で基本 Operation に展開。階段系は頭上空間と到着口を自動で空ける）

| type | 必須 | 任意 | 動作 |
|---|---|---|---|
| `stairs` | `start`（1 段目 = 下の階の床の 1 つ上）, `direction`, `height`（段数 = 登る高さ）, `block` / `palette` | `width`(1), `headroom`(3), `base` | 直進階段。各段の上 `headroom` ブロックと到着口を空気にする。最後の段は上の階の床と同じ高さ |
| `spiral_stairs` | `center`, `radius`(1〜8), `height`, `block` / `palette` | `turn`(clockwise), `headroom`(3), `column` | 螺旋階段。1 周で半径 1: 8 段、半径 2: 12 段、半径 3: 16 段 |
| `roof` | `from`, `to`（軒の高さの矩形 = 壁の外周）, `block` / `palette` | `style`(gable / hip), `ridge`(x / z), `overhang`(1), `gable`（妻壁のブロック）, `ridgeBlock` | 階段ブロックで屋根。`*_stairs` なら向きと寄棟の角の `shape` は自動 |
| `pillar` | `position`, `height`, `block` / `palette` | `base`, `cap` | 柱 |
| `doorway` | `position`（開口の左下）, `facing`（ドアの facing。北の壁なら `south`） | `width`(1), `height`(2), `door`（`oak_door` など）, `arch`（`{ "style", "block", "trim" }`） | 開口を空けてドアを 2 段置く。幅 2 で両開き。`arch` で頭上をアーチにする。`depth` で厚い壁を貫通 |
| `window` | `position`, `axis`（壁の向き x / z） | `width`(1), `height`(1), `block`(glass_pane), `arch` | 接続プロパティ付きのガラス板を置く。`arch` でアーチ窓 |
| `arch` | `position`（開口の左下）, `width`, `height`（開口の高さ。頂点まで）, `block` / `palette` | `axis`(x), `style`(round / pointed / flat), `depth`(1), `trim`（角の逆さ階段）, `fill`（開口を埋めるブロック）, `hollow`(true) | 開口の周りに厚さ 1 の縁を作り開口を空ける。`round` は幅 3 で高さ 2 以上、幅 5 で 3 以上、幅 7 で 4 以上。`pointed` は幅 3 で 3 以上、幅 5 で 5 以上 |
| `room` | `from`, `to`（外寸。`from.y` = 床の層、`to.y` = 天井の層）, `wall`（ブロックか `{ "palette" }`） | `floor`, `ceiling`, `corners`（四隅の柱）, `thickness`(1), `interior`(true), `doors`（`[{ side, offset, width, height, door, arch }]`）, `windows`（`[{ side, offset, width, height, sill(2), count, spacing(2), block, arch }]`） | 1 階分の床・壁・天井とドア・窓をまとめて作る。`offset` 省略で中央。ドア下段は自動で床の 1 つ上 |

```json
{ "type": "stairs", "start": [2, 1, 1], "direction": "south", "height": 4, "block": "oak_stairs", "base": "oak_planks" }
```

```json
{ "type": "roof", "from": [0, 5, 0], "to": [10, 5, 8], "block": "dark_oak_stairs", "gable": "spruce_planks" }
```

```json
{ "type": "doorway", "position": [5, 1, 0], "facing": "south", "width": 3, "height": 3, "arch": { "style": "round", "block": "stone_bricks", "trim": "stone_brick_stairs" } }
```

```json
{ "type": "room", "from": [0, 0, 0], "to": [10, 5, 8], "wall": { "palette": "plaster" }, "floor": "stone_bricks", "corners": "oak_log",
  "doors": [ { "side": "north", "door": "oak_door" } ],
  "windows": [ { "side": "north", "count": 2, "spacing": 5, "height": 2 }, { "side": "south", "count": 3, "height": 2 } ] }
```

## 部品（`components/<name>.json`）

| type | 必須 | 任意 | 動作 |
|---|---|---|---|
| `component` | `name`（`components/` のファイル名）, `position` | `rotation`(0 / 90 / 180 / 270) | 部品の原点を `position` に置いて配置。向きは自動で回る |

同梱部品は `components/README.md` を見る（`lantern_post`, `medieval_window`, `arched_gate` など）。同じ部品を何度も使うときや、依頼者が部品を用意しているときに使う。新しい部品を作るときは `components/<name>.json` に Blueprint と同じ書式で書く（`minecraftVersion` / `origin` / `size` / `seed` は不要、座標は `[0,0,0]` 基準）。

```json
{ "type": "component", "name": "medieval_window", "position": [1, 2, 0] }
```

## よくある組み合わせ

| 作りたいもの | 書き方 |
|---|---|
| 部屋（外壁 + 床 + 天井 + ドア・窓） | `room` 1 つ（`doors` / `windows` で開口）。装飾のない箱なら `box`（hollow） |
| 家 | `room` + `roof`（`roof` の `from` / `to` は `room` の `to.y` の高さ）。`examples/cottage.json` |
| 上の階へ行く階段 | `stairs`（直進）または `spiral_stairs`。頭上と到着口は自動 |
| 切妻屋根 | `roof`（`gable` に妻壁のブロック） |
| 中身が空の建物 | `fill` で全体 → `fill` で内側を `air` |
| 窓を等間隔に並べる | `repeat` の中に `set`（`air` またはガラス） |
| 左右対称の建物 | 片側を書いて `mirror` |
| 四方に同じ部品（塔の 4 隅など） | 部品を 1 つ書き、`rotate` 90 / 180 / 270 で残り 3 つ |
| 同じ階を積む | 1 階を作って `copy` で `offset: [0, 階高, 0]` |
| 壁に質感を後付け | 壁を単色で作って `replace` で Palette に置き換え |
| 塔 | `cylinder`（hollow）+ `repeat` で各階の `circle`（solid）床 |
| ドーム | `sphere`（hollow）→ 下半分を `fill` で `air` |
| 柱 | `wall` で `from == to`、または `fill` の 1 列 |
| 出入口 | `doorway`（`door` を指定すればドア付き） |
| 窓 | `window`（接続は自動） |
| 門・アーチ窓 | `doorway` / `window` に `arch`。単独の縁だけなら `arch` |
| 回廊・橋脚 | `arch` を `repeat` で並べる（`depth` で奥行き） |
