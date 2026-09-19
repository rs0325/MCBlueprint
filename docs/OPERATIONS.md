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
| 構造 | [`translate`](#translate) | ネストした Operation を平行移動 |
| 構造 | [`rotate`](#rotate) | ネストした Operation を鉛直軸まわりに 90° 単位で回転 |
| 編集 | [`replace`](#replace) | 範囲内の一致するブロックを置き換え |
| 編集 | [`copy`](#copy) | 範囲の現在の内容を別の場所へ複製 |
| 建築 | [`stairs`](#stairs) | 直進階段（頭上空間と到着口を自動確保） |
| 建築 | [`spiral_stairs`](#spiral_stairs) | 螺旋階段 |
| 建築 | [`roof`](#roof) | 切妻・寄棟屋根 |
| 建築 | [`pillar`](#pillar) | 柱（台座・笠付き） |
| 建築 | [`doorway`](#doorway) | 出入口（開口 + ドア） |
| 建築 | [`window`](#window) | 窓（接続済みガラス板） |
| 建築 | [`arch`](#arch) | アーチ（半円 / 尖頭 / 平）と開口 |
| 部品 | [`component`](#component) | `components/<name>.json` の部品を配置 |

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
- ブロック状態の変換: 鏡像側では、向きを持つプロパティを次のとおり書き換える（[座標変換とブロック状態](#座標変換とブロック状態)）。

| `axis` | 変換 |
|---|---|
| `x` | `facing`: `east` ↔ `west`、接続プロパティ `east` ↔ `west` |
| `z` | `facing`: `north` ↔ `south`、接続プロパティ `north` ↔ `south` |
| `y` | `facing`: `up` ↔ `down`、`half`: `top` ↔ `bottom`、`type`: `top` ↔ `bottom`（スラブ） |
| 共通 | `shape`: `inner_left` ↔ `inner_right`、`outer_left` ↔ `outer_right`（階段）、`hinge`: `left` ↔ `right`（ドア） |

- 看板・旗の `rotation`（0〜15）は変換しない。
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

### translate

ネストした Operation を平行移動して配置する。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `offset` | `[dx, dy, dz]` | ✓ | 移動量 |
| `operations` | array | ✓ | ネストした Operation（1 件以上） |

```json
{ "type": "translate", "offset": [20, 0, 0], "operations": [ { "type": "box", "from": [0, 0, 0], "to": [4, 3, 4], "block": "stone" } ] }
```

- 同じ部品を離れた場所に置くときに使う。`repeat` の `count: 1` と同じだが意図が明確になる。
- bounds: ネストした Operation の bounds を移動したもの。

### rotate

ネストした Operation を、`center` を通る鉛直軸まわりに回転して配置する。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `angle` | `90` / `180` / `270` | ✓ | 上から見て時計回りの角度 |
| `center` | Pos | ✓ | 回転軸が通る位置（`y` は使わない） |
| `operations` | array | ✓ | ネストした Operation（1 件以上） |

```json
{
  "type": "rotate",
  "angle": 90,
  "center": [0, 0, 0],
  "operations": [ { "type": "wall", "from": [1, 0, 0], "to": [5, 0, 0], "height": 3, "block": "stone" } ]
}
```

- 座標変換（90° 時計回り、`center = (cx, cz)`）: `x' = cx − (z − cz)`, `z' = cz + (x − cx)`。東 → 南 → 西 → 北の順に回る。
- 回転の中心はブロックの中心。偶数幅の構造を中心対称に回したい場合は `translate` と組み合わせる。
- ブロック状態は `facing`、`axis`、接続プロパティが回転に追従する（[座標変換とブロック状態](#座標変換とブロック状態)）。
- 4 方向に同じ部品を置くには、元 + `rotate` 90 / 180 / 270 の 4 つを並べる。
- bounds: ネストした Operation の bounds を回転したもの。

---

## 編集 Operation

編集 Operation は、その時点までに配置された結果（先行する Operation の出力）を読んで動作する。配列内での順序が結果を決める。

### replace

範囲内で、一致するブロックを別のブロックへ置き換える。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `from`, `to` | Pos | ✓ | 範囲（両端含む） |
| `match` | string または string の配列 | ✓ | 置き換え対象のブロック指定。プロパティを省略した場合は ID だけで一致、書いたプロパティは値まで一致が必要 |
| `block` / `palette` | | ✓（一方） | 置き換え後のブロック |

```json
{ "type": "replace", "from": [0, 0, 0], "to": [10, 8, 10], "match": "minecraft:stone_bricks", "palette": "stone_wall", "comment": "外壁に苔を混ぜる" }
```

- 範囲内の未設定セルは `minecraft:air` として扱う。`"match": "air"` で隙間を埋められる。
- `"match": "oak_stairs"` は向きに関係なくすべての樫の階段に一致し、`"match": "oak_stairs[facing=east]"` は東向きだけに一致する。
- Palette を指定した場合は置き換えるセルごとに乱数を消費する。
- bounds: `min` .. `max`。

### copy

範囲の現在の内容を、`offset` だけずらした位置へ複製する。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `from`, `to` | Pos | ✓ | コピー元の範囲（両端含む） |
| `offset` | `[dx, dy, dz]` | ✓ | コピー先への移動量 |

```json
{ "type": "copy", "from": [0, 0, 0], "to": [8, 4, 8], "offset": [0, 5, 0], "comment": "1 階をそのまま 2 階に" }
```

- コピーされるのは範囲内で配置済みのセルだけ。未設定セルはコピー先を上書きしない（明示的に置いた `minecraft:air` はコピーされる）。
- コピー元は実行時点で読み取ってから書き込むため、コピー先がコピー元と重なっていても連鎖しない。
- ブロック状態は変換しない（向きはそのまま）。回転・反転したコピーが必要なら、元を `rotate` / `mirror` の中に入れて 2 回書く。
- bounds: コピー元とコピー先の和。

---

## 高レベル建築 Operation

建築でよく使う部品を 1 つの Operation で書けるようにしたもの。内部で基本 Operation の列へ展開して実行するため、`mirror` / `repeat` / `rotate` の中でも使え、bounds も展開結果から求まる。

`block` に階段ブロック（`*_stairs`）を指定すると、`facing` / `half` を省略した場合に向きが自動で設定される（`stairs` / `spiral_stairs` / `roof`）。`palette` を使う場合は向きを自動設定できないので、Palette 内の階段ブロックに向きを書く。

### stairs

直進階段。各段の上に `headroom` 分の空気を確保し、最後の段の先（到着口）の頭上も空ける。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `start` | Pos | ✓ | | 1 段目のブロック（下の階の床の 1 つ上） |
| `direction` | `north` / `south` / `east` / `west` | ✓ | | 登る方向 |
| `height` | integer ≥ 1 | ✓ | | 段数 = 登る高さ。最後の段の上面が上の階の床の上面と同じ高さになる |
| `width` | integer ≥ 1 | | `1` | 幅。`direction` を向いて右側へ広がる |
| `headroom` | integer ≥ 2 | | `3` | 各段の上に確保する空気の高さ |
| `base` | ブロック | | | 段の下を埋めるブロック（省略時は空洞のまま） |
| `block` / `palette` | | ✓（一方） | | 段のブロック |

```json
{ "type": "stairs", "start": [2, 1, 1], "direction": "south", "height": 4, "block": "oak_stairs", "base": "oak_planks" }
```

- `i` 段目は `start + direction × i + (0, i, 0)`。段の上 `headroom` ブロックと、到着口（`start + direction × height` の高さ `start.y + height` から `headroom` ブロック）を `minecraft:air` にする。上の階の床（`y = start.y + height − 1`）は最後の `headroom` 段分だけ自動的に開く。
- 途中に壁や梁があっても頭上分は削られる。削りたくない場合は経路を変える。
- 折り返し階段は、`stairs` を 2 つと踊り場（`floor`）で組み合わせる。

### spiral_stairs

中心軸のまわりを 1 段ごとに 1 ブロック上がる螺旋階段。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `center` | Pos | ✓ | | 軸の位置（最下段の高さ） |
| `radius` | integer 1〜8 | ✓ | | 外周の半径 |
| `height` | integer ≥ 1 | ✓ | | 段数 = 登る高さ |
| `turn` | `clockwise` / `counterclockwise` | | `clockwise` | 上から見た回転方向。東 → 南 → 西 → 北が時計回り |
| `headroom` | integer ≥ 2 | | `3` | 各段の上に確保する空気の高さ |
| `column` | ブロック | | | 中心軸に立てるブロック |
| `block` / `palette` | | ✓（一方） | | 段のブロック |

```json
{ "type": "spiral_stairs", "center": [0, 0, 0], "radius": 2, "height": 15, "block": "stone_bricks", "column": "stone_bricks" }
```

- 段は半径 `radius` のリングのセルを角度順に 1 つずつ使う（東から開始）。踏面はそのセルと、角度が最も近い内側のセル（軸を除く）を合わせた扇形で、同じ (x, z) は 1 周に 1 回しか使われない（段が縦に重ならない）。
- 1 周に必要な段数はリングのセル数（半径 1: 8、半径 2: 12、半径 3: 16）。1 周でこの高さを登る。
- 階段ブロックを使うと進行方向を `facing` にするが、斜めに進む段では見た目が崩れやすい。通常ブロックまたはハーフブロックのほうが無難。

### roof

矩形の上に階段ブロックで屋根を架ける。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `from`, `to` | Pos | ✓ | | 軒の高さの矩形（壁の外周と同じ範囲。`from.y == to.y`） |
| `style` | `gable` / `hip` | | `gable` | 切妻 / 寄棟（正方形なら方形＝ピラミッド） |
| `ridge` | `x` / `z` | | 長い辺 | 切妻の棟の向き |
| `overhang` | integer ≥ 0 | | `1` | 軒の張り出し |
| `gable` | ブロック | | | 切妻の妻壁（三角部分）を埋めるブロック。省略時は空いたまま |
| `ridgeBlock` | ブロック | | 階段なら対応するハーフブロック | 棟（最上段）のブロック |
| `block` / `palette` | | ✓（一方） | | 斜面のブロック |

```json
{ "type": "roof", "from": [0, 5, 0], "to": [10, 5, 8], "block": "dark_oak_stairs", "gable": "spruce_planks" }
```

- 1 段ごとに内側へ 1 ブロック寄せながら 1 段上がる。斜面の階段は内側（棟）を向く。
- 幅が奇数なら最上段が 1 列の棟になり `ridgeBlock` を置く。偶数なら最上段は向かい合う 2 列の階段で終わる。
- `hip` の四隅は `shape=outer_left` / `outer_right` の階段で置く（Minecraft が隣接ブロックから求める形と同じ。角は z 方向の `facing` を持ち、その前にある x 方向の辺の向きで左右が決まる）。最上段が向かい合う 2 列で終わる層は四辺がそろわないため `straight` のままにする。`palette` の場合は各ブロックが階段とは限らないため `shape` を付けない。
- 2 つの `roof` を重ねて L 字の屋根を作る場合、谷（`inner_*`）は自動では付かない。必要なら `set` で補正する。
- `rotate` の中では、角の階段が同じ形の別表現（`facing=east,shape=outer_left` と `facing=north,shape=outer_right` は同じ形）になることがある。見た目は変わらない。
- `gable` は `from` / `to` の壁の位置（張り出しの内側）に三角形の壁を作る。

### pillar

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `position` | Pos | ✓ | | 最下段 |
| `height` | integer ≥ 1 | ✓ | | 高さ |
| `base` | ブロック | | | 最下段を置き換えるブロック |
| `cap` | ブロック | | | 最上段を置き換えるブロック（`height` が 2 以上のとき） |
| `block` / `palette` | | ✓（一方） | | 柱のブロック |

```json
{ "type": "pillar", "position": [0, 0, 0], "height": 5, "block": "stone_bricks", "base": "chiseled_stone_bricks", "cap": "stone_brick_slab" }
```

### doorway

壁に出入口を空け、必要ならドアを付ける。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `position` | Pos | ✓ | | 開口の左下（壁の中のブロック） |
| `facing` | `north` / `south` / `east` / `west` | ✓ | | ドアの `facing`（外から中を向く方向。北の壁なら `south`） |
| `width` | integer ≥ 1 | | `1` | 幅。`position` から正の方向（東または南）へ広がる。ドアを付ける場合は 1 または 2 |
| `height` | integer ≥ 2 | | `2` | 高さ |
| `door` | ブロック | | | ドアのブロック（`*_door`）。省略時は開口だけ |
| `arch` | object | | | 頭上をアーチにする。`{ "style": "round" \| "pointed" \| "flat", "block": 縁のブロック, "trim": 角の階段 }`（[arch](#arch) 参照） |

```json
{ "type": "doorway", "position": [5, 1, 0], "facing": "south", "width": 2, "door": "oak_door" }
```

- 開口を `minecraft:air` にしてから、ドアを `half=lower` / `upper` の 2 段で置く。幅 2 のときは両開きになるよう `hinge` を左右に振り分ける。
- `arch` を付けると、`height` 段の開口の最上段を起拱点として上にアーチの曲線を足し、周りを `arch.block` で縁取る（開口は `height` + アーチの高さになる）。庇など他の装飾は別の Operation で足す。

### window

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `position` | Pos | ✓ | | 窓の左下 |
| `axis` | `x` / `z` | ✓ | | 壁が伸びる方向 |
| `width` | integer ≥ 1 | | `1` | 幅（`axis` の正方向へ） |
| `height` | integer ≥ 1 | | `1` | 高さ |
| `block` | ブロック | | `glass_pane` | 窓のブロック |
| `arch` | object | | | 上部をアーチ窓にする。`{ "style", "block": 縁のブロック, "trim" }`。曲線部分も `block`（ガラス板）で埋める（[arch](#arch) 参照） |

```json
{ "type": "window", "position": [2, 2, 0], "axis": "x", "width": 2, "height": 2 }
```

- ガラス板・鉄格子・フェンス・壁ブロックのときは、`axis` 方向の接続プロパティ（`east` / `west` または `north` / `south`）を自動で `true` にする。明示した値は変えない。
- `glass` のような完全ブロックはそのまま置く。

### arch

開口の周りに厚さ 1 の縁（アーチ）を作り、開口を空ける。門・アーチ窓・回廊・橋脚に使う。`doorway` / `window` の `arch` キーからも内部で使われる。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `position` | Pos | ✓ | | 開口の左下（縁ではなく開口の最初のブロック） |
| `axis` | `x` / `z` | | `x` | 壁が伸びる方向（開口はこの方向へ `width` 分広がる） |
| `width` | integer ≥ 1 | ✓ | | 開口の幅。奇数を推奨（偶数は頂点が 2 ブロックになる） |
| `height` | integer ≥ 1 | ✓ | | 開口の高さ（床から頂点の空気まで）。`style` と `width` で決まる最小値以上 |
| `style` | `round` / `pointed` / `flat` | | `round` | 半円 / 尖頭 / 平（水平のまぐさ） |
| `depth` | integer ≥ 1 | | `1` | 奥行き（`axis` と直交する正の方向へ） |
| `trim` | ブロック | | | 開口の内側の角に置くブロック。`*_stairs` なら `half=top` と縁側を向く `facing`、`*_slab` なら `type=top` を自動設定 |
| `fill` | ブロック | | | 開口を埋めるブロック（アーチ窓のガラス板など）。省略時は `hollow` に従う |
| `hollow` | boolean | | `true` | `true` なら開口を `minecraft:air` にする。`false` なら縁だけ置く（壁の装飾） |
| `block` / `palette` | | ✓（一方） | | 縁のブロック |

```json
{ "type": "arch", "position": [3, 1, 0], "axis": "x", "width": 3, "height": 4, "style": "round", "block": "stone_bricks", "trim": "stone_brick_stairs" }
```

- 開口は幅 `width` × 高さ `height` の矩形の上部を曲線で狭めた形。上から `rise + 1` 段が曲線部分（最下段の起拱点は全幅）、その下が直線部分。縁は開口に上下左右で接するブロック（床より下は除く）。
- `rise`（起拱点から頂点までの段数）: `round` は直径 `width` の円の上半分（`circle` と同じ判定）、`pointed` は起拱点の外側を中心とする半径 `width` の 2 つの弧、`flat` は 0。`height` は `rise + 1` 以上が必要（不足するとエラー）。

| `width` | 3 | 5 | 7 | 9 |
|---|---|---|---|---|
| `round` の rise / 各段の幅 | 1 / 3,3 | 2 / 5,5,3 | 3 / 7,7,5,3 | 4 / 9,9,9,7,5 |
| `pointed` の rise / 各段の幅 | 2 / 3,3,1 | 4 / 5,5,5,3,1 | 6 / 7,7,7,5,5,3,1 | 8 / 9,9,9,9,7,7,5,3,1 |

- `trim` は開口の中で「上が縁、左右のどちらか一方が縁」のブロック（角）に置く。幅 3 の `round` なら最上段の両端に逆さ階段が入り、古典的なアーチになる。
- 展開順: 縁 → 開口（`air` または `fill`）→ `trim`。既にある壁の上に書けば縁が壁を置き換え、開口が空く。
- 支持チェックの対象になるブロック（ランタンなど）を縁の上に置く場合は、縁が完全ブロックであることを確認する。

### component

`components/<name>.json` に書いた部品を配置する（[FORMAT.md §11](FORMAT.md#11-部品component)）。

| キー | 型 | 必須 | 既定値 | 説明 |
|---|---|---|---|---|
| `name` | string | ✓ | | 部品名（ファイル名から `.json` を除いたもの。`^[a-z0-9_]+$`） |
| `position` | Pos | ✓ | | 部品の原点を置く位置 |
| `rotation` | `0` / `90` / `180` / `270` | | `0` | 部品の原点を軸に上から見て時計回りに回転 |

```json
{ "type": "component", "name": "medieval_window", "position": [14, 2, 2], "rotation": 90 }
```

- 部品の Operation を、回転 → 平行移動の変換で実行する。`facing` / `axis` / 接続プロパティは自動で回る。
- 部品の Palette は部品内で優先され、ない名前は呼び出し元の Palette を使う。
- bounds: 部品の Operation の bounds の合成を変換したもの。

---

## 座標変換とブロック状態

`mirror` / `rotate`（および `repeat` / `translate` の平行移動）は、位置だけでなくブロック状態の向きも変換する。

| プロパティ | 変換 |
|---|---|
| `facing`（`north` / `south` / `east` / `west` / `up` / `down`） | 方向ベクトルを変換した先の方向 |
| `axis`（原木など。`x` / `y` / `z`） | 軸を変換した先の軸 |
| 接続プロパティ `north` / `south` / `east` / `west` / `up` / `down`（板ガラス・フェンス・壁など） | プロパティ名の方向を変換して付け替え |
| `half` / `type` の `top` ↔ `bottom` | Y 軸を反転する変換（`mirror` の `axis: "y"`）のときのみ |
| `shape` の `inner_left` ↔ `inner_right`, `outer_left` ↔ `outer_right`、`hinge` の `left` ↔ `right` | 鏡像（反転を含む変換）のときのみ。回転では変わらない |
| `rotation`（看板・旗の 0〜15）、レール `shape` など | 変換しない |

---

## 将来対応

以下は formatVersion 1 の範囲で追加予定の Operation で、本書の対象外である。

- 高レベル建築: `arch`, `bridge`, `room`, `tower`
