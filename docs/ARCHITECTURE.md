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
├─ model/
│  ├─ vec.py            Vec3, AABB
│  ├─ block.py          BlockState
│  ├─ palette.py        Palette, PaletteEntry
│  └─ blueprint.py      Blueprint
├─ operations/
│  ├─ base.py           Operation, BlockSpec, Transform, ExecutionContext
│  ├─ registry.py       type 文字列 → Operation クラス
│  ├─ set.py fill.py box.py wall.py floor.py line.py
│  ├─ circle.py cylinder.py sphere.py
│  └─ mirror.py repeat.py
├─ exporters/
│  ├─ base.py           Exporter
│  └─ schem.py          Sponge Schematic v2
├─ schema/
│  └─ blueprint.schema.json   パッケージ同梱の JSON Schema（リポジトリの schema/ と同一）
└─ data/
   ├─ versions.json     { "<minecraftVersion>": { "dataVersion": <int> } }
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

### Transform

座標変換。平行移動と軸反転の合成を表す。

```python
@dataclass(frozen=True)
class Transform:
    flip: tuple[bool, bool, bool]   # 軸ごとの反転
    offset: Vec3                    # 軸ごとの加算

    def apply(self, pos: Vec3) -> Vec3            # 軸ごとに flip なら offset - p、そうでなければ offset + p
    def apply_state(self, state: BlockState) -> BlockState   # flip している軸のプロパティ反転
    def then(self, outer: Transform) -> Transform            # self を適用してから outer を適用する合成
```

- `mirror(axis, at)` は `flip` をその軸だけ `True`、`offset` をその軸だけ `2 × at` にした Transform（`at` が `.5` でも `2 × at` は整数）。`repeat` の平行移動は `flip` がすべて `False` で `offset = offset × i`。
- 合成順序は「内側の Operation の座標 → 内側の Transform → 外側の Transform」。`repeat` の中の `mirror` では、鏡面の位置も `repeat` の平行移動を受ける。
- 同じ軸で鏡像化を 2 回重ねると `flip` は打ち消され、`facing` も元に戻る。プロパティ反転の対応表は [OPERATIONS.md](OPERATIONS.md#mirror) に従う。

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
- `BlockVolume` に存在しないセルは `minecraft:air` にする（Palette に `minecraft:air` を含める）。
- Palette の状態文字列は `BlockState.with_defaults()` で全プロパティを補完したもの。
- varint: 7 bit ごとに下位から出力し、続きがあれば最上位 bit を立てる。
- 空の `BlockVolume`（Operation が 1 つもセルを生成しなかった場合）はエラーにする。

### 検証方法

テストでは書き出した `.schem` を `nbtlib.load` で読み戻し、`Width` / `Height` / `Length` / `Offset` / `Palette` / `BlockData` を検証する。手動確認では WorldEdit の `//schem load` → `//paste` を使う。

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
mcblueprint validate <blueprint.json> [--max-dimension N]
mcblueprint build    <blueprint.json> [-o DIR|FILE] [--format schem] [--seed N] [--max-dimension N]
```

| 終了コード | 意味 |
|---|---|
| `0` | 正常終了 |
| `1` | 検証エラー |
| `2` | 引数・入出力エラー（ファイル未存在、JSON 構文エラー、書き込み失敗など） |

- `build` は必ず `validate` を先に行い、エラーがあれば書き出さずに `1` で終了する。
- 出力先の既定は `output/<入力ファイルの stem>.schem`。`-o` にディレクトリを渡せばその中に既定名で、ファイルパスを渡せばそのパスに書く。ディレクトリは自動作成する。
- 成功時の表示:

```text
Wrote output/house.schem
Bounds: X -5..5  Y 0..7  Z -5..5  (11 x 8 x 11)
Blocks: 612
```

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
