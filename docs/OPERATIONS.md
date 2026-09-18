# Operation 仕様（formatVersion 1）

Operation は Blueprint JSON の `operations` 配列に並べる建築の単位である。
共通項目（`type`, `block`, `palette`, `comment`）、座標系、適用順序、上限は [FORMAT.md](FORMAT.md) を参照。

本書が Operation の正本である。

## 目次

| 分類 | type | 概要 |
|---|---|---|
| 基本 | [`set`](#set) | 1 ブロックを配置 |
| 基本 | [`fill`](#fill) | 直方体を充填 |
| 基本 | [`box`](#box) | 直方体（中空 / 充填） |
| 基本 | [`wall`](#wall) | 壁（直線 / 矩形外周） |
| 基本 | [`floor`](#floor) | 1 段の床 |
| 基本 | [`line`](#line) | 2 点を結ぶ線 |
| 図形 | [`circle`](#circle) | 円（リング / 円盤） |
| 図形 | [`cylinder`](#cylinder) | 円柱（側面 / 充填） |
| 図形 | [`sphere`](#sphere) | 球（球殻 / 充填） |
| 構造 | [`mirror`](#mirror) | ネストした Operation を鏡像化 |
| 構造 | [`repeat`](#repeat) | ネストした Operation を繰り返し配置 |

## 共通の記法

- `Pos` は `[x, y, z]` の整数配列。
- `from` / `to` は両端を含み、順序は問わない。以下では `min = 要素ごとの min(from, to)`, `max = 要素ごとの max(from, to)` とする。
- `mode` を持つ Operation は `"hollow"`（中空）と `"solid"`（充填）のいずれかで、既定値は `"hollow"`。
- 各 Operation は「生成するセル集合」を定義する。セルの並び（配置順）は Palette の乱数消費順に影響するため、本書で定めた順序に従う。
- 「bounds」は、Operation を実行せずに求められる、生成セルをすべて含む直方体である。検証（`size`、最大寸法）に使う。

---

## 基本 Operation

### set

1 ブロックを配置する。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `position` | Pos | ✓ | 配置位置 |

```json
{ "type": "set", "position": [3, 1, 0], "block": "minecraft:oak_door[facing=north,half=lower]" }
```

- bounds: `position` の 1 セル。

### fill

直方体の範囲をすべて充填する。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `from` | Pos | ✓ | 一方の角 |
| `to` | Pos | ✓ | もう一方の角 |

```json
{ "type": "fill", "from": [0, 0, 0], "to": [9, 3, 9], "block": "minecraft:air" }
```

- セル: `min ≤ (x, y, z) ≤ max` のすべて。配置順は y → z → x の昇順（y が最外ループ）。
- bounds: `min` .. `max`。

### box

直方体を生成する。既定では 6 面 1 ブロック厚の中空。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `from` | Pos | ✓ | | 一方の角 |
| `to` | Pos | ✓ | | もう一方の角 |
| `mode` | `"hollow"` / `"solid"` | | `"hollow"` | `hollow`: 外周の面のみ。`solid`: `fill` と同じ |

```json
{ "type": "box", "from": [0, 0, 0], "to": [9, 4, 9], "mode": "hollow", "palette": "stone_wall" }
```

- `hollow` のセル: `min ≤ p ≤ max` かつ、いずれかの軸で `p == min` または `p == max`。
- 辺の長さが 1 または 2 の軸があると、その方向の内部は存在しないため `solid` と同じ結果になる。
- 配置順は `fill` と同じ。
- bounds: `min` .. `max`。

### wall

壁を生成する。`from` と `to` は同じ高さで指定し、その高さから上へ `height` 段積む。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `from` | Pos | ✓ | | 一方の端（底面） |
| `to` | Pos | ✓ | | もう一方の端（底面）。`from[1] == to[1]` が必須 |
| `height` | integer ≥ 1 | ✓ | | 高さ（段数） |
| `thickness` | integer ≥ 1 | | `1` | 壁の厚さ |

形状は `from` / `to` の位置関係で決まる。

| 条件 | 形状 |
|---|---|
| `from.x == to.x` または `from.z == to.z` | **直線の壁**。`from`–`to` を結ぶ 1 列の底面を `height` 段積む |
| それ以外 | **矩形の外周壁**。`from`–`to` を対角とする矩形の外周 1 列を `height` 段積む（内部は空） |

`thickness` が 2 以上のときの拡張方向:

- 直線の壁（X 方向、`from.z == to.z`）: +Z 方向へ `thickness − 1` 列追加。
- 直線の壁（Z 方向、`from.x == to.x`）: +X 方向へ `thickness − 1` 列追加。
- 矩形の外周壁: 内側へ `thickness − 1` 列追加。厚さが矩形の半分を超える場合は内部がすべて埋まる。

```json
{ "type": "wall", "from": [0, 0, 0], "to": [9, 0, 9], "height": 4, "palette": "stone_wall", "comment": "外周壁" }
```

```json
{ "type": "wall", "from": [0, 0, 5], "to": [9, 0, 5], "height": 4, "block": "minecraft:oak_planks", "comment": "仕切り壁" }
```

- 直線かつ `from == to` の場合は 1 列の柱になる。
- 配置順は y → z → x の昇順。
- bounds: 底面の矩形（`thickness` 拡張を含む）を `height` 段分持ち上げた直方体。

### floor

1 段の床を生成する。`fill` の高さ 1 版で、床であることを明示するために用意している。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `from` | Pos | ✓ | 一方の角 |
| `to` | Pos | ✓ | もう一方の角。`from[1] == to[1]` が必須 |

```json
{ "type": "floor", "from": [1, 0, 1], "to": [8, 0, 8], "block": "minecraft:oak_planks" }
```

- 天井も `floor` で作る（高さを天井の y にする）。
- 配置順は z → x の昇順。
- bounds: `min` .. `max`。

### line

2 点間をブロックで結ぶ。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `from` | Pos | ✓ | 始点 |
| `to` | Pos | ✓ | 終点 |

```json
{ "type": "line", "from": [0, 0, 0], "to": [10, 6, 3], "block": "minecraft:oak_fence" }
```

- 生成規則（3D DDA）: `d = to − from`、`n = max(|d.x|, |d.y|, |d.z|)` として、`i = 0..n` について `from + round(d × i / n)` を配置する。`round(v)` は `floor(v + 0.5)`。`n == 0` のときは `from` の 1 セル。
- 両端を含む。`from` 側から順に配置する。
- bounds: `min` .. `max`。

---

## 図形 Operation

### 円・球の判定基準

すべての円・球は次の基準で統一する（WorldEdit の `//cyl` / `//hcyl` と同等）。

- **solid(r)**: 中心からの距離の 2 乗が `(r + 0.5)²` 未満のセル集合。
  - 円: `dx² + dz² < (r + 0.5)²`（`axis: "y"` の場合。他の軸では対応する 2 軸）
  - 球: `dx² + dy² + dz² < (r + 0.5)²`
- **hollow(r)**: `solid(r)` のうち、外側に接するセル（円では 4 近傍、球では 6 近傍のいずれかが `solid(r)` に含まれないセル）。常に 1 ブロック厚で、隙間のない（斜め方向を含めて連結した）リング・殻になる。`r == 1` のときは `solid(1)` から中心 1 セルを除いたもの。

`r` は 1 以上の整数。`dx, dy, dz` は中心からの整数オフセット。

半径 6 の例（`#` が hollow、`.` が solid のみ）:

```text
    #####
  ##.....##
 #.........#
 #.........#
#...........#
#...........#
#...........#
#...........#
#...........#
 #.........#
 #.........#
  ##.....##
    #####
```

### circle

円を生成する。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `center` | Pos | ✓ | | 中心 |
| `radius` | integer ≥ 1 | ✓ | | 半径 |
| `axis` | `"x"` / `"y"` / `"z"` | | `"y"` | 円が乗る平面の法線。`"y"` なら水平な円 |
| `mode` | `"hollow"` / `"solid"` | | `"hollow"` | `hollow`: リング。`solid`: 円盤 |

```json
{ "type": "circle", "center": [0, 0, 0], "radius": 6, "mode": "solid", "block": "minecraft:stone_bricks" }
```

- `axis: "y"`: XZ 平面、`center.y` の高さ。`axis: "x"`: YZ 平面。`axis: "z"`: XY 平面。
- 配置順は、平面の 2 軸を（Y があれば Y を外側、なければ Z を外側）昇順に走査する。
- bounds: 平面上で `center ± radius`、法線方向は `center` の 1 段。

### cylinder

円柱を生成する。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `center` | Pos | ✓ | | 底面の中心 |
| `radius` | integer ≥ 1 | ✓ | | 半径 |
| `height` | integer ≥ 1 | ✓ | | 高さ |
| `axis` | `"x"` / `"y"` / `"z"` | | `"y"` | 円柱の軸。`center` から軸の正方向へ `height` 段 |
| `mode` | `"hollow"` / `"solid"` | | `"hollow"` | `hollow`: 側面のみ（底・天井なし）。`solid`: 充填 |

```json
{ "type": "cylinder", "center": [0, 0, 0], "radius": 8, "height": 20, "mode": "hollow", "palette": "stone_wall" }
```

- `axis` 方向に `circle` を `height` 枚重ねたものと等価。底や天井が必要な場合は `circle` の `solid` を別に置く。
- 配置順は軸方向の昇順を外側とし、各段は `circle` と同じ。
- bounds: 平面上で `center ± radius`、軸方向は `center` から `height − 1` まで。

### sphere

球を生成する。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `center` | Pos | ✓ | | 中心 |
| `radius` | integer ≥ 1 | ✓ | | 半径 |
| `mode` | `"hollow"` / `"solid"` | | `"hollow"` | `hollow`: 球殻。`solid`: 充填 |

```json
{ "type": "sphere", "center": [0, 20, 0], "radius": 6, "mode": "hollow", "block": "minecraft:deepslate_tiles" }
```

- ドーム（半球）が必要な場合は、`sphere` の後に `fill` で下半分を `minecraft:air` にする。
- 配置順は y → z → x の昇順。
- bounds: `center ± radius`。

---

## 構造 Operation

構造 Operation は `block` / `palette` を持たず、`operations` にネストした Operation を持つ。
ネストした Operation には任意の Operation（構造 Operation を含む）を置ける。ネスト深さの上限は 8（トップレベルを深さ 1 とする）。

ネストした Operation 内の Palette は、それぞれの配置で独立に乱数を消費する。したがって鏡像や繰り返しの各コピーで Palette の選択結果は異なる（結果は seed により再現可能）。

### mirror

ネストした Operation を実行し、さらに指定した平面で鏡像化したものも配置する。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `axis` | `"x"` / `"y"` / `"z"` | ✓ | | 反転する軸 |
| `at` | number（整数または `.5`） | ✓ | | 鏡面の位置（`axis` 座標）。`.5` を指定するとブロックの境界を鏡面にできる |
| `keepOriginal` | boolean | | `true` | `true`: 元と鏡像の両方を配置。`false`: 鏡像のみ |
| `operations` | array | ✓ | | ネストした Operation（1 件以上） |

```json
{
  "type": "mirror",
  "axis": "x",
  "at": 0,
  "operations": [
    { "type": "wall", "from": [2, 0, -5], "to": [8, 0, -5], "height": 4, "palette": "stone_wall" }
  ]
}
```

- 座標変換: `axis: "x"` なら `x' = 2 × at − x`（y, z も同様）。`at` が `.5` のとき、`x = at − 0.5` のブロックは `x = at + 0.5` に写る。
- 実行順: `keepOriginal: true` のとき、まずネストした Operation を元の座標で先頭から順にすべて実行し、その後に鏡像として先頭から順にすべて実行する。
- ブロック状態の変換: 鏡像側では、方向を持つプロパティを次のとおり反転する。

| `axis` | 変換 |
|---|---|
| `x` | `facing`: `east` ↔ `west` |
| `z` | `facing`: `north` ↔ `south` |
| `y` | `facing`: `up` ↔ `down`、`half`: `top` ↔ `bottom`、`type`: `top` ↔ `bottom`（スラブ） |

- 上表以外のプロパティ（`shape`, `hinge`, `rotation`, `axis` など）は変換しない。階段の角（`shape`）やドアの蝶番（`hinge`）は鏡像側で意図と異なる場合があるため、必要なら鏡像側を個別の `set` で上書きする。
- bounds: ネストした Operation の bounds の合成と、その鏡像の合成の和（`keepOriginal: false` なら鏡像のみ）。

### repeat

ネストした Operation を一定間隔で繰り返し配置する。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `count` | integer 1〜512 | ✓ | 繰り返し回数（元の位置を含む） |
| `offset` | `[dx, dy, dz]` | ✓ | 1 回ごとの平行移動量 |
| `operations` | array | ✓ | ネストした Operation（1 件以上） |

```json
{
  "type": "repeat",
  "count": 4,
  "offset": [3, 0, 0],
  "operations": [
    { "type": "set", "position": [1, 2, 0], "block": "minecraft:glass_pane" },
    { "type": "set", "position": [1, 3, 0], "block": "minecraft:glass_pane" }
  ]
}
```

- `i = 0, 1, …, count − 1` について、ネストした Operation を `offset × i` だけ平行移動して先頭から順に実行する。
- `offset` が `[0, 0, 0]` でも検証エラーにはならないが、同じ位置に `count` 回上書きするだけになる。
- `mirror` を `repeat` の中に置いた場合、鏡面 (`at`) も一緒に平行移動する。
- bounds: `i = 0` と `i = count − 1` の bounds の和。

---

## 将来対応（v0.2 以降）

以下は formatVersion 1 の範囲で追加予定の Operation で、本書の対象外である。

- 編集: `replace`, `translate`, `copy`, `rotate`
- 高レベル建築: `pillar`, `arch`, `stairs`, `spiral_stairs`, `roof`, `window`, `doorway`, `bridge`, `room`, `tower`
- 部品: `component`
