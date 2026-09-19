# アーキテクチャ

MCBlueprint の内部構成と各モジュールの責務を定義する。実装は本書に従う。
Blueprint JSON の仕様は [FORMAT.md](FORMAT.md)、Operation の仕様は [OPERATIONS.md](OPERATIONS.md) を参照。

## 1. 処理フロー

```text
blueprints/house.json
        │
        ▼
   Loader        JSON → Blueprint モデル（ブロック文字列の正規化、Operation オブジェクト化）
        │
        ▼
   Validator     JSON Schema 検証 + 意味検証（ブロック ID、Palette 参照、上限 …）
        │
        ▼
   Generator     Operation を順に実行し BlockVolume を組み立てる
        │
        ▼
   BlockVolume   (x, y, z) → BlockState の疎な集合
        │
        ▼
   Exporter      Sponge Schematic v2 (.schem) へ書き出し
        │
        ▼
output/house.schem
```

AI エージェントは Blueprint JSON を書くところまでを担当し、Minecraft 固有のデータ形式は Validator / Generator / Exporter が担当する。この境界を崩さない。

## 2. モジュール構成

```text
src/mcblueprint/
├─ __init__.py          __version__
├─ __main__.py          python -m mcblueprint
├─ cli.py               argparse。validate / build
├─ errors.py            BlueprintError, ValidationError
├─ loader.py            JSON 読み込み → Blueprint
├─ validator.py         Schema 検証 + 意味検証
├─ generator.py         Blueprint → BlockVolume
├─ volume.py            BlockVolume
├─ blockdata.py         同梱ブロックデータの読み込み
├─ components.py        部品ファイルの探索・読み込み・循環検出
├─ support.py           支持チェック
├─ preview.py           PNG プレビュー（任意依存 Pillow）
├─ model/
│  ├─ vec.py            Vec3, AABB
│  ├─ block.py          BlockState
│  ├─ palette.py        Palette, PaletteEntry
│  └─ blueprint.py      Blueprint
├─ operations/
│  ├─ base.py           Operation, BlockSpec, ExecutionContext
│  ├─ transform.py      Transform（平行移動・反転・回転とブロック状態の変換）
│  ├─ nested.py         mirror / repeat / translate / rotate の共通基底
│  ├─ registry.py       type 文字列 → Operation クラス
│  ├─ set.py fill.py box.py wall.py floor.py line.py
│  ├─ circle.py cylinder.py sphere.py
│  ├─ mirror.py repeat.py translate.py rotate.py
│  ├─ replace.py copy.py
│  ├─ composite.py      高レベル Operation の基底（基本 Operation の列へ展開）
│  ├─ stairs.py spiral_stairs.py roof.py pillar.py doorway.py window.py
│  └─ component.py      部品の配置
├─ exporters/
│  ├─ base.py           Exporter
│  ├─ schem.py          Sponge Schematic v2
│  └─ litematic.py      Litematica
├─ schema/
│  └─ blueprint.schema.json   パッケージ同梱の JSON Schema（リポジトリの schema/ と同一）
└─ data/
   ├─ versions.json     { "<minecraftVersion>": { "dataVersion": <int> } }
   ├─ colors.json       プレビュー用の近似色
   └─ blocks/<minecraftVersion>.json
```

依存の向き: `cli` → `loader` / `validator` / `generator` / `exporters` → `operations` / `volume` / `model` / `blockdata`。下位モジュールは上位を import しない。

## 3. データモデル（`model/`）

### Vec3

不変の整数 3 次元ベクトル。`+`, `-`, スカラー倍、要素ごとの `min` / `max`。`dict` のキーにできる（hashable）。

### AABB

両端を含む直方体 `min: Vec3`, `max: Vec3`。`size`（各辺の長さ）、`volume`、`union(other)`、`contains(pos)`。

### BlockState

```python
@dataclass(frozen=True)
class BlockState:
    id: str                       # "minecraft:oak_stairs"（名前空間付き）
    properties: tuple[tuple[str, str], ...]   # 名前順にソート済み
```

- `BlockState.parse(text)`: [FORMAT.md §4](FORMAT.md#4-ブロック指定) の文法で解析し正規化する。文法違反は `BlueprintError`。
- `to_string()`: 正規化済み文字列。
- `with_defaults(block_data)`: 未指定プロパティをデフォルト値で補完した `BlockState` を返す（Exporter が使う）。
- `with_property(name, value)`: プロパティを差し替えた新しい `BlockState`（`mirror` が使う）。

### Palette / PaletteEntry

`Palette(name, entries)`、`PaletteEntry(block: BlockState, weight: float)`。`Palette.choose(rng)` が重み付きで 1 つ選ぶ（`random.Random.choices` を使用）。

### Blueprint

トップレベル項目を保持する dataclass。`operations: list[Operation]`、`palettes: dict[str, Palette]`。既定値の補完（`seed = 0`, `origin = Vec3(0, 0, 0)`）はここで行う。

## 4. Loader（`loader.py`）

`load_blueprint(path) -> Blueprint`

1. ファイルを UTF-8 で読み、`json.loads` する。構文エラー・ファイル未存在は `BlueprintError`。
2. Palette、Operation（`registry.build_operation`）をオブジェクト化する。

Loader は Schema 検証済みのデータを前提とし、それでも見つかった形状の問題は `BlueprintError` で報告する。CLI は `validator.validate()` → `load_blueprint()` の順に呼ぶ（Validator が内部で Loader を使って `bounds()` を求めるため、逆方向の依存は持たない）。

`load_blueprint_dict(data: dict) -> Blueprint` も提供し、テストや将来の API 利用から使えるようにする。

## 5. Operation 実行モデル（`operations/base.py`）

```python
class Operation(ABC):
    type: ClassVar[str]

    @classmethod
    def from_dict(cls, data: dict, path: str) -> Self: ...
    def bounds(self) -> AABB: ...
    def apply(self, ctx: ExecutionContext) -> None: ...
```

- `path` は `operations[3].operations[0]` のような JSON パスで、エラー報告に使う。
- `bounds()` は実行せずに範囲を返す。Validator の `size` / 最大寸法チェックと、将来の `inspect` が使う。

### BlockSpec

`block: BlockState | None` と `palette: str | None` のどちらか一方を持つ。配置系 Operation は `from_dict` で共通項目から生成する。

### Transform（`operations/transform.py`）

座標変換。符号付き置換行列とオフセットの合成 `p' = rows · p + offset` で表し、平行移動・軸反転・鉛直軸まわりの 90° 回転とそれらの合成を扱う。

```python
@dataclass(frozen=True)
class Transform:
    rows: Matrix        # 3×3、各行に ±1 が 1 つ
    offset: Vec3

    @classmethod identity() / translation(offset) / mirror(axis, at) / rotation(angle, center)
    def apply(self, pos: Vec3) -> Vec3
    def apply_state(self, state: BlockState) -> BlockState   # facing / axis / 接続 / half / type / shape / hinge
    def then(self, outer: Transform) -> Transform            # self を適用してから outer を適用する合成
    def bounds(self, box: AABB) -> AABB
```

- `mirror(axis, at)` は該当軸の対角成分を −1、オフセットを `2 × at`（`.5` でも整数）にする。
- `rotation(angle, center)` は上から見て時計回り。90° は `(x, z) → (−z, x)` で、`offset = center − rows · center` により中心を固定する。
- 合成順序は「内側の Operation の座標 → 内側の Transform → 外側の Transform」。`repeat` の中の `mirror` では、鏡面の位置も `repeat` の平行移動を受ける。
- `apply_state` は方向を持つプロパティを行列で写す（`docs/OPERATIONS.md` の「座標変換とブロック状態」）。`shape` / `hinge` の左右入れ替えは行列式が負（鏡像）のときだけ行う。

### ExecutionContext

```python
class ExecutionContext:
    volume: BlockVolume
    rng: random.Random
    palettes: dict[str, Palette]
    transform: Transform
    depth: int

    def place(self, pos: Vec3, spec: BlockSpec) -> None
    def child(self, transform: Transform) -> ExecutionContext
```

- `place`: `spec` が Palette なら `rng` で 1 つ選び、`transform.apply(pos)` と `transform.apply_state(state)` を適用して `volume.set` する。配置系 Operation はセルを列挙して `place` を呼ぶだけにする。
- `child`: `transform` を合成し `depth + 1` にした子コンテキスト。`volume` / `rng` / `palettes` は共有する。
- `rng` は Blueprint 全体で 1 本。Palette 解決時のみ消費する。

### CompositeOperation（`operations/composite.py`）

高レベル建築 Operation の基底。`expand()` が基本 Operation の JSON（dict）の列を返し、registry で通常どおり組み立てる。`bounds()` は展開結果の合成、`apply()` は展開結果を同じコンテキストで順に実行する（ネスト深さは増えない）。展開結果の JSON パスは `operations[3]<stairs>` のように元の Operation を示す。

### ComponentOperation（`operations/component.py`, `components.py`）

`components/<name>.json` を読み、その Operation 群を回転 → 平行移動の Transform と部品ローカルの Palette（`ExecutionContext.child(transform, palettes=...)` で呼び出し元の Palette を ChainMap で覆う）で実行する。探索パスは `components.component_search_paths()` の contextvar で与え、`load_blueprint(path)` と CLI が「Blueprint の階層の `components/` → cwd の `components/`」を設定する。循環参照は読み込み中の名前のスタック（contextvar）で検出する。Validator は部品ファイルに対して部品用 Schema（Blueprint Schema から `minecraftVersion` / `origin` / `size` / `seed` を除いたもの）と意味検証を行い、`operations[3]<name>.…` のパスで報告する。

### registry

`OPERATIONS: dict[str, type[Operation]]` と `build_operation(data, path) -> Operation`。未知の `type` は Schema 検証で弾かれる前提だが、registry でも `BlueprintError` にする。

## 6. Generator（`generator.py`）

```python
def generate(blueprint: Blueprint, *, seed: int | None = None) -> BlockVolume
```

`ExecutionContext` を `Transform.identity()`、`depth = 1` で初期化し、`blueprint.operations` を順に `apply` する。`seed` 引数は CLI の `--seed` による上書き用。

## 7. BlockVolume（`volume.py`）

```python
class BlockVolume:
    def set(self, pos: Vec3, state: BlockState) -> None
    def get(self, pos: Vec3) -> BlockState | None
    def bounds(self) -> AABB | None          # 空なら None
    def count_by_state(self) -> dict[str, int]
    def __len__(self) -> int
    @property
    def palette(self) -> list[BlockState]
```

- 内部は `dict[Vec3, int]`（値は `palette` の index）。同じ `BlockState` は同じ index を共有する。
- `set` は上書き。未設定の位置は `get` で `None`。

## 8. Validator（`validator.py`）

```python
def validate_schema(data: dict) -> list[ValidationError]
def validate(data: dict, *, max_dimension: int = 1024) -> list[ValidationError]
def format_errors(errors: list[ValidationError]) -> str
```

### 手順

1. **Schema 検証**: `jsonschema.Draft202012Validator(schema).iter_errors(data)` で全件収集する。`error.absolute_path` を `operations[4].radius` 形式に整形する。
2. **意味検証**（Schema 検証にエラーがなかった場合のみ）:

| 検証項目 | 内容 |
|---|---|
| `minecraftVersion` | `blockdata.supported_versions()` に含まれる |
| ブロック指定 | 文法、ID の存在、プロパティ名・値の妥当性（`operations` 内と `palettes` 内の両方） |
| `block` / `palette` の排他 | 配置系 Operation で必ず一方のみ |
| Palette 参照 | `palette` で指定した名前が `palettes` に存在する |
| `wall` / `floor` | `from[1] == to[1]` |
| ネスト深さ | ≤ 8 |
| `size` | 全 Operation の `bounds()` の合成が `size` 以下 |
| 最大寸法 | `bounds()` 合成の各辺 ≤ `max_dimension`、体積 ≤ 100,000,000 |

### ValidationError

```python
@dataclass(frozen=True)
class ValidationError:
    path: str              # "operations[4]" / "palettes.stone_wall[1].block" / "" (トップレベル)
    message: str           # 英語。1 文で原因を述べる
    op_type: str | None    # Operation に関するエラーなら type
    value: object | None   # 問題の値
```

### 出力形式

AI が読んで修正しやすいよう、1 エラーを 1 ブロックで表示する。

```text
ERROR operations[4] (cylinder)
  radius must be greater than 0.
  Current value: -5

ERROR palettes.stone_wall[1].block
  Unknown block id.
  Current value: minecraft:stone_brick

2 errors found.
```

- エラーがなければ `Blueprint is valid.`
- 単数形は `1 error found.`

## 8.5 支持チェック（`support.py`）

Validator が扱うのは JSON の妥当性であり、「そのブロックがその場所で物理的に成立するか」は扱わない。代わりに、生成後の `BlockVolume` を走査して代表的な付着ブロックの支持を検査し、**警告**として報告する。

```python
def check_support(volume: BlockVolume) -> list[SupportWarning]
def format_warnings(warnings: list[SupportWarning]) -> str
```

| 対象ブロック | 条件 |
|---|---|
| 吊りランタン（`hanging=true`） | 真上のブロックの下面が支持面（完全ブロック、下付きハーフ、通常向きの階段、鎖、鉄格子、フェンス、壁） |
| 床置きランタン・松明・ろうそく・感圧板 | 真下のブロックの上面が支持面（完全ブロック、上付きハーフ、逆さ階段、閉じた上付きトラップドア、フェンス、壁、8 層の雪） |
| 壁松明・壁看板・壁旗・はしご | `facing` の反対側のブロックの側面が支持面（完全ブロック、または `facing` が一致する階段） |
| ボタン・レバー | `face` に応じて上記の床・天井・壁の条件 |
| ドア | 下段の下が支持面で、上段／下段が同じ `facing` / `hinge` で対になっている |
| ベッド | `facing` 方向に `part` の対（foot / head）がある |
| カーペット・雪 | 真下が空気でない |
| 草花・苗木 | 真下が土系（`grass_block`, `dirt`, `podzol`, `moss_block`, `farmland`, `mud` など） |
| 作物 | 真下が `farmland`（`nether_wart` は `soul_sand`） |

- 「完全ブロック」の判定はブロック名のパターン（`_slab`, `_stairs`, `_pane`, `_door`, `_carpet`, … と液体・植物・装飾の一覧）で「支持しないもの」を列挙し、それ以外を完全ブロックとみなす。Mojang のデータには形状情報がないため、この分類は近似である。
- 未設定セルは `minecraft:air` として扱い、構造の bounds の外（貼り付け先のワールド）は不明として警告しない。
- CLI では `validate` と `build` が生成後にこのチェックを行い、警告があれば表示する。終了コードは `0` のままだが、`--strict` を付けると `1` になり、`build` は書き出さない。

```text
WARNING [3, 5, 2] minecraft:lantern[hanging=true]
  Needs a solid block above; found minecraft:oak_slab[type=top].

1 warning found.
```

## 9. Exporter（`exporters/`）

```python
class Exporter(ABC):
    format: ClassVar[str]        # "schem"
    extension: ClassVar[str]     # ".schem"
    def export(self, volume: BlockVolume, blueprint: Blueprint, out_path: Path) -> None
```

### Sponge Schematic v2（`schem.py`）

`nbtlib` で書き出す。ファイル全体を gzip 圧縮する。

| タグ | 型 | 値 |
|---|---|---|
| ルート | Compound（名前 `Schematic`） | |
| `Version` | Int | `2` |
| `DataVersion` | Int | `blockdata.data_version(minecraftVersion)` |
| `Width` / `Height` / `Length` | Short | バウンディングボックスの X / Y / Z 方向の長さ |
| `Offset` | IntArray[3] | `bounds.min − origin` |
| `Palette` | Compound | 完全な状態文字列 → Int（index） |
| `PaletteMax` | Int | Palette のエントリ数 |
| `BlockData` | ByteArray | 各セルの Palette index を varint で連結 |
| `Metadata` | Compound | `WEOffsetX` / `WEOffsetY` / `WEOffsetZ`（Int、`Offset` と同値） |

- `BlockData` のセル順序は `index = x + z × Width + y × Width × Length`（`x, y, z` は `bounds.min` からの相対）。
- `BlockVolume` に存在しないセルは `minecraft:air` にする（未設定セルがある場合のみ Palette に `minecraft:air` を追加する）。
- Palette の状態文字列は `BlockState.with_defaults()` で全プロパティを補完したもの。
- varint: 7 bit ごとに下位から出力し、続きがあれば最上位 bit を立てる。
- 空の `BlockVolume`（Operation が 1 つもセルを生成しなかった場合）はエラーにする。

### Litematica（`litematic.py`）

Litematica 用の `.litematic`。ルート Compound は無名、gzip 圧縮。1 リージョン（`Main`）のみで、エンティティ・タイルエンティティは含めない。

| タグ | 値 |
|---|---|
| `MinecraftDataVersion` | `blockdata.data_version(minecraftVersion)` |
| `Version` | `6` |
| `Metadata` | `Name` / `Author`（省略時 `MCBlueprint`）/ `Description` / `RegionCount: 1` / `TotalVolume` / `TotalBlocks`（air 以外）/ `EnclosingSize` / `TimeCreated` / `TimeModified` |
| `Regions.Main.Position` | `bounds.min − origin` |
| `Regions.Main.Size` | バウンディングボックスの各辺 |
| `Regions.Main.BlockStatePalette` | `{Name, Properties}` の List。index 0 は必ず `minecraft:air` |
| `Regions.Main.BlockStates` | LongArray。`bits = max(2, ceil(log2(パレット数)))` ビットのエントリを long 境界をまたいで詰める（Litematica の `LitematicaBitArray` 方式） |
| `TileEntities` / `Entities` / `PendingBlockTicks` / `PendingFluidTicks` | 空の List |

- セル順序は `.schem` と同じ `index = x + z × Width + y × Width × Length`。
- 未設定セルは index 0（air）。

### 検証方法

テストでは書き出した `.schem` を `nbtlib.load` で読み戻し、`Width` / `Height` / `Length` / `Offset` / `Palette` / `BlockData` を検証する。手動確認では WorldEdit の `//schem load` → `//paste` を使う。

## 9.5 Preview（`preview.py`, `data/colors.json`）

生成した `BlockVolume` を PNG に描画する。任意依存 `Pillow`（`pip install -e ".[preview]"`）が必要で、未導入なら `BlueprintError` で案内する。

| ビュー | 内容 |
|---|---|
| `top` | 平面図。各 (x, z) の最上段のブロック。高いほど明るい |
| `north` / `south` / `east` / `west` | 立面図。その方向から見て最も手前のブロック |
| `isometric` | 2:1 のピクセルアイソメトリック（南東上空から）。上面・+x 面・+z 面を塗り分け、3 面とも隠れる立方体は描かない |

- 色は `data/colors.json` のキーワード（ブロック ID の部分一致、最長一致）で決める近似。染料名で始まるブロック（`white_concrete` など）は染料の色、テラコッタとステンドグラスは色味を混ぜる。`air` は描かない。
- 出力は `preview/<stem>-<view>.png`（`--scale` は 1 ブロックあたりのピクセル数、既定 8）。

## 10. ブロックデータ（`blockdata.py`, `data/`）

- `data/blocks/<version>.json`:

```json
{
  "minecraft:oak_stairs": {
    "properties": {
      "facing": ["north", "south", "west", "east"],
      "half": ["top", "bottom"],
      "shape": ["straight", "inner_left", "inner_right", "outer_left", "outer_right"],
      "waterlogged": ["true", "false"]
    },
    "default": { "facing": "north", "half": "bottom", "shape": "straight", "waterlogged": "false" }
  }
}
```

- `data/versions.json`: `{ "1.21.11": { "dataVersion": <int> } }`
- 生成は `scripts/generate_block_data.py` で Mojang 公式データジェネレータ（`java -DbundlerMainClass=net.minecraft.data.Main -jar server.jar --reports`）の `reports/blocks.json` と `server.jar` 内 `version.json` の `world_version` から行う。生成結果をコミットし、利用者には Java を要求しない。
- API: `supported_versions() -> list[str]`, `load_block_data(version) -> dict`, `data_version(version) -> int`。読み込みは `functools.cache` で 1 回だけ行う。

## 11. CLI（`cli.py`）

```text
mcblueprint validate <blueprint.json> [--strict] [--max-dimension N]
mcblueprint build    <blueprint.json> [-o DIR|FILE] [--format schem|litematic] [--seed N] [--strict] [--max-dimension N]
mcblueprint inspect  <blueprint.json> [--json] [--max-dimension N]
mcblueprint stats    <blueprint.json> [--json] [--seed N] [--max-dimension N]
mcblueprint preview  <blueprint.json> [-o DIR] [--views top,north,east,isometric] [--scale N] [--seed N]
```

| 終了コード | 意味 |
|---|---|
| `0` | 正常終了 |
| `1` | 検証エラー |
| `2` | 引数・入出力エラー（ファイル未存在、JSON 構文エラー、書き込み失敗など） |

- `build` は必ず `validate` を先に行い、エラーがあれば書き出さずに `1` で終了する。
- `validate` / `build` は生成後に支持チェック（§8.5）を行い、警告を表示する。`--strict` で警告を終了コード `1` として扱う（`build` は書き出さない）。
- 出力先の既定は `output/<入力ファイルの stem>.schem`。`-o` にディレクトリを渡せばその中に既定名で、ファイルパスを渡せばそのパスに書く。ディレクトリは自動作成する。
- 成功時の表示:

```text
Wrote output/house.schem
Bounds: X -5..5  Y 0..7  Z -5..5  (11 x 8 x 11)
Blocks: 612
```

- `inspect` は生成せずに、名前・Minecraft バージョン・`bounds()` の合成による範囲とサイズ・Operation 数（ネスト込みとトップレベル）・Palette 数・seed・origin・宣言 `size`・説明を表示する。`--json` で機械可読な JSON。
- `stats` は生成して、総ブロック数（`minecraft:air` は除外し別枠で表示）、範囲、ブロック状態ごとの個数を多い順に表示する。`--json` で機械可読な JSON、`--seed` で seed を上書き。
- どちらも先に validate を行い、エラーがあれば表示して終了コード `1`。

## 12. エラー型（`errors.py`）

- `BlueprintError(Exception)`: 入出力・構文・内部整合性のエラー。CLI は終了コード `2`。
- `BlueprintValidationError(BlueprintError)`: `errors: list[ValidationError]` を持つ。CLI は `format_errors` で表示し終了コード `1`。

## 13. テスト方針

- 各 Operation: 既知の小さな入力に対するセル集合の完全一致、`bounds()` の一致、`hollow` の内部が空であること。
- Generator: 同じ Blueprint と seed で `BlockVolume` が完全一致すること。
- Validator: 検証項目ごとの異常系と、複数エラーの同時報告。
- Exporter: `nbtlib` での読み戻し。128 種以上の Palette で varint が 2 byte になるケース。
- examples: すべて validate / build が通ること。
- Skill: `.agents/skills/` と `.claude/skills/` の内容が同一であること。
